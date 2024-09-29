import datetime as dt

from sqlalchemy import Column, Integer, String, DateTime
from db import Base


class UserModel(Base):
    """
    Класс для храннеия данных пользователя
    """
    __tablename__ = 'users'

    user_id = Column(Integer, primary_key=True, unique=True)
    chat_id = Column(Integer, nullable=False)
    username = Column(String, nullable=False)
    token_capacity = Column(Integer, default=500)
    token_usage = Column(Integer, default=0)
    last_message_date = Column(DateTime, default=dt.datetime.utcnow)
    last_clear_token_date = Column(DateTime)
    context_capacity = Column(Integer, default=10)
    context_length = Column(Integer, default=0)
    context = Column(String, default='[]')
