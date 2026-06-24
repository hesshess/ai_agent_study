import asyncio

import dotenv
import streamlit as st
from agents import (
    InputGuardrailTripwireTriggered,
    OutputGuardrailTripwireTriggered,
    Runner,
)

from models import RestaurantCustomerContext
from my_agents.triage_agent import triage_agent

dotenv.load_dotenv()

customer_context = RestaurantCustomerContext(
    name="Guest",
    tier="basic",
    phone="010-1234-5678",
)


def ensure_ui_state():
    if "restaurant_bot_chat_history" not in st.session_state:
        st.session_state["restaurant_bot_chat_history"] = []
    if "restaurant_bot_pending_handoffs" not in st.session_state:
        st.session_state["restaurant_bot_pending_handoffs"] = []


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
                st.caption(handoff_message["label"])
            if entry.get("text"):
                st.write(entry["text"])


async def run_restaurant_bot():
    with st.chat_message("assistant"):
        status_container = st.status("요청을 파악하는 중...", expanded=True)
        handoff_placeholder = st.empty()
        text_placeholder = st.empty()
        response_text = ""
        handoff_messages = []
        st.session_state["restaurant_bot_pending_handoffs"] = []

        try:
            stream = Runner.run_streamed(
                triage_agent,
                build_runner_input(),
                context=customer_context,
            )

            async for event in stream.stream_events():
                pending_handoffs = st.session_state["restaurant_bot_pending_handoffs"]
                if pending_handoffs:
                    visible_labels = [item["label"] for item in pending_handoffs]
                    handoff_placeholder.caption("\n".join(visible_labels))
                    handoff_messages = list(pending_handoffs)
                    status_container.update(label=visible_labels[-1], state="running")

                if event.type != "raw_response_event":
                    continue

                if event.data.type == "response.output_text.delta":
                    response_text += event.data.delta
                    text_placeholder.write(response_text)
                elif event.data.type == "response.completed":
                    status_container.update(label="응답 완료", state="complete")
                    if response_text:
                        text_placeholder.write(response_text)
        except InputGuardrailTripwireTriggered as exc:
            info = exc.guardrail_result.output.output_info
            response_text = (
                "저는 레스토랑 관련 질문에 대해서만 도와드리고 있어요. "
                "메뉴를 확인하거나, 예약하거나, 음식을 주문할 수 있어요."
                if getattr(info, "is_off_topic", False)
                else "불편한 표현은 도와드리기 어려워요. 메뉴, 주문, 예약, 불만 접수처럼 레스토랑 관련 내용으로 말씀해 주세요."
            )
            status_container.update(label="입력 가드레일 작동", state="complete")
            text_placeholder.write(response_text)
            handoff_messages = [{"label": "[input guardrail 작동]"}]
        except OutputGuardrailTripwireTriggered as exc:
            response_text = (
                "죄송합니다. 더 정중하고 안전한 방식으로만 안내드릴 수 있어요. "
                "메뉴, 주문, 예약, 불만 해결과 관련된 내용으로 다시 말씀해 주세요."
            )
            status_container.update(label="출력 가드레일 작동", state="complete")
            text_placeholder.write(response_text)
            handoff_messages = [{"label": "[output guardrail 작동]"}]

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
    reset = st.button("Reset memory")
    if reset:
        st.session_state["restaurant_bot_chat_history"] = []
        st.session_state["restaurant_bot_pending_handoffs"] = []
        st.rerun()

    st.write(st.session_state["restaurant_bot_chat_history"])