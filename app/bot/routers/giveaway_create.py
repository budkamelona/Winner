from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Bot, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.application.services.giveaway_service import GiveawayService
from app.bot.filters import IsAdmin
from app.bot.keyboards.channels import channel_select_for_giveaway_keyboard
from app.bot.keyboards.giveaway import (
    finish_mode_keyboard,
    make_participate_keyboard,
    winner_selection_mode_keyboard,
)
from app.bot.keyboards.main_menu import main_menu_keyboard
from app.bot.states.giveaway_create import GiveawayCreateStates
from app.config import settings
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


@router.callback_query(lambda c: c.data == "menu:create_giveaway")
async def cb_create_giveaway(callback: CallbackQuery, state: FSMContext):
    user_id = await get_db_user_id(callback.from_user.id)
    if user_id is None:
        await callback.answer("Ошибка.", show_alert=True)
        return

    async with async_session_factory() as session:
        repo = ChannelRepository(session)
        channels = await repo.get_channels_by_owner(user_id)

    if not channels:
        await callback.message.edit_text(
            "У вас нет добавленных каналов.\nСначала добавьте канал через меню 📢 Мои каналы.",
            reply_markup=main_menu_keyboard(),
        )
        await callback.answer()
        return

    await state.set_state(GiveawayCreateStates.choosing_channel)
    await callback.message.edit_text(
        "Выберите канал для публикации розыгрыша:",
        reply_markup=channel_select_for_giveaway_keyboard(channels),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("giveaway:channel:"))
async def cb_giveaway_channel(callback: CallbackQuery, state: FSMContext):
    channel_id = int(callback.data.split(":")[2])
    user_id = await get_db_user_id(callback.from_user.id)

    async with async_session_factory() as session:
        repo = ChannelRepository(session)
        channel = await repo.get_by_id(channel_id)

    if channel is None or channel.owner_user_id != user_id:
        await callback.answer("Канал не найден.", show_alert=True)
        return

    await state.update_data(channel_id=channel_id)
    await state.set_state(GiveawayCreateStates.entering_text)
    await callback.message.edit_text("Введите текст поста розыгрыша:")
    await callback.answer()


@router.message(GiveawayCreateStates.entering_text)
async def msg_giveaway_text(message: Message, state: FSMContext):
    if not message.text or len(message.text.strip()) < 3:
        await message.answer("Текст слишком короткий. Введите снова:")
        return
    await state.update_data(text=message.text.strip())
    await state.set_state(GiveawayCreateStates.entering_winners_count)
    await message.answer("Сколько победителей? Введите число:")


@router.message(GiveawayCreateStates.entering_winners_count)
async def msg_winners_count(message: Message, state: FSMContext):
    if not message.text or not message.text.strip().isdigit() or int(message.text.strip()) < 1:
        await message.answer("Введите корректное число победителей (≥ 1):")
        return
    await state.update_data(winners_count=int(message.text.strip()))
    await state.set_state(GiveawayCreateStates.choosing_finish_mode)
    await message.answer("Как завершить розыгрыш?", reply_markup=finish_mode_keyboard())


@router.callback_query(lambda c: c.data.startswith("giveaway:finish_mode:"))
async def cb_finish_mode(callback: CallbackQuery, state: FSMContext):
    mode = callback.data.split(":")[2]
    await state.update_data(finish_mode=mode)

    if mode == "by_time":
        await state.set_state(GiveawayCreateStates.entering_finish_time)
        await callback.message.edit_text(
            f"Введите дату и время завершения в формате:\n"
            f"<code>ДД.ММ.ГГГГ ЧЧ:ММ</code>\n\n"
            f"Часовой пояс: <b>{settings.TIMEZONE}</b>",
            parse_mode="HTML",
        )
    else:
        await state.set_state(GiveawayCreateStates.choosing_winner_selection_mode)
        await callback.message.edit_text(
            "Как выбирать победителей?",
            reply_markup=winner_selection_mode_keyboard(),
        )
    await callback.answer()


@router.message(GiveawayCreateStates.entering_finish_time)
async def msg_finish_time(message: Message, state: FSMContext):
    text = message.text.strip() if message.text else ""
    try:
        local_naive = datetime.strptime(text, "%d.%m.%Y %H:%M")
    except ValueError:
        await message.answer("Неверный формат. Введите: ДД.ММ.ГГГГ ЧЧ:ММ")
        return

    tz = ZoneInfo(settings.TIMEZONE)
    local_dt = local_naive.replace(tzinfo=tz)
    finish_dt_utc = local_dt.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)

    if finish_dt_utc <= datetime.utcnow():
        await message.answer("Дата должна быть в будущем. Введите снова:")
        return

    await state.update_data(finish_at_utc=finish_dt_utc.isoformat())
    await state.set_state(GiveawayCreateStates.choosing_winner_selection_mode)
    await message.answer("Как выбирать победителей?", reply_markup=winner_selection_mode_keyboard())


@router.callback_query(lambda c: c.data.startswith("giveaway:winner_mode:"))
async def cb_winner_mode(callback: CallbackQuery, state: FSMContext, bot: Bot):
    winner_mode = callback.data.split(":")[2]
    data = await state.get_data()
    await state.update_data(winner_selection_mode=winner_mode)

    user_id = await get_db_user_id(callback.from_user.id)
    if user_id is None:
        await callback.answer("Ошибка.", show_alert=True)
        return

    channel_id = data["channel_id"]
    text = data["text"]
    winners_count = data["winners_count"]
    finish_mode = data["finish_mode"]
    finish_at_utc = None
    if "finish_at_utc" in data:
        finish_at_utc = datetime.fromisoformat(data["finish_at_utc"])

    async with async_session_factory() as session:
        tg_service = TelegramService(bot)
        giveaway_service = GiveawayService(session, tg_service)
        channel_repo = ChannelRepository(session)

        channel = await channel_repo.get_by_id(channel_id)
        if channel is None or channel.owner_user_id != user_id:
            await callback.answer("Канал не найден.", show_alert=True)
            return

        giveaway = await giveaway_service.create(
            owner_user_id=user_id,
            channel_id=channel_id,
            text=text,
            winners_count=winners_count,
            finish_mode=finish_mode,
            winner_selection_mode=winner_mode,
            finish_at_utc=finish_at_utc,
        )

        kb = make_participate_keyboard(giveaway.id, 0, settings.BOT_USERNAME)
        sent = await tg_service.send_message(
            chat_id=channel.telegram_channel_id,
            text=text,
            reply_markup=kb,
        )

        if sent:
            await giveaway_service.set_post_message_id(giveaway, sent.message_id)

        await session.commit()

        giveaway_id = giveaway.id

    await state.clear()

    if finish_mode == "by_time" and finish_at_utc:
        from app.bot.tasks import schedule_giveaway
        schedule_giveaway(giveaway_id, finish_at_utc)

    await callback.message.edit_text(
        f"✅ Розыгрыш #{giveaway_id} создан и опубликован в канале!",
        reply_markup=main_menu_keyboard(),
    )
    await callback.answer()
