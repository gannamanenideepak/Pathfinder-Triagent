"""Three LangChain agents (SkillMap, TravelBuddy, CourseFinder) with per-session memory."""
import os
import datetime
import requests

from langchain.chat_models import init_chat_model
from langchain.agents import create_agent
from langchain.tools import tool
from langchain_tavily import TavilySearch
from langgraph.checkpoint.memory import InMemorySaver

try:  # .env only matters locally; on Hugging Face keys come from Space secrets
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

MODEL_NAME = os.getenv("MODEL_NAME", "google_genai:gemini-3.5-flash-lite")

model = init_chat_model(MODEL_NAME, api_key=GEMINI_API_KEY)
checkpointer = InMemorySaver()  # shared; each (agent, visitor) gets its own thread_id
TODAY = datetime.date.today().isoformat()


def _search_tool():
    return TavilySearch(max_results=5, search_depth="advanced", tavily_api_key=TAVILY_API_KEY)


# ---------------------------------------------------------------- Agent 1: SkillMap
@tool
def search_jobs(skill: str, location: str) -> list:
    """Search live job listings for a skill in a location (e.g. skill='Data Analyst', location='India')."""
    try:
        response = requests.get(
            "https://jsearch.p.rapidapi.com/search",
            headers={
                "x-rapidapi-key": RAPIDAPI_KEY,
                "x-rapidapi-host": "jsearch.p.rapidapi.com",
            },
            params={"query": f"{skill} jobs in {location}", "page": "1", "num_pages": "1"},
            timeout=30,
        )
        data = response.json()
    except Exception as e:
        return f"Job search failed: {e}"

    jobs = [
        {
            "title": j.get("job_title"),
            "company": j.get("employer_name"),
            "location": j.get("job_city") or j.get("job_country"),
            "apply_link": j.get("job_apply_link"),
        }
        for j in data.get("data", [])[:8]
    ]
    return jobs or f"No jobs found. API message: {data.get('message', data)}"


skill_agent = create_agent(
    model=model,
    tools=[_search_tool(), search_jobs],
    checkpointer=checkpointer,
    system_prompt="""You are a Skill-to-Career Mapping assistant that helps students understand skill demand and find matching job opportunities.
You have access to these tools:
- tavily_search: industry demand, salary insights, and career trends
- search_jobs: real job listings requiring a specific skill
Research the skill the student asks about, then find relevant openings.
Format the answer with clear sections: Market Demand, then Job Openings.
For every job include title, company, location and the apply link as a clickable link.
If the user asks a follow-up about an earlier answer, use the conversation history instead of searching again.""",
)


# ---------------------------------------------------------------- Agent 2: TravelBuddy
def _summarize_flight(option: dict) -> dict:
    legs = option.get("flights", [])
    return {
        "price_inr": option.get("price"),
        "total_duration_min": option.get("total_duration"),
        "stops": max(len(legs) - 1, 0),
        "layovers": [l.get("name") for l in option.get("layovers", [])],
        "legs": [
            {
                "airline": l.get("airline"),
                "flight_number": l.get("flight_number"),
                "from": l.get("departure_airport", {}).get("id"),
                "departs": l.get("departure_airport", {}).get("time"),
                "to": l.get("arrival_airport", {}).get("id"),
                "arrives": l.get("arrival_airport", {}).get("time"),
                "class": l.get("travel_class"),
                "facilities": l.get("extensions", []),
            }
            for l in legs
        ],
    }


@tool
def search_flights(origin: str, destination: str, date: str) -> list:
    """Search one-way flights with Google Flights. origin/destination are IATA codes (HYD, GOI, BOM, DEL, BLR). date is YYYY-MM-DD."""
    try:
        response = requests.get(
            "https://serpapi.com/search",
            params={
                "engine": "google_flights",
                "departure_id": origin,
                "arrival_id": destination,
                "outbound_date": date,
                "currency": "INR",
                "type": "2",
                "hl": "en",
                "api_key": SERPAPI_KEY,
            },
            timeout=45,
        )
        data = response.json()
    except Exception as e:
        return f"Flight search failed: {e}"

    if "error" in data:
        return f"Flight search error: {data['error']}"
    options = data.get("best_flights", []) + data.get("other_flights", [])
    return [_summarize_flight(o) for o in options[:8]] or "No flights found."


flight_agent = create_agent(
    model=model,
    tools=[_search_tool(), search_flights],
    checkpointer=checkpointer,
    system_prompt=f"""You are a TravelBuddy assistant that helps travelers plan trips. Today's date is {TODAY}.
You have access to these tools:
- tavily_search: research attractions, culture, and travel tips
- search_flights: find flight options (use IATA codes: HYD=Hyderabad, GOI=Goa, BOM=Mumbai, DEL=Delhi, BLR=Bangalore, MAA=Chennai, CCU=Kolkata)
Help the traveler by researching destinations and finding flights.
For flights show airline, flight number, departure and arrival times, duration, stops, price in INR, and facilities when available.
Use clear sections. If the user asks a follow-up about an earlier answer, use the conversation history.
If the user gives no date, ask for one before searching flights.""",
)


# ---------------------------------------------------------------- Agent 3: CourseFinder
@tool
def search_courses(skill: str) -> list:
    """Search YouTube for free full-length video courses and tutorials on a skill."""
    try:
        response = requests.get(
            "https://www.googleapis.com/youtube/v3/search",
            params={
                "part": "snippet",
                "q": f"{skill} complete course tutorial",
                "type": "video",
                "videoDuration": "long",
                "maxResults": 5,
                "order": "relevance",
                "key": YOUTUBE_API_KEY,
            },
            timeout=30,
        )
        data = response.json()
    except Exception as e:
        return f"YouTube search failed: {e}"

    if "error" in data:
        return f"YouTube API error: {data['error'].get('message')}"
    return [
        {
            "title": item["snippet"]["title"],
            "channel": item["snippet"]["channelTitle"],
            "url": f"https://www.youtube.com/watch?v={item['id']['videoId']}",
        }
        for item in data.get("items", [])
    ] or "No videos found."


course_agent = create_agent(
    model=model,
    tools=[_search_tool(), search_courses],
    checkpointer=checkpointer,
    system_prompt="""You are a CourseFinder assistant that helps students discover the best learning resources.
You have access to these tools:
- tavily_search: research learning roadmaps, free resources, certifications, and prerequisites
- search_courses: find free video courses on YouTube
For a new topic: first build a roadmap broken into sub-topics, then find YouTube courses.
Present two sections: Learning Roadmap and Video Courses.
For each video show the title, channel and the full YouTube link.
If the user asks a follow-up about an earlier answer, use the conversation history.""",
)


AGENTS = {"skill": skill_agent, "flight": flight_agent, "course": course_agent}


def _text(message) -> str:
    """Gemini may return a string or a list of content blocks; normalise to text."""
    content = message.content
    if isinstance(content, str):
        return content
    parts = []
    for block in content:
        if isinstance(block, str):
            parts.append(block)
        elif isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text", ""))
    return "\n".join(parts)


def ask(agent_name: str, message: str, session_id: str) -> str:
    """Run one turn. thread_id = agent + visitor session, so memory is private per visitor per agent."""
    config = {"configurable": {"thread_id": f"{agent_name}-{session_id}"}}
    result = AGENTS[agent_name].invoke(
        {"messages": [{"role": "user", "content": message}]}, config=config
    )
    return _text(result["messages"][-1])
