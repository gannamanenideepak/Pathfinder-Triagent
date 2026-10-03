import uuid
import streamlit as st
from agents import ask

st.set_page_config(page_title="Pathfinder", page_icon="🧭", layout="centered")

ACCENT = "#C2410C"

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=DM+Sans:wght@400;500;600&display=swap');

.stApp, .stApp p, .stApp button, .stApp textarea { font-family: 'DM Sans', sans-serif !important; }

/* remove Streamlit chrome */
#MainMenu, footer, header[data-testid="stHeader"], [data-testid="stToolbar"],
[data-testid="stDecoration"], .stAppDeployButton { display: none !important; }

.block-container { max-width: 820px; padding-top: 3rem; padding-bottom: 7rem; }

/* header */
.eyebrow { letter-spacing: .16em; text-transform: uppercase; font-size: .74rem; font-weight: 600; color: #C2410C; }
.hero h1 { font-family: 'DM Serif Display', serif !important; font-weight: 400 !important;
           font-size: 3.6rem !important; line-height: 1.04 !important; margin: .35rem 0 .7rem !important; padding: 0 !important; }
.hero p { font-size: 1.08rem; max-width: 560px; opacity: .72; margin-bottom: 1.6rem; }

/* agent card */
.card { border: 1px solid rgba(128,128,128,.28); border-radius: 14px; padding: 1.1rem 1.3rem;
        margin: 1.1rem 0 1.4rem; background: rgba(128,128,128,.06); }
.card-title { font-family: 'DM Serif Display', serif; font-size: 1.4rem; }
.card-text { opacity: .8; margin: .25rem 0 .8rem; }
.chip { display: inline-block; font-size: .74rem; padding: .18rem .65rem; margin-right: .4rem;
        border: 1px solid rgba(128,128,128,.4); border-radius: 999px; opacity: .85; }
.hint { font-size: .86rem; margin-top: .85rem; opacity: .62; }
.label { font-size: .74rem; letter-spacing: .12em; text-transform: uppercase; font-weight: 600; opacity: .55; margin: 0 0 .5rem; }

/* buttons */
.stButton > button { width: 100%; justify-content: flex-start; text-align: left; border-radius: 12px;
        border: 1px solid rgba(128,128,128,.32); padding: .7rem 1rem; transition: all .15s ease; }
.stButton > button div { justify-content: flex-start; text-align: left; }
.stButton > button:hover { border-color: #C2410C; color: #C2410C; transform: translateY(-1px); }

/* chat */
[data-testid="stChatMessage"] { background: rgba(128,128,128,.06); border: 1px solid rgba(128,128,128,.16);
        border-radius: 14px; padding: 1rem 1.15rem; }
[data-testid="stChatInput"] { border-radius: 14px; }
</style>
""",
    unsafe_allow_html=True,
)

AGENTS = {
    "skill": {
        "label": "Careers",
        "title": "Skills to jobs",
        "blurb": "Tell it a skill. It checks current market demand and pulls live openings with apply links.",
        "sources": ["Live web search", "Job listings"],
        "working": "Researching the market...",
        "placeholder": "Try: data analyst roles in Hyderabad",
        "suggestions": [
            "What's the demand for generative AI skills, and show me openings in India",
            "Data analyst jobs in Hyderabad",
            "Entry-level cloud engineer roles in Bangalore",
        ],
    },
    "flight": {
        "label": "Flights",
        "title": "Trip and flight planner",
        "blurb": "Give it a route and a date. It compares live fares, timings and facilities, and adds destination tips.",
        "sources": ["Live web search", "Google Flights"],
        "working": "Checking flights...",
        "placeholder": "Try: Hyderabad to Goa on 2026-12-15",
        "suggestions": [
            "Hyderabad to Goa on 2026-12-15, plus top attractions",
            "Cheapest flights from Delhi to Mumbai on 2026-11-20",
            "Bangalore to Chennai on 2026-12-01, with facilities",
        ],
    },
    "course": {
        "label": "Courses",
        "title": "Learning roadmaps",
        "blurb": "Name a topic. It breaks it into sub-topics and finds full YouTube courses for each stage.",
        "sources": ["Live web search", "YouTube"],
        "working": "Building your roadmap...",
        "placeholder": "Try: machine learning from scratch",
        "suggestions": [
            "I want to learn Machine Learning from scratch. Show a roadmap and beginner courses",
            "Learn SQL for data analysis",
            "Full stack web development for beginners",
        ],
    },
}

# State: chat history and a separate memory thread per assistant, per visitor
st.session_state.setdefault("history", {k: [] for k in AGENTS})
st.session_state.setdefault("threads", {k: str(uuid.uuid4()) for k in AGENTS})
st.session_state.setdefault("pending", None)
st.session_state.setdefault("active", "skill")
st.session_state.setdefault("last", "skill")

# Header
st.markdown(
    '<div class="hero"><div class="eyebrow">Careers · Travel · Learning</div>'
    "<h1>Pathfinder</h1>"
    "<p>Three research assistants that search the live web, pull real data, and remember your conversation.</p></div>",
    unsafe_allow_html=True,
)

# Assistant picker
left, right = st.columns([5, 2], vertical_alignment="center")
with left:
    st.segmented_control(
        "Assistant", list(AGENTS), format_func=lambda k: AGENTS[k]["label"],
        key="active", label_visibility="collapsed",
    )
choice = st.session_state.active or st.session_state.last
st.session_state.last = choice
a = AGENTS[choice]
with right:
    if st.button("New chat", key="new_chat"):
        st.session_state.history[choice] = []
        st.session_state.threads[choice] = str(uuid.uuid4())  # also wipes the agent's memory
        st.rerun()

chips = "".join(f'<span class="chip">{s}</span>' for s in a["sources"])
st.markdown(
    f'<div class="card"><div class="card-title">{a["title"]}</div>'
    f'<div class="card-text">{a["blurb"]}</div>{chips}'
    '<div class="hint">You can ask follow-up questions.</div></div>',
    unsafe_allow_html=True,
)

# Input (pinned to the bottom of the page by Streamlit)
typed = st.chat_input(a["placeholder"])
prompt = typed or st.session_state.pending
st.session_state.pending = None

USER_AVATAR, BOT_AVATAR = ":material/person:", ":material/explore:"

for msg in st.session_state.history[choice]:
    with st.chat_message(msg["role"], avatar=USER_AVATAR if msg["role"] == "user" else BOT_AVATAR):
        st.markdown(msg["content"])

# Empty state: starter questions
if not st.session_state.history[choice] and not prompt:
    st.markdown('<div class="label">Start with</div>', unsafe_allow_html=True)
    for i, s in enumerate(a["suggestions"]):
        if st.button(s, key=f"sug-{choice}-{i}"):
            st.session_state.pending = s
            st.rerun()

if prompt:
    st.session_state.history[choice].append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar=USER_AVATAR):
        st.markdown(prompt)
    with st.chat_message("assistant", avatar=BOT_AVATAR):
        with st.spinner(a["working"]):
            try:
                answer = ask(choice, prompt, st.session_state.threads[choice])
            except Exception as e:
                print(f"[{choice}] error: {e!r}")
                answer = "Something went wrong on my end, possibly a rate limit. Please try again in a moment."
        st.markdown(answer)
    st.session_state.history[choice].append({"role": "assistant", "content": answer})