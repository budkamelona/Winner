from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.models import GiveawayWinner, SelectionType


class WinnerRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_giveaway(self, giveaway_id: int) -> list[GiveawayWinner]:
        result = await self.session.execute(
            select(GiveawayWinner).where(GiveawayWinner.giveaway_id == giveaway_id)
        )
        return list(result.scalars().all())

    async def create(
        self,
        giveaway_id: int,
        telegram_user_id: int,
        username: str | None,
        selection_type: SelectionType,
    ) -> GiveawayWinner:
        winner = GiveawayWinner(
            giveaway_id=giveaway_id,
            telegram_user_id=telegram_user_id,
            username=username,
            selection_type=selection_type,
        )
        self.session.add(winner)
        await self.session.flush()
        return winner

    async def create_many(
        self,
        giveaway_id: int,
        participants: list,
        selection_type: SelectionType,
    ) -> list[GiveawayWinner]:
        winners = []
        for p in participants:
            winner = GiveawayWinner(
                giveaway_id=giveaway_id,
                telegram_user_id=p.telegram_user_id,
                username=p.username,
                selection_type=selection_type,
            )
            self.session.add(winner)
            winners.append(winner)
        await self.session.flush()
        return winners
