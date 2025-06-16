from aiogram.types import Message
import app_logger as loger
from defs.user_results import generate_daily_report


log = loger.get_logger(__name__)


async def get_daily_report(message: Message):
    await generate_daily_report(bot = message.bot, admin_id = message.from_user.id)
