from zoneinfo import ZoneInfo

from aiogram import Bot, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.application.services.giveaway_service import GiveawayService
from app.config import settings
from app.application.services.winner_service import WinnerService
from app.bot.filters import IsAdmin
from app.bot.keyboards.giveaway import (
    confirm_delete_keyboard,
    confirm_finish_keyboard,
    giveaway_manage_keyboard,
    giveaways_list_keyboard,
)
from app.bot.keyboards.main_menu import main_menu_keyboard
from app.bot.states.giveaway_finish import GiveawayFinishStates
from app.infrastructure.database import async_session_factory
from app.infrastructure.models import GiveawayStatus, WinnerSelectionMode
from app.infrastructure.repositories.channel_repository import ChannelRepository
from app.infrastructure.repositories.giveaway_repository import GiveawayRepository
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


@router.callback_query(lambda c: c.data == "menu:my_giveaways")
async def cb_my_giveaways(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    user_id = await get_db_user_id(callback.from_user.id)
    if user_id is None:
        await callback.answer("Ошибка.", show_alert=True)
        return

    async with async_session_factory() as session:
        repo = GiveawayRepository(session)
        giveaways = await repo.get_by_owner(user_id)

    if not giveaways:
        await callback.message.edit_text(
            "У вас пока нет розыгрышей.", reply_markup=main_menu_keyboard()
        )
    else:
        await callback.message.edit_text(
            "🗒 Ваши розыгрыши:", reply_markup=giveaways_list_keyboard(giveaways)
        )
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("giveaway:view:"))
async def cb_giveaway_view(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    giveaway_id = int(callback.data.split(":")[2])
    user_id = await get_db_user_id(callback.from_user.id)

    async with async_session_factory() as session:
        repo = GiveawayRepository(session)
        giveaway = await repo.get_by_id(giveaway_id)

    if giveaway is None or giveaway.owner_user_id != user_id:
        await callback.answer("Розыгрыш не найден.", show_alert=True)
        return

    status_labels = {
        "active": "🟢 Активен",
        "finished": "✅ Завершён",
        "draft": "📝 Черновик",
        "scheduled": "⏰ Запланирован",
        "cancelled": "❌ Отменён",
    }
    finish_mode_labels = {"manual": "Вручную", "by_time": "По времени"}
    selection_labels = {"random": "Случайный", "manual": "Вручную"}

    lines = [
        f"<b>Розыгрыш #{giveaway.id}</b>",
        f"Статус: {status_labels.get(giveaway.status, giveaway.status)}",
        f"Канал: {giveaway.channel.title}",
        f"Победителей: {giveaway.winners_count}",
        f"Завершение: {finish_mode_labels.get(giveaway.finish_mode, giveaway.finish_mode)}",
        f"Выбор победителей: {selection_labels.get(giveaway.winner_selection_mode, '')}",
    ]
    if giveaway.finish_at_utc:
        local = giveaway.finish_at_utc.replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo(settings.TIMEZONE))
        lines.append(f"Завершить ({settings.TIMEZONE}): {local.strftime('%d.%m.%Y %H:%M')}")

    text = "\n".join(lines)
    await callback.message.edit_text(text, reply_markup=giveaway_manage_keyboard(giveaway), parse_mode="HTML")
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("giveaway:finish:"))
async def cb_giveaway_finish(callback: CallbackQuery, state: FSMContext):
    giveaway_id = int(callback.data.split(":")[2])
    user_id = await get_db_user_id(callback.from_user.id)

    async with async_session_factory() as session:
        repo = GiveawayRepository(session)
        giveaway = await repo.get_by_id(giveaway_id)

    if giveaway is None or giveaway.owner_user_id != user_id:
        await callback.answer("Розыгрыш не найден.", show_alert=True)
        return

    if giveaway.status != GiveawayStatus.active:
        await callback.answer("Розыгрыш уже завершён или недоступен.", show_alert=True)
        return

    await callback.message.edit_text(
        f"Завершить розыгрыш #{giveaway_id}?",
        reply_markup=confirm_finish_keyboard(giveaway_id),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("giveaway:finish_confirm:"))
async def cb_giveaway_finish_confirm(callback: CallbackQuery, state: FSMContext, bot: Bot):
    giveaway_id = int(callback.data.split(":")[2])
    user_id = await get_db_user_id(callback.from_user.id)

    async with async_session_factory() as session:
        repo = GiveawayRepository(session)
        giveaway = await repo.get_by_id(giveaway_id)

        if giveaway is None or giveaway.owner_user_id != user_id:
            await callback.answer("Розыгрыш не найден.", show_alert=True)
            return

        if giveaway.status != GiveawayStatus.active:
            await callback.answer("Розыгрыш уже завершён.", show_alert=True)
            return

        if giveaway.winner_selection_mode == WinnerSelectionMode.manual:
            await state.update_data(giveaway_id=giveaway_id)
            await state.set_state(GiveawayFinishStates.entering_winners)
            await callback.message.edit_text(
                f"Введите {giveaway.winners_count} победителей — по одному на строку.\n"
                "Можно указать @username или user_id.\n"
                "Победители должны быть участниками этого розыгрыша."
            )
            await callback.answer()
            return

        winner_service = WinnerService(session)
        result = await winner_service.select_random(giveaway_id, giveaway.winners_count)
        if not result.ok:
            await callback.answer(result.error, show_alert=True)
            return

        tg_service = TelegramService(bot)
        channel_repo = ChannelRepository(session)
        channel = await channel_repo.get_by_id(giveaway.channel_id)
        giveaway_service = GiveawayService(session, tg_service)

        await giveaway_service.publish_results(giveaway, result.winners, channel.telegram_channel_id)
        await session.commit()

    await callback.message.edit_text(
        f"✅ Розыгрыш #{giveaway_id} завершён! Результаты опубликованы.",
        reply_markup=main_menu_keyboard(),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("giveaway:delete:"))
async def cb_giveaway_delete(callback: CallbackQuery):
    giveaway_id = int(callback.data.split(":")[2])
    user_id = await get_db_user_id(callback.from_user.id)

    async with async_session_factory() as session:
        repo = GiveawayRepository(session)
        giveaway = await repo.get_by_id(giveaway_id)

    if giveaway is None or giveaway.owner_user_id != user_id:
        await callback.answer("Розыгрыш не найден.", show_alert=True)
        return

    await callback.message.edit_text(
        f"Удалить розыгрыш #{giveaway_id}?\n\n"
        f"Будут удалены: розыгрыш, все участники, победители, капчи.\n"
        f"Сообщения в канале — тоже (если есть).\n\n"
        f"<b>Действие необратимо.</b>",
        reply_markup=confirm_delete_keyboard(giveaway_id),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("giveaway:delete_confirm:"))
async def cb_giveaway_delete_confirm(callback: CallbackQuery, state: FSMContext, bot: Bot):
    giveaway_id = int(callback.data.split(":")[2])
    user_id = await get_db_user_id(callback.from_user.id)

    async with async_session_factory() as session:
        repo = GiveawayRepository(session)
        giveaway = await repo.get_by_id(giveaway_id)

        if giveaway is None or giveaway.owner_user_id != user_id:
            await callback.answer("Розыгрыш не найден.", show_alert=True)
            return

        channel_repo = ChannelRepository(session)
        channel = await channel_repo.get_by_id(giveaway.channel_id)

        post_msg_id = giveaway.post_message_id
        result_msg_id = giveaway.result_message_id
        chat_id = channel.telegram_channel_id if channel else None

        await repo.delete(giveaway)
        await session.commit()

    if chat_id is not None:
        tg = TelegramService(bot)
        if post_msg_id:
            await tg.delete_message(chat_id, post_msg_id)
        if result_msg_id:
            await tg.delete_message(chat_id, result_msg_id)

    from app.bot.tasks import cancel_scheduled_finish
    cancel_scheduled_finish(giveaway_id)

    await state.clear()
    await callback.message.edit_text(
        f"✅ Розыгрыш #{giveaway_id} удалён.",
        reply_markup=main_menu_keyboard(),
    )
    await callback.answer()


@router.message(GiveawayFinishStates.entering_winners)
async def msg_enter_winners(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    giveaway_id = data["giveaway_id"]
    identifiers = [line.strip() for line in message.text.strip().splitlines() if line.strip()]
    user_id = await get_db_user_id(message.from_user.id)

    async with async_session_factory() as session:
        repo = GiveawayRepository(session)
        giveaway = await repo.get_by_id(giveaway_id)

        if giveaway is None or giveaway.owner_user_id != user_id:
            await message.answer("Розыгрыш не найден.", reply_markup=main_menu_keyboard())
            await state.clear()
            return

        winner_service = WinnerService(session)
        result = await winner_service.select_manual(giveaway_id, identifiers, giveaway.winners_count)
        if not result.ok:
            await message.answer(f"❌ {result.error}\nПопробуйте снова:")
            return

        tg_service = TelegramService(bot)
        channel_repo = ChannelRepository(session)
        channel = await channel_repo.get_by_id(giveaway.channel_id)
        giveaway_service = GiveawayService(session, tg_service)

        await giveaway_service.publish_results(giveaway, result.winners, channel.telegram_channel_id)
        await session.commit()

    await state.clear()
    await message.answer(
        f"✅ Розыгрыш #{giveaway_id} завершён! Результаты опубликованы.",
        reply_markup=main_menu_keyboard(),
    )
