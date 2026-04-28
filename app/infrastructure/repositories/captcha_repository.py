from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.models import CaptchaChallenge


class CaptchaRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_active(self, giveaway_id: int, telegram_user_id: int) -> CaptchaChallenge | None:
        now = datetime.utcnow()
        result = await self.session.execute(
            select(CaptchaChallenge).where(
                CaptchaChallenge.giveaway_id == giveaway_id,
                CaptchaChallenge.telegram_user_id == telegram_user_id,
                CaptchaChallenge.is_solved == False,
                CaptchaChallenge.expires_at_utc > now,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, captcha_id: int) -> CaptchaChallenge | None:
        result = await self.session.execute(
            select(CaptchaChallenge).where(CaptchaChallenge.id == captcha_id)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        giveaway_id: int,
        telegram_user_id: int,
        question: str,
        correct_answer: int,
        wrong_answer_1: int,
        wrong_answer_2: int,
        expires_at_utc: datetime,
    ) -> CaptchaChallenge:
        challenge = CaptchaChallenge(
            giveaway_id=giveaway_id,
            telegram_user_id=telegram_user_id,
            question=question,
            correct_answer=correct_answer,
            wrong_answer_1=wrong_answer_1,
            wrong_answer_2=wrong_answer_2,
            expires_at_utc=expires_at_utc,
            is_solved=False,
        )
        self.session.add(challenge)
        await self.session.flush()
        return challenge

    async def mark_solved(self, challenge: CaptchaChallenge) -> None:
        challenge.is_solved = True
        await self.session.flush()
