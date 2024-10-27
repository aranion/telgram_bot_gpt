from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def clear_state_kb():
    inline_kb_list = [
        [
            InlineKeyboardButton(text="Отмена", callback_data='clear_state'),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=inline_kb_list)


def regenerate_kb():
    inline_kb_list = [
        [
            InlineKeyboardButton(text="Пересоздать", callback_data='regenerate'),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=inline_kb_list)
