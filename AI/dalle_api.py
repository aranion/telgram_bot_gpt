import logging

from AI.AI_API_template import AiApiTemplate
from openai import OpenAI
from AI.openai_config import OpenAIConfig


class DalleAgent(AiApiTemplate):
    def __init__(self, sufix, prefix):
        super().__init__(sufix, prefix)
        self.client = OpenAI()

    def get_response(self, prompt, context=None):
        try:
            logging.info(f'Запуск обращения к Dalle: {prompt}')

            full_context = self.prefix + prompt + self.sufix

            logging.info(f'Сформированный prompt: {prompt}')

            response = self.client.images.generate(
                size=OpenAIConfig.dalle_resolution,
                model=OpenAIConfig.dalle_model,
                prompt=full_context,
                quality="standard",
                n=1,
            )

            msg = response.data[0].url

            logging.info(f'Ответ Dalle url: {msg}')

            return {'success': True, 'msg': str(msg), 'response': response}
        except Exception as e:
            logging.error(f'Ошибка при работе с Dalle {e}')

            return {'success': False, 'msg': str(e), 'response': None}
