from agents import Agent, RunContextWrapper

from models import RESTAURANT_INFO, RestaurantCustomerContext
from output_guardrails import restaurant_output_guardrail


def dynamic_menu_agent_instructions(
    wrapper: RunContextWrapper[RestaurantCustomerContext],
    agent: Agent[RestaurantCustomerContext],
):
    return f"""
You are the Menu Agent for Sunny Table. Always reply in Korean.

You are helping {wrapper.context.name}.

Your role:
- Answer menu, ingredient, vegetarian, vegan, and allergy questions clearly.
- Use only the confirmed restaurant information below.

{RESTAURANT_INFO}

Guidelines:
- Be concise, helpful, and polite.
- If something is not confirmed, say you cannot guarantee it.
"""


menu_agent = Agent(
    name="Menu Agent",
    handoff_description="메뉴, 재료, 채식 메뉴, 알레르기 정보를 설명하는 전문가",
    instructions=dynamic_menu_agent_instructions,
    output_guardrails=[restaurant_output_guardrail],
)
