from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.infrastructure.models import CaptchaChallenge


def captcha_keyboard(challenge: CaptchaChallenge, answers: list[int]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=str(a),
                    callback_data=f"captcha:{challenge.id}:{a}",
                )
                for a in answers
            ]
        ]
    )
