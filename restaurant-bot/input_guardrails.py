from agents import (
    Agent,
    GuardrailFunctionOutput,
    RunContextWrapper,
    Runner,
    input_guardrail,
)

from models import InputGuardRailOutput, RestaurantCustomerContext


input_guardrail_agent = Agent(
    name="Restaurant Input Guardrail Agent",
    instructions="""
You check whether a user's latest message is appropriate for a restaurant support bot.

Mark the message as off-topic if it is not about:
- restaurant menu questions
- ingredients, allergy, vegetarian, vegan questions
- ordering food
- reservations
- complaints about food, service, refunds, or staff experience

Mark the message as inappropriate if it contains abusive, insulting, or explicit profanity.

Return:
- is_off_topic: true or false
- contains_inappropriate_language: true or false
- reason: one short Korean explanation
""",
    output_type=InputGuardRailOutput,
)


@input_guardrail(run_in_parallel=False)
async def restaurant_input_guardrail(
    wrapper: RunContextWrapper[RestaurantCustomerContext],
    agent: Agent[RestaurantCustomerContext],
    input: str,
):
    result = await Runner.run(
        input_guardrail_agent,
        input,
        context=wrapper.context,
    )

    output = result.final_output

    return GuardrailFunctionOutput(
        output_info=output,
        tripwire_triggered=(
            output.is_off_topic or output.contains_inappropriate_language
        ),
    )
