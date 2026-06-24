from dataclasses import dataclass

from pydantic import BaseModel


@dataclass
class RestaurantCustomerContext:
    name: str
    tier: str = "basic"
    phone: str = "010-0000-0000"


class InputGuardRailOutput(BaseModel):
    is_off_topic: bool
    contains_inappropriate_language: bool
    reason: str


class RestaurantOutputGuardRailOutput(BaseModel):
    contains_unprofessional_tone: bool
    contains_internal_information: bool
    reason: str


class HandoffData(BaseModel):
    reason: str
    issue_type: str
    issue_description: str


RESTAURANT_INFO = """
Restaurant Name: Sunny Table

Menu:
- Margherita Pizza: tomato, mozzarella, basil. Vegetarian.
- Vegan Garden Bowl: quinoa, chickpeas, avocado, roasted vegetables. Vegan.
- Shrimp Rose Pasta: shrimp, tomato cream sauce, parmesan.
- Caesar Salad: romaine, croutons, parmesan, Caesar dressing.

Allergy notes:
- Margherita Pizza: dairy, gluten
- Vegan Garden Bowl: gluten-free
- Shrimp Rose Pasta: shellfish, dairy, gluten
- Caesar Salad: dairy, egg, gluten

Reservation policy:
- Reservations are accepted for 1 to 8 guests.
- Collect name, party size, date, time, and phone number.

Order policy:
- Orders can be dine-in or takeout.
- Confirm items, quantities, and special requests before finalizing.
"""
