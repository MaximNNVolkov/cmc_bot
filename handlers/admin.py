from aiogram import Router
from aiogram.filters import Command, StateFilter

from defs.admins.add_new_admin import add_new_admin, write_new_admin
from comands.admins_commands.new_report import get_daily_report
from comands.admins_commands.admins_commands import exit_admin
from fsm.admins import StateAdmin


router = Router()


router.message.register(add_new_admin, StateFilter(StateAdmin.admin_enter), Command("add_new_admin"))
router.message.register(get_daily_report, StateFilter(StateAdmin.admin_enter), Command("new_report"))
router.message.register(exit_admin, StateFilter(StateAdmin.admin_enter), Command("exit_admin"))
router.message.register(write_new_admin, StateFilter(StateAdmin.add_admin))
