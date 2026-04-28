from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import InlineKeyboardMarkup
from loguru import logger


class TelegramService:
    def __init__(self, bot: Bot):
        self.bot = bot

    async def get_chat(self, chat_id: int | str):
        try:
            return await self.bot.get_chat(chat_id)
        except (TelegramBadRequest, TelegramForbiddenError) as e:
            logger.warning(f"get_chat failed for {chat_id}: {e}")
            return None

    async def get_chat_member(self, chat_id: int | str, user_id: int):
        try:
            return await self.bot.get_chat_member(chat_id, user_id)
        except (TelegramBadRequest, TelegramForbiddenError) as e:
            logger.warning(f"get_chat_member failed for chat={chat_id} user={user_id}: {e}")
            return None

    async def send_message(
        self,
        chat_id: int | str,
        text: str,
        reply_markup: InlineKeyboardMarkup | None = None,
        reply_to_message_id: int | None = None,
    ):
        try:
            kwargs = {"chat_id": chat_id, "text": text}
            if reply_markup:
                kwargs["reply_markup"] = reply_markup
            if reply_to_message_id:
                kwargs["reply_to_message_id"] = reply_to_message_id
            return await self.bot.send_message(**kwargs)
        except TelegramBadRequest as e:
            if "reply message not found" in str(e).lower() or "message to reply not found" in str(e).lower():
                logger.warning(f"Reply not possible, sending standalone: {e}")
                kwargs.pop("reply_to_message_id", None)
                return await self.bot.send_message(**kwargs)
            logger.error(f"send_message failed: {e}")
            raise
        except TelegramForbiddenError as e:
            logger.error(f"send_message forbidden: {e}")
            raise

    async def edit_message_reply_markup(
        self,
        chat_id: int | str,
        message_id: int,
        reply_markup: InlineKeyboardMarkup | None = None,
    ):
        try:
            await self.bot.edit_message_reply_markup(
                chat_id=chat_id, message_id=message_id, reply_markup=reply_markup
            )
        except TelegramBadRequest as e:
            logger.warning(f"edit_message_reply_markup failed: {e}")

    async def delete_message(self, chat_id: int | str, message_id: int) -> bool:
        try:
            await self.bot.delete_message(chat_id=chat_id, message_id=message_id)
            return True
        except (TelegramBadRequest, TelegramForbiddenError) as e:
            logger.warning(f"delete_message failed for chat={chat_id} msg={message_id}: {e}")
            return False

    async def is_bot_admin(self, chat_id: int) -> bool:
        me = await self.bot.get_me()
        member = await self.get_chat_member(chat_id, me.id)
        if member is None:
            return False
        return member.status in ("administrator", "creator")

    async def bot_can_post(self, chat_id: int) -> bool:
        me = await self.bot.get_me()
        member = await self.get_chat_member(chat_id, me.id)
        if member is None:
            return False
        if member.status == "creator":
            return True
        if member.status == "administrator":
            return getattr(member, "can_post_messages", False)
        return False

    async def is_user_admin(self, chat_id: int, user_id: int) -> bool:
        member = await self.get_chat_member(chat_id, user_id)
        if member is None:
            return False
        return member.status in ("administrator", "creator")
