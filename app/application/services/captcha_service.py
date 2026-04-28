import random
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.models import CaptchaChallenge
from app.infrastructure.repositories.captcha_repository import CaptchaRepository

CAPTCHA_TTL_MINUTES = 10


def _generate_math_captcha() -> tuple[str, int, int, int]:
    a = random.randint(1, 10)
    b = random.randint(1, 10)
    correct = a + b
    wrong_set = set()
    while len(wrong_set) < 2:
        delta = random.choice([-2, -1, 1, 2])
        candidate = correct + delta
        if candidate > 0 and candidate != correct:
            wrong_set.add(candidate)
    wrongs = list(wrong_set)
    return f"Сколько будет {a} + {b}?", correct, wrongs[0], wrongs[1]


class CaptchaService:
    def __init__(self, session: AsyncSession):
        self.repo = CaptchaRepository(session)

    async def create_challenge(self, giveaway_id: int, telegram_user_id: int) -> CaptchaChallenge:
        question, correct, wrong1, wrong2 = _generate_math_captcha()
        expires_at = datetime.utcnow() + timedelta(minutes=CAPTCHA_TTL_MINUTES)
        return await self.repo.create(
            giveaway_id=giveaway_id,
            telegram_user_id=telegram_user_id,
            question=question,
            correct_answer=correct,
            wrong_answer_1=wrong1,
            wrong_answer_2=wrong2,
            expires_at_utc=expires_at,
        )

    async def get_active_challenge(self, giveaway_id: int, telegram_user_id: int) -> CaptchaChallenge | None:
        return await self.repo.get_active(giveaway_id, telegram_user_id)

    async def get_by_id(self, captcha_id: int) -> CaptchaChallenge | None:
        return await self.repo.get_by_id(captcha_id)

    async def solve(self, challenge: CaptchaChallenge) -> None:
        await self.repo.mark_solved(challenge)

    def get_shuffled_answers(self, challenge: CaptchaChallenge) -> list[int]:
        answers = [challenge.correct_answer, challenge.wrong_answer_1, challenge.wrong_answer_2]
        random.shuffle(answers)
        return answers
