from aiogram import Dispatcher
from filters.admins.is_admin import IsAdmin


def register_filter(dp: Dispatcher):
    dp.filters_factory.bind(IsAdmin)
