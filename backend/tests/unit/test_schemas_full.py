from app.schemas.auth import LoginRequest
from app.schemas.billing import PlanResponse
from app.schemas.project import ProjectCreateRequest


def test_project_create_request():
    req = ProjectCreateRequest(name="Test Project", description="A test")
    assert req.name == "Test Project"
    assert req.description == "A test"


def test_project_create_request_minimal():
    req = ProjectCreateRequest(name="Minimal")
    assert req.name == "Minimal"
    assert req.description is None


def test_login_request():
    req = LoginRequest(email="test@example.com", password="secret123")
    assert req.email == "test@example.com"
    assert req.password == "secret123"


def test_plan_response():
    resp = PlanResponse(
        name="Pro",
        price=49,
        conversions_limit=200,
        storage_limit=5 * 1024 * 1024 * 1024,
        priority_processing=True,
    )
    assert resp.name == "Pro"
    assert resp.price == 49
    assert resp.conversions_limit == 200
    assert resp.priority_processing is True
