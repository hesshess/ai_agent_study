import asyncio
import base64
import os

import dotenv
import streamlit as st
from openai import OpenAI
from agents import (
    Agent,
    FileSearchTool,
    ImageGenerationTool,
    Runner,
    WebSearchTool,
)

dotenv.load_dotenv()

client = OpenAI()
VECTOR_STORE_ID = os.getenv("VECTOR_STORE_ID")


def require_vector_store_id() -> str:
    if not VECTOR_STORE_ID:
        st.error("`.env`에 `VECTOR_STORE_ID`를 설정해주세요.")
        st.stop()
    return VECTOR_STORE_ID


def build_agent(vector_store_id: str) -> Agent:
    return Agent(
        name="Life Coach Agent",
        instructions="""
You are a warm, practical life coach who always replies in Korean.

Your job is to help the user reflect on goals, stay motivated, and turn progress into action.

You have three tools and should use them together naturally:

1. File Search Tool
- Use this first when the user asks about personal goals, routines, journals, progress, or uploaded documents.
- Treat uploaded files as the source of truth for the user's personal context.

2. Web Search Tool
- Use this when current advice, examples, or outside ideas would strengthen your coaching.
- Search for motivation tips, habit strategies, productivity advice, exercise tips, study methods, and inspiration.

3. Image Generation Tool
- Use this when the user asks for a vision board, motivational poster, celebration image, or visual progress summary.
- Create images that reflect the user's real goals found in their files whenever possible.

How to work:
- For personal coaching, check the user's files first.
- If helpful, combine personal context with web insights.
- If the user wants something visual, generate an image that matches their goals and tone.
- Be specific, encouraging, and actionable.

You must be able to create:
- goal-based vision boards
- motivational posters with custom messages
- visual representations of progress

Example behaviors:
- If the user says "2025년 목표로 비전 보드를 만들어줘", first inspect their uploaded goal files, summarize the themes, then generate the image.
- If the user says "올해 책 10권 읽기 목표를 달성했어!", celebrate them and generate a congratulatory poster.
- If the user asks how to stay consistent, look at their journals or goals first, then add web-based advice if useful.
""",
        tools=[
            FileSearchTool(
                vector_store_ids=[vector_store_id],
                max_num_results=3,
            ),
            WebSearchTool(),
            ImageGenerationTool(
                tool_config={
                    "type": "image_generation",
                    "quality": "low",
                    "output_format": "jpeg",
                    "partial_images": 1,
                }
            ),
        ],
    )


def get_agent() -> Agent:
    if "agent" not in st.session_state:
        st.session_state["agent"] = build_agent(require_vector_store_id())
    return st.session_state["agent"]


def ensure_ui_state():
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []
    if "generated_images" not in st.session_state:
        st.session_state["generated_images"] = []


def escape_markdown(text: str) -> str:
    return text.replace("$", "\\$")


def render_saved_chat():
    for entry in st.session_state["chat_history"]:
        with st.chat_message(entry["role"]):
            if entry.get("text"):
                st.write(escape_markdown(entry["text"]))
            for image_index in entry.get("image_indices", []):
                image_entry = st.session_state["generated_images"][image_index]
                st.image(
                    base64.b64decode(image_entry["image_b64"]),
                    caption=image_entry.get("caption") or "생성된 이미지",
                )


def build_runner_input():
    runner_input = []
    for entry in st.session_state["chat_history"]:
        text = entry.get("text", "").strip()
        if not text:
            continue
        runner_input.append(
            {
                "role": entry["role"],
                "content": text,
            }
        )
    return runner_input


def update_status(status_container, event_type: str):
    status_messages = {
        "response.file_search_call.in_progress": ("🗂️ 목표와 일기를 읽는 중...", "running"),
        "response.file_search_call.searching": ("🗂️ 목표와 일기를 읽는 중...", "running"),
        "response.file_search_call.completed": ("✅ 개인 목표와 기록을 확인했어요.", "complete"),
        "response.web_search_call.in_progress": ("🔍 웹에서 팁을 찾는 중...", "running"),
        "response.web_search_call.searching": ("🔍 웹에서 팁을 찾는 중...", "running"),
        "response.web_search_call.completed": ("✅ 도움이 되는 외부 자료를 찾았어요.", "complete"),
        "response.image_generation_call.in_progress": ("🎨 이미지를 만들고 있어요...", "running"),
        "response.image_generation_call.generating": ("🎨 이미지를 만들고 있어요...", "running"),
        "response.image_generation_call.completed": ("✅ 이미지 생성이 끝났어요.", "complete"),
        "response.completed": ("완료", "complete"),
    }

    if event_type in status_messages:
        label, state = status_messages[event_type]
        status_container.update(label=label, state=state)


async def run_agent(agent: Agent, message: str):
    with st.chat_message("assistant"):
        status_container = st.status("생각 중...", expanded=True)
        text_placeholder = st.empty()
        image_placeholder = st.empty()
        response_text = ""
        latest_image_b64 = None

        stream = Runner.run_streamed(
            agent,
            build_runner_input(),
        )

        async for event in stream.stream_events():
            if event.type != "raw_response_event":
                continue

            update_status(status_container, event.data.type)

            if event.data.type == "response.output_text.delta":
                response_text += event.data.delta
                text_placeholder.write(escape_markdown(response_text))
            elif event.data.type == "response.image_generation_call.partial_image":
                latest_image_b64 = event.data.partial_image_b64
                image_bytes = base64.b64decode(latest_image_b64)
                image_placeholder.image(image_bytes)
            elif event.data.type == "response.completed":
                if response_text:
                    text_placeholder.write(escape_markdown(response_text))

        image_indices = []
        if latest_image_b64:
            st.session_state["generated_images"].append(
                {
                    "image_b64": latest_image_b64,
                    "caption": f"'{message}' 요청으로 만든 이미지",
                    "prompt": message,
                }
            )
            image_indices.append(len(st.session_state["generated_images"]) - 1)

        st.session_state["chat_history"].append(
            {
                "role": "assistant",
                "text": response_text,
                "image_indices": image_indices,
            }
        )


def upload_file_to_vector_store(uploaded_file, vector_store_id: str):
    uploaded = client.files.create(
        file=(uploaded_file.name, uploaded_file.getvalue()),
        purpose="user_data",
    )
    client.vector_stores.files.create(
        vector_store_id=vector_store_id,
        file_id=uploaded.id,
    )


st.set_page_config(page_title="Life Coach Agent", page_icon="🌱", layout="wide")

vector_store_id = require_vector_store_id()
agent = get_agent()
ensure_ui_state()

st.title("🌱 Life Coach Agent")

render_saved_chat()

prompt = st.chat_input(
    "라이프코치에게 물어보세요",
    accept_file=True,
    file_type=["txt", "md", "pdf", "docx"],
)

if prompt:
    if prompt.files:
        for uploaded_file in prompt.files:
            with st.chat_message("assistant"):
                with st.status(f"{uploaded_file.name} 업로드 중...", expanded=False) as status:
                    upload_file_to_vector_store(uploaded_file, vector_store_id)
                    status.update(
                        label=f"✅ {uploaded_file.name} 업로드 완료..",
                        state="complete",
                    )

    if prompt.text:
        st.session_state["chat_history"].append(
            {
                "role": "user",
                "text": prompt.text,
                "image_indices": [],
            }
        )
        with st.chat_message("user"):
            st.write(prompt.text)
        asyncio.run(run_agent(agent, prompt.text))

with st.sidebar:
    reset = st.button("Reset memory")
    if reset:
        st.session_state["chat_history"] = []
        st.session_state["generated_images"] = []
        st.rerun()

    if st.session_state["generated_images"]:
        st.divider()
        st.subheader("Generated Images")
        for image_entry in reversed(st.session_state["generated_images"]):
            st.image(
                base64.b64decode(image_entry["image_b64"]),
                caption=image_entry.get("caption") or "생성된 이미지",
            )
