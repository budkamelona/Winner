from datetime import datetime

from aiogram import Bot, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.application.services.captcha_service import CaptchaService
from app.application.services.giveaway_service import GiveawayService
from app.application.services.participant_service import ParticipantService
from app.bot.keyboards.captcha import captcha_keyboard
from app.bot.keyboards.main_menu import main_menu_keyboard
from app.config import settings
from app.infrastructure.database import async_session_factory
from app.infrastructure.models import GiveawayStatus
from app.infrastructure.repositories.channel_repository import ChannelRepository
from app.infrastructure.repositories.giveaway_repository import GiveawayRepository
from app.infrastructure.telegram.telegram_service import TelegramService

router = Router()


async def start_participation(message: Message, state: FSMContext, giveaway_id: int):
    await state.clear()

    async with async_session_factory() as session:
        repo = GiveawayRepository(session)
        giveaway = await repo.get_by_id(giveaway_id)

        if giveaway is None:
            await message.answer("Розыгрыш не найден.", reply_markup=main_menu_keyboard())
            return

        if giveaway.status != GiveawayStatus.active:
            await message.answer("Этот розыгрыш уже завершён.", reply_markup=main_menu_keyboard())
            return

        participant_service = ParticipantService(session)
        existing = await participant_service.get_participant(giveaway_id, message.from_user.id)
        if existing and existing.is_captcha_passed:
            await message.answer("Вы уже участвуете в этом розыгрыше.", reply_markup=main_menu_keyboard())
            return

        captcha_service = CaptchaService(session)
        challenge = await captcha_service.get_active_challenge(giveaway_id, message.from_user.id)
        if challenge is None:
            challenge = await captcha_service.create_challenge(giveaway_id, message.from_user.id)

        answers = captcha_service.get_shuffled_answers(challenge)
        await session.commit()

    await message.answer(
        f"Чтобы участвовать в розыгрыше, пройдите капчу:\n\n{challenge.question}",
        reply_markup=captcha_keyboard(challenge, answers),
    )


@router.callback_query(lambda c: c.data.startswith("captcha:"))
async def cb_captcha_answer(callback: CallbackQuery, bot: Bot):
    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("Ошибка.", show_alert=True)
        return

    captcha_id = int(parts[1])
    user_answer = int(parts[2])

    async with async_session_factory() as session:
        captcha_service = CaptchaService(session)
        challenge = await captcha_service.get_by_id(captcha_id)

        if challenge is None:
            await callback.answer("Капча не найдена.", show_alert=True)
            return

        if challenge.is_solved:
            await callback.answer("Эта капча уже была решена.", show_alert=True)
            return

        if challenge.telegram_user_id != callback.from_user.id:
            await callback.answer("Это не ваша капча.", show_alert=True)
            return

        if challenge.expires_at_utc < datetime.utcnow():
            await callback.answer(
                "Срок действия капчи истёк. Нажмите кнопку участия ещё раз.", show_alert=True
            )
            return

        giveaway_id = challenge.giveaway_id

        repo = GiveawayRepository(session)
        giveaway = await repo.get_by_id(giveaway_id)

        if giveaway is None or giveaway.status != GiveawayStatus.active:
            await callback.answer("Этот розыгрыш уже завершён.", show_alert=True)
            return

        if user_answer != challenge.correct_answer:
            new_challenge = await captcha_service.create_challenge(giveaway_id, callback.from_user.id)
            new_answers = captcha_service.get_shuffled_answers(new_challenge)
            await session.commit()

            await callback.message.edit_text(
                f"❌ Неверный ответ! Попробуйте снова:\n\n{new_challenge.question}",
                reply_markup=captcha_keyboard(new_challenge, new_answers),
            )
            await callback.answer()
            return

        await captcha_service.solve(challenge)

        participant_service = ParticipantService(session)
        participant = await participant_service.register(
            giveaway_id=giveaway_id,
            telegram_user_id=callback.from_user.id,
            username=callback.from_user.username,
            first_name=callback.from_user.first_name,
        )
        await participant_service.pass_captcha(participant)
        count = await participant_service.count_participants(giveaway_id)

        channel_repo = ChannelRepository(session)
        channel = await channel_repo.get_by_id(giveaway.channel_id)

        tg = TelegramService(bot)
        giveaway_service = GiveawayService(session, tg)
        await giveaway_service.update_participant_button(
            giveaway, channel.telegram_channel_id, count, settings.BOT_USERNAME
        )

        await session.commit()

    await callback.message.edit_text(
        "✅ Капча пройдена! Вы успешно добавлены в список участников.",
        reply_markup=main_menu_keyboard(),
    )
    await callback.answer("Вы участвуете!")
