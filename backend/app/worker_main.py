"""Standalone detection worker process.

Runs the same atomic detection loop as the in-process worker, but in its own
container so it never competes with HTTP requests on the API event loop. It
polls for pending projects, runs detection+OCR, writes the result and returns.

Run against a DB that already has the schema (the API applies migrations):
    python -m app.worker_main
"""

from __future__ import annotations

import asyncio
import contextlib
import logging

from app.database import engine
from app.services.detection_worker import start_detection_worker

logger = logging.getLogger(__name__)


async def _wait_for_db() -> None:
    """Poll until the DB is reachable (it may start up slower than us)."""
    from sqlalchemy import text

    from app.database import async_session_factory

    for attempt in range(90):
        try:
            async with async_session_factory() as session:
                await session.execute(text("SELECT 1"))
            return
        except Exception:
            if attempt == 89:
                raise
            await asyncio.sleep(2)


async def _run() -> None:
    from app.utils.logging import setup_logging

    setup_logging()
    await _wait_for_db()
    logger.info("Dedicated detection worker started (polling every 2s)")
    task = await start_detection_worker()
    try:
        await asyncio.Future()  # run forever, cancelled on shutdown
    except asyncio.CancelledError:
        pass
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(_run())
