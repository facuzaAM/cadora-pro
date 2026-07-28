"""Seed script: create 4 test users (one per plan) for recognition engine testing.

Run inside the backend container:
    docker compose exec backend python -m scripts.seed_test_users
"""

import asyncio
import sys
from pathlib import Path

# Ensure `app` package is importable when run as -m script
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.models.user import User
from app.utils.security import hash_password

TEST_USERS = [
    {
        "email": "test-free@cadora.pro",
        "name": "Test Free",
        "plan": "free",
        "conversions_limit": 3,
        "storage_limit": 50 * 1024 * 1024,
        "priority_processing": False,
    },
    {
        "email": "test-starter@cadora.pro",
        "name": "Test Starter",
        "plan": "starter",
        "conversions_limit": 50,
        "storage_limit": 1 * 1024 * 1024 * 1024,
        "priority_processing": False,
    },
    {
        "email": "test-pro@cadora.pro",
        "name": "Test Pro",
        "plan": "pro",
        "conversions_limit": 200,
        "storage_limit": 5 * 1024 * 1024 * 1024,
        "priority_processing": True,
    },
    {
        "email": "test-business@cadora.pro",
        "name": "Test Business",
        "plan": "business",
        "conversions_limit": 0,  # unlimited
        "storage_limit": 25 * 1024 * 1024 * 1024,
        "priority_processing": True,
    },
]

PASSWORD = "Test1234!"


async def main():
    engine = create_async_engine(settings.DATABASE_URL)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    hashed = hash_password(PASSWORD)

    async with session_factory() as db:
        for u in TEST_USERS:
            existing = (await db.execute(
                select(User).where(User.email == u["email"])
            )).scalar_one_or_none()

            if existing:
                print(f"  ↳ {u['email']} already exists, updating plan")
                existing.subscription_plan = u["plan"]
                existing.conversions_limit = u["conversions_limit"]
                existing.storage_limit = u["storage_limit"]
                existing.priority_processing = u["priority_processing"]
                existing.subscription_status = "active"
            else:
                user = User(
                    email=u["email"],
                    name=u["name"],
                    hashed_password=hashed,
                    subscription_plan=u["plan"],
                    subscription_status="active",
                    conversions_used=0,
                    conversions_limit=u["conversions_limit"],
                    storage_used=0,
                    storage_limit=u["storage_limit"],
                    priority_processing=u["priority_processing"],
                )
                db.add(user)
                print(f"  ✓ Created {u['email']} ({u['plan']})")

        await db.commit()

    await engine.dispose()
    print("\nDone. All test users ready.")
    print(f"Password for all: {PASSWORD}")


if __name__ == "__main__":
    asyncio.run(main())
