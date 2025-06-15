import asyncio
import app_logger as log

from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums.parse_mode import ParseMode
from aiogram.client.bot import DefaultBotProperties

from config_reader import config
from handlers import comands, admin
from handlers import user_results
from database.db_start import write_main_admin_db

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from defs.user_results import send_reminders, generate_daily_report

Token = config.bot_token.get_secret_value()
logger = log.get_logger(__name__)


async def main():
    logger.info('bot started')
    write_main_admin_db()
    bot = Bot(token=Token, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_routers(admin.router, user_results.router, comands.router)
    await bot.set_my_commands([types.BotCommand(command="start", description="Перезапустить бота"),
                               types.BotCommand(command="help", description="Помощь"),
                               types.BotCommand(command="sendresult", description="Результаты"),
                               types.BotCommand(command='cancel', description="Отмена"),
                               ])
    # Добавляем планировщик
    scheduler = AsyncIOScheduler()
    scheduler.add_job(send_reminders, 'cron', hour=17, minute=30, args=[bot])
    scheduler.add_job(generate_daily_report, 'cron', hour=17, minute=50, args=[bot])
    scheduler.start()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
