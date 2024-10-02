import logging
import os
import datetime

from typing import Iterable, TypedDict
from openai import OpenAI, Stream
from openai.types.chat import ChatCompletionMessageParam, ChatCompletion, ChatCompletionChunk
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)


class ResponseDict(TypedDict):
    success: bool
    msg: str
    response: ChatCompletion | Stream[ChatCompletionChunk] | None


def get_gpt_response(messages: Iterable[ChatCompletionMessageParam],
                     model: str = 'gpt-4o-mini-2024-07-18',
                     max_tokens: int = 1000,
                     temperature: float = 0.7,
                     n: int = 1,
                     *args,
                     **kwargs) -> ResponseDict:
    try:
        logging.info(f'Запуск обращения к GPT: {messages}')

        completion = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            n=n,
            *args,
            **kwargs
        )
        msg = completion.choices[0].message.content

        logging.info(f'Ответ GPT: {msg}')

        return {'success': True, 'msg': str(msg), 'response': completion}
    except Exception as e:
        logging.error(f'Ошибка при работе с GPT {e}')

        return {'success': False, 'msg': str(e), 'response': None}


def add_secs_to_datetime(date, secs_to_add):
    """Добавляет указанное количество секунд к заданному времени.

    Args:
        date(datetime.datetime): Исходное время.
        secs_to_add (int): Количество секунд, которые нужно добавить.

    Returns:
        datetime.datetime: Новое время с добавленными секундами.
    """

    new_time = date + datetime.timedelta(seconds=secs_to_add)

    return new_time
