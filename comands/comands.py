import app_logger as log
from aiogram import types
import aiogram.utils.markdown as fmt
from aiogram.fsm.context import FSMContext
from defs.classes import User
from fsm.admins import StateAdmin
from comands.admins_commands.admins_commands import admin_commands
from fsm.user_results import StateUser
from database.defs_base import check_daily_report_exists


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
                                       fmt.text(f'Доступны команды: {", ".join(admin_commands)}'),
                                       fmt.text('Для выхода из режима администратора отправьте команду /exit_admin'),
                                       sep='\n')
                                   )


async def user_msg(message: types.Message, state: FSMContext):
    u = User(message.from_user)
    log.info('сообщение от пользователя' + u.info_user())
    await message.answer('user_msg')


async def cmd_sendresult(message: types.Message, state: FSMContext):
    u = User(message.from_user)
    log.info('кнопка sendresult ' + u.info_user())

    # Проверяем, отправлял ли пользователь отчет сегодня
    if await check_daily_report_exists(u.id):
        await message.answer("Вы уже отправили отчет сегодня!")
        return

    await state.set_state(StateUser.BRANCH)
    await message.answer(
        "Выберите ваше отделение:\n8589, 8610, 8611, 8612, 8613, 8614, 8618, 6984, 9042",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await message.delete()
