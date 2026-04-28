from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.models import GiveawayParticipant


class ParticipantRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, giveaway_id: int, telegram_user_id: int) -> GiveawayParticipant | None:
        result = await self.session.execute(
            select(GiveawayParticipant).where(
                GiveawayParticipant.giveaway_id == giveaway_id,
                GiveawayParticipant.telegram_user_id == telegram_user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_all(self, giveaway_id: int) -> list[GiveawayParticipant]:
        result = await self.session.execute(
            select(GiveawayParticipant).where(
                GiveawayParticipant.giveaway_id == giveaway_id,
                GiveawayParticipant.is_captcha_passed == True,
            )
        )
        return list(result.scalars().all())

    async def count(self, giveaway_id: int) -> int:
        result = await self.session.execute(
            select(func.count()).where(
                GiveawayParticipant.giveaway_id == giveaway_id,
                GiveawayParticipant.is_captcha_passed == True,
            )
        )
        return result.scalar_one()

    async def create(
        self,
        giveaway_id: int,
        telegram_user_id: int,
        username: str | None,
        first_name: str | None,
    ) -> GiveawayParticipant:
        participant = GiveawayParticipant(
            giveaway_id=giveaway_id,
            telegram_user_id=telegram_user_id,
            username=username,
            first_name=first_name,
            is_captcha_passed=False,
        )
        self.session.add(participant)
        await self.session.flush()
        return participant

    async def mark_captcha_passed(self, participant: GiveawayParticipant) -> None:
        participant.is_captcha_passed = True
        await self.session.flush()

    async def get_by_username(self, giveaway_id: int, username: str) -> GiveawayParticipant | None:
        result = await self.session.execute(
            select(GiveawayParticipant).where(
                GiveawayParticipant.giveaway_id == giveaway_id,
                GiveawayParticipant.username == username.lstrip("@"),
                GiveawayParticipant.is_captcha_passed == True,
            )
        )
        return result.scalar_one_or_none()
