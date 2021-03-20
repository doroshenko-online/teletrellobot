from aiogram import types
import __init__


def yes_no_keyboard(resize_keyboard=False):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=resize_keyboard, one_time_keyboard=True)
    keyboard.add('Да')
    keyboard.add('Нет')
    return keyboard


def yes_no_cancel_keyboard(resize_keyboard=False):
    keyboard = yes_no_keyboard(resize_keyboard)
    keyboard.add('Отмена')
    return keyboard


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


def task_inline_keyboard(task_id, admin=False):
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    kb_close = types.InlineKeyboardButton("✖ Закрыть",  callback_data=f"task_action:close|task_id:{task_id}")
    kb_edit = types.InlineKeyboardButton("® Редактировать", callback_data=f"task_action:edit|task_id:{task_id}")
    kb_show_comments = types.InlineKeyboardButton("👁‍🗨 Комментарии", callback_data=f"task_action:show_comments|task_id:{task_id}")
    kb_add_comment = types.InlineKeyboardButton("➕ Добавить комментарий", callback_data=f"task_action:add_comment|task_id:{task_id}")
    kb_replace = types.InlineKeyboardButton("🔛 Поместить в другой список", callback_data=f"task_action:move|task_id:{task_id}")

    keyboard.insert(kb_close)
    keyboard.insert(kb_edit)
    keyboard.insert(kb_show_comments)
    keyboard.insert(kb_add_comment)
    if admin:
        keyboard.insert(kb_replace)
    return keyboard
