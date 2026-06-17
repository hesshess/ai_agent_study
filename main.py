import os
import dotenv
import asyncio
import streamlit as st
from openai import OpenAI
from agents import Agent, Runner, SQLiteSession, WebSearchTool, FileSearchTool

dotenv.load_dotenv()

client = OpenAI()

VECTOR_STORE_ID = os.getenv("VECTOR_STORE_ID")

if "agent" not in st.session_state:
    st.session_state["agent"] = Agent(
        name="Life Coach",
        instructions="""
You are a supportive life coach.

You help users with:
- personal goals
- journal entries
- habit building
- motivation
- productivity
- self improvement
- progress tracking

You have access to the following tools:

- File Search Tool:
Use this when the user asks about their personal goals, journal entries,
past records, uploaded documents, or progress.

- Web Search Tool:
Use this when the user needs useful tips, habit strategies,
motivation methods, or general self-improvement advice.

When the user asks about their progress:
1. First search their uploaded goal or journal documents.
2. Then use web search if helpful.
3. Combine their personal goals with practical advice.
4. Always answer in Korean.
5. Be encouraging, realistic, and actionable.
""",
        tools=[
            FileSearchTool(
                vector_store_ids=[VECTOR_STORE_ID],
                max_num_results=3,
            ),
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
                    if message.get("type") == "message":
                        st.write(
                            message["content"][0]["text"].replace("$", "\\$")
                        )

        if "type" in message:
            message_type = message["type"]

            if message_type == "file_search_call":
                with st.chat_message("assistant"):
                    st.write("🗂️ [목표 문서 검색]")

            elif message_type == "web_search_call":
                with st.chat_message("assistant"):
                    st.write("🔍 [웹 검색]")


asyncio.run(paint_history())


def update_status(status_container, event):
    status_messages = {
        "response.file_search_call.in_progress": (
            "🗂️ 목표 문서 검색 시작...",
            "running",
        ),
        "response.file_search_call.searching": (
            "🗂️ 목표 문서 검색 중...",
            "running",
        ),
        "response.file_search_call.completed": (
            "✅ 목표 문서 검색 완료",
            "complete",
        ),
        "response.web_search_call.in_progress": (
            "🔍 웹 검색 시작...",
            "running",
        ),
        "response.web_search_call.searching": (
            "🔍 웹 검색 중...",
            "running",
        ),
        "response.web_search_call.completed": (
            "✅ 웹 검색 완료",
            "complete",
        ),
        "response.completed": (
            " ",
            "complete",
        ),
    }

    if event in status_messages:
        label, state = status_messages[event]
        status_container.update(label=label, state=state)


async def run_agent(message):
    with st.chat_message("assistant"):
        status_container = st.status("⏳", expanded=False)
        text_placeholder = st.empty()
        response = ""

        stream = Runner.run_streamed(
            agent,
            message,
            session=session,
        )

        async for event in stream.stream_events():
            if event.type == "raw_response_event":
                update_status(status_container, event.data.type)

                if event.data.type == "response.file_search_call.in_progress":
                    st.write("🗂️ [목표 문서 검색]")

                elif event.data.type == "response.web_search_call.in_progress":
                    st.write("🔍 [웹 검색]")

                elif event.data.type == "response.output_text.delta":
                    response += event.data.delta
                    text_placeholder.write(response.replace("$", "\\$"))


st.title("🌱 Life Coach Agent")

prompt = st.chat_input(
    "목표 문서나 일기를 업로드하고, 고민을 말해보세요.",
    accept_file=True,
    file_type=["txt", "pdf"],
)

if prompt:
    for file in prompt.files:
        with st.chat_message("assistant"):
            with st.status("⏳ 파일 업로드 중...") as status:
                uploaded_file = client.files.create(
                    file=(file.name, file.getvalue()),
                    purpose="user_data",
                )

                status.update(label="⏳ 목표 문서 연결 중...")

                client.vector_stores.files.create(
                    vector_store_id=VECTOR_STORE_ID,
                    file_id=uploaded_file.id,
                )

                status.update(
                    label=f"✅ {file.name} 업로드 완료",
                    state="complete",
                )

    if prompt.text:
        with st.chat_message("user"):
            st.write(prompt.text)

        asyncio.run(run_agent(prompt.text))


with st.sidebar:
    reset = st.button("Reset")


    if reset:
        asyncio.run(session.clear_session())
        st.rerun()

    st.write(asyncio.run(session.get_items()))