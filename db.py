import logging
import os
import pandas as pd
import sqlalchemy as _sql
import sqlalchemy.ext.declarative as _declarative
import sqlalchemy.orm as _orm

from dotenv import load_dotenv

load_dotenv()

MODEL = 'gpt-4o-mini-2024-07-18'
DATABASE_URL = os.getenv('DATABASE_URL')

# Подключение к базе данных
engine = _sql.create_engine(DATABASE_URL)
# Подключение локальной сессии
SessionLocal = _orm.sessionmaker(autocommit=False, autoflush=False, bind=engine)
# Базовая модель
Base = _sql.orm.declarative_base()


def get_db_df():
    if not os.path.exists('users.csv'):
        users_df = pd.DataFrame(columns=[
            'user_id',
            'token_capacity',  # Доступно
            'token_usage',  # Использовано
            'last_message_date',
            'context_capacity',  # Размер контекста(сколько информации нужно хранить)
            'context_length',  # Длина контекста
            'context'  # Контекст []
        ])

        users_df.to_csv('users.csv', index=False)
        return users_df

    return pd.read_csv('users.csv', index_col='user_id')


def create_models() -> None:
    """
    Создание таблиц в базе данных
    :return: None
    """
    Base.metadata.create_all(bind=engine)


def check_connect_db() -> None:
    """
    Проверка соединения с БД
    :return: None
    """
    try:
        with engine.connect() as connection:
            logging.info('Успешное подключение в БД!')
    except Exception as ex:
        logging.error('Ошибка подключения к БД!', ex)
