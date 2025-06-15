from sqlalchemy import Column, Integer, String, DateTime, Date, Float, Boolean, UniqueConstraint
from sqlalchemy import create_engine, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.engine.url import URL
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import app_logger as loger
from config_reader import config


log = loger.get_logger(__name__)


url_object = URL.create(
    "sqlite",
    username="",
    password="",
    host="",
    database="cmc_bot.db",
)


engine = create_engine(url_object)
DeclarativeBase = declarative_base()


class Users(DeclarativeBase):
    __tablename__ = 'users'

    user_id = Column('user_id', Integer, primary_key=True)
    date = Column(DateTime(), default=datetime.now)
    first_name = Column('first_name', String)
    last_name = Column('last_name', String)
    user_name = Column('user_name', String)

    def __repr__(self):
        return f"<user_id={self.user_id}," \
               f"first_name={self.first_name}," \
               f"last_name={self.last_name}," \
               f"user_name={self.user_name}>"

    @property
    def serialize(self):
        return {
            'user_id': self.user_id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'user_name': self.user_name
        }


class Admins(DeclarativeBase):
    __tablename__ = 'admins'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer)
    date = Column(DateTime(), default=datetime.now)
    who_add = Column(Integer)


class UserInfo(DeclarativeBase):
    __tablename__ = 'user_info'

    user_id = Column(Integer, ForeignKey('users.user_id'), primary_key=True)
    branch = Column(String)  # Код отделения
    first_name = Column(String)  # Имя пользователя
    last_name = Column(String)  # Фамилия пользователя
    date_added = Column(DateTime, default=datetime.now)


class DailyResults(DeclarativeBase):
    __tablename__ = 'daily_results'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.user_id'))
    date = Column(Date, default=datetime.now().date)
    legal_examination = Column(Integer)  # Правовая экспертиза
    subscription = Column(Integer)  # Подписка
    non_mortgage_secondary_count = Column(Integer)  # Вторичка - кол-во
    non_mortgage_secondary_sum = Column(Float)  # Вторичка - сумма
    non_mortgage_primary_count = Column(Integer)  # Первичка - кол-во
    non_mortgage_primary_sum = Column(Float)  # Первичка - сумма
    non_mortgage_country_count = Column(Integer)  # Загородка - кол-во
    non_mortgage_country_sum = Column(Float)  # Загородка - сумма

    __table_args__ = (UniqueConstraint('user_id', 'date', name='_user_date_uc'),)


def db_conn():
    engine = create_engine(url_object)
    DeclarativeBase.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    return session


def write_main_admin_db():
    u_id = config.admin.get_secret_value()
    log.info(f'Добавление главного админа {u_id}, от .')
    conn = db_conn()
    s = conn.query(Admins.user_id).filter(Admins.user_id == u_id).all()
    if len(s) > 0:
        log.info('main_admin_already_added')
    else:
        u = Admins(
            user_id=u_id,
            who_add=u_id,
        )
        conn = db_conn()
        conn.add(u)
        conn.commit()
        log.info('main_admin_added')