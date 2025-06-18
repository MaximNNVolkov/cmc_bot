from aiogram import Router
from aiogram.filters import Command
from comands.comands import user_msg, cmd_help, cmd_start, admin_cmd
from handlers.user_results import cmd_cancel
from filters.admins.is_admin import IsAdmin


router = Router()


router.message.register(cmd_start, Command('start'))
router.message.register(cmd_help, Command('help'))
router.message.register(admin_cmd, Command('admin'), IsAdmin())
router.message.register(cmd_cancel, Command("cancel"))
router.message.register(user_msg)
