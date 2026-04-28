from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.models import Channel


class ChannelRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, channel_id: int) -> Channel | None:
        result = await self.session.execute(select(Channel).where(Channel.id == channel_id))
        return result.scalar_one_or_none()

    async def get_by_owner_and_telegram_id(self, owner_user_id: int, telegram_channel_id: int) -> Channel | None:
        result = await self.session.execute(
            select(Channel).where(
                Channel.owner_user_id == owner_user_id,
                Channel.telegram_channel_id == telegram_channel_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_channels_by_owner(self, owner_user_id: int) -> list[Channel]:
        result = await self.session.execute(
            select(Channel).where(Channel.owner_user_id == owner_user_id).order_by(Channel.created_at_utc)
        )
        return list(result.scalars().all())

    async def create(
        self,
        owner_user_id: int,
        telegram_channel_id: int,
        title: str,
        username: str | None,
    ) -> Channel:
        channel = Channel(
            owner_user_id=owner_user_id,
            telegram_channel_id=telegram_channel_id,
            title=title,
            username=username,
        )
        self.session.add(channel)
        await self.session.flush()
        return channel

    async def delete(self, channel: Channel) -> None:
        await self.session.delete(channel)
        await self.session.flush()
