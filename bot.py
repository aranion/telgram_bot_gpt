import datetime
import logging
import re

from aiogram.methods import SendMessage
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from AI.openai_config import OpenAIConfig

from aiogram import Router, Bot, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from AI import dalle_api, gpt_api

from aiogram.types import (
    Message, CallbackQuery
)

from db import SessionLocal
from inline_kbs import clear_state_kb, regenerate_kb
from models.message import MessageModel
from models.user import UserModel
from parser import Parser
from util import add_secs_to_datetime

answer_bot = {
    'not_auth': 'Извините, сначала нужно зарегистрироваться!',
    'error': '⛔ Что-то пошло не так...',
    'not_connect': 'AI недоступен, повторите попытку позже...'
}
cash = {
    "answer_not_completed": {}
}

main_router = Router()
image_router = Router()
control_router = Router()

add_desc_image_model = gpt_api.GptAgent(
    "Describe the hero of the work: face, clothes, physique, age and character, appearance and distinctive features of appearance."
    "Describe the setting of the work. Years in which the action takes place. Original prompt:",
    '\nAdd additional fields to the passed json:\n'
    '{"desc_hero": "face, appearance, clothing, physique, age, character", "scene": "brief description of the scene"}'
)
dalle_model = dalle_api.DalleAgent(OpenAIConfig.dalle_sufix, OpenAIConfig.dalle_prefix)
improve_prompt_model = gpt_api.GptAgent(
    "Briefly formulate the description of the picture so that it is more thoughtful and interesting:\n",
    "\nSave the context of the original prompt. Make sure that your answer only contains prompt."
)
check_prompt_model = gpt_api.GptAgent(
    "In the prompt, find the author of the work and the hero from his books.\n"
    "If the author is not specified, identify him by the specified hero of the work.\n"
    "Original prompt:\n",
    "\nIf the hero of the story is not specified, return 'NOT_FOUND'"
    "\nIf the author and hero are found, generate a response in the format:"
    "\n{\"author\": \"Полное имя автора\", \"hero\": \"Герой произведения\", \"book\" : \"Название книги\"}"
)
check_author_create_hero_model = gpt_api.GptAgent('', "Верни TRUE, если является, иначе FALSE")


class States(StatesGroup):
    image: State = State()
    main: State = State()
    generate_image: State = State()


@main_router.message(CommandStart())
async def start(message: Message, state: FSMContext):
    """
        Метод для регистрации в боте
        :param message: asyncio Message
        :return: None
    """
    user = message.from_user
    user_id = user.id
    username = user.username
    session = SessionLocal()

    await state.set_state(States.main)

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
            'Это бот создает иллюстрации героев книг по заданному имени персонажа, '
            'а также есть возможность сгенерировать любое изображение по команде /image')
    except Exception as ex:
        logging.error(f'Ошибка при регистрации пользователя {user_id}: {ex}')
        await message.answer(answer_bot['error'])
    finally:
        session.close()


@image_router.message(Command("image"))
async def image(message: Message, state: FSMContext):
    user_id = message.from_user.id
    session = SessionLocal()

    try:
        user = session.query(UserModel).filter_by(user_id=user_id).first()

        if user:
            full_token_usage = user.token_usage
            token_capacity = user.token_capacity

            if full_token_usage > token_capacity:
                return message.answer('У вас закончились токены! Для получения токенов выполните команду /tokens')
            if cash['answer_not_completed'].get(user_id):
                return message.answer(f'Ожидается завершение предыдущего запроса к боту...')
            await message.answer("Введите описание создаваемого изображения!", reply_markup=clear_state_kb())
            await state.set_state(States.image)
        else:
            logging.info(f'Пользователь с id {user_id} не найден!')

            await message.answer(answer_bot['not_auth'])
    except Exception as ex:
        logging.error(ex)
        await message.answer(answer_bot['error'])


@image_router.message(States.image)
async def image(message: Message, state: FSMContext):
    await state.set_state(States.generate_image)
    user_prompt = message.text
    builder = ReplyKeyboardBuilder()
    builder.button(text=user_prompt)
    for i in range(0, 3):
        improved_prompt = improve_prompt_model.get_response(user_prompt, context=[])

        if not improved_prompt['success']:
            await message.answer(answer_bot['error'])

        builder.button(text=improved_prompt['msg'])
    builder.adjust(1, 1, 1, 1)
    await message.answer("Выберите лучшее описание изображения: ",
                         reply_markup=builder.as_markup(one_time_keyboard=True, resize_keyboard=True))


@image_router.message(States.generate_image)
async def image(message: Message, state: FSMContext):
    final_prompt = message.text
    try:
        res = dalle_model.get_response(final_prompt)

        if not res['success']:
            raise 'Ошибка при получении изображения'

        await message.answer_photo(res['msg'])
        await state.clear()
    except Exception as ex:
        logging.error(ex)
        await state.set_state(States.main)
        return await message.answer(answer_bot['error'])


@main_router.message(Command('tokens'))
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

            user.token_capacity += 2000
            user.last_clear_token_date = current_time
            session.commit()

            await message.answer(f'🤘 Так-то лучше. Теперь мы можем продолжить общаться!')
        else:
            logging.debug(f'Пользователь {user_id} не найден!')

            await message.answer(answer_bot['not_auth'])
    except Exception as ex:
        logging.error(f'Ошибка при сбросе токенов {ex}')

        await message.answer(answer_bot['error'])
    finally:
        session.close()


@main_router.message(Command('info'))
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
                'Бот генерирует иллюстрации персонажей из книга. '
                'Для формирования образа используется анализ личности персонажа при помощи GPT.'
                '\nЧтобы сформировать запрос, нужно указать имя персонажа. '
                'Дополнительно указывается автор, если автор не указан будет попытка определения автора автоматически.',
                # reply_markup=get_home_kb()
            )
        else:
            logging.info(f'Пользователь с id {user_id} не найден!')

            await message.answer(answer_bot['not_auth'])
    except Exception as ex:
        logging.error(f'Ошибка получения информации {user_id}: {ex}')

        await message.answer(answer_bot['error'])
    finally:
        session.close()


@main_router.callback_query(F.data == 'clear_state')
async def clear_state(call: CallbackQuery, state: FSMContext):
    await call.answer()

    user_id = call.from_user.id
    session = SessionLocal()
    exist_user = session.query(UserModel).filter_by(user_id=user_id).first()

    if exist_user:
        await state.clear()
        await call.bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        await call.message.answer("Генерация произвольного изображения отменена")
    else:
        logging.debug(f'Пользователь {user_id} не найден!')
        await call.message.answer(answer_bot['not_auth'])


@main_router.callback_query(F.data == 'regenerate')
async def regenerate(call: CallbackQuery, state: FSMContext):
    await call.answer()

    user_id = call.from_user.id
    session = SessionLocal()
    exist_user = session.query(UserModel).filter_by(user_id=user_id).first()

    if exist_user:
        await call.message.answer('Функционал в разработке...')
    else:
        logging.debug(f'Пользователь {user_id} не найден!')
        await call.message.answer(answer_bot['not_auth'])


@main_router.message(F.text)
async def handle_main(message: Message):
    message_text = message.text
    user = message.from_user
    user_id = user.id
    session = SessionLocal()
    exist_user = session.query(UserModel).filter_by(user_id=user_id).first()
    full_token_usage = 0

    if not exist_user:
        return message.answer(answer_bot['not_auth'])
    try:
        full_token_usage = exist_user.token_usage
        token_capacity = exist_user.token_capacity

        if full_token_usage > token_capacity:
            cash['answer_not_completed'][user_id] = False
            return message.answer('⛔ У вас закончились токены! Для получения токенов выполните команду /tokens')

        logging.debug(f'Проверка завершения предыдущего запроса: {cash["answer_not_completed"].get(user_id)}')
        if cash['answer_not_completed'].get(user_id):
            return message.answer(f'⛔ Ваш запрос "{message_text}" не отправлен. Ожидается завершение предыдущего...')
        else:
            cash['answer_not_completed'][user_id] = True

        temp_msg = await message.answer('🔍 Поиск автора и персонажа...')

        logging.debug('Проверка на наличие автора и героя произведения в сообщение')
        check_prompt_response = check_prompt_model.get_response(message_text, context=[])
        check_prompt = check_prompt_response['msg']
        length_context = check_prompt_response['length_context']
        full_token_usage += length_context

        await message.bot.delete_message(chat_id=message.chat.id, message_id=temp_msg.message_id)

        if not check_prompt_response['success']:
            raise 'Ошибка при поиске автора и героя произведения в сообщение'
        if check_prompt == 'NOT_FOUND':
            cash['answer_not_completed'][user_id] = False
            return message.answer('🛑 В вашем сообщение не найден персонаж произведения или автор, попробуйте еще раз.')

        temp_msg = await message.answer('👀 Проверка автора и персонажа...')

        logging.debug(f'Парсинг автора, персонажа и книги {check_prompt}')
        check_prompt_data = Parser(check_prompt).get_parsed_text()[0]

        author = check_prompt_data["author"]
        book = check_prompt_data["book"]
        hero = check_prompt_data["hero"]

        logging.debug(f'Сохранение сообщения пользователя')
        new_message = MessageModel(user_id=user_id, user_message=message_text, assistant_message=check_prompt)
        session.add(new_message)
        session.commit()

        logging.debug(f'Проверка автора и героя произведения')
        check_author_create_hero_response = check_author_create_hero_model.get_response(
            f"Check if the author {author} is the creator of the character {hero}.", context=[])
        check_author_create_hero = check_author_create_hero_response['msg']
        length_context = check_prompt_response['length_context']
        full_token_usage += length_context

        await message.bot.delete_message(chat_id=message.chat.id, message_id=temp_msg.message_id)

        if not check_author_create_hero_response['success']:
            raise 'Ошибка при получении ответа, является ли автор создателем персонажа'

        is_author_not_create_hero = bool(re.search(r'FALSE', check_author_create_hero))
        is_author_create_hero = bool(re.search(r'TRUE', check_author_create_hero))

        if is_author_not_create_hero:
            cash['answer_not_completed'][user_id] = False
            return message.answer(f'🛑 Извините, не смог найти персонаж "{hero}" у автора "{author}".')
        if is_author_create_hero:
            await message.answer(f'😎 Автор: \"{author}\"\n📕 Произведение: \"{book}\"\n👤 Персонаж: \"{hero}\"')

        temp_msg = await message.answer('📝 Собираю характеристики персонажа...')

        logging.debug(f'Добавление описание характера героя для иллюстрации')
        gpt_response = add_desc_image_model.get_response(check_prompt, context=[])
        length_context = check_prompt_response['length_context']
        full_token_usage += length_context

        await message.bot.delete_message(chat_id=message.chat.id, message_id=temp_msg.message_id)

        if not gpt_response['success']:
            raise 'Ошибка при добавление описания характера героя для иллюстрации'
    except Exception as ex:
        logging.error(ex)
        cash['answer_not_completed'][user_id] = False

        exist_user.token_usage = full_token_usage
        session.commit()
        return await message.answer(answer_bot['not_connect'])

    try:
        parsed_response = Parser(gpt_response['msg']).get_parsed_text()[0]

        if "scene" in parsed_response:
            desc_image = str(parsed_response['desc_hero']) + str(parsed_response['scene'])
            temp_msg = await message.answer('⏳ Формирую описание...')

            logging.debug(f'Формирование описание картинки')
            gpt_response = improve_prompt_model.get_response(desc_image, context=[])
            improve_prompt = gpt_response['msg']
            length_context = check_prompt_response['length_context']
            full_token_usage += length_context

            await message.bot.delete_message(chat_id=message.chat.id, message_id=temp_msg.message_id)

            if not gpt_response['success']:
                raise 'Ошибка при получении подробного описания изображения'

            temp_msg = await message.answer('🎨 Начинаю рисовать...')

            try:
                logging.debug(f'Создание изображения')
                dalle_answer = dalle_model.get_response(improve_prompt)
                image_link = dalle_answer['msg']

                await message.bot.delete_message(chat_id=message.chat.id, message_id=temp_msg.message_id)

                if not dalle_answer['success']:
                    raise 'Ошибка при генерации изображения'

                cash['answer_not_completed'][user_id] = False
                exist_user.token_usage = full_token_usage
                session.commit()
                return message.answer_photo(image_link, reply_markup=regenerate_kb())
            except Exception as ex:
                logging.error(ex)
                cash['answer_not_completed'][user_id] = False
                exist_user.token_usage = full_token_usage
                session.commit()
                await message.bot.delete_message(chat_id=message.chat.id, message_id=temp_msg.message_id)
                await message.answer('Произошла ошибка при формировании изображения...')
                return message.answer(improve_prompt)
    except Exception as e:
        logging.error(f"Ошибка при формировании ответа: {e}")
        cash['answer_not_completed'][user_id] = False
        exist_user.token_usage = full_token_usage
        session.commit()
        return message.answer(answer_bot['error'])
