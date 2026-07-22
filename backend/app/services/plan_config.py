"""Plan definitions used for feature enforcement and Stripe price mapping."""

from dataclasses import dataclass


@dataclass
class Plan:
    name: str
    price: int
    conversions_limit: int
    storage_limit: int  # bytes
    priority_processing: bool
    stripe_price_key: str  # key into settings.STRIPE_PRICE_*
    description: str


PLANS: dict[str, Plan] = {
    "free": Plan(
        name="Free",
        price=0,
        conversions_limit=3,
        storage_limit=50 * 1024 * 1024,
        priority_processing=False,
        stripe_price_key="",
        description="Para pruebas ocasionales",
    ),
    "starter": Plan(
        name="Starter",
        price=19,
        conversions_limit=50,
        storage_limit=1 * 1024 * 1024 * 1024,
        priority_processing=False,
        stripe_price_key="STRIPE_PRICE_STARTER",
        description="Para profesionales independientes",
    ),
    "pro": Plan(
        name="Pro",
        price=49,
        conversions_limit=200,
        storage_limit=5 * 1024 * 1024 * 1024,
        priority_processing=True,
        stripe_price_key="STRIPE_PRICE_PRO",
        description="Para estudios y equipos pequeños",
    ),
    "business": Plan(
        name="Business",
        price=99,
        conversions_limit=0,  # unlimited
        storage_limit=25 * 1024 * 1024 * 1024,
        priority_processing=True,
        stripe_price_key="STRIPE_PRICE_BUSINESS",
        description="Para empresas con alto volumen",
    ),
}


def get_plan(name: str) -> Plan:
    return PLANS.get(name, PLANS["free"])
