import streamlit as st
from agents import (
    Agent,
    RunContextWrapper,
    handoff,
)
from agents.extensions import handoff_filters
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX

from input_guardrails import restaurant_input_guardrail
from models import HandoffData, RestaurantCustomerContext
from output_guardrails import restaurant_output_guardrail
from my_agents.complaints_agent import complaints_agent
from my_agents.menu_agent import menu_agent
from my_agents.order_agent import order_agent
from my_agents.reservation_agent import reservation_agent


def dynamic_triage_agent_instructions(
    wrapper: RunContextWrapper[RestaurantCustomerContext],
    agent: Agent[RestaurantCustomerContext],
):
    return f"""
    {RECOMMENDED_PROMPT_PREFIX}

    You are a restaurant triage agent for Sunny Table. Always reply in Korean.
    You are helping {wrapper.context.name}.

    YOUR MAIN JOB: classify the customer's restaurant-related request and route them to the right specialist.

    ROUTING GUIDE:
    🍽️ MENU AGENT
    - menu questions
    - ingredients
    - allergy information
    - vegetarian or vegan options
    - recommendations

    🧾 ORDER AGENT
    - placing an order
    - editing an order
    - takeout or dine-in order details
    - quantities and special requests

    📅 RESERVATION AGENT
    - table bookings
    - reservation changes
    - party size, date, time, contact details

    😞 COMPLAINTS AGENT
    - bad food experience
    - rude staff
    - refund complaints
    - service dissatisfaction
    - escalation requests

    PROCESS:
    1. Understand the latest user request.
    2. If clear, explain briefly that you are connecting them to the right specialist.
    3. Handoff immediately.
    4. If unclear, ask one short clarifying question.
    """


def make_handoff(agent: Agent):
    def handle_handoff(
        wrapper: RunContextWrapper[RestaurantCustomerContext],
        input_data: HandoffData,
    ):
        handoff_log = {
            "label": f"[Triage Agent -> {agent.name}]",
            "agent_label": agent.name,
        }
        st.session_state["restaurant_bot_pending_handoffs"].append(handoff_log)

    return handoff(
        agent=agent,
        on_handoff=handle_handoff,
        input_type=HandoffData,
        input_filter=handoff_filters.remove_all_tools,
    )


triage_agent = Agent(
    name="Triage Agent",
    instructions=dynamic_triage_agent_instructions,
    input_guardrails=[restaurant_input_guardrail],
    output_guardrails=[restaurant_output_guardrail],
    handoffs=[
        make_handoff(menu_agent),
        make_handoff(order_agent),
        make_handoff(reservation_agent),
        make_handoff(complaints_agent),
    ],
)
