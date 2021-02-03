from aiogram import types
import __init__


def main_keyboard_admin():
    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    kb_show_created_tasks = '🔞 Показать задачи'
    kb_create_task = '🆕 Создать задачу'
    kb_settings = '⚙ Настройки'
    keyboard.row(kb_show_created_tasks, kb_create_task)
    keyboard.add(kb_settings)
    message = "👉 Команда /update обновит списки и метки в базе данных\n👉 /id - узнать свой chat id"
    message += "\n🛠 Выбирай что ты хочешь сделать! 🛠"
    if not __init__.ListIdForTasksFromTG:
        message += "\nДля начала тебе надо перейти 🚶🏿‍♂ в '⚙ Настройки'\nи установить список по-умолчанию(" \
                   "для задач созданных в боте)"
    if not __init__.ImportantLabelId:
        message += "\nТакже в '⚙ Настройки' необходимо выбрать метку, которой будут отмечатся срочные задачи " \
                   "на трелло"

    return message, keyboard


def main_keyboard_user():
    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    kb_show_created_tasks = '🔞 Показать задачи'
    kb_create_task = '🆕 Создать задачу'
    kb_quick_task = '🏃🏽‍♂ Quick Task\n(лишь название и важность)'
    keyboard.row(kb_show_created_tasks, kb_create_task)
    keyboard.add(kb_quick_task)
    message = "👉 /id - узнать свой chat id\n🛠 Выбирай что ты хочешь сделать! 🛠"

    return message, keyboard


def cancel_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add('Отмена')

    return keyboard


def time_keyboard():
    keyboard = types.InlineKeyboardMarkup(row_width=4)
    for i in range(0, 24):
        kb = types.InlineKeyboardButton(str(i)+'h', callback_data=f"deadline_hour:{str(i)}")
        keyboard.insert(kb)

    return keyboard
