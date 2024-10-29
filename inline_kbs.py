from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def clear_state_kb():
    inline_kb_list = [
        [
            InlineKeyboardButton(text="Отмена", callback_data='clear_state'),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=inline_kb_list)


def regenerate_kb():
    inline_kb_list = [
        [
            InlineKeyboardButton(text="👍", callback_data='like'),
            InlineKeyboardButton(text="Пересоздать", callback_data='regenerate'),
            InlineKeyboardButton(text="👎", callback_data='dislike'),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=inline_kb_list)
