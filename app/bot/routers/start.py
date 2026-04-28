from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.main_menu import main_menu_keyboard
from app.config import settings
from app.infrastructure.database import async_session_factory
from app.infrastructure.repositories.user_repository import UserRepository

router = Router()


async def ensure_user(telegram_user_id: int, username: str | None, first_name: str | None):
    async with async_session_factory() as session:
        repo = UserRepository(session)
        user = await repo.get_or_create(telegram_user_id, username, first_name)
        await session.commit()
        return user


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    args = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else ""

    await ensure_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name,
    )

    if args.startswith("join_"):
        giveaway_id_str = args[5:]
        if giveaway_id_str.isdigit():
            from app.bot.routers.participation import start_participation
            await start_participation(message, state, int(giveaway_id_str))
            return

    await state.clear()

    if message.from_user.id == settings.ADMIN_TELEGRAM_ID:
        await message.answer(
            "👋 Добро пожаловать!\n\nВыберите действие:",
            reply_markup=main_menu_keyboard(),
        )
    else:
        await message.answer(
            "👋 Привет!\n\nЯ бот для проведения розыгрышей.\n"
            "Чтобы участвовать, нажми кнопку «🎁 Участвовать» под постом розыгрыша в канале."
        )


@router.callback_query(lambda c: c.data == "menu:back")
@router.callback_query(lambda c: c.data == "menu:cancel")
async def cb_main_menu(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != settings.ADMIN_TELEGRAM_ID:
        await callback.answer("Нет доступа.", show_alert=True)
        return
    await state.clear()
    await callback.message.edit_text(
        "Главное меню:",
        reply_markup=main_menu_keyboard(),
    )
    await callback.answer()
