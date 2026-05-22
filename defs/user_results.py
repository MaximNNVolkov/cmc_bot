from aiogram import Bot
from aiogram import types
from database.db_start import db_conn, UserInfo, LeadRecord, DailyResults
from datetime import date, timedelta
import pandas as pd
from io import BytesIO
import app_logger as loger
from config_reader import config


log = loger.get_logger(__name__)


async def send_reminders(bot: Bot):
    try:
        today = date.today()
        conn = db_conn()

        users_with_report = {r[0] for r in conn.query(DailyResults.user_id).filter(DailyResults.date == today).all()}
        all_users = {u.user_id for u in conn.query(UserInfo.user_id).all()}

        for user_id in all_users - users_with_report:
            try:
                await bot.send_message(
                    user_id,
                    "⏰ Напоминание: пожалуйста, отправьте отчет за сегодня!\n"
                    "Используйте команду /sendresult"
                )
                log.info(f"Отправлено напоминание пользователю {user_id}")
            except Exception as e:
                log.error(f"Ошибка отправки напоминания пользователю {user_id}: {e}")
    except Exception as e:
        log.error(f"Ошибка в send_reminders: {e}")


async def generate_daily_report(bot: Bot, admin_id: int = None):
    try:
        today = date.today()
        monday = today - timedelta(days=today.weekday())  # Понедельник
        conn = db_conn()

        # Данные за сегодня
        query_today = conn.query(
            UserInfo.branch,
            UserInfo.last_name,
            UserInfo.first_name,
            LeadRecord.lead_name,
            LeadRecord.channel,
            LeadRecord.lead_index
        ).join(LeadRecord, UserInfo.user_id == LeadRecord.user_id
        ).filter(LeadRecord.date == today).all()

        # Данные за неделю (пн → сегодня) для второго листа
        query_week = conn.query(
            UserInfo.branch,
            UserInfo.last_name,
            UserInfo.first_name,
            LeadRecord.channel
        ).join(LeadRecord, UserInfo.user_id == LeadRecord.user_id
        ).filter(LeadRecord.date >= monday, LeadRecord.date <= today).all()

        if not query_today and not query_week:
            await bot.send_message(
                config.admin.get_secret_value(),
                f"ℹ️ За {today.strftime('%d.%m.%Y')} и за неделю ({monday.strftime('%d.%m')}–{today.strftime('%d.%m.%Y')}) отчетов не поступало."
            )
            return

        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # --- ЛИСТ 1: Свод по ГОСБ за сегодня ---
            if query_today:
                df_detail = pd.DataFrame(query_today, columns=[
                    'ГОСБ', 'Фамилия', 'Имя',
                    'Имя_Отчество_клиента', 'Канал', 'lead_index'
                ])
                df_detail['Менеджер'] = df_detail['Фамилия'] + ' ' + df_detail['Имя']

                df_gosb = df_detail.groupby(['ГОСБ', 'Канал']).size().reset_index(name='Количество')
                df_gosb_pivot = df_gosb.pivot(index='ГОСБ', columns='Канал', values='Количество').fillna(0).astype(int)
                for ch in ['ВСП', 'Премьер', 'Первый']:
                    if ch not in df_gosb_pivot.columns:
                        df_gosb_pivot[ch] = 0
                df_gosb_pivot = df_gosb_pivot[['ВСП', 'Премьер', 'Первый']]
                df_gosb_pivot.index.name = 'ГОСБ'
            else:
                df_gosb_pivot = pd.DataFrame()
            df_gosb_pivot.to_excel(writer, sheet_name='Свод по ГОСБ')

            # --- ЛИСТ 2: Недельный свод по лидам (ГОСБ + ФИО менеджера) ---
            if query_week:
                df_week = pd.DataFrame(query_week, columns=[
                    'ГОСБ', 'Фамилия', 'Имя', 'Канал'
                ])
                df_week['Менеджер'] = df_week['Фамилия'] + ' ' + df_week['Имя']

                df_week_svod = df_week.groupby(['ГОСБ', 'Менеджер', 'Канал']).size().reset_index(name='Количество')
                df_week_pivot = df_week_svod.pivot(index=['ГОСБ', 'Менеджер'], columns='Канал', values='Количество').fillna(0).astype(int)
                for ch in ['ВСП', 'Премьер', 'Первый']:
                    if ch not in df_week_pivot.columns:
                        df_week_pivot[ch] = 0
                df_week_pivot = df_week_pivot[['ВСП', 'Премьер', 'Первый']]
                df_week_pivot.index.names = ['ГОСБ', 'Менеджер']
            else:
                df_week_pivot = pd.DataFrame()
            df_week_pivot.to_excel(writer, sheet_name='Недельный свод')

            # --- ЛИСТ 3: Свод по менеджерам за сегодня ---
            if query_today:
                df_mgr = df_detail.groupby(['ГОСБ', 'Менеджер', 'Канал']).size().reset_index(name='Количество')
                df_mgr_pivot = df_mgr.pivot(index=['ГОСБ', 'Менеджер'], columns='Канал', values='Количество').fillna(0).astype(int)
                for ch in ['ВСП', 'Премьер', 'Первый']:
                    if ch not in df_mgr_pivot.columns:
                        df_mgr_pivot[ch] = 0
                df_mgr_pivot = df_mgr_pivot[['ВСП', 'Премьер', 'Первый']]
                df_mgr_pivot.index.names = ['ГОСБ', 'Менеджер']
            else:
                df_mgr_pivot = pd.DataFrame()
            df_mgr_pivot.to_excel(writer, sheet_name='Свод по менеджерам')

            # --- ЛИСТ 4: Детализация за сегодня ---
            if query_today:
                df_detail_out = df_detail[['ГОСБ', 'Менеджер', 'Имя_Отчество_клиента', 'Канал']]
            else:
                df_detail_out = pd.DataFrame()
            df_detail_out.to_excel(writer, sheet_name='Детализация', index=False)

        output.seek(0)

        if admin_id is None:
            admin_id = config.admin.get_secret_value()
        await bot.send_document(
            admin_id,
            types.BufferedInputFile(output.read(), filename=f"report_{today.strftime('%Y%m%d')}.xlsx")
        )

        log.info(f"Сформирован отчет за {today.strftime('%d.%m.%Y')}")
    except Exception as e:
        log.error(f"Ошибка при генерации отчета: {e}")
