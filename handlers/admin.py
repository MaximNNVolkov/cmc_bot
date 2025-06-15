from aiogram import Router
from aiogram.filters import Command, StateFilter

from defs.admins.add_new_admin import add_new_admin
from fsm.admins import StateAdmin


router = Router()


router.message.register(add_new_admin, StateFilter(StateAdmin.admin_enter), Command("add_new_admin"))
