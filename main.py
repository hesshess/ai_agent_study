import dotenv
import asyncio
import streamlit as st

from agents import (
    Agent,
    Runner,
    SQLiteSession,
    WebSearchTool,
)

dotenv.load_dotenv()

if "agent" not in st.session_state:
    st.session_state["agent"] = Agent(
        name="Life Coach",
        instructions="""
You are a supportive life coach.

Help users with:
- motivation
- productivity
- habit building
- self improvement
- discipline
- goal setting

Use web search whenever it helps provide better advice.

Always answer in Korean.

Be encouraging, practical and positive.
Give actionable advice.
""",
        tools=[
            WebSearchTool(),
        ],
    )

agent = st.session_state["agent"]

if "session" not in st.session_state:
    st.session_state["session"] = SQLiteSession(
        "life-coach-history",
        "life-coach-memory.db",
    )

session = st.session_state["session"]


async def paint_history():
    messages = await session.get_items()

    for message in messages:

        if "role" in message:

            with st.chat_message(message["role"]):

                if message["role"] == "user":
                    st.write(message["content"])

                else:
                    if message["type"] == "message":
                        st.write(
                            message["content"][0]["text"]
                            .replace("$", "\$")
                        )

        if "type" in message:

            if message["type"] == "web_search_call":

                with st.chat_message("assistant"):
                    st.info("🔎 웹 검색 수행")


asyncio.run(paint_history())


def update_status(status_container, event):

    status_messages = {
        "response.web_search_call.in_progress": (
            "🔎 웹 검색 시작...",
            "running",
        ),
        "response.web_search_call.searching": (
            "🌐 웹 검색 중...",
            "running",
        ),
        "response.web_search_call.completed": (
            "✅ 검색 완료",
            "complete",
        ),
        "response.completed": (
            " ",
            "complete",
        ),
    }

    if event in status_messages:

        label, state = status_messages[event]

        status_container.update(
            label=label,
            state=state,
        )


async def run_agent(message):

    with st.chat_message("assistant"):

        status_container = st.status(
            "⏳",
            expanded=False,
        )

        text_placeholder = st.empty()

        response = ""

        stream = Runner.run_streamed(
            agent,
            message,
            session=session,
        )

        async for event in stream.stream_events():

            if event.type == "raw_response_event":

                update_status(
                    status_container,
                    event.data.type,
                )

                if (
                    event.data.type
                    == "response.output_text.delta"
                ):
                    response += event.data.delta

                    text_placeholder.write(
                        response.replace("$", "\$")
                    )


st.title("🌱 Life Coach Agent")

prompt = st.chat_input(
    "어떤 고민이 있으신가요?"
)

if prompt:

    with st.chat_message("user"):
        st.write(prompt)

    asyncio.run(
        run_agent(prompt)
    )


with st.sidebar:

    reset = st.button("Reset Memory")

    if reset:
        asyncio.run(
            session.clear_session()
        )
        st.rerun()

    st.divider()

    st.write(
        asyncio.run(
            session.get_items()
        )
    )