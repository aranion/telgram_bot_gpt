import asyncio
import os
import sys
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from bot import image_router, main_router, control_router
from db import check_connect_db, create_models

API_TOKEN = os.getenv("API_TOKEN")


async def main() -> None:
    """
    Метод для запуска бота
    :return: None
    """
    try:
        logging.basicConfig(level=logging.INFO, stream=sys.stdout)

        create_models()
        check_connect_db()

        bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        dp = Dispatcher()

        dp.include_router(image_router)
        dp.include_router(main_router)
        dp.include_router(control_router)

        await dp.start_polling(bot)
    except Exception as ex:
        logging.error(f'Ошибка при старте polling! {ex}')


if __name__ == '__main__':
    asyncio.run(main())

    # # check_prompt_model = gpt_api.GptAgent(
    # #     "In the prompt, find the author of the work and the hero from his books.\n"
    # #     "If the author is not specified, identify him by the specified hero of the work.\n"
    # #     "Original prompt:\n",
    # #     "If the hero of the work is not specified, return 'NOT_FOUND'\n"
    # #     "If the author and hero are found, generate json in the format:\n"
    # #     "{\"author\": \"Полное имя автора\", \"hero\": \"Герой произведения\"}")
    # # # check_prompt_response = check_prompt_model.get_response('Иван Гончаров', context=[])
    # # check_prompt_response = check_prompt_model.get_response('нарисуй герой произведения Обломов', context=[])
    # # check_prompt = check_prompt_response['msg']
    #
    # check_prompt = '{"author": "Иван Александрович Гончаров", "hero": "Обломов"}'
    # print(check_prompt)

    # # add_desc_image_model = gpt_api.GptAgent(
    # #     # Передан json с автором произведения и героем
    # #     "Json with the author of the work and the hero is transmitted."
    # #     # Опиши героя произведения: лицо, внешний вид, одежду, телосложение, возраст и характер. Опиши место действия произведения. Годы в которых происходит действие.
    # #     "Describe the hero of the work: face, appearance, clothes, physique, age and character. "
    # #     "Describe the setting of the work. Years in which the action takes place.",
    # #     # Добавь к переданному json дополнительные поля: {"desc_hero": "", "image": ""}
    # #     'Add additional fields to the passed json:\n'
    # #     '{"desc_hero": "лицо, внешний вид, одежда, телосложение, возраст, характер", '
    # #     '"image": "краткое описание места действия"}'
    # # )
    # # response = add_desc_image_model.get_response(check_prompt, context=[])
    # # msg = response['msg']
    # # msg = json.loads(msg)
    #
    # msg = {'author': 'Иван Александрович Гончаров',
    #        'hero': 'Обломов',
    #        'desc_hero': {'face': 'круглое лицо с мягкими чертами', 'appearance': 'недовольный и усталый вид',
    #                      'clothes': 'обычная, но немного запущенная одежда, часто в домашнем халате',
    #                      'physique': 'пухлый, с недостатком физической активности', 'age': 'около 30 лет',
    #                      'character': 'ленивый, мечтательный, склонный к самоанализу и меланхолии'},
    #        'image': 'действие происходит в Санкт-Петербурге, в уютной, но запущенной квартире Обломова, отражающей его внутреннее состояние',
    #        'years': 'середина 19 века'
    #        }
    # print(msg)

    # # improve_prompt_model = gpt_api.GptAgent(
    # #     "Briefly formulate the description of the picture so that it is more thoughtful and interesting:\n",
    # #     "\nSave the context of the original prompt. Make sure that your answer only contains prompt.")
    # # res = improve_prompt_model.get_response(str(msg['years']) + str(msg['desc_hero']) + str(msg['image']), [])
    # # desc_image = res['msg']
    #
    # desc_image = 'На картине изображен Обломов, погруженный в свои мысли, сидящий в уютной, но запущенной квартире в Санкт-Петербурге середины 19 века. Его круглое лицо с мягкими чертами выражает недовольство и усталость, а пухлое тело выдает недостаток физической активности. Одетый в обычный, но немного запущенный домашний халат, он олицетворяет ленивую мечтательность, склонную к самоанализу и меланхолии. Интерьер квартиры, отражающий его внутреннее состояние, наполнен легкой небрежностью, создавая атмосферу затянувшегося бездействия и тоски по утерянным возможностям.'
    # print(desc_image)

    # dalle_model = dalle_api.DalleAgent('Цветная иллюстрация', 'не содержит текста')
    # # Сформировать картинку
    # dalle_answer = dalle_model.get_response(desc_image)
    # image_link = dalle_answer['msg']
    # print(image_link)
