from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.models import Giveaway, GiveawayStatus, WinnerSelectionMode
from app.infrastructure.repositories.giveaway_repository import GiveawayRepository
from app.infrastructure.repositories.participant_repository import ParticipantRepository
from app.infrastructure.repositories.winner_repository import WinnerRepository
from app.infrastructure.telegram.telegram_service import TelegramService


def format_winners_text(winners, participants_count: int, selection_mode: str) -> str:
    lines = ["🎉 Розыгрыш завершён!\n\nПобедители:"]
    for i, w in enumerate(winners, 1):
        if w.username:
            lines.append(f"{i}. @{w.username}")
        else:
            lines.append(f"{i}. ID: {w.telegram_user_id}")
    lines.append(f"\nКоличество участников: {participants_count}")
    return "\n".join(lines)


class GiveawayService:
    def __init__(self, session: AsyncSession, telegram_service: TelegramService):
        self.repo = GiveawayRepository(session)
        self.participant_repo = ParticipantRepository(session)
        self.winner_repo = WinnerRepository(session)
        self.tg = telegram_service

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
        return await self.repo.create(
            owner_user_id=owner_user_id,
            channel_id=channel_id,
            text=text,
            winners_count=winners_count,
            finish_mode=finish_mode,
            winner_selection_mode=winner_selection_mode,
            finish_at_utc=finish_at_utc,
        )

    async def get_by_id(self, giveaway_id: int) -> Giveaway | None:
        return await self.repo.get_by_id(giveaway_id)

    async def get_by_id_for_owner(self, giveaway_id: int, owner_user_id: int) -> Giveaway | None:
        giveaway = await self.repo.get_by_id(giveaway_id)
        if giveaway is None or giveaway.owner_user_id != owner_user_id:
            return None
        return giveaway

    async def get_by_owner(self, owner_user_id: int) -> list[Giveaway]:
        return await self.repo.get_by_owner(owner_user_id)

    async def set_post_message_id(self, giveaway: Giveaway, message_id: int) -> None:
        await self.repo.update_post_message_id(giveaway, message_id)

    async def publish_results(
        self,
        giveaway: Giveaway,
        winners,
        telegram_channel_id: int,
    ) -> None:
        participants_count = await self.participant_repo.count(giveaway.id)
        text = format_winners_text(winners, participants_count, giveaway.winner_selection_mode)

        msg = await self.tg.send_message(
            chat_id=telegram_channel_id,
            text=text,
            reply_to_message_id=giveaway.post_message_id,
        )
        result_msg_id = msg.message_id if msg else None
        await self.repo.finish(giveaway, result_msg_id)

    async def finish(self, giveaway: Giveaway) -> None:
        await self.repo.finish(giveaway)

    async def get_due_giveaways(self) -> list[Giveaway]:
        return await self.repo.get_active_by_time(datetime.utcnow())

    async def update_participant_button(
        self,
        giveaway: Giveaway,
        telegram_channel_id: int,
        count: int,
        bot_username: str,
    ) -> None:
        from app.bot.keyboards.giveaway import make_participate_keyboard

        if giveaway.post_message_id is None:
            return
        kb = make_participate_keyboard(giveaway.id, count, bot_username)
        await self.tg.edit_message_reply_markup(
            chat_id=telegram_channel_id,
            message_id=giveaway.post_message_id,
            reply_markup=kb,
        )
