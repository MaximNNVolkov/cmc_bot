import app_logger as loger
from aiogram import types
from aiogram.fsm.context import FSMContext
from fsm.admins import StateAdmin
from aiogram.utils import markdown as fmt
from defs.classes import User
from database.defs_base import write_admin_db


log = loger.get_logger(__name__)


async def add_new_admin(message: types.Message, state: FSMContext):
    u = User(message.from_user)
    log.info(u.info_user())
    log.info(f'Admin. Добавление нового админа. Пользователь {u.info_user()}')
    await message.bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    await state.set_state(StateAdmin.add_admin)
    await message.bot.send_message(chat_id=u.id,
                                   text=fmt.text(
                                       fmt.text('Перешлите любое сообщение от нового админа в переписку'),
                                       sep=' '),
                                   reply_markup=types.ReplyKeyboardRemove()
                                   )


async def write_new_admin(message: types.Message, state: FSMContext):
    u = User(message.from_user)
    log.info(u.info_user())
    log.info(f'Admin. Запись нового админа. Пользователь {u.info_user()}')
    await state.set_state(StateAdmin.admin_enter)
    id_new_admin = message.forward_from.id
    res_add = write_admin_db(u_id=id_new_admin, id_who_add=u.id)
    if res_add == 'admin_added':
        await message.bot.send_message(chat_id=u.id,
                                       text=fmt.text(
                                           fmt.text('Новый адмиин добавлен.'),
                                           sep=' '),
                                       reply_markup=types.ReplyKeyboardRemove()
                                       )
    elif res_add == 'user_already_added':
        await message.bot.send_message(chat_id=u.id,
                                       text=fmt.text(
                                           fmt.text('Такой админ уже добавлен.'),
                                           sep=' '),
                                       reply_markup=types.ReplyKeyboardRemove()
                                       )
