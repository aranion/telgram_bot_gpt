from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_home_kb():
    inline_kb_list = [
        [
            InlineKeyboardButton(text="Тесты", callback_data='get_test'),
            InlineKeyboardButton(text="Статистика", callback_data='get_user_info')
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=inline_kb_list)


def get_user_answer_test_kb(test_id, list_answer):
    inline_kb_list = []

    for key in list_answer:
        inline_kb_list.append(
            [InlineKeyboardButton(text=f"{key}) {list_answer[key]}", callback_data=f'answer_{key}_{test_id}')])

    return InlineKeyboardMarkup(inline_keyboard=inline_kb_list)


def get_error_message_test_kb():
    inline_kb_list = [
        [InlineKeyboardButton(text="Новый тест", callback_data='get_test')],
        [InlineKeyboardButton(text="Статистика", callback_data='get_user_info')],
        [InlineKeyboardButton(text="Сообщить об ошибке", callback_data='error_message_test')],
    ]

    return InlineKeyboardMarkup(inline_keyboard=inline_kb_list)
