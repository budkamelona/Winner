from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.infrastructure.models import FinishMode, Giveaway, GiveawayStatus


class GiveawayRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, giveaway_id: int) -> Giveaway | None:
        result = await self.session.execute(
            select(Giveaway)
            .options(selectinload(Giveaway.channel))
            .where(Giveaway.id == giveaway_id)
        )
        return result.scalar_one_or_none()

    async def get_by_owner(self, owner_user_id: int) -> list[Giveaway]:
        result = await self.session.execute(
            select(Giveaway)
            .options(selectinload(Giveaway.channel))
            .where(Giveaway.owner_user_id == owner_user_id)
            .order_by(Giveaway.created_at_utc.desc())
        )
        return list(result.scalars().all())

    async def get_active_by_time(self, now: datetime) -> list[Giveaway]:
        result = await self.session.execute(
            select(Giveaway)
            .options(selectinload(Giveaway.channel))
            .where(
                Giveaway.status == GiveawayStatus.active,
                Giveaway.finish_mode == FinishMode.by_time,
                Giveaway.finish_at_utc <= now,
            )
        )
        return list(result.scalars().all())

    async def get_all_active_scheduled(self) -> list[Giveaway]:
        result = await self.session.execute(
            select(Giveaway)
            .options(selectinload(Giveaway.channel))
            .where(
                Giveaway.status == GiveawayStatus.active,
                Giveaway.finish_mode == FinishMode.by_time,
                Giveaway.finish_at_utc.isnot(None),
            )
        )
        return list(result.scalars().all())

    async def create(
        self,
        owner_user_id: int,
        channel_id: int,
        text: str,
        winners_count: int,
        finish_mode: str,
        winner_selection_mode: str,
        finish_at_utc: datetime | None = None,
    ) -> Giveaway:
        giveaway = Giveaway(
            owner_user_id=owner_user_id,
            channel_id=channel_id,
            text=text,
            winners_count=winners_count,
            finish_mode=finish_mode,
            winner_selection_mode=winner_selection_mode,
            finish_at_utc=finish_at_utc,
            status=GiveawayStatus.active,
        )
        self.session.add(giveaway)
        await self.session.flush()
        return giveaway

    async def update_post_message_id(self, giveaway: Giveaway, message_id: int) -> None:
        giveaway.post_message_id = message_id
        giveaway.published_at_utc = datetime.utcnow()
        await self.session.flush()

    async def delete(self, giveaway: Giveaway) -> None:
        from sqlalchemy import delete
        from app.infrastructure.models import (
            CaptchaChallenge,
            GiveawayParticipant,
            GiveawayWinner,
        )

        await self.session.execute(
            delete(CaptchaChallenge).where(CaptchaChallenge.giveaway_id == giveaway.id)
        )
        await self.session.execute(
            delete(GiveawayWinner).where(GiveawayWinner.giveaway_id == giveaway.id)
        )
        await self.session.execute(
            delete(GiveawayParticipant).where(GiveawayParticipant.giveaway_id == giveaway.id)
        )
        await self.session.delete(giveaway)
        await self.session.flush()

    async def finish(self, giveaway: Giveaway, result_message_id: int | None = None) -> None:
        giveaway.status = GiveawayStatus.finished
        giveaway.finished_at_utc = datetime.utcnow()
        if result_message_id is not None:
            giveaway.result_message_id = result_message_id
        await self.session.flush()
