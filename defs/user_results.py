from aiogram import Bot
from aiogram import types
from database.db_start import db_conn, UserInfo, DailyResults
from datetime import date
import pandas as pd
from io import BytesIO
import app_logger as loger
from config_reader import config
from handlers.user_results import notify_admin


log = loger.get_logger(__name__)


async def send_reminders(bot: Bot):
    try:
        today = date.today()
        conn = db_conn()

        # Пользователи без отчета за сегодня
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
                await notify_admin(f"Ошибка отправки напоминания: {e}", bot_main= bot)
    except Exception as e:
        log.error(f"Ошибка в send_reminders: {e}")
        await notify_admin(f"Ошибка в send_reminders: {e}", bot_main= bot)


async def generate_daily_report(bot: Bot, admin_id: int = None):
    try:
        today = date.today()
        conn = db_conn()

        # Получаем данные для отчета
        query = conn.query(
            UserInfo.branch,
            UserInfo.last_name,
            UserInfo.first_name,
            DailyResults.legal_examination,
            DailyResults.subscription,
            DailyResults.non_mortgage_secondary_count,
            DailyResults.non_mortgage_secondary_sum,
            DailyResults.non_mortgage_primary_count,
            DailyResults.non_mortgage_primary_sum,
            DailyResults.non_mortgage_country_count,
            DailyResults.non_mortgage_country_sum
        ).join(DailyResults,
               UserInfo.user_id == DailyResults.user_id).filter(DailyResults.date == today)

        # Создаем DataFrame
        results = query.all()

        if not results:
            await bot.send_message(
                config.admin.get_secret_value(),
                f"ℹ️ За {today.strftime('%d.%m.%Y')} отчетов не поступало."
            )
            return

        # Создаем DataFrame
        df = pd.DataFrame(results, columns=[
                'Отделение', 'Фамилия', 'Имя',
                'ПЭ', 'Подписка',
                'НВ, шт.', 'НВ, руб.',
                'НП, шт.', 'НП, руб.',
                'НЗ, шт.', 'НЗ, руб.'
            ])
        df = df.sort_values(by='Отделение')

        # Добавляем итоги
        totals = df.groupby('Отделение').agg({'Фамилия': 'count', 'ПЭ': 'sum', 'Подписка': 'sum',
                                              'НВ, шт.': 'sum', 'НВ, руб.': 'sum', 'НП, шт.': 'sum',
                                              'НП, руб.': 'sum', 'НЗ, шт.': 'sum', 'НЗ, руб.': 'sum'})
        totals = totals.rename(columns={'Фамилия': 'МРП'})
        grand_total = df.sum(numeric_only=True)

        # Создаем Excel файл
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Отчет', index=False)
            totals.to_excel(writer, sheet_name='Итоги по отделениям')
            grand_total.to_frame().T.to_excel(writer, sheet_name='Общий итог', index=False)

        output.seek(0)

        # Отправляем администратору
        if admin_id is None:
            admin_id = config.admin.get_secret_value()
        await bot.send_document(
                admin_id,
                types.BufferedInputFile(output.read(), filename=f"report_{today.strftime('%Y%m%d')}.xlsx")
            )

        log.info(f"Сформирован отчет за {today.strftime('%d.%m.%Y')}")
    except Exception as e:
        log.error(f"Ошибка при генерации отчета: {e}")
        await notify_admin(f"Ошибка при генерации отчета: {e}", bot_main = bot)