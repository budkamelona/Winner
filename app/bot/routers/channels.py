from aiogram import Bot, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.application.services.channel_service import ChannelService
from app.bot.filters import IsAdmin
from app.bot.keyboards.channels import channel_detail_keyboard, channels_list_keyboard
from app.bot.keyboards.main_menu import main_menu_keyboard
from app.bot.states.channel_add import ChannelAddStates
from app.infrastructure.database import async_session_factory
from app.infrastructure.repositories.channel_repository import ChannelRepository
from app.infrastructure.repositories.user_repository import UserRepository
from app.infrastructure.telegram.telegram_service import TelegramService

router = Router()
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


async def get_db_user_id(telegram_user_id: int) -> int | None:
    async with async_session_factory() as session:
        repo = UserRepository(session)
        user = await repo.get_by_telegram_id(telegram_user_id)
        return user.id if user else None


@router.callback_query(lambda c: c.data == "menu:my_channels")
async def cb_my_channels(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    user_id = await get_db_user_id(callback.from_user.id)
    if user_id is None:
        await callback.answer("Ошибка: пользователь не найден.", show_alert=True)
        return

    async with async_session_factory() as session:
        repo = ChannelRepository(session)
        channels = await repo.get_channels_by_owner(user_id)

    if channels:
        text = "📢 Ваши каналы:"
    else:
        text = "У вас пока нет добавленных каналов."

    await callback.message.edit_text(text, reply_markup=channels_list_keyboard(channels))
    await callback.answer()


@router.callback_query(lambda c: c.data == "channel:add")
async def cb_channel_add(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ChannelAddStates.waiting_for_channel)
    await callback.message.edit_text(
        "Введите @username канала или перешлите сообщение из канала.\n\n"
        "Бот должен быть добавлен администратором в этот канал с правом публиковать сообщения."
    )
    await callback.answer()


@router.message(ChannelAddStates.waiting_for_channel)
async def msg_channel_identifier(message: Message, state: FSMContext, bot: Bot):
    identifier = None

    if message.forward_from_chat:
        identifier = message.forward_from_chat.id
    elif message.text:
        text = message.text.strip()
        if text.lstrip("-").isdigit():
            identifier = int(text)
        elif text.startswith("@"):
            identifier = text
        else:
            await message.answer(
                "Не удалось распознать канал. Введите @username или перешлите сообщение из канала."
            )
            return

    if identifier is None:
        await message.answer("Не удалось распознать канал. Попробуйте ещё раз.")
        return

    user_id = await get_db_user_id(message.from_user.id)
    if user_id is None:
        await message.answer("Ошибка: пользователь не найден.")
        return

    async with async_session_factory() as session:
        tg_service = TelegramService(bot)
        service = ChannelService(session, tg_service)
        result = await service.verify_and_add_channel(
            owner_user_id=user_id,
            owner_telegram_id=message.from_user.id,
            channel_identifier=identifier,
        )
        if result.ok:
            await session.commit()

    await state.clear()

    if not result.ok:
        await message.answer(f"❌ {result.error}", reply_markup=main_menu_keyboard())
        return

    ch_display = f"@{result.username}" if result.username else result.title
    await message.answer(
        f"✅ Канал <b>{result.title}</b> ({ch_display}) успешно добавлен!",
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(lambda c: c.data.startswith("channel:select:"))
async def cb_channel_select(callback: CallbackQuery):
    channel_id = int(callback.data.split(":")[2])
    user_id = await get_db_user_id(callback.from_user.id)

    async with async_session_factory() as session:
        repo = ChannelRepository(session)
        channel = await repo.get_by_id(channel_id)

    if channel is None or channel.owner_user_id != user_id:
        await callback.answer("Канал не найден.", show_alert=True)
        return

    ch_display = f"@{channel.username}" if channel.username else str(channel.telegram_channel_id)
    text = (
        f"📢 <b>{channel.title}</b>\n"
        f"Username: {ch_display}\n"
        f"ID: <code>{channel.telegram_channel_id}</code>"
    )
    await callback.message.edit_text(text, reply_markup=channel_detail_keyboard(channel_id), parse_mode="HTML")
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("channel:delete:"))
async def cb_channel_delete(callback: CallbackQuery):
    channel_id = int(callback.data.split(":")[2])
    user_id = await get_db_user_id(callback.from_user.id)

    async with async_session_factory() as session:
        repo = ChannelRepository(session)
        channel = await repo.get_by_id(channel_id)
        if channel is None or channel.owner_user_id != user_id:
            await callback.answer("Канал не найден.", show_alert=True)
            return
        await repo.delete(channel)
        await session.commit()

    await callback.message.edit_text("✅ Канал удалён.", reply_markup=main_menu_keyboard())
    await callback.answer()
