from aiogram.fsm.state import State, StatesGroup


class StateAdmin(StatesGroup):
    admin_enter = State()
    add_admin = State()
