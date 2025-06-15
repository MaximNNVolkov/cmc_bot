import logging
import re
from aiogram import Router, types, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import ReplyKeyboardBuilder
import aiogram.utils.markdown as fmt
from fsm.user_results import StateUser
from database.db_start import db_conn, UserInfo, DailyResults
from datetime import datetime, date
from config_reader import config
import app_logger

log = app_logger.get_logger(__name__)

router = Router()

BRANCHES = ['8589', '8610', '8611', '8612', '8613', '8614', '8618', '6984', '9042']

@router.message(Command("sendresult"))
async def cmd_sendresult(message: types.Message, state: FSMContext):
    try:
        user_id = message.from_user.id

        # Проверяем существующий отчет
        if await check_daily_report_exists(user_id):
            await message.answer("📊 Вы уже отправили отчет сегодня!")
            return

        # Проверяем существующие данные пользователя
        conn = db_conn()
        user_info = conn.query(UserInfo).filter(UserInfo.user_id == user_id).first()

        if user_info:
            # Сохраняем данные в состояние
            await state.update_data(
                branch=user_info.branch,
                first_name=user_info.first_name,
                last_name=user_info.last_name
            )

            # Запрашиваем подтверждение личности
            await state.set_state(StateUser.USER_CONFIRMATION)
            await message.answer(
                f"👤 Ваши сохраненные данные:\n"
                f"ФИО: {user_info.first_name} {user_info.last_name}\n"
                f"Отделение: {user_info.branch}\n\n"
                "Это вы? (Да/Нет)",
                reply_markup=types.ReplyKeyboardRemove()
            )
        else:
            # Новый пользователь - сразу запрашиваем ФИО
            await state.set_state(StateUser.USER_CONFIRMATION)
            await message.answer(
                "👤 Введите ваше имя и фамилию (например: Иван Иванов):",
                reply_markup=types.ReplyKeyboardRemove()
            )

    except Exception as e:
        log.error(f"Ошибка в cmd_sendresult: {e}")
        await notify_admin(f"Ошибка в cmd_sendresult: {e}", message)

@router.message(StateUser.USER_CONFIRMATION, F.text.lower() == "нет")
async def process_user_decline(message: types.Message, state: FSMContext):
    try:
        await state.update_data(first_name=None, last_name=None, branch=None)
        await message.answer("👤 Введите ваше имя и фамилию (например: Иван Иванов):")
    except Exception as e:
        log.error(f"Ошибка в process_user_decline: {e}")
        await notify_admin(f"Ошибка в process_user_decline: {e}", message)

@router.message(StateUser.USER_CONFIRMATION, F.text.lower() == "да")
async def process_user_confirm(message: types.Message, state: FSMContext):
    try:
        # Переходим к вводу первого показателя
        await state.set_state(StateUser.LEGAL_EXAMINATION)
        await message.answer("✅ Личность подтверждена!\n\n"
                             "Введите количество Правовых экспертиз:")
    except Exception as e:
        log.error(f"Ошибка в process_user_confirm: {e}")
        await notify_admin(f"Ошибка в process_user_confirm: {e}", message)

@router.message(StateUser.USER_CONFIRMATION)
async def process_user_name(message: types.Message, state: FSMContext):
    try:
        if len(message.text.split()) < 2:
            await message.answer("❌ Пожалуйста, введите имя и фамилию полностью:")
            return

        first_name, last_name = message.text.split(maxsplit=1)
        await state.update_data(first_name=first_name, last_name=last_name)

        # Создаем клавиатуру для выбора отделения
        builder = ReplyKeyboardBuilder()
        for branch in BRANCHES:
            builder.add(types.KeyboardButton(text=branch))
        builder.adjust(3)

        await state.set_state(StateUser.BRANCH_SELECTION)
        await message.answer(
            "🏢 Выберите ваше отделение:",
            reply_markup=builder.as_markup(resize_keyboard=True)
        )
    except Exception as e:
        log.error(f"Ошибка в process_user_name: {e}")
        await notify_admin(f"Ошибка в process_user_name: {e}", message)

@router.message(StateUser.BRANCH_SELECTION)
async def process_branch(message: types.Message, state: FSMContext):
    try:
        if message.text not in BRANCHES:
            await message.answer("❌ Пожалуйста, выберите отделение из списка:")
            return

        await state.update_data(branch=message.text)

        # Сохраняем данные пользователя
        user_data = await state.get_data()
        conn = db_conn()
        user_info = UserInfo(
            user_id=message.from_user.id,
            branch=message.text,
            first_name=user_data['first_name'],
            last_name=user_data['last_name'],
            date_added=datetime.now()
        )
        conn.merge(user_info)
        conn.commit()

        await state.set_state(StateUser.LEGAL_EXAMINATION)
        await message.answer(
            "✅ Данные сохранены!\n\n"
            "Введите количество Правовых экспертиз:",
            reply_markup=types.ReplyKeyboardRemove()
        )
    except Exception as e:
        log.error(f"Ошибка в process_branch: {e}")
        await notify_admin(f"Ошибка в process_branch: {e}", message)

# Обработчики для каждого показателя
@router.message(StateUser.LEGAL_EXAMINATION)
async def process_legal_examination(message: types.Message, state: FSMContext):
    try:
        if not message.text.isdigit() or int(message.text) < 0:
            await message.answer("❌ Пожалуйста, введите целое неотрицательное число:")
            return

        await state.update_data(legal_examination=int(message.text))
        await state.set_state(StateUser.SUBSCRIPTION)
        await message.answer("Введите количество Подписок:")
    except Exception as e:
        log.error(f"Ошибка в process_legal_examination: {e}")
        await notify_admin(f"Ошибка в process_legal_examination: {e}", message)

@router.message(StateUser.SUBSCRIPTION)
async def process_subscription(message: types.Message, state: FSMContext):
    try:
        if not message.text.isdigit() or int(message.text) < 0:
            await message.answer("❌ Пожалуйста, введите целое неотрицательное число:")
            return

        await state.update_data(subscription=int(message.text))
        await state.set_state(StateUser.NON_MORTGAGE_SECONDARY)
        await message.answer("Введите данные по Неипотеке-Вторичка:\nКоличество и сумму через пробел (например: 2 4500)")
    except Exception as e:
        log.error(f"Ошибка в process_subscription: {e}")
        await notify_admin(f"Ошибка в process_subscription: {e}", message)

@router.message(StateUser.NON_MORTGAGE_SECONDARY)
async def process_non_mortgage_secondary(message: types.Message, state: FSMContext):
    try:
        parts = message.text.split()
        if len(parts) != 2 or not parts[0].isdigit() or not is_float(parts[1]):
            await message.answer("❌ Неверный формат. Введите количество и сумму через пробел (например: 2 4500):")
            return

        await state.update_data(
            non_mortgage_secondary_count=int(parts[0]),
            non_mortgage_secondary_sum=float(parts[1])
        )
        await state.set_state(StateUser.NON_MORTGAGE_PRIMARY)
        await message.answer("Введите данные по Неипотеке-Первичка:\nКоличество и сумму через пробел (например: 1 3000)")
    except Exception as e:
        log.error(f"Ошибка в process_non_mortgage_secondary: {e}")
        await notify_admin(f"Ошибка в process_non_mortgage_secondary: {e}", message)

@router.message(StateUser.NON_MORTGAGE_PRIMARY)
async def process_non_mortgage_primary(message: types.Message, state: FSMContext):
    try:
        parts = message.text.split()
        if len(parts) != 2 or not parts[0].isdigit() or not is_float(parts[1]):
            await message.answer("❌ Неверный формат. Введите количество и сумму через пробел (например: 1 3000):")
            return

        await state.update_data(
            non_mortgage_primary_count=int(parts[0]),
            non_mortgage_primary_sum=float(parts[1])
        )
        await state.set_state(StateUser.NON_MORTGAGE_COUNTRY)
        await message.answer("Введите данные по Неипотеке-Загородка:\nКоличество и сумму через пробел (например: 0 0)")
    except Exception as e:
        log.error(f"Ошибка в process_non_mortgage_primary: {e}")
        await notify_admin(f"Ошибка в process_non_mortgage_primary: {e}", message)

@router.message(StateUser.NON_MORTGAGE_COUNTRY)
async def process_non_mortgage_country(message: types.Message, state: FSMContext):
    try:
        parts = message.text.split()
        if len(parts) != 2 or not parts[0].isdigit() or not is_float(parts[1]):
            await message.answer("❌ Неверный формат. Введите количество и сумму через пробел (например: 0 0):")
            return

        await state.update_data(
            non_mortgage_country_count=int(parts[0]),
            non_mortgage_country_sum=float(parts[1])
        )

        # Формируем сообщение для подтверждения
        user_data = await state.get_data()
        confirmation_text = (
            "✅ Пожалуйста, проверьте введенные данные:\n\n"
            f"ФИО: {user_data['first_name']} {user_data['last_name']}\n"
            f"Отделение: {user_data['branch']}\n\n"
            f"1. Правовая экспертиза: {user_data.get('legal_examination', 0)}\n"
            f"2. Подписка: {user_data.get('subscription', 0)}\n"
            f"3. Неипотека-Вторичка: {user_data.get('non_mortgage_secondary_count', 0)} / {user_data.get('non_mortgage_secondary_sum', 0)}\n"
            f"4. Неипотека-Первичка: {user_data.get('non_mortgage_primary_count', 0)} / {user_data.get('non_mortgage_primary_sum', 0)}\n"
            f"5. Неипотека-Загородка: {user_data.get('non_mortgage_country_count', 0)} / {user_data.get('non_mortgage_country_sum', 0)}\n\n"
            "Все верно? (Да/Нет)"
        )

        await state.set_state(StateUser.CONFIRMATION)
        await message.answer(confirmation_text)
    except Exception as e:
        log.error(f"Ошибка в process_non_mortgage_country: {e}")
        await notify_admin(f"Ошибка в process_non_mortgage_country: {e}", message)

@router.message(StateUser.CONFIRMATION, F.text.lower() == "да")
async def process_final_confirmation(message: types.Message, state: FSMContext):
    try:
        user_data = await state.get_data()
        conn = db_conn()
        today = date.today()

        # Сохраняем результаты
        daily_result = DailyResults(
            user_id=message.from_user.id,
            date=today,
            legal_examination=user_data.get('legal_examination', 0),
            subscription=user_data.get('subscription', 0),
            non_mortgage_secondary_count=user_data.get('non_mortgage_secondary_count', 0),
            non_mortgage_secondary_sum=user_data.get('non_mortgage_secondary_sum', 0),
            non_mortgage_primary_count=user_data.get('non_mortgage_primary_count', 0),
            non_mortgage_primary_sum=user_data.get('non_mortgage_primary_sum', 0),
            non_mortgage_country_count=user_data.get('non_mortgage_country_count', 0),
            non_mortgage_country_sum=user_data.get('non_mortgage_country_sum', 0)
        )

        conn.add(daily_result)
        conn.commit()

        await message.answer("📈 Ваши результаты успешно сохранены! Спасибо!")
        await state.clear()
    except Exception as e:
        log.error(f"Ошибка при сохранении результатов: {e}")
        await notify_admin(f"Ошибка при сохранении результатов: {e}", message)
        await message.answer("❌ Произошла ошибка при сохранении. Пожалуйста, попробуйте позже.")

@router.message(StateUser.CONFIRMATION, F.text.lower() == "нет")
async def process_final_rejection(message: types.Message, state: FSMContext):
    try:
        await state.set_state(StateUser.LEGAL_EXAMINATION)
        await message.answer("Начнем ввод показателей заново.\n\nВведите количество Правовых экспертиз:")
    except Exception as e:
        log.error(f"Ошибка в process_final_rejection: {e}")
        await notify_admin(f"Ошибка в process_final_rejection: {e}", message)


@router.message(Command("cancel"))
@router.message(F.text.lower() == "отмена")
async def cmd_cancel(message: types.Message, state: FSMContext):
    try:
        current_state = await state.get_state()
        if current_state is None:
            return

        await state.clear()
        await message.answer(
            "❌ Действие отменено",
            reply_markup=types.ReplyKeyboardRemove()
        )
        log.info(f"Пользователь {message.from_user.id} отменил действие")
    except Exception as e:
        log.error(f"Ошибка в cmd_cancel: {e}")
        await notify_admin(f"Ошибка в cmd_cancel: {e}", message)


# Вспомогательные функции
def is_float(value):
    try:
        float(value)
        return True
    except ValueError:
        return False


async def check_daily_report_exists(user_id: int) -> bool:
    try:
        conn = db_conn()
        today = date.today()
        return conn.query(DailyResults).filter(
            DailyResults.user_id == user_id,
            DailyResults.date == today
        ).first() is not None
    except Exception as e:
        log.error(f"Ошибка при проверке отчета: {e}")
        return False

async def notify_admin(admin_message: str, message: types.Message = None, bot_main: Bot = None):
    try:
        admin_id = config.admin.get_secret_value()
        bot = message.bot if message is not None else bot_main
        await bot.send_message(chat_id=admin_id,
                               text=fmt.text(fmt.text("⚠️ ОШИБКА В БОТЕ:"),
        fmt.blockquote(admin_message),sep = '\n'))
    except Exception as e:
        log.error(f"Ошибка при отправке уведомления админу: {e}")