import logging
import re
import json


class Parser:
    def __init__(self, response_text):
        self._response_text = response_text
        self._parsed_text = []

        try:
            self._parse_prompt_json()
        except Exception as ex:
            logging.error(ex)
            self._parse_prompt()

    def _parse_prompt_json(self):
        parsed_text = json.loads(self._response_text)

        if type(parsed_text) == list:
            self._parsed_text = parsed_text
        else:
            self._parsed_text.append(parsed_text)

    def _parse_prompt(self):
        pattern = r'\[IMAGE\]\{(.*?)\}'
        matches = re.finditer(pattern, self._response_text)

        it = 0
        for match in matches:
            start, end = match.span()
            image_prompt = match.group(1).strip()

            # Текст перед текущим [IMAGE]{...}
            text = self._response_text[it:start].strip()
            if text:
                parsed_text_input = {'text': text}
                self._parsed_text.append(parsed_text_input)

            # Добавляем изображение
            parsed_image_input = {'image': image_prompt}
            self._parsed_text.append(parsed_image_input)

            # Обновляем итератор 'it' на позицию после текущего совпадения
            it = end

        # Обрабатываем оставшийся текст после последнего совпадения
        remaining_text = self._response_text[it:].strip()
        if remaining_text:
            parsed_text_input = {'text': remaining_text}
            self._parsed_text.append(parsed_text_input)

    def get_parsed_text(self):
        return self._parsed_text

    # def _process_image(self):
    #     for i in range(0, len(self._parsed_text)):
    #         if 'image' in self._parsed_text[i]:
    #             image_link = generate_image_link(self._parsed_text[i]['image'], 'user_id')
    #             self._parsed_text[i]['image'] = image_link

    def _delete_images(self):
        parsed_text_only = []

        for i in range(0, len(self._parsed_text)):
            if 'text' in self._parsed_text[i]:
                parsed_text_only.append(self._parsed_text[i])

        self._parsed_text = parsed_text_only
