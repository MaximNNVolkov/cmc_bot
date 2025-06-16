import app_logger as log
from aiogram import types
import aiogram.utils.markdown as fmt
from aiogram.fsm.context import FSMContext
from defs.classes import User
from fsm.admins import StateAdmin


log = log.get_logger(__name__)


async def cmd_start(message: types.Message, state: FSMContext):
    u = User(message.from_user)
    log.info('кнопка старт. ' + u.info_user())
    await message.answer(text=fmt.text(
        fmt.text('Привет! Я помогу составить отчет по Вашей работе.'),
        fmt.text('Для начала работы напишите команду /sendresult')),
        sep='\n'
    )
    await message.delete()


async def cmd_help(message: types.Message):
    u = User(message.from_user)
    log.info('кнопка хэлп ' + u.info_user())
    await message.answer(fmt.text(
        fmt.text('Обнаруженные ошибки и предложения по доработкам прошу направлять автору @MaximVolkov'),
        sep='\n'))
    await message.delete()


async def admin_cmd(message: types.Message, state: FSMContext):
    u = User(message.from_user)
    log.info(u.info_user())
    log.info(f'Вход в режим Admin. Пользователь {u.info_user()}')
    await message.bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    await state.set_state(StateAdmin.admin_enter)
    await message.bot.send_message(chat_id=u.id,
                                   text=fmt.text(
                                       fmt.text(f'Привет, {u.get_url()}!'),
                                       fmt.text('Вы вошли в режим администратора.'),
                                       fmt.text('Для выхода из режима администратора /exit\_admin'),
                                       fmt.text('Для получения обновленного отчета /new\_report'),
                                       sep='\n')
                                   )


async def user_msg(message: types.Message, state: FSMContext):
    u = User(message.from_user)
    log.info('сообщение от пользователя' + u.info_user())
    await message.answer(text=fmt.text('user\_msg'))
