import asyncio

import dotenv
import streamlit as st
from agents import Runner

from my_agents.triage_agent import triage_agent

dotenv.load_dotenv()


def ensure_ui_state():
    if "restaurant_bot_chat_history" not in st.session_state:
        st.session_state["restaurant_bot_chat_history"] = []


def format_handoff_message(agent_name: str) -> str:
    return f"[{agent_name}로 handoff]"


def build_runner_input():
    runner_input = []
    for entry in st.session_state["restaurant_bot_chat_history"]:
        text = entry.get("text", "").strip()
        if not text:
            continue
        runner_input.append({"role": entry["role"], "content": text})
    return runner_input


def render_history():
    for entry in st.session_state["restaurant_bot_chat_history"]:
        with st.chat_message(entry["role"]):
            for handoff_message in entry.get("handoffs", []):
                st.caption(handoff_message)
            if entry.get("text"):
                st.write(entry["text"])


async def run_restaurant_bot():
    with st.chat_message("assistant"):
        status_container = st.status("요청을 파악하는 중...", expanded=True)
        handoff_placeholder = st.empty()
        text_placeholder = st.empty()
        response_text = ""
        handoff_messages = []

        stream = Runner.run_streamed(
            triage_agent,
            build_runner_input(),
        )

        async for event in stream.stream_events():
            if event.type == "agent_updated_stream_event":
                handoff_label = format_handoff_message(event.new_agent.name)
                if handoff_label and handoff_label not in handoff_messages:
                    handoff_messages.append(handoff_label)
                    handoff_placeholder.caption("\n".join(handoff_messages))
                    status_container.update(label=handoff_label, state="running")
                continue

            if event.type == "run_item_stream_event" and event.name == "handoff_occured":
                target_name = event.item.target_agent.name
                handoff_label = format_handoff_message(target_name)
                if handoff_label and handoff_label not in handoff_messages:
                    handoff_messages.append(handoff_label)
                    handoff_placeholder.caption("\n".join(handoff_messages))
                    status_container.update(label=handoff_label, state="running")
                continue

            if event.type != "raw_response_event":
                continue

            if event.data.type == "response.output_text.delta":
                response_text += event.data.delta
                text_placeholder.write(response_text)
            elif event.data.type == "response.completed":
                status_container.update(label="응답 완료", state="complete")
                if response_text:
                    text_placeholder.write(response_text)

        st.session_state["restaurant_bot_chat_history"].append(
            {
                "role": "assistant",
                "text": response_text,
                "handoffs": handoff_messages,
            }
        )


st.set_page_config(page_title="Restaurant Bot", page_icon="🍽️", layout="wide")
ensure_ui_state()

st.title("🍽️ Restaurant Bot")

render_history()

prompt = st.chat_input("메뉴, 주문, 예약에 대해 물어보세요")

if prompt:
    st.session_state["restaurant_bot_chat_history"].append(
        {
            "role": "user",
            "text": prompt,
            "handoffs": [],
        }
    )
    with st.chat_message("user"):
        st.write(prompt)
    asyncio.run(run_restaurant_bot())

with st.sidebar:
    st.subheader("전문 에이전트")
    st.write("`Triage Agent`")
    st.write("`Menu Agent`")
    st.write("`Order Agent`")
    st.write("`Reservation Agent`")

    if st.button("대화 초기화"):
        st.session_state["restaurant_bot_chat_history"] = []
        st.rerun()
