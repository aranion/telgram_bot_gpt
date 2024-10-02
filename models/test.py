from sqlalchemy import Column, Integer, String, ForeignKey
from db import Base
from models.user import UserModel


class TestModel(Base):
    """
    Класс для хранения тестов пользователей
    """
    __tablename__ = 'test'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey(UserModel.user_id))
    question = Column(String, nullable=False)
    answer = Column(String, nullable=False)
    correct_answer = Column(String, nullable=False)
