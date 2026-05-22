import logging
from aiogram import Router, types, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import ReplyKeyboardBuilder
import aiogram.utils.markdown as fmt
from fsm.user_results import StateUser
from database.db_start import db_conn, UserInfo, DailyResults, LeadRecord
from datetime import datetime, date
from config_reader import config
import app_logger

log = app_logger.get_logger(__name__)

router = Router()

BRANCHES = ['8589', '8610', '8611', '8612', '8613', '8614', '8618', '6984', '9042']
CHANNELS = ['ВСП', 'Премьер', 'Первый']


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


@router.message(Command("sendresult"))
async def cmd_sendresult(message: types.Message, state: FSMContext):
    try:
        user_id = message.from_user.id

        if await check_daily_report_exists(user_id):
            await message.answer("📊 Вы уже отправили отчет сегодня!")
            return

        conn = db_conn()
        user_info = conn.query(UserInfo).filter(UserInfo.user_id == user_id).first()

        if user_info:
            await state.update_data(
                branch=user_info.branch,
                first_name=user_info.first_name,
                last_name=user_info.last_name
            )
            await state.set_state(StateUser.USER_CONFIRMATION)
            await message.answer(
                f"👤 Ваши сохраненные данные:\n"
                f"ФИО: {user_info.first_name} {user_info.last_name}\n"
                f"Отделение: {user_info.branch}\n\n"
                "Это вы? (Да/Нет)",
                reply_markup=types.ReplyKeyboardRemove()
            )
        else:
            await state.set_state(StateUser.USER_CONFIRMATION)
            await message.answer(
                "👤 Введите ваше имя и фамилию (например: Иван Иванов):",
                reply_markup=types.ReplyKeyboardRemove()
            )
    except Exception as e:
        log.error(f"Ошибка в cmd_sendresult: {e}")


@router.message(StateUser.USER_CONFIRMATION, F.text.lower() == "нет")
async def process_user_decline(message: types.Message, state: FSMContext):
    try:
        await state.update_data(first_name=None, last_name=None, branch=None)
        await message.answer("👤 Введите ваше имя и фамилию (например: Иван Иванов):")
    except Exception as e:
        log.error(f"Ошибка в process_user_decline: {e}")


@router.message(StateUser.USER_CONFIRMATION, F.text.lower() == "да")
async def process_user_confirm(message: types.Message, state: FSMContext):
    try:
        await state.set_state(StateUser.LEADS_COUNT)
        await message.answer(
            "✅ Личность подтверждена!\n\n"
            "Сколько вы сегодня передали ЛИДов по ЗП? (введите целое число):"
        )
    except Exception as e:
        log.error(f"Ошибка в process_user_confirm: {e}")


@router.message(StateUser.USER_CONFIRMATION)
async def process_user_name(message: types.Message, state: FSMContext):
    try:
        if len(message.text.split()) < 2:
            await message.answer("❌ Пожалуйста, введите имя и фамилию полностью:")
            return

        first_name, last_name = message.text.split(maxsplit=1)
        await state.update_data(first_name=first_name, last_name=last_name)

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


@router.message(StateUser.BRANCH_SELECTION)
async def process_branch(message: types.Message, state: FSMContext):
    try:
        if message.text not in BRANCHES:
            await message.answer("❌ Пожалуйста, выберите отделение из списка:")
            return

        await state.update_data(branch=message.text)

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

        await state.set_state(StateUser.LEADS_COUNT)
        await message.answer(
            "✅ Данные сохранены!\n\n"
            "Сколько вы сегодня передали ЛИДов по ЗП? (введите целое число):",
            reply_markup=types.ReplyKeyboardRemove()
        )
    except Exception as e:
        log.error(f"Ошибка в process_branch: {e}")


# ──────────────────────────────────────────────
# Новая логика: сбор лидов
# ──────────────────────────────────────────────

@router.message(StateUser.LEADS_COUNT)
async def process_leads_count(message: types.Message, state: FSMContext):
    try:
        if not message.text.isdigit() or int(message.text) < 0:
            await message.answer("❌ Пожалуйста, введите целое неотрицательное число:")
            return

        leads_count = int(message.text)
        await state.update_data(leads_count=leads_count, leads=[])

        if leads_count == 0:
            # Нет лидов — сразу на подтверждение
            await show_confirmation(message, state)
            return

        # Начинаем цикл по лидам
        await state.update_data(lead_index=0)
        await state.set_state(StateUser.LEADS_LOOP_LEAD_NAME)
        await message.answer(
            f"📝 ЛИД №1 из {leads_count}\n\n"
            "Укажите Имя и Отчество клиента (например: Иван Иванович):"
        )
    except Exception as e:
        log.error(f"Ошибка в process_leads_count: {e}")


@router.message(StateUser.LEADS_LOOP_LEAD_NAME)
async def process_lead_name(message: types.Message, state: FSMContext):
    try:
        parts = message.text.strip().split()
        if len(parts) < 2:
            await message.answer("❌ Укажите Имя и Отчество через пробел (например: Иван Иванович):")
            return
        if len(parts) > 2:
            await message.answer("❌ Указывать нужно без фамилии. Введите только Имя и Отчество (например: Иван Иванович):")
            return

        name = f"{parts[0]} {parts[1]}"
        await state.update_data(current_lead_name=name)
        await state.set_state(StateUser.LEADS_LOOP_LEAD_CHANNEL)

        # Клавиатура с каналами
        builder = ReplyKeyboardBuilder()
        for ch in CHANNELS:
            builder.add(types.KeyboardButton(text=ch))
        builder.adjust(2)

        await message.answer(
            "📡 Выберите канал:",
            reply_markup=builder.as_markup(resize_keyboard=True)
        )
    except Exception as e:
        log.error(f"Ошибка в process_lead_name: {e}")


@router.message(StateUser.LEADS_LOOP_LEAD_CHANNEL)
async def process_lead_channel(message: types.Message, state: FSMContext):
    try:
        if message.text not in CHANNELS:
            await message.answer("❌ Пожалуйста, выберите канал из списка (ВСП / Премьер / Первый):")
            return

        channel = message.text
        data = await state.get_data()
        name = data.get('current_lead_name', '')

        # Сохраняем лид
        leads = data.get('leads', [])
        leads.append({'name': name, 'channel': channel})
        await state.update_data(leads=leads)

        lead_index = data.get('lead_index', 0) + 1
        leads_count = data.get('leads_count', 0)

        if lead_index >= leads_count:
            # Все лиды собраны
            await show_confirmation(message, state)
        else:
            await state.update_data(lead_index=lead_index)
            await state.set_state(StateUser.LEADS_LOOP_LEAD_NAME)
            await message.answer(
                f"📝 ЛИД №{lead_index + 1} из {leads_count}\n\n"
                "Укажите Имя и Отчество клиента (например: Иван Иванович):",
                reply_markup=types.ReplyKeyboardRemove()
            )
    except Exception as e:
        log.error(f"Ошибка в process_lead_channel: {e}")


async def show_confirmation(message: types.Message, state: FSMContext):
    """Показывает подтверждение всех данных."""
    data = await state.get_data()
    leads = data.get('leads', [])
    leads_count = data.get('leads_count', 0)

    text = (
        "✅ Пожалуйста, проверьте введенные данные:\n\n"
        f"ФИО: {data['first_name']} {data['last_name']}\n"
        f"Отделение: {data['branch']}\n"
        f"Передано лидов: {leads_count}\n\n"
    )

    if leads:
        for i, lead in enumerate(leads, 1):
            text += f"{i}. {lead['name']} — {lead['channel']}\n"

    text += "\nВсе верно? (Да/Нет)"

    await state.set_state(StateUser.CONFIRMATION)
    await message.answer(text, reply_markup=types.ReplyKeyboardRemove())


@router.message(StateUser.CONFIRMATION, F.text.lower() == "да")
async def process_final_confirmation(message: types.Message, state: FSMContext):
    try:
        user_data = await state.get_data()
        conn = db_conn()
        today = date.today()

        # Сохраняем лидов
        leads = user_data.get('leads', [])
        for i, lead in enumerate(leads):
            lead_record = LeadRecord(
                user_id=message.from_user.id,
                date=today,
                lead_index=i,
                lead_name=lead['name'],
                channel=lead['channel']
            )
            conn.add(lead_record)

        # Сохраняем строку в daily_results (для совместимости с проверками отчёта)
        daily_result = DailyResults(
            user_id=message.from_user.id,
            date=today,
            legal_examination=0,
            subscription=0,
            non_mortgage_secondary_count=0,
            non_mortgage_secondary_sum=0,
            non_mortgage_primary_count=0,
            non_mortgage_primary_sum=0,
            non_mortgage_country_count=0,
            non_mortgage_country_sum=0
        )
        conn.add(daily_result)
        conn.commit()

        await message.answer("📈 Ваши лиды успешно сохранены! Спасибо!")
        await state.clear()
    except Exception as e:
        log.error(f"Ошибка при сохранении: {e}")
        await message.answer("❌ Произошла ошибка при сохранении. Пожалуйста, попробуйте позже.")


@router.message(StateUser.CONFIRMATION, F.text.lower() == "нет")
async def process_final_rejection(message: types.Message, state: FSMContext):
    try:
        await state.set_state(StateUser.LEADS_COUNT)
        await message.answer(
            "Начнем ввод заново.\n\n"
            "Сколько вы сегодня передали ЛИДов по ЗП? (введите целое число):"
        )
    except Exception as e:
        log.error(f"Ошибка в process_final_rejection: {e}")


# ──────────────────────────────────────────────
# Вспомогательные функции
# ──────────────────────────────────────────────

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
