from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.models import User
from app.infrastructure.repositories.user_repository import UserRepository


class UserService:
    def __init__(self, session: AsyncSession):
        self.repo = UserRepository(session)

    async def get_or_create(self, telegram_user_id: int, username: str | None, first_name: str | None) -> User:
        return await self.repo.get_or_create(telegram_user_id, username, first_name)
