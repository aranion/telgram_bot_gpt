import logging
import os

from AI.AI_API_template import AiApiTemplate
from openai import OpenAI
from AI.openai_config import OpenAIConfig


class GptAgent(AiApiTemplate):
    def __init__(self, sufix, prefix):
        super().__init__(sufix, prefix)
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def get_response(self, prompt, context):
        length_context = 0

        try:
            logging.info(f'Запуск обращения к GPT: {prompt}')

            full_context = context + [
                {'role': 'system', 'content': self.prefix},
                {'role': 'user', 'content': prompt},
                {'role': 'system', 'content': self.sufix}
            ]

            length_context = self._calc_length_content(full_context)

            response = self.client.chat.completions.create(
                model=OpenAIConfig.gpt_model_name,
                temperature=OpenAIConfig.gpt_temperature,
                max_tokens=OpenAIConfig.gpt_max_tokens,
                n=1,
                messages=full_context
            )

            msg = response.choices[0].message.content

            logging.info(f'Ответ GPT: {msg}')

            length_context += + len(msg)

            return {'success': True, 'msg': str(msg), 'response': response, 'length_context': length_context}
        except Exception as e:
            logging.error(f'Ошибка при работе с GPT {e}')

            return {'success': False, 'msg': str(e), 'response': None, 'length_context': length_context}
