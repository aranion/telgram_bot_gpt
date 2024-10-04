import asyncio
import datetime
import json
import math
import os
import sys
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.methods import SendMessage
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv
from db import create_models, check_connect_db, SessionLocal
from inline_kbs import get_home_kb, get_user_answer_test_kb, get_error_message_test_kb
from models.test import TestModel
from models.user import UserModel
from models.message import MessageModel
from sqlalchemy import desc
from search import process_search_openai
from util import get_gpt_response, add_secs_to_datetime

dp = Dispatcher()
bot = None
cash = {
    "last_message_date": {}
}
answer_bot = {
    'not_auth': 'Извините, сначала нужно зарегистрироваться!',
    'error': 'Что-то пошло не так...',
}

load_dotenv()

MODEL = 'gpt-4o-mini-2024-07-18'
API_TOKEN = os.getenv("API_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_SEARCH_ENGINE_ID = os.getenv("GOOGLE_SEARCH_ENGINE_ID")


@dp.callback_query(F.data.startswith('answer_'))
async def handler_answer_kb(call: CallbackQuery):
    await call.answer()

    try:
        temp, answer, test_id = call.data.split('_')

        await call.message.edit_reply_markup(reply_markup=None)

        session = SessionLocal()
        test = session.query(TestModel).filter_by(id=test_id).first()
        user = session.query(UserModel).filter_by(user_id=call.from_user.id).first()
        is_correct = test.correct_answer.lower() == answer.lower()

        if is_correct:
            markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Ок", callback_data='get_test')]])

            await call.message.answer('Верно! Продолжим?', reply_markup=markup)

            user.test_success += 1
        else:
            answer = json.loads(test.answer)
            correct_answer = test.correct_answer.lower()

            await call.message.answer(f'Ошибка! Правильный ответ:\n{correct_answer}) {answer[correct_answer]}',
                                      reply_markup=get_error_message_test_kb())
            user.test_failure += 1

        session.commit()
    except Exception as ex:
        logging.error(f'Ошибка при проверки теста! {ex}')

        await call.message.answer(answer_bot['error'])


@dp.callback_query(F.data == 'error_message_test')
async def error_message_test(call: CallbackQuery):
    await call.answer('Бот будет наказан...')


@dp.callback_query(F.data == 'get_test')
async def get_test(call: CallbackQuery):
    await call.answer()

    user_id = call.from_user.id
    session = SessionLocal()
    exist_user = session.query(UserModel).filter_by(user_id=user_id).first()

    if exist_user:
        context_test = json.loads(exist_user.context_test)
        test_success = exist_user.test_success
        current_token_usage = exist_user.token_usage
        token_capacity = exist_user.token_capacity
        level = math.ceil(test_success / 5) if test_success else 1

        await call.message.answer(f'🏆 Твой уровень: {level}')

        if current_token_usage > token_capacity:
            logging.info(f'Закончились токены! Использовано {current_token_usage}, разрешено {token_capacity}')

            return call.message.answer(f'У вас закончились токены! Для получения токенов выполните команду /tokens')
        if not context_test:
            content = 'You are a professional, a Russian-speaking test writer for testing your knowledge of the Python language. ' \
                      'You need to come up with a one test with the following structure:' \
                      '{"question": "Test question", "answer": { "a": "answer 1", "b": "answer 2", "c": "answer 3", "d": "answer 4"}, "correct_answer": "one of the above answers is correct"}'

            context_test.append({"role": "system", "content": content})
            context_test.append({"role": 'system', "content": 'Tests should not be repeated'})
        if exist_user.token_usage == 0:
            exist_user.token_usage = exist_user.token_usage + len(
                ''.join([item.get('content') for item in context_test]))

        gpt_answer = get_gpt_response(messages=context_test)

        if not gpt_answer['success']:
            return call.message.answer(answer_bot['error'])

        assistant_message = gpt_answer['msg']
        assistant_message = assistant_message.strip('`')

        try:
            context_test.append({"role": 'assistant', "content": assistant_message})

            test_dict = json.loads(assistant_message)
            new_test = TestModel(user_id=user_id,
                                 question=json.dumps(test_dict.get('question')),
                                 answer=json.dumps(test_dict.get('answer')),
                                 correct_answer=test_dict.get('correct_answer'))

            exist_user.context_test = json.dumps(context_test)
            exist_user.token_usage = exist_user.token_usage + len(assistant_message)
            session.add(new_test)
            session.commit()

            await call.message.answer(f'Вопрос:\n{test_dict.get("question")}',
                                      reply_markup=get_user_answer_test_kb(test_id=new_test.id,
                                                                           list_answer=test_dict.get('answer')))
        except Exception as ex:
            logging.error(f'Ошибка в обработке ответ бота {ex}')

            return call.message.answer(answer_bot['error'])


@dp.callback_query(F.data == 'get_user_info')
async def get_user_info(call: CallbackQuery):
    await call.answer()
    user_id = call.from_user.id
    session = SessionLocal()
    exist_user = session.query(UserModel).filter_by(user_id=user_id).first()

    if exist_user:
        username = exist_user.username
        test_success = exist_user.test_success
        test_failure = exist_user.test_failure
        question_count = session.query(MessageModel).filter_by(user_id=user_id).count()
        level = math.ceil(test_success / 5) if test_success else 1

        formatted_message = (
            f"😎 <b>Имя:</b> {username}\n"
            f"🧠 <b>Всего пройдено тестов:</b> {test_success + test_failure}\n"
            f"✅ <b>Правильные ответы:</b> {test_success}\n"
            f"❌ <b>Неправильные ответы:</b> {test_failure}\n"
            f"🔸 <b>Верные ответы:</b> {round(100 * test_success / (test_failure + test_success)) if test_failure else 100}%\n"
            f"🏆 <b>Уровень:</b> {level}\n"
            f"❔ <b>Количество вопросов:</b> {question_count}\n"
        )

        await call.message.answer(formatted_message)

        top_user = session.query(UserModel).order_by(desc('test_success')).limit(3)
        list_top_user = []

        for item in top_user:
            list_top_user.append(f'{len(list_top_user) + 1}. {item.username}\n')

        await call.message.answer(f'⭐ Топ 3:\n{"".join(list_top_user)}')
    else:
        logging.debug(f'Пользователь {user_id} не найден!')

        await call.answer(answer_bot['not_auth'])


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

            await message.answer(f'И снова здравствуй, {exist_user.username}!')
        else:
            logging.info(f'Создание пользователя {user_id} в БД')

            new_user = UserModel(user_id=user_id, username=username, chat_id=message.chat.id)
            session.add(new_user)
            session.commit()

            await message.answer(f'Привет, {username}!')
        await message.answer(
            'Тебя приветствует гуру Python.\n'
            'Задай мне любой вопрос.\n'
            'Прокачай знания с помощью тестов.\n'
            'Соревнуйся с другими пользователями и попади в топ-3.',
            reply_markup=get_home_kb())
    except Exception as ex:
        logging.error(f'Ошибка при регистрации пользователя {user_id}: {ex}')

        await message.answer(answer_bot['error'])
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

    logging.info(f'Получить токены для пользователя {user_id}')

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
                        f'Слишком частое обновление токенов, подождите еще '
                        f'{int(-1 * delta.seconds / 60 // 1 * -1)} минутки!')

            user.token_capacity += 500
            user.last_clear_token_date = current_time
            session.commit()

            await message.answer(f'Так-то лучше. Теперь мы можем продолжить общаться!')
        else:
            logging.debug(f'Пользователь {user_id} не найден!')

            await message.answer(answer_bot['not_auth'])
    except Exception as ex:
        logging.error(f'Ошибка при сбросе токенов {ex}')

        await message.answer(answer_bot['error'])
    finally:
        session.close()


@dp.message(Command('info'))
async def info(message: Message) -> None:
    """
    Информация про бот
    :param message: asyncio Message
    :return: None
    """
    user_id = message.from_user.id
    session = SessionLocal()

    try:
        user = session.query(UserModel).filter_by(user_id=user_id).first()

        if user:
            await message.answer(
                f'<b>Информация о боте:</b>\n'
                f'- Задавай вопросы о Python\n'
                f'- Получай новые знания\n'
                f'- Проходи тесты\n'
                f'- Повышай рейтинг\n'
                f'- Отслеживай статистику\n',
                reply_markup=get_home_kb())
        else:
            logging.info(f'Пользователь с id {user_id} не найден!')

            await message.answer(answer_bot['not_auth'])
    except Exception as ex:
        logging.error(f'Ошибка получения информации {user_id}: {ex}')

        await message.answer(answer_bot['error'])
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

            await message.answer(f'Все забыл, но готов продолжить беседу!')
        else:
            logging.info(f'Пользователь с id {user_id} не найден!')

            await message.answer(answer_bot['not_auth'])
    except Exception as ex:
        logging.error(f'Ошибка при сбросе контекста пользователю {user_id}: {ex}')

        await message.answer(answer_bot['error'])
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
            context = json.loads(user.context)
            current_token_usage = user.token_usage
            token_capacity = user.token_capacity
            context_length = user.context_length
            context_capacity = user.context_capacity
            token_usage = len(text) + current_token_usage
            last_message_date = cash.get('last_message_date').get(user_id)
            current_datetime = datetime.datetime.now()

            if last_message_date and current_datetime <= add_secs_to_datetime(last_message_date, 2):
                return message.answer(f'Отправка сообщений возможна не чаще чем раз в 2 сек!')

            cash.get('last_message_date')[user_id] = current_datetime

            await message.answer('Думаю...')

            if token_usage > token_capacity:
                logging.info(f'Закончились токены! Использовано {current_token_usage}, разрешено {token_capacity}')

                return message.answer(f'У вас закончились токены! Для получения токенов выполните команду /tokens')
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

                content = 'You are a professional Russian-speaking assistant in learning programming in Python, ' \
                          'your task is to give clear, short and correct answers to the questions asked. ' \
                          'If the question is not related to the Python language, please return a polite refusal.'

                context.append({"role": "system", "content": content})

            context.append({"role": "user", "content": text})

            # search_res = process_search_openai(GOOGLE_API_KEY, GOOGLE_SEARCH_ENGINE_ID, text)
            # context.append({"role": 'system', "content": f'Here is information from the internet: {search_res}'})
            # context.append({"role": 'system', "content": 'Combine answers into one general and short one.'})

            gpt_answer = get_gpt_response(messages=context)

            if not gpt_answer['success']:
                return message.answer(answer_bot['error'])

            assistant_message = gpt_answer['msg']

            context.append({"role": 'assistant', "content": assistant_message})

            await message.answer(assistant_message, reply_markup=get_home_kb())

            new_message = MessageModel(user_id=user_id, user_message=text, assistant_message=assistant_message)

            session.add(new_message)

            user.context = json.dumps(context)
            user.token_usage = token_usage
            user.context_length = len(context)
            user.last_message_date = datetime.datetime.now()

            session.commit()
        else:
            logging.debug(f'Пользователь {user_id} не найден в БД')

            return message.answer(answer_bot['not_auth'])
    except Exception as ex:
        logging.error(f'Ошибка при работе с GPT: {ex}')

        await message.answer(answer_bot['error'])
    finally:
        session.close()


async def main() -> None:
    """
    Метод для запуска бота
    :return: None
    """
    global bot

    try:
        bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

        await dp.start_polling(bot)
    except Exception as ex:
        logging.error(f'Ошибка при старте polling! {ex}')


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)

    check_connect_db()
    create_models()

    asyncio.run(main())
