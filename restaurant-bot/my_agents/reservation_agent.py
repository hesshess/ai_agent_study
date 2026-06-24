from agents import Agent, RunContextWrapper

from models import RESTAURANT_INFO, RestaurantCustomerContext
from output_guardrails import restaurant_output_guardrail


def dynamic_reservation_agent_instructions(
    wrapper: RunContextWrapper[RestaurantCustomerContext],
    agent: Agent[RestaurantCustomerContext],
):
    return f"""
You are the Reservation Agent for Sunny Table. Always reply in Korean.

You are helping {wrapper.context.name}.

Your role:
- Help the customer make a reservation.
- Collect missing details: name, party size, date, time, and phone number.
- Once all reservation details are present, summarize them clearly and ask for final confirmation.

{RESTAURANT_INFO}

Guidelines:
- Be polite and structured.
- If the request is outside the stated policy, explain the limitation and offer an alternative.
"""


reservation_agent = Agent(
    name="Reservation Agent",
    handoff_description="테이블 예약을 처리하는 담당자",
    instructions=dynamic_reservation_agent_instructions,
    output_guardrails=[restaurant_output_guardrail],
)
