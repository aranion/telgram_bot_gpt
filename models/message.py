from sqlalchemy import Column, Integer, String, ForeignKey
from db import Base
from models.user import UserModel


class MessageModel(Base):
    """
    Класс для хранения сообщение пользователя
    """
    __tablename__ = 'message'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey(UserModel.user_id))
    user_message = Column(String)
    assistant_message = Column(String)
