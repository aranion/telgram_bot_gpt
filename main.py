import asyncio
import datetime
import json
import os
import sys
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.methods import SendMessage
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from dotenv import load_dotenv
from db import create_models, check_connect_db, SessionLocal
from models.user import UserModel
from models.message import MessageModel
from search import process_search_openai
from util import get_gpt_response, add_secs_to_datetime

dp = Dispatcher()
bot = None
answer = {
    'not_auth': 'Извините, сначала нужно зарегистрироваться!',
    'error': 'Что-то пошло не так...',
}

load_dotenv()

MODEL = 'gpt-4o-mini-2024-07-18'
API_TOKEN = os.getenv("API_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_SEARCH_ENGINE_ID = os.getenv("GOOGLE_SEARCH_ENGINE_ID")


@dp.message(CommandStart())
async def start(message: Message) -> None:
    """
    Метод для регистрации в боте
    :param message: asyncio Message
    :return: None
    """
    user = message.from_user
    user_id = user.id
    username = user.username
    session = SessionLocal()

    logging.info(f'Регистрация в боте пользователя {user_id}')
    logging.debug(f'Информация о чате: {message}')

    try:
        exist_user = session.query(UserModel).filter_by(user_id=user_id).first()

        if exist_user:
            logging.info(f'Пользователь {user_id} уже зарегистрирован!')

            await message.answer(f'И снова здравствуйте, {exist_user.username}!')
        else:
            logging.info(f'Создание пользователя {user_id} в БД')

            new_user = UserModel(user_id=user_id, username=username, chat_id=message.chat.id)
            session.add(new_user)
            session.commit()

            await message.answer(f'Привет, {username}!')
    except Exception as ex:
        logging.error(f'Ошибка при регистрации пользователя {user_id}: {ex}')

        await message.answer(answer['error'])
    finally:
        session.close()


@dp.message(Command('tokens'))
async def get_tokens(message: Message) -> None | SendMessage:
    """
    Сбросить доступные токены для пользователя
    :param message: asyncio Message
    :return: None
    """
    user_id = message.from_user.id
    session = SessionLocal()

    logging.info(f'Сброс количества токенов для пользователя {user_id}')

    try:
        user = session.query(UserModel).filter_by(user_id=user_id).first()

        logging.debug(f'Пользователь в БД {user}')

        if user:
            last_clear_token_date = user.last_clear_token_date
            current_time = datetime.datetime.now()

            if last_clear_token_date:
                finish_time = add_secs_to_datetime(last_clear_token_date, 180)

                if current_time <= finish_time:
                    delta = finish_time - current_time

                    return message.answer(
                        f'Слишком частое обновление токенов, подождите еще {int(-1 * delta.seconds / 60 // 1 * -1)} минутки!')

            user.token_usage = 0
            user.last_clear_token_date = current_time
            session.commit()

            await message.answer(f'Так-то лучше. Теперь мы можем продолжить говорить!')
        else:
            logging.debug(f'Пользователь {user_id} не найден!')

            await message.answer(answer['not_auth'])
    except Exception as ex:
        logging.error(f'Ошибка при сбросе токенов {ex}')

        await message.answer(answer['error'])
    finally:
        session.close()


@dp.message(Command('clean'))
async def clean_context(message: Message) -> None:
    """
    Сбросить ограничение контекста
    :param message: asyncio Message
    :return: None
    """
    user_id = message.from_user.id
    session = SessionLocal()

    logging.info(f'Сброс ограничение контекста для пользователя {user_id}')

    try:
        user = session.query(UserModel).filter_by(user_id=user_id).first()

        if user:
            user.context_length = 0
            user.context = json.dumps([])
            session.commit()

            await message.answer(f'Все забыл, но решительно готов продолжить беседу!')
        else:
            logging.debug(f'Пользователь с id {user_id} не найден!')

            await message.answer(answer['error'])
    except Exception as ex:
        logging.error(f'Ошибка при сбросе контекста пользователю {user_id}: {ex}')

        await message.answer('Ошибка!')
    finally:
        session.close()


@dp.message(F.text)
async def handle_messages(message: Message) -> None | SendMessage:
    """
    Метод для ответа на сообщения пользователя
    :param message: asyncio Message
    :return: None|SendMessage
    """
    text = message.text
    user_id = message.from_user.id
    session = SessionLocal()

    logging.info(f'Пользователь c id {user_id} отправил сообщение: {text}')

    try:
        user = session.query(UserModel).filter_by(user_id=user_id).first()

        if user:
            await message.answer('Думаю...')

            context = json.loads(user.context)
            current_token_usage = user.token_usage
            token_capacity = user.token_capacity
            context_length = user.context_length
            context_capacity = user.context_capacity
            last_message_date = user.last_message_date
            token_usage = len(text) + current_token_usage

            if datetime.datetime.now() < add_secs_to_datetime(last_message_date, 1):
                return message.answer(f'Отправка сообщений возможна не чаще чем раз в 1 сек!')
            if token_usage > token_capacity:
                logging.info(f'Закончились токены! Использовано {current_token_usage}, разрешено {token_capacity}')

                return message.answer(f'У вас закончились токены! (доступно: {token_capacity - current_token_usage})')
            if context_length >= context_capacity:
                logging.info(
                    f'Превышено ограничение по контексту! Текущая длина: {context_length}, ограничение: {context_capacity}')

                removed_context = []

                while context_length >= context_capacity:
                    removed_context.append(context.pop(1))
                    context_length -= 1

                logging.info(f'Удаленный контекст: {removed_context}')
            if len(context) == 0:
                logging.info('Задание начального prompt')

                content = "You are a Russian-speaking assistant, your task is to answer the questions asked as clearly, briefly and understandably as possible."
                context.append({"role": "system", "content": content})

            search_res = process_search_openai(GOOGLE_API_KEY,
                                               GOOGLE_SEARCH_ENGINE_ID,
                                               text)

            context.append({"role": 'system', "content": f'Here is information from the internet: {search_res}'})

            gpt_answer = get_gpt_response(messages=context)

            if not gpt_answer['success']:
                return message.answer(answer['error'])

            assistant_message = gpt_answer['msg']

            context.append({"role": 'assistant', "content": assistant_message})

            await message.answer(assistant_message)

            new_message = MessageModel(user_id=user_id, user_message=text, assistant_message=assistant_message)

            session.add(new_message)

            user.context = json.dumps(context)
            user.token_usage = token_usage
            user.context_length = len(context)
            user.last_message_date = datetime.datetime.now()

            session.commit()
        else:
            logging.debug(f'Пользователь {user_id} не найден в БД')

            await message.answer(answer['not_auth'])
    except Exception as ex:
        logging.error(f'Ошибка при работе с GPT: {ex}')

        await message.answer(answer['error'])
    finally:
        session.close()


async def main() -> None:
    """
    Метод для запуска бота
    :return: None
    """
    bot = Bot(token=API_TOKEN)
    await dp.start_polling(bot)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)

    check_connect_db()
    create_models()

    asyncio.run(main())
