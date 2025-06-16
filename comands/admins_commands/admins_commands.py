from aiogram.utils import markdown as fmt
from aiogram import types
from aiogram.fsm.context import FSMContext
from defs.classes import User

import app_logger as log


log = log.get_logger(__name__)
admin_commands = ['/add_new_admin']


async def exit_admin(message: types.Message, state: FSMContext):
    u = User(message.from_user)
    log.info(u.info_user())
    log.info(f'Выход из режима Admin. Пользователь {u.info_user()}')
    await message.bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    await state.clear()
    await message.bot.send_message(chat_id=u.id,
                                   text=fmt.text(
                                       fmt.text(f'{u.get_url()}, Вы вышли из режима администратора.'),
                                       sep='\n')
                                   )
