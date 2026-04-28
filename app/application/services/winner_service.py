import random
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.models import GiveawayWinner, SelectionType
from app.infrastructure.repositories.participant_repository import ParticipantRepository
from app.infrastructure.repositories.winner_repository import WinnerRepository


@dataclass
class WinnerSelectionResult:
    ok: bool
    winners: list[GiveawayWinner] | None = None
    error: str | None = None


class WinnerService:
    def __init__(self, session: AsyncSession):
        self.winner_repo = WinnerRepository(session)
        self.participant_repo = ParticipantRepository(session)

    async def select_random(self, giveaway_id: int, count: int) -> WinnerSelectionResult:
        participants = await self.participant_repo.get_all(giveaway_id)
        if len(participants) < count:
            return WinnerSelectionResult(
                ok=False,
                error=f"Недостаточно участников. Участников: {len(participants)}, победителей: {count}.",
            )
        chosen = random.sample(participants, count)
        winners = await self.winner_repo.create_many(giveaway_id, chosen, SelectionType.random)
        return WinnerSelectionResult(ok=True, winners=winners)

    async def select_manual(
        self, giveaway_id: int, identifiers: list[str], count: int
    ) -> WinnerSelectionResult:
        if len(identifiers) != count:
            return WinnerSelectionResult(
                ok=False,
                error=f"Необходимо указать ровно {count} победителей, указано {len(identifiers)}.",
            )

        winners = []
        seen = set()
        for ident in identifiers:
            ident = ident.strip()
            participant = None

            if ident.lstrip("@").isdigit():
                participant = await self.participant_repo.get(giveaway_id, int(ident.lstrip("@")))
            else:
                participant = await self.participant_repo.get_by_username(giveaway_id, ident)

            if participant is None:
                return WinnerSelectionResult(
                    ok=False,
                    error=f"Пользователь {ident} не участвует в этом розыгрыше.",
                )

            if participant.telegram_user_id in seen:
                return WinnerSelectionResult(
                    ok=False,
                    error=f"Пользователь {ident} указан дважды.",
                )
            seen.add(participant.telegram_user_id)

            winner = await self.winner_repo.create(
                giveaway_id=giveaway_id,
                telegram_user_id=participant.telegram_user_id,
                username=participant.username,
                selection_type=SelectionType.manual,
            )
            winners.append(winner)

        return WinnerSelectionResult(ok=True, winners=winners)

    async def get_winners(self, giveaway_id: int) -> list[GiveawayWinner]:
        return await self.winner_repo.get_by_giveaway(giveaway_id)
