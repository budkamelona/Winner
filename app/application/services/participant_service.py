from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.models import GiveawayParticipant
from app.infrastructure.repositories.participant_repository import ParticipantRepository


class ParticipantService:
    def __init__(self, session: AsyncSession):
        self.repo = ParticipantRepository(session)

    async def get_participant(self, giveaway_id: int, telegram_user_id: int) -> GiveawayParticipant | None:
        return await self.repo.get(giveaway_id, telegram_user_id)

    async def get_all_participants(self, giveaway_id: int) -> list[GiveawayParticipant]:
        return await self.repo.get_all(giveaway_id)

    async def count_participants(self, giveaway_id: int) -> int:
        return await self.repo.count(giveaway_id)

    async def register(
        self,
        giveaway_id: int,
        telegram_user_id: int,
        username: str | None,
        first_name: str | None,
    ) -> GiveawayParticipant:
        existing = await self.repo.get(giveaway_id, telegram_user_id)
        if existing is not None:
            return existing
        return await self.repo.create(giveaway_id, telegram_user_id, username, first_name)

    async def pass_captcha(self, participant: GiveawayParticipant) -> None:
        await self.repo.mark_captcha_passed(participant)

    async def get_by_username(self, giveaway_id: int, username: str) -> GiveawayParticipant | None:
        return await self.repo.get_by_username(giveaway_id, username)
