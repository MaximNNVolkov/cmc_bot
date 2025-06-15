import app_logger as loger
from database.db_start import db_conn, Admins, Users


log = loger.get_logger(__name__)


def admins_list():
    log.info(f'Запрос на список администраторов')
    conn = db_conn()
    s = conn.query(Admins.user_id).all()
    if len(s) > 0:
        res = s
    else:
        res = ()
    return res
