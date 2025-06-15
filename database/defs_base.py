import app_logger as loger
from .db_start import db_conn, Users, Admins, DailyResults
import time
import datetime


log = loger.get_logger(__name__)
date_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
date = time.strftime('%Y-%m-%d', time.localtime())


def add_user(user):
    log.info(
        f'Запрос на добавление нового пользователя с '
        f'{user.id}, {user.first_name}, {user.last_name}, {user.username}.')

    u = Users(user_id=user.id,
              first_name=user.first_name,
              last_name=user.last_name,
              user_name=user.username)
    conn = db_conn()
    conn.add(u)
    conn.commit()


def user_check(user):
    log.info(f'Запрос на поиск пользователя {user.id}.')
    conn = db_conn()
    s = conn.query(Users.user_id).filter(Users.user_id == user.id).all()
    if len(s) > 0:
        res = 'ok_user'
    else:
        res = 'no_user'
    return res


def admin_check(new_admin_id: int):
    log.info(f'Запрос на поиск админа {new_admin_id}.')
    conn = db_conn()
    s = conn.query(Admins.user_id).filter(Admins.user_id == new_admin_id).all()
    if len(s) > 0:
        res = 'ok_user'
    else:
        res = 'no_user'
    return res


def write_admin_db(u_id: int, id_who_add: int):
    log.info(f'Добавление нового админа {u_id}, от {id_who_add}.')
    if admin_check(u_id) == 'ok_user':
        return 'user_already_added'
    else:
        u = Admins(
            user_id=u_id,
            who_add=id_who_add,
        )
        conn = db_conn()
        conn.add(u)
        conn.commit()
        return 'admin_added'


async def check_daily_report_exists(user_id: int) -> bool:
    conn = db_conn()
    today = datetime.date.today()
    return conn.query(DailyResults).filter(
        DailyResults.user_id == user_id,
        DailyResults.date == today
    ).first() is not None