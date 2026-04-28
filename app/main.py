import asyncio
import logging
import sys
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from loguru import logger

logging.basicConfig(level=logging.INFO, stream=sys.stdout, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")

from app.config import settings
from app.bot.routers import channels, giveaway_create, giveaway_manage, participation, start
from app.bot.tasks import finish_giveaway_task, init_tasks, schedule_giveaway


async def _reschedule_active_giveaways():
    from app.infrastructure.database import async_session_factory
    from app.infrastructure.repositories.giveaway_repository import GiveawayRepository

    async with async_session_factory() as session:
        repo = GiveawayRepository(session)
        giveaways = await repo.get_all_active_scheduled()

    now_utc = datetime.now(timezone.utc)
    for g in giveaways:
        if g.finish_at_utc is None:
            continue

        finish_at_utc = g.finish_at_utc.replace(tzinfo=timezone.utc)
        if finish_at_utc > now_utc:
            schedule_giveaway(g.id, g.finish_at_utc)
            logger.info(f"Re-scheduled giveaway {g.id} at {g.finish_at_utc}")
        else:
            logger.info(f"Giveaway {g.id} is overdue, finishing now")
            asyncio.create_task(finish_giveaway_task(g.id))


async def main():
    logger.info("Starting bot...")

    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    dp.include_router(start.router)
    dp.include_router(channels.router)
    dp.include_router(giveaway_create.router)
    dp.include_router(giveaway_manage.router)
    dp.include_router(participation.router)

    scheduler = AsyncIOScheduler(timezone="UTC")
    init_tasks(scheduler, bot)
    scheduler.start()

    await _reschedule_active_giveaways()

    try:
        logger.info("Bot polling started")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        scheduler.shutdown()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
