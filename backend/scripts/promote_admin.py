"""Promote a user to admin (or remove the flag).

Run inside the backend container:
    docker compose exec api python -m scripts.promote_admin you@example.com [--remove]

The container service is named `api` in docker-compose.yml.
"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.models.user import User


async def main() -> int:
    parser = argparse.ArgumentParser(description="Promote/revoke a Cadora admin")
    parser.add_argument("email", help="Email of the user to modify")
    parser.add_argument(
        "--remove",
        action="store_true",
        help="Revoke admin instead of granting it",
    )
    args = parser.parse_args()

    engine = create_async_engine(settings.DATABASE_URL)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as db:
        user = (
            await db.execute(select(User).where(User.email == args.email.lower()))
        ).scalar_one_or_none()

        if not user:
            print(f"✗ No user found with email {args.email}")
            return 1

        user.is_admin = not args.remove
        await db.commit()
        action = "removed from" if args.remove else "granted"
        print(f"✓ Admin {action} for {user.email}")

    await engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
