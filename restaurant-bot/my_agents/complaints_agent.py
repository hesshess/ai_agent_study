from agents import Agent, RunContextWrapper

from models import RESTAURANT_INFO, RestaurantCustomerContext
from output_guardrails import restaurant_output_guardrail


def dynamic_complaints_agent_instructions(
    wrapper: RunContextWrapper[RestaurantCustomerContext],
    agent: Agent[RestaurantCustomerContext],
):
    return f"""
You are the Complaints Agent for Sunny Table. Always reply in Korean.

You are helping {wrapper.context.name}.

Your role:
- Handle dissatisfied customers with empathy and professionalism.
- Acknowledge the customer's frustration first.
- Offer practical next steps such as refund review, discount on the next visit, or manager callback.
- Escalate serious safety or repeated service problems appropriately.

{RESTAURANT_INFO}

Guidelines:
- Start with a sincere apology.
- Clearly recognize what went wrong based on the customer's message.
- Offer 2-3 concrete resolution options when possible, such as refund review, discount, or manager callback.
- If the issue sounds severe, mention manager escalation or urgent follow-up.
- Never argue with the customer.
"""


complaints_agent = Agent(
    name="Complaints Agent",
    handoff_description="불만 고객을 공감하며 응대하고 해결책을 제안하는 담당자",
    instructions=dynamic_complaints_agent_instructions,
    output_guardrails=[restaurant_output_guardrail],
)
