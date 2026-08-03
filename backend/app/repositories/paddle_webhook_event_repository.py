from sqlalchemy import select

from app.models.paddle_event import PaddleWebhookEvent
from app.repositories import BaseRepository


class PaddleWebhookEventRepository(BaseRepository):
    async def get_by_event_id(self, event_id: str) -> PaddleWebhookEvent | None:
        stmt = select(PaddleWebhookEvent).where(
            PaddleWebhookEvent.event_id == event_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self, event_id: str, event_type: str, payload: dict
    ) -> PaddleWebhookEvent:
        event = PaddleWebhookEvent(
            event_id=event_id, event_type=event_type, payload=payload
        )
        await self._save(event)
        return event
