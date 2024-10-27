from typing import TypedDict
from openai import Stream
from openai.types.chat import ChatCompletion, ChatCompletionChunk


class ResponseDict(TypedDict):
    success: bool
    msg: str
    response: ChatCompletion | Stream[ChatCompletionChunk] | None
    length_context: int
    pass


class AiApiTemplate:
    def __init__(self, sufix: str = '', prefix: str = ''):
        self.sufix = sufix
        self.prefix = prefix

    def get_response(self, prompt: str, context: list) -> ResponseDict:
        pass

    def _calc_length_content(self, content):
        length_content = 0
        for item in content:
            length_content += len(item['content'])
        return length_content
