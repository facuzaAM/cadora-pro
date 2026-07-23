from app.services.plan_config import PLANS, get_plan


def test_plan_configs_exist():
    assert "free" in PLANS
    assert "starter" in PLANS
    assert "pro" in PLANS
    assert "business" in PLANS


def test_free_plan_limits():
    free = PLANS["free"]
    assert free.price == 0
    assert free.conversions_limit == 3
    assert free.priority_processing is False
    assert free.dwg_enabled is False


def test_pro_plan_limits():
    pro = PLANS["pro"]
    assert pro.price == 49
    assert pro.conversions_limit == 200
    assert pro.priority_processing is True
    assert pro.dwg_enabled is True


def test_dwg_enabled_only_for_pro_and_business():
    assert PLANS["free"].dwg_enabled is False
    assert PLANS["starter"].dwg_enabled is False
    assert PLANS["pro"].dwg_enabled is True
    assert PLANS["business"].dwg_enabled is True


def test_get_plan():
    plan = get_plan("pro")
    assert plan is not None
    assert plan.name == "Pro"


def test_get_invalid_plan_returns_free():
    plan = get_plan("nonexistent")
    assert plan is not None
    assert plan.name == "Free"
