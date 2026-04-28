from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.models import Channel
from app.infrastructure.repositories.channel_repository import ChannelRepository
from app.infrastructure.telegram.telegram_service import TelegramService


@dataclass
class ChannelVerificationResult:
    ok: bool
    error: str | None = None
    telegram_channel_id: int | None = None
    title: str | None = None
    username: str | None = None


class ChannelService:
    def __init__(self, session: AsyncSession, telegram_service: TelegramService):
        self.repo = ChannelRepository(session)
        self.tg = telegram_service

    async def verify_and_add_channel(
        self,
        owner_user_id: int,
        owner_telegram_id: int,
        channel_identifier: str | int,
    ) -> ChannelVerificationResult:
        chat = await self.tg.get_chat(channel_identifier)
        if chat is None:
            return ChannelVerificationResult(ok=False, error="Канал не найден. Проверьте правильность @username или ID.")

        if chat.type not in ("channel", "supergroup"):
            return ChannelVerificationResult(ok=False, error="Указанный чат не является каналом или супергруппой.")

        if not await self.tg.bot_can_post(chat.id):
            return ChannelVerificationResult(
                ok=False,
                error="Бот не является администратором этого канала или не имеет права публиковать сообщения.",
            )

        if not await self.tg.is_user_admin(chat.id, owner_telegram_id):
            return ChannelVerificationResult(
                ok=False,
                error="Вы не являетесь администратором этого канала.",
            )

        existing = await self.repo.get_by_owner_and_telegram_id(owner_user_id, chat.id)
        if existing is not None:
            return ChannelVerificationResult(ok=False, error="Этот канал уже добавлен в ваш список.")

        channel = await self.repo.create(
            owner_user_id=owner_user_id,
            telegram_channel_id=chat.id,
            title=chat.title or str(chat.id),
            username=chat.username,
        )

        return ChannelVerificationResult(
            ok=True,
            telegram_channel_id=channel.telegram_channel_id,
            title=channel.title,
            username=channel.username,
        )

    async def get_user_channels(self, owner_user_id: int) -> list[Channel]:
        return await self.repo.get_channels_by_owner(owner_user_id)

    async def get_channel_by_id(self, channel_id: int, owner_user_id: int) -> Channel | None:
        channel = await self.repo.get_by_id(channel_id)
        if channel is None or channel.owner_user_id != owner_user_id:
            return None
        return channel
