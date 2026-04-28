from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message

from app.config import settings


class IsAdmin(BaseFilter):
    async def __call__(self, event: Message | CallbackQuery) -> bool:
        return event.from_user is not None and event.from_user.id == settings.ADMIN_TELEGRAM_ID
