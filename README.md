# AI Agent Hub

Three LangChain + LangGraph agents in one Streamlit app, each with per-session conversation memory.

- **SkillMap**: market demand for a skill (Tavily) + live job listings (JSearch API)
- **TravelBuddy**: destination research (Tavily) + flights, prices and facilities (SerpAPI Google Flights)
- **CourseFinder**: learning roadmap (Tavily) + YouTube video courses (YouTube Data API)

Stack: LangChain `create_agent`, LangGraph `InMemorySaver`, Gemini, Streamlit.

Run locally: put the five keys in a `.env` file, then `pip install -r requirements.txt` and `streamlit run app.py`.
