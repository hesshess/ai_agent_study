from agents import Agent, RunContextWrapper

from models import RESTAURANT_INFO, RestaurantCustomerContext
from output_guardrails import restaurant_output_guardrail


def dynamic_order_agent_instructions(
    wrapper: RunContextWrapper[RestaurantCustomerContext],
    agent: Agent[RestaurantCustomerContext],
):
    return f"""
You are the Order Agent for Sunny Table. Always reply in Korean.

You are helping {wrapper.context.name}.

Your role:
- Help the customer place or update an order.
- Ask for missing details such as dine-in or takeout, quantities, and special requests.
- Summarize the order clearly before asking for confirmation.

{RESTAURANT_INFO}

Guidelines:
- Stay practical and organized.
- Reflect allergy or dietary constraints in the order summary.
"""


order_agent = Agent(
    name="Order Agent",
    handoff_description="주문을 받고 확인하는 담당자",
    instructions=dynamic_order_agent_instructions,
    output_guardrails=[restaurant_output_guardrail],
)
