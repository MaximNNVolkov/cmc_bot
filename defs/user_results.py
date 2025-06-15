from aiogram import Bot
from aiogram import types
from database.db_start import db_conn, UserInfo, DailyResults
from datetime import datetime, date
import pandas as pd
from io import BytesIO
import app_logger as loger
from config_reader import config
from handlers.user_results import notify_admin


log = loger.get_logger(__name__)
#
#
# async def send_reminders(bot: Bot):
#     today = date.today()
#     conn = db_conn()
#
#     # Пользователи без отчета за сегодня
#     users_without_report = conn.query(UserInfo).filter(
#         ~UserInfo.user_id.in_(
#             conn.query(DailyResults.user_id)
#             .filter(DailyResults.date == today)
#         )
#     ).all()
#
#     for user in users_without_report:
#         try:
#             await bot.send_message(
#                 user.user_id,
#                 "⏰ Не забудьте отправить отчет за сегодня!\nИспользуйте команду /sendresult"
#             )
#         except Exception as e:
#             log.error(f"Ошибка отправки напоминания: {e}")
#
# async def generate_daily_report(bot: Bot):
#     today = date.today()
#     conn = db_conn()
#
#     # Получаем данные для отчета
#     results = conn.query(
#         UserInfo.branch,
#         UserInfo.last_name,
#         UserInfo.first_name,
#         DailyResults.legal_examination,
#         DailyResults.subscription,
#         DailyResults.non_mortgage_secondary_count,
#         DailyResults.non_mortgage_secondary_sum,
#         DailyResults.non_mortgage_primary_count,
#         DailyResults.non_mortgage_primary_sum,
#         DailyResults.non_mortgage_country_count,
#         DailyResults.non_mortgage_country_sum
#     ).join(DailyResults).filter(DailyResults.date == today).all()
#
#     # Создаем DataFrame
#     df = pd.DataFrame(results, columns=[
#         'Отделение', 'Фамилия', 'Имя',
#         'Правовая экспертиза', 'Подписка',
#         'НВ-Кол-во', 'НВ-Сумма',
#         'НП-Кол-во', 'НП-Сумма',
#         'НЗ-Кол-во', 'НЗ-Сумма'
#     ])
#
#     # Добавляем итоги
#     totals = df.groupby('Отделение').sum()
#     grand_total = df.sum(numeric_only=True)
#
#     # Создаем Excel файл
#     output = BytesIO()
#     with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
#         df.to_excel(writer, sheet_name='Отчет', index=False)
#         totals.to_excel(writer, sheet_name='Итоги по отделениям')
#         grand_total.to_frame().T.to_excel(writer, sheet_name='Общий итог', index=False)
#
#     output.seek(0)
#
#     # Отправляем администратору
#     admin_id = config.admin.get_secret_value()
#     await bot.send_document(
#         admin_id,
#         types.BufferedInputFile(output.read(), filename=f"report_{today.strftime('%Y%m%d')}.xlsx")
#     )

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

async def generate_daily_report(bot: Bot):
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
                'Правовая экспертиза', 'Подписка',
                'НВ-Кол-во', 'НВ-Сумма',
                'НП-Кол-во', 'НП-Сумма',
                'НЗ-Кол-во', 'НЗ-Сумма'
            ])

        # Добавляем итоги
        totals = df.groupby('Отделение').sum()
        grand_total = df.sum(numeric_only=True)

        # Создаем Excel файл
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Отчет', index=False)
            totals.to_excel(writer, sheet_name='Итоги по отделениям')
            grand_total.to_frame().T.to_excel(writer, sheet_name='Общий итог', index=False)

        output.seek(0)

        # Отправляем администратору
        admin_id = config.admin.get_secret_value()
        await bot.send_document(
                admin_id,
                types.BufferedInputFile(output.read(), filename=f"report_{today.strftime('%Y%m%d')}.xlsx")
            )

        log.info(f"Сформирован отчет за {today.strftime('%d.%m.%Y')}")
    except Exception as e:
        log.error(f"Ошибка при генерации отчета: {e}")
        await notify_admin(f"Ошибка при генерации отчета: {e}", bot_main = bot)