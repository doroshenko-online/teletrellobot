from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher, FSMContext
from aiogram.utils import executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters import Text
from states.Task import *
from states.Setup_list import *
from states.Task_edit import *
from states.Task_add_comment import *
from states.Task_close import *
from states.Quick_task import *
from db_handler import *
from misc import *
from aiogramcalendar import calendar_callback, create_calendar, process_calendar_selection
import os
import uuid
import __init__
from datetime import datetime, timedelta
import asyncio

memory_storage = MemoryStorage()
bot = Bot(token=TG_TOKEN)
dp = Dispatcher(bot, storage=memory_storage)


@dp.message_handler(commands=['calendar'])
async def cmd_start(message: types.Message):
    keyboard = cancel_keyboard()
    await message.answer("Нажмите 'Отмена'", reply_markup=keyboard)
    await message.answer("Или выберите дату: ", reply_markup=create_calendar())


@dp.callback_query_handler(calendar_callback.filter())  # handler is processing only calendar_callback queries
async def process_calendar(callback_query: types.CallbackQuery, callback_data: dict):
    selected, date = await process_calendar_selection(callback_query, callback_data)
    if selected:
        await callback_query.message.answer(f'Вы выбрали {date.strftime("%d/%m/%Y")}',
                                            reply_markup=types.ReplyKeyboardRemove())


@dp.message_handler(commands="cancel", state="*")
@dp.message_handler(Text(equals="Отмена", ignore_case=True), state="*")
async def cmd_cancel(msg: types.Message, state: FSMContext):
    if str(msg.from_user.id) in TG_WORKERS_CHAT_ID:
        message, keyboard = main_keyboard_admin()
    else:
        message, keyboard = main_keyboard_user()
    await msg.answer("Действие отменено", reply_markup=None)
    await msg.answer(message, reply_markup=keyboard)
    # Сбрасываем текущее состояние пользователя и сохранённые о нём данные
    await state.finish()


@dp.message_handler(commands=['start', 'help'], state='*')
async def echo_message(msg: types.Message):
    if str(msg.from_user.id) in TG_WORKERS_CHAT_ID:
        message, keyboard = main_keyboard_admin()
    else:
        message, keyboard = main_keyboard_user()

    await msg.answer(message, reply_markup=keyboard)


async def update():
    trunc_lists()
    trunc_labels()
    lists = []
    ls_from_tr = BOARD.get_lists(list_filter='open')
    for lis in ls_from_tr:
        lists.append([lis.id, lis.name])

    insert_dashboard_lists(lists)

    labels = []
    lab_from_tr = BOARD.get_labels()
    for label in lab_from_tr:
        labels.append([str(label.id), str(label.name), str(label.color)])
    insert_labels(labels)
    if __init__.ListIdForTasksFromTG:
        check_list = get_list(__init__.ListIdForTasksFromTG)
        if not check_list:
            config['trello']['listidfortasksfromtg'] = ''
            with open(CONFIG_FILE, 'w') as conffile:
                config.write(conffile)
            config.read(CONFIG_FILE)
            __init__.ListIdForTasksFromTG = config['trello']['listidfortasksfromtg']
            for chat in TG_WORKERS_CHAT_ID:
                await bot.send_message(chat_id=chat,
                                       text="❗❗ Список по-умолчанию был удален из трелло! Необходимо снова "
                                            "выбрать список "
                                            "по-умолчанию в '⚙ Настройки' ❗❗")

    if __init__.ImportantLabelId:
        check_label = get_label(__init__.ImportantLabelId)
        if not check_label:
            config['trello']['importantlabelid'] = ''
            with open(CONFIG_FILE, 'w') as conffile:
                config.write(conffile)
            config.read(CONFIG_FILE)
            __init__.ImportantLabelId = config['trello']['importantlabelid']
            for chat in TG_WORKERS_CHAT_ID:
                await bot.send_message(chat_id=chat, text="❗❗ Метка для важных задач была удалена из трелло! "
                                                          "Необходимо снова выбрать метку в "
                                                          "'⚙ Настройки' ❗❗")
    tasks = get_tasks()
    for task in tasks:
        task_tr = client.get_card(str(task[0]))
        if task_tr.closed:
            delete_task(task[0])
            continue
        if str(task_tr.list_id) != task[1]:
            task_change_list(task[0], task_tr.list_id)


async def update_auto():
    while True:
        await update()
        await asyncio.sleep(300)


@dp.message_handler(commands=['update'], state='*')
async def update_manual(msg: types.Message):
    if str(msg.from_user.id) in TG_WORKERS_CHAT_ID:
        await update()
        await msg.answer("Данные списков, меток и задач обновлены")
        message, keyboard = main_keyboard_admin()
    else:
        message, keyboard = main_keyboard_user()

    await msg.answer(message, reply_markup=keyboard)


@dp.callback_query_handler(lambda c: c.data and c.data.startswith('list_id'))
async def process_set_list_tr(callback_query: types.CallbackQuery):
    await bot.edit_message_text(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id,
                                text='👉 Необходимо выбрать список на доске в трелло, куда помещать задачи созданные в боте',
                                reply_markup=None)
    list_id = callback_query.data.split(':')[1]
    config['trello']['listidfortasksfromtg'] = list_id
    with open(CONFIG_FILE, 'w') as conffile:
        config.write(conffile)
    config.read(CONFIG_FILE)
    __init__.ListIdForTasksFromTG = config['trello']['listidfortasksfromtg']
    db_list = BOARD.get_list(list_id)
    message = f"Теперь задачи будут создаваться в списке '{db_list.name}'\n"
    await bot.send_message(callback_query.from_user.id, message, reply_markup=None)
    message, kb = main_keyboard_admin()
    await bot.send_message(callback_query.from_user.id, message, reply_markup=kb)


@dp.callback_query_handler(lambda c: c.data and c.data.startswith('label_id'))
async def process_set_label_tr(callback_query: types.CallbackQuery):
    await bot.edit_message_text(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id,
                                text='👉 Необходимо выбрать метку, которой будут отмечатся важные задачи на трелло',
                                reply_markup=None)
    label_id = callback_query.data.split(':')[1]
    config['trello']['importantlabelid'] = label_id
    with open(CONFIG_FILE, 'w') as conffile:
        config.write(conffile)
    config.read(CONFIG_FILE)
    __init__.ImportantLabelId = config['trello']['importantlabelid']
    db_label = get_label(label_id)
    message = f"Метка с названием '{db_label[1]}', цвета {db_label[2]} теперь будет отмечать срочные задачи\nВведите " \
              f"/help для просмотра команд "
    await bot.send_message(callback_query.from_user.id, message, reply_markup=None)
    message, kb = main_keyboard_admin()
    await bot.send_message(callback_query.from_user.id, message, reply_markup=kb)


@dp.message_handler(state=Setup_list.waiting_for_list_name, content_types=types.ContentTypes.TEXT)
async def setup_new_list_step_1(msg: types.Message, state: FSMContext):
    message = f"🟢 Создан новый список с названием '{msg.text}'"
    list_id = BOARD.add_list(msg.text)
    await state.update_data(list_id=str(list_id.id))
    insert_dashboard_lists([[list_id, msg.text]])
    await msg.answer(message)
    keyboard = yes_no_keyboard()
    message = "Установить этот список как список для задач из бота по-умолчанию?"
    await msg.answer(message, reply_markup=keyboard)
    await Setup_list.next()


@dp.message_handler(state=Setup_list.waiting_for_list_default, content_types=types.ContentTypes.TEXT)
async def setup_new_list_step_2(msg: types.Message, state: FSMContext):
    if msg.text == 'Да':
        user_data = await state.get_data()
        config['trello']['ListIdForTasksFromTG'] = user_data['list_id']
        with open(CONFIG_FILE, 'w') as conffile:
            config.write(conffile)
        config.read(CONFIG_FILE)
        __init__.ListIdForTasksFromTG = config['trello']['listidfortasksfromtg']
        await msg.answer("🟢 Список успешно установлен как список по-умолчанию 🟢")
        await state.finish()
    elif msg.text == 'Нет':
        await msg.answer("🏁 Создание списка окончено")
        await state.finish()
    else:
        return

    message, keyboard = main_keyboard_admin()
    await msg.answer(message, reply_markup=keyboard)


@dp.message_handler(commands=['id'])
async def echo_message(msg: types.Message):
    await bot.send_message(msg.from_user.id, msg.from_user.id)


@dp.message_handler(state=QuickTask.waiting_for_task_name, content_types=types.ContentTypes.TEXT)
async def quick_task_step_1(msg: types.Message, state: FSMContext):
    await state.update_data(task_name=msg.text)
    message = "Установить эту задачу как срочную?\nотправьте команду /cancel или нажмите кнопку 'Отмена' чтобы " \
              "отменить создание задачи"
    keyboard = yes_no_cancel_keyboard(True)
    await QuickTask.next()
    await msg.answer(message, reply_markup=keyboard)


@dp.message_handler(state=QuickTask.waiting_for_task_label, content_types=types.ContentTypes.TEXT)
async def quick_task_step_2(msg: types.Message, state: FSMContext):
    if msg.text == 'Да':
        await state.update_data(task_label=True)
    elif msg.text == 'Нет':
        await state.update_data(task_label=False)
    else:
        message = "Нажмите кнопку 'Да', 'Нет' или 'Отмена'"
        await msg.answer(message)
        return

    user_data = await state.get_data()
    if user_data['task_label']:
        msg_important = "⛔ ⛔ Срочная ⛔ ⛔"
        fdb = str(__init__.ImportantLabelId)
    else:
        fdb = ''
        msg_important = "Обычная"

    task_name = f"[{str(msg.from_user.username)}] " + user_data['task_name']
    list_id = user_data['list_id']
    board_list = BOARD.get_list(list_id)

    if not __init__.ImportantLabelId or user_data['task_label'] == False:
        card = board_list.add_card(name=task_name)
    else:
        label = client.get_label(__init__.ImportantLabelId, TR_BOARD_ID)
        card = board_list.add_card(name=task_name, labels=[label])

    mesg_workers = []

    mesg = await bot.send_message(str(msg.from_user.id),
                                  f"✅ Задача создана!\n💥 От кого: @{str(msg.from_user.username)}\n💥 Название:{task_name}\n💥 Важность: {msg_important}",
                                  reply_markup=types.ReplyKeyboardRemove())
    for chat in TG_WORKERS_CHAT_ID:
        mes = await bot.send_message(chat,
                                     f"✅ Пришла новая Quick задача! - {card.shortUrl}\n💥 От кого: @{str(msg.from_user.username)}\n💥 Название:{task_name}\n💥 Список: {board_list.name}\n💥 Важность: {msg_important}")
        mesg_workers.append(f"{chat}:" + str(mes.message_id))

    insert_task(task_id=str(card.id), list_id=str(card.list_id), name=task_name, user_id=str(msg.from_user.id),
                username=str(msg.from_user.username), message_creator_id=mesg.message_id,
                short_link=str(card.shortUrl), workers_messages=mesg_workers)

    message, keyboard = main_keyboard_user()
    await msg.answer(message, reply_markup=keyboard)
    await state.finish()


@dp.message_handler(state=Task.waiting_for_task_name, content_types=types.ContentTypes.TEXT)
async def task_step_2(msg: types.Message, state: FSMContext):
    await state.update_data(task_name=msg.text)
    keyboard = cancel_keyboard()
    message = "Введите описание задачи\nотправьте команду /cancel или нажмите кнопку 'Отмена' чтобы отменить " \
              "создание задачи "
    await Task.next()
    await msg.answer(message, reply_markup=keyboard)


@dp.message_handler(state=Task.waiting_for_task_desc, content_types=types.ContentTypes.TEXT)
async def task_step_3(msg: types.Message, state: FSMContext):
    await state.update_data(task_desc=msg.text)
    message = "Добавить файлы или фото к задаче?\nотправьте команду /cancel или нажмите кнопку 'Отмена' чтобы " \
              "отменить создание задачи"
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add('Да')
    keyboard.add('Нет')
    keyboard.add('Отмена')
    await Task.next()
    await msg.answer(message, reply_markup=keyboard)


@dp.message_handler(state=Task.need_files, content_types=types.ContentTypes.TEXT)
async def task_step_4(msg: types.Message, state: FSMContext):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    if msg.text == 'Да':
        await Task.waiting_for_files.set()
        uid = str(uuid.uuid1())
        kb = "🤲 Хватит добавлять, идем дальше!!"
        keyboard.add(kb)
        message = "Добавьте фото, группу фото или документ\nотправьте команду /cancel или нажмите кнопку 'Отмена' чтобы " \
                  "отменить создание задачи"
        await state.update_data(files_dir_id=uid)
        await state.update_data(docs={})
    elif msg.text == 'Нет':
        await Task.waiting_for_task_label.set()
        await state.update_data(files_dir_id='')
        message = "Установить эту задачу как срочную?\nотправьте команду /cancel или нажмите кнопку 'Отмена' чтобы " \
                  "отменить создание задачи"
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        keyboard.add('Да')
        keyboard.add('Нет')
    else:
        message = "Нажмите кнопку 'Да', 'Нет' или 'Отмена'"
        await msg.answer(message)
        return
    keyboard.add('Отмена')
    await msg.answer(message, reply_markup=keyboard)


@dp.message_handler(state=Task.waiting_for_files, content_types=types.ContentTypes.ANY)
async def task_step_5(msg: types.Message, state: FSMContext):
    user_data = await state.get_data()
    main_dir = BASE_PATH + "files/" + str(msg.from_user.id) + "/" + user_data['files_dir_id']
    if not os.path.exists(BASE_PATH + "files/" + str(msg.from_user.id)):
        os.mkdir(BASE_PATH + "files/" + str(msg.from_user.id))
    if not os.path.exists(main_dir):
        os.mkdir(main_dir)
    if msg.content_type == 'photo':
        photo = msg.photo.pop()
        if not os.path.exists(main_dir + "/photo"):
            os.mkdir(main_dir + "/photo")
        await photo.download(main_dir + "/photo/" + str(photo.file_id) + ".jpg")
    elif msg.content_type == 'document':
        if not os.path.exists(main_dir + "/document"):
            os.mkdir(main_dir + "/document")
        user_data = await state.get_data()
        user_data['docs'].update({str(msg.document.file_name): str(msg.document.mime_type)})
        await state.update_data(docs=user_data['docs'])
        await msg.document.download(main_dir + "/document/" + str(msg.document.file_name))
    elif msg.content_type == 'text' and msg.text.startswith("🤲"):
        await Task.waiting_for_task_label.set()
        message = "Установить эту задачу как срочную?\nотправьте команду /cancel или нажмите кнопку 'Отмена' чтобы " \
                  "отменить создание задачи"
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        keyboard.add('Да')
        keyboard.add('Нет')
        keyboard.add('Отмена')
        await msg.answer(message, reply_markup=keyboard)
    else:
        message = "Доступны лишь фото и документы"
        await msg.answer(message)
        return


@dp.message_handler(state=Task.waiting_for_task_label, content_types=types.ContentTypes.TEXT)
async def task_step_6(msg: types.Message, state: FSMContext):
    if msg.text == 'Да':
        await state.update_data(task_label=True)
    elif msg.text == 'Нет':
        await state.update_data(task_label=False)
    else:
        message = "Нажмите кнопку 'Да', 'Нет' или 'Отмена'"
        await msg.answer(message)
        return
    await state.update_data(important=True)
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add('Да')
    keyboard.add('Нет')
    keyboard.add('Отмена')
    await Task.next()
    message = "Установить дедлайн по задаче?"
    await msg.answer(message, reply_markup=keyboard)


@dp.message_handler(state=Task.waiting_for_deadline, content_types=types.ContentTypes.TEXT)
async def task_step_7(msg: types.Message, state: FSMContext):
    if msg.text == 'Да':
        await Task.waiting_for_date.set()
        keyboard = cancel_keyboard()
        await msg.answer("Нажмите 'Отмена'", reply_markup=keyboard)
        await msg.answer("Или выберите дату: ", reply_markup=create_calendar())
    elif msg.text == 'Нет':
        list_of_photos = []
        list_of_documents = []
        # Сохранение задачи, дедлайн не установлен
        user_data = await state.get_data()
        if user_data['task_label']:
            msg_important = "⛔ ⛔ Срочная ⛔ ⛔"
            fdb = str(__init__.ImportantLabelId)
        else:
            fdb = ''
            msg_important = "Обычная"

        task_name = f"[{str(msg.from_user.username)}] " + user_data['task_name']
        list_id = user_data['list_id']
        board_list = BOARD.get_list(list_id)
        if not __init__.ImportantLabelId or user_data['task_label'] == False:
            card = board_list.add_card(name=task_name,
                                       desc=user_data['task_desc'])
        else:
            label = client.get_label(__init__.ImportantLabelId, TR_BOARD_ID)
            card = board_list.add_card(name=task_name,
                                       desc=user_data['task_desc'],
                                       labels=[label])
        if user_data['files_dir_id'] != '':
            photo_dir = BASE_PATH + 'files/' + str(msg.from_user.id) + '/' + user_data['files_dir_id'] + "/photo"
            document_dir = BASE_PATH + 'files/' + str(msg.from_user.id) + '/' + user_data['files_dir_id'] + "/document"
            list_of_photos = []
            list_of_documents = []
            if os.path.exists(photo_dir):
                list_of_photos = os.listdir(photo_dir)
                for file in list_of_photos:
                    card.attach(name=file, file=open(photo_dir + "/" + file, mode='rb'), mimeType='image/jpeg')

            if os.path.exists(document_dir):
                list_of_documents = os.listdir(document_dir)
                for file in list_of_documents:
                    card.attach(name=file, file=open(document_dir + "/" + file, mode='rb'),
                                mimeType=user_data['docs'][file])

        mesg_workers = []
        if str(msg.from_user.id) in TG_WORKERS_CHAT_ID:
            mesg = await bot.send_message(str(msg.from_user.id),
                                          f"✅ Задача создана! - {card.shortUrl}\n💥 От кого: @{str(msg.from_user.username)}\n💥 Название:{task_name}\n💥 Список: {board_list.name}\n💥 Описание:\n{user_data['task_desc']}\n💥 Дедлайн: Нет\n💥 Важность: {msg_important}",
                                          reply_markup=types.ReplyKeyboardRemove())
            for chat in TG_WORKERS_CHAT_ID:
                if chat != str(msg.from_user.id):
                    mes = await bot.send_message(chat,
                                                 f"✅ Пришла новая задача! - {card.shortUrl}\n💥 От кого: @{str(msg.from_user.username)}\n💥 Название:{task_name}\n💥 Список: {board_list.name}\n💥 Описание:\n{user_data['task_desc']}\n💥 Дедлайн: Нет\n💥 Важность: {msg_important}")
                    mesg_workers.append(f"{chat}:" + str(mes.message_id))
                    if user_data['files_dir_id'] == '':
                        pass
                    else:
                        await bot.send_message(chat, "💥 Вложения к задаче:\n")
                        if list_of_photos:
                            media = types.MediaGroup()
                            for photo in list_of_photos:
                                media.attach_photo(types.InputFile(photo_dir + "/" + photo))
                            await bot.send_media_group(chat, media=media)

                        if list_of_documents:
                            for doc in list_of_documents:
                                await bot.send_document(chat, document=types.InputFile(document_dir + "/" + doc))

        else:
            mesg = await bot.send_message(str(msg.from_user.id),
                                          f"✅ Задача создана!\n💥 От кого: @{str(msg.from_user.username)}\n💥 Название:{task_name}\n💥 Описание:\n{user_data['task_desc']}\n💥 Дедлайн: Нет\n💥 Важность: {msg_important}",
                                          reply_markup=types.ReplyKeyboardRemove())
            for chat in TG_WORKERS_CHAT_ID:
                mes = await bot.send_message(chat,
                                             f"✅ Пришла новая задача! - {card.shortUrl}\n💥 От кого: @{str(msg.from_user.username)}\n💥 Название:{task_name}\n💥 Список: {board_list.name}\n💥 Описание:\n{user_data['task_desc']}\n💥 Дедлайн: Нет\n💥 Важность: {msg_important}")
                mesg_workers.append(f"{chat}:" + str(mes.message_id))
                if user_data['files_dir_id'] == '':
                    pass
                else:
                    await bot.send_message(chat, "💥 Вложения к задаче:\n")
                    if list_of_photos:
                        media = types.MediaGroup()
                        for photo in list_of_photos:
                            media.attach_photo(types.InputFile(photo_dir + "/" + photo))
                        await bot.send_media_group(chat, media=media)

                    if list_of_documents:
                        for doc in list_of_documents:
                            await bot.send_document(chat, document=types.InputFile(document_dir + "/" + doc))

        if user_data['files_dir_id'] == '':
            pass
        else:
            await msg.answer("💥 Вложения к задаче:\n")
            if list_of_photos:
                media = types.MediaGroup()
                for photo in list_of_photos:
                    media.attach_photo(types.InputFile(photo_dir + "/" + photo))
                await bot.send_media_group(msg.from_user.id, media=media)

            if list_of_documents:
                for doc in list_of_documents:
                    await bot.send_document(msg.from_user.id, document=types.InputFile(document_dir + "/" + doc))

        insert_task(task_id=str(card.id), list_id=str(card.list_id), name=task_name, user_id=str(msg.from_user.id),
                    username=str(msg.from_user.username), message_creator_id=mesg.message_id,
                    files_uid=user_data['files_dir_id'], short_link=str(card.shortUrl), workers_messages=mesg_workers)

        if str(msg.from_user.id) in TG_WORKERS_CHAT_ID:
            message, keyboard = main_keyboard_admin()
        else:
            message, keyboard = main_keyboard_user()
        await msg.answer(message, reply_markup=keyboard)
        await state.finish()
    else:
        message = "Нажмите кнопку 'Да', 'Нет' или 'Отмена'"
        await msg.answer(message)
        return


@dp.callback_query_handler(calendar_callback.filter(), state=Task.waiting_for_date)
async def process_task_set_date(callback_query: types.CallbackQuery, callback_data: dict, state: FSMContext):
    selected, date = await process_calendar_selection(callback_query, callback_data)
    if selected:
        await state.update_data(deadline_date=date.strftime("%m-%d-%Y"))
        await callback_query.message.answer(f'Вы выбрали {date.strftime("%m-%d-%Y")}',
                                            reply_markup=types.ReplyKeyboardRemove())
        keyboard = cancel_keyboard()
        await callback_query.message.answer("Нажмите 'Отмена'", reply_markup=keyboard)
        await callback_query.message.answer("Или выберите время: ", reply_markup=time_keyboard())
        await Task.waiting_for_time.set()


# Запись задачи после выбора задачи
@dp.callback_query_handler(lambda c: c.data and c.data.startswith('deadline_hour'), state=Task.waiting_for_time)
async def process_task_set_time(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.message.delete_reply_markup()
    selected_hour = str(callback_query.data.split(':')[1])
    user_data = await state.get_data()
    username = str(callback_query.from_user.username)
    chat_id = str(callback_query.from_user.id)
    task_name = f"[{username}] " + user_data['task_name']
    photo_dir = BASE_PATH + 'files/' + str(callback_query.from_user.id) + '/' + user_data['files_dir_id'] + "/photo"
    document_dir = BASE_PATH + 'files/' + str(callback_query.from_user.id) + '/' + user_data[
        'files_dir_id'] + "/document"
    list_of_photos = []
    list_of_documents = []
    if user_data['task_label']:
        msg_important = "⛔ ⛔ Срочная ⛔ ⛔"
    else:
        msg_important = "Обычная"

    if int(selected_hour) == 0:
        selected_hour = '22'
    elif int(selected_hour) == 1:
        selected_hour = '23'
    else:
        selected_hour = str(int(selected_hour) - 2)

    board_list = BOARD.get_list(user_data['list_id'])
    if not __init__.ImportantLabelId or user_data['task_label'] == False:
        card = board_list.add_card(name=f"[{callback_query.from_user.username}]" + str(user_data['task_name']),
                                   desc=user_data['task_desc'],
                                   due=f"{user_data['deadline_date']}Z{selected_hour}:00:00")
    else:
        label = client.get_label(__init__.ImportantLabelId, TR_BOARD_ID)
        card = board_list.add_card(name=f"[{callback_query.from_user.username}]" + str(user_data['task_name']),
                                   desc=user_data['task_desc'],
                                   due=f"{user_data['deadline_date']}Z{selected_hour}:00:00",
                                   labels=[label])

    if user_data['files_dir_id'] != '':
        photo_dir = BASE_PATH + 'files/' + str(chat_id) + '/' + user_data['files_dir_id'] + "/photo"
        document_dir = BASE_PATH + 'files/' + str(chat_id) + '/' + user_data['files_dir_id'] + "/document"
        list_of_photos = []
        list_of_documents = []
        if os.path.exists(photo_dir):
            list_of_photos = os.listdir(photo_dir)
            for file in list_of_photos:
                card.attach(name=file, file=open(photo_dir + "/" + file, mode='rb'), mimeType='image/jpeg')

        if os.path.exists(document_dir):
            list_of_documents = os.listdir(document_dir)
            for file in list_of_documents:
                card.attach(name=file, file=open(document_dir + "/" + file, mode='rb'),
                            mimeType=user_data['docs'][file])

    mesg_workers = []
    if str(callback_query.from_user.id) in TG_WORKERS_CHAT_ID:
        mesg = await bot.send_message(chat_id,
                                      f"✅ Задача создана! - {card.shortUrl}\n💥 От кого: @{str(callback_query.from_user.username)}\n💥 Название:{task_name}\n💥 Список: {board_list.name}\n💥 Описание:\n{user_data['task_desc']}\n💥 Дедлайн: {user_data['deadline_date']} {int(selected_hour) + 2}:00:00\n💥 Важность: {msg_important}",
                                      reply_markup=types.ReplyKeyboardRemove())
        for chat in TG_WORKERS_CHAT_ID:
            if chat != str(callback_query.from_user.id):
                mes = await bot.send_message(chat,
                                             f"✅ Пришла новая задача! - {card.shortUrl}\n💥 От кого: @{str(callback_query.from_user.username)}\n💥 Название:{task_name}\n💥 Список: {board_list.name}\n💥 Описание:\n{user_data['task_desc']}\n💥 Дедлайн: {user_data['deadline_date']} {int(selected_hour) + 2}:00:00\n💥 Важность: {msg_important}")
                mesg_workers.append(mes.message_id)

                if user_data['files_dir_id'] == '':
                    await bot.send_message(chat, "💥 Вложения к задаче: нету")
                else:
                    await bot.send_message(chat, "💥 Вложения к задаче:\n")
                    if list_of_photos:
                        media = types.MediaGroup()
                        for photo in list_of_photos:
                            media.attach_photo(types.InputFile(photo_dir + "/" + photo))
                        await bot.send_media_group(chat, media=media)

                    if list_of_documents:
                        for doc in list_of_documents:
                            await bot.send_document(chat, document=types.InputFile(document_dir + "/" + doc))

    else:
        mesg = await bot.send_message(chat_id,
                                      f"✅ Задача создана!\n💥 От кого: @{str(callback_query.from_user.username)}\n💥 Название:{task_name}\n💥 Описание:\n{user_data['task_desc']}\n💥 Дедлайн: {user_data['deadline_date']} {int(selected_hour) + 2}:00:00\n💥 Важность: {msg_important}",
                                      reply_markup=types.ReplyKeyboardRemove())
        for chat in TG_WORKERS_CHAT_ID:
            mes = await bot.send_message(chat,
                                         f"✅ Пришла новая задача! - {card.shortUrl}\n💥 От кого: @{str(callback_query.from_user.username)}\n💥 Название:{task_name}\n💥 Список: {board_list.name}\n💥 Описание:\n{user_data['task_desc']}\n💥 Дедлайн: {user_data['deadline_date']} {int(selected_hour) + 2}:00:00\n💥 Важность: {msg_important}")
            mesg_workers.append(mes.message_id)

            if user_data['files_dir_id'] == '':
                pass
            else:
                await bot.send_message(chat, "💥 Вложения к задаче:\n")
                if list_of_photos:
                    media = types.MediaGroup()
                    for photo in list_of_photos:
                        media.attach_photo(types.InputFile(photo_dir + "/" + photo))
                    await bot.send_media_group(chat, media=media)

                if list_of_documents:
                    for doc in list_of_documents:
                        await bot.send_document(chat, document=types.InputFile(document_dir + "/" + doc))
    if user_data['files_dir_id'] == '':
        pass
    else:
        await bot.send_message(chat_id, "💥 Вложения к задаче:\n")
        if list_of_photos:
            media = types.MediaGroup()
            for photo in list_of_photos:
                media.attach_photo(types.InputFile(photo_dir + "/" + photo))
            await bot.send_media_group(callback_query.from_user.id, media=media)

        if list_of_documents:
            for doc in list_of_documents:
                await bot.send_document(callback_query.from_user.id, document=types.InputFile(document_dir + "/" + doc))

    insert_task(task_id=str(card.id), list_id=str(card.list_id), name=task_name, user_id=chat_id,
                username=username, message_creator_id=mesg.message_id, files_uid=user_data['files_dir_id'],
                short_link=str(card.shortUrl))

    if chat_id in TG_WORKERS_CHAT_ID:
        message, keyboard = main_keyboard_admin()
    else:
        message, keyboard = main_keyboard_user()
    await callback_query.message.answer(message, reply_markup=keyboard)
    await state.finish()


@dp.message_handler(state=Task.waiting_for_select_list, content_types=types.ContentTypes.TEXT)
async def process_set_list_for_task(msg: types.Message, state: FSMContext):
    db_list = get_list_by_name(msg.text)
    if db_list:
        await Task.next()
        await state.update_data(list_id=db_list[0])
        keyboard = cancel_keyboard()
        message = f"Выбран список '{db_list[1]}'\nВведите название задачи\nотправьте команду /cancel или нажмите кнопку 'Отмена' чтобы отменить " \
                  "создание задачи"
        await msg.answer(message, reply_markup=keyboard)
    else:
        return


@dp.message_handler(content_types=types.ContentTypes.TEXT)
async def select_action(msg: types.Message, state: FSMContext):
    if str(msg.from_user.id) in TG_WORKERS_CHAT_ID:
        message, keyboard = main_keyboard_admin()
        # Переход в настройки
        if msg.text.startswith('⚙'):
            keyboard = types.ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)
            keyboard.row('🔖 Установить список для задач', '📍 Установить метку для срочных задач')
            keyboard.row('⬅ Назад', '⏫ Создать список')
            message = "'⬅ Назад' чтобы вернутся в главное меню"
        # Назад
        elif msg.text.startswith('⬅'):
            pass
        # Создать задачу
        elif msg.text.startswith('🆕'):
            await Task.waiting_for_select_list.set()
            message = "👇🏻 Выбери список для задачи: 👇🏻"
            keyboard = types.ReplyKeyboardMarkup(row_width=2)
            lists = get_dashboards_lists()
            for ls in lists:
                keyboard.insert(ls[1])
            keyboard.add('Отмена')
        elif msg.text.startswith('🔞'):
            tasks = get_tasks()
            if not tasks:
                message = "Список задач пуст 🥡"
                await msg.answer(message)
            else:
                for task in tasks:
                    task_tr = client.get_card(task[0])
                    list_tr = BOARD.get_list(task[1])
                    if task_tr.due:
                        deadline_date = datetime.strptime(task_tr.due, "%Y-%m-%dT%H:%M:%S.%fZ") + timedelta(hours=2)
                    else:
                        deadline_date = 'Нет'
                    message = f"📄 {task[7]}\n🔥 НАЗВАНИЕ: {task_tr.name}\n🔥 Список: {list_tr.name}\n🔥 ОПИСАНИЕ: {task_tr.desc}\n🔥 СОЗДАТЕЛЬ: @{task[4]}\n🔥 ДЕДЛАЙН: {deadline_date}\n" \
                              f"🔥 ДАТА СОЗДАНИЯ: {str(task[5])}"

                    if task[6]:
                        uid = task[6]
                        message += "\n 🔥 Вложения:"
                    keyboard = task_inline_keyboard(task[0], admin=True)
                    if task[6]:
                        mesg = await msg.answer(message)
                        mesg = mesg.message_id
                        uid = task[6]
                        message += "\n 🔥 Вложения:"
                        fdir = BASE_PATH + f"files/{task[3]}/{uid}/"
                        if os.path.exists(fdir + "photo"):
                            photos = os.listdir(fdir + "photo")
                            media = types.MediaGroup()
                            for photo in photos:
                                media.attach_photo(types.InputFile(fdir + "photo/" + photo))
                            await bot.send_media_group(msg.from_user.id, media=media)
                        if os.path.exists(fdir + "document"):
                            docs = os.listdir(fdir + "document")
                            for doc in docs:
                                mesg = await bot.send_document(msg.from_user.id,
                                                               document=types.InputFile(fdir + "document/" + doc))
                                mesg = mesg.message_id
                        await bot.edit_message_reply_markup(msg.from_user.id, mesg, reply_markup=keyboard)
                    else:
                        await msg.answer(message, reply_markup=keyboard)
            return
        elif msg.text.startswith('🔖'):
            keyboard = types.InlineKeyboardMarkup()
            message = "👉 Необходимо выбрать список на доске в трелло, куда помещать задачи созданные в боте"
            lists = get_dashboards_lists()
            if len(lists) > 0:
                for ls in lists:
                    keyboard.add(types.InlineKeyboardButton(ls[1], callback_data=f"list_id:{ls[0]}"))
            else:
                message = "😞 Нет списков в базе данных. Выполните команду /update, если списки имеются на трелло"
                keyboard = None
                await msg.answer(message, keyboard)
                message, keyboard = main_keyboard_admin()
        elif msg.text.startswith('📍'):
            keyboard = types.InlineKeyboardMarkup()
            message = '👉 Необходимо выбрать метку, которой будут отмечатся важные задачи на трелло'
            labels = get_labels()
            if len(labels) > 0:
                for lb in labels:
                    keyboard.add(types.InlineKeyboardButton(f"Название: {lb[1]} | Цвет: {lb[2]}",
                                                            callback_data=f"label_id:{lb[0]}"))
            else:
                message = "😞 Нет меток в базе данных. Выполните команду /update, если метки имеются на трелло"
                keyboard = None
                await msg.answer(message, keyboard)
                message, keyboard = main_keyboard_admin()
        elif msg.text.startswith('⏫'):
            await Setup_list.waiting_for_list_name.set()
            message = "Введите /cancel или нажмите кнопку 'Отмена' чтобы выйти\n👉 Введите название нового списка:"
            keyboard = cancel_keyboard()
    else:
        message, keyboard = main_keyboard_user()
        if msg.text.startswith('🆕'):
            if not __init__.ListIdForTasksFromTG or not __init__.ImportantLabelId:
                message = "К сожалению администратор еще не полностью настроил меня, вы пока не можете создать задачу😔\nПопробуйте позже!!"
            else:
                await Task.waiting_for_task_name.set()
                await state.update_data(list_id=__init__.ListIdForTasksFromTG)
                message = "Введите название задачи\nотправьте команду /cancel или нажмите кнопку 'Отмена' чтобы отменить " \
                          "создание задачи"
                keyboard = cancel_keyboard()
        elif msg.text.startswith('🏃🏽‍♂'):
            if not __init__.ListIdForTasksFromTG or not __init__.ImportantLabelId:
                message = "К сожалению администратор еще не полностью настроил меня, вы пока не можете создать задачу😔\nПопробуйте позже!!"
            else:
                await QuickTask.waiting_for_task_name.set()
                await state.update_data(list_id=__init__.ListIdForTasksFromTG)
                message = "Введите название задачи\nотправьте команду /cancel или нажмите кнопку 'Отмена' чтобы отменить " \
                          "создание задачи"
                keyboard = cancel_keyboard()
        elif msg.text.startswith('🔞'):
            tasks = get_tasks_by_chat_id(str(msg.from_user.id))
            if not tasks:
                message = "Ваш список задач пуст 🥡"
                await msg.answer(message)
            else:
                for task in tasks:
                    task_tr = client.get_card(task[0])
                    list_tr = BOARD.get_list(task[1])
                    if task_tr.due:
                        deadline_date = datetime.strptime(task_tr.due, "%Y-%m-%dT%H:%M:%S.%fZ") + timedelta(hours=2)
                    else:
                        deadline_date = 'Нет'
                    message = f"🔥 НАЗВАНИЕ: {task_tr.name}\n🔥 ОПИСАНИЕ: {task_tr.desc}\n🔥 СОЗДАТЕЛЬ: @{task[4]}\n🔥 ДЕДЛАЙН: {deadline_date}\n" \
                              f"🔥 ДАТА СОЗДАНИЯ: {str(task[5])}"

                    if task[6]:
                        message += "\n 🔥 Вложения:"
                    keyboard = task_inline_keyboard(task[0])
                    if task[6]:
                        mesg = await msg.answer(message)
                        mesg = mesg.message_id
                        uid = task[6]
                        message += "\n 🔥 Вложения:"
                        fdir = BASE_PATH + f"files/{task[3]}/{uid}/"
                        if os.path.exists(fdir + "photo"):
                            photos = os.listdir(fdir + "photo")
                            media = types.MediaGroup()
                            for photo in photos:
                                media.attach_photo(types.InputFile(fdir + "photo/" + photo))
                            await bot.send_media_group(msg.from_user.id, media=media)
                        if os.path.exists(fdir + "document"):
                            docs = os.listdir(fdir + "document")
                            for doc in docs:
                                mesg = await bot.send_document(msg.from_user.id,
                                                               document=types.InputFile(fdir + "document/" + doc))
                                mesg = mesg.message_id
                        await bot.edit_message_reply_markup(msg.from_user.id, mesg, reply_markup=keyboard)
                    else:
                        await msg.answer(message, reply_markup=keyboard)
            return
    await msg.answer(message, reply_markup=keyboard)


@dp.callback_query_handler(lambda c: c.data and c.data.startswith('task_action'))
async def procces_task_action(callback_query: types.CallbackQuery, state: FSMContext):
    arr_action_task = callback_query.data.split('|')
    action = arr_action_task[0].split(':')[1]
    task_id = arr_action_task[1].split(':')[1]
    if action == 'edit':
        await TaskEdit.waiting_for_edited.set()
        await state.update_data(task_id=task_id)
        await callback_query.message.edit_reply_markup(reply_markup=None)
        task = client.get_card(task_id)
        message = f"Название: {task.name}\nОписание: {task.desc}"
        await callback_query.message.answer(message, reply_markup=cancel_keyboard())
        await callback_query.message.answer("👉 Введите новое описание задачи:")
    if action == 'add_comment':
        await AddComment.waiting_for_comment.set()
        keyboard = cancel_keyboard()
        message = "👉 Добавьте комментарий:"
        await state.update_data(task_id=task_id)
        await state.update_data(uid='')
        await callback_query.message.answer(message, reply_markup=keyboard)
    if action == 'close':
        await CloseTask.confirm_close.set()
        msg_id = callback_query.message.message_id
        await state.update_data(msg_id=msg_id)
        keyboard = types.ReplyKeyboardMarkup()
        keyboard.add('Да')
        keyboard.add('Нет')
        keyboard.add('Отмена')
        await state.update_data(task_id=task_id)
        message = '❕❕❕Вы дествительно хотите закрыть задачу?❕❕❕'
        await callback_query.message.answer(message, reply_markup=keyboard)
    if action == 'show_comments':
        await callback_query.message.reply("📄Комментарии к задаче:📄")
        comments = get_comments(task_id)
        for com in comments:
            message = f"🔥Автор: @{com[5]}\n🔥Комментарий: {com[2]}"
            if com[3]:
                fdir = BASE_PATH + f"files/{com[4]}/{com[3]}/"
                message += "\nВложения:"
                await callback_query.message.answer(message)
                if os.path.exists(fdir + "photo"):
                    photos = os.listdir(fdir + "photo")
                    media = types.MediaGroup()
                    for photo in photos:
                        media.attach_photo(types.InputFile(fdir + "photo/" + photo))
                    await bot.send_media_group(callback_query.from_user.id, media=media)
                if os.path.exists(fdir + "document"):
                    docs = os.listdir(fdir + "document")
                    for doc in docs:
                        await bot.send_document(callback_query.from_user.id,
                                                document=types.InputFile(fdir + "document/" + doc))
            else:
                await callback_query.message.answer(message)
    if action == 'move':
        keyboard = types.InlineKeyboardMarkup()
        lists = get_dashboards_lists()
        for dash_list in lists:
            keyboard.add(types.InlineKeyboardButton(dash_list[1], callback_data=f"li_id:{dash_list[0]}" \
                                                                                f"|t_id:{task_id}"))

        await callback_query.message.edit_reply_markup(reply_markup=keyboard)


@dp.callback_query_handler(lambda c: c.data and c.data.startswith('li_id'))
async def move_task(callback_query: types.CallbackQuery):
    list_task = callback_query.data.split('|')
    list_id = list_task[0].split(':')[1]
    task_id = list_task[1].split(':')[1]
    task_tr = client.get_card(task_id)
    task_tr.change_list(list_id)
    await update()
    await callback_query.message.edit_reply_markup(task_inline_keyboard(task_id, admin=True))
    moved_list_name = get_list(list_id)[1]
    await callback_query.message.answer(f"Задача перенесена в список '{moved_list_name}'")


@dp.message_handler(state=CloseTask.confirm_close, content_types=types.ContentTypes.TEXT)
async def close_task(msg: types.Message, state: FSMContext):
    if msg.text == 'Да':
        user_data = await state.get_data()
        task_id = user_data['task_id']
        workers_messages = list(get_workers_messages(task_id))
        task = get_task(task_id)
        if str(msg.from_user.id) in TG_WORKERS_CHAT_ID:
            if str(msg.from_user.id) != task[3]:
                await bot.forward_message(task[3], task[3], task[8])
                await bot.send_message(task[3], 'Задача закрыта!')
        else:
            for ch in TG_WORKERS_CHAT_ID:
                await bot.forward_message(ch, task[3], task[8])
                await bot.send_message(ch, 'Задача закрыта!')

        await msg.answer('Задача закрыта!')
        # delete messages
        for mesg in workers_messages:
            mesg_arr = str(mesg).split(':')
            chat = mesg_arr[0]
            mess = mesg_arr[1]
            await bot.delete_message(chat, int(mess))
        await bot.delete_message(task[3], int(task[8]))

        delete_task(task_id)
        task_tr = client.get_card(task_id)
        task_tr.set_closed(closed=True)
        await bot.delete_message(msg.from_user.id, user_data['msg_id'])
    await state.finish()
    if str(msg.from_user.id) in TG_WORKERS_CHAT_ID:
        message, keyboard = main_keyboard_admin()
    else:
        message, keyboard = main_keyboard_user()
    await msg.answer(message, reply_markup=keyboard)


@dp.message_handler(state=AddComment.waiting_for_comment, content_types=types.ContentTypes.TEXT)
async def procces_add_comment(msg: types.Message, state: FSMContext):
    comment = msg.text
    await state.update_data(comment=comment)
    message = "Добавить изображения или документы к коментарию?"
    keyboard = types.ReplyKeyboardMarkup()
    keyboard.row("🧩 Да", "📛 Нет")
    keyboard.add("Отмена")
    await AddComment.next()
    await msg.answer(message, reply_markup=keyboard)


@dp.message_handler(state=AddComment.add_files, content_types=types.ContentTypes.TEXT)
async def procces_add_comment_step_2(msg: types.Message, state: FSMContext):
    if msg.text.startswith('🧩'):
        await AddComment.next()
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        uid = str(uuid.uuid1())
        await state.update_data(uid=uid)
        kb = "🤲 Хватит добавлять, идем дальше!!"
        keyboard.add(kb)
        message = "Добавьте фото, группу фото или документ\nотправьте команду /cancel или нажмите кнопку 'Отмена' чтобы " \
                  "отменить создание задачи"
        cn = "Отмена"
        keyboard.add(cn)
        await state.update_data(docs={})
        await msg.answer(message, reply_markup=keyboard)
    elif msg.text.startswith('📛'):
        user_data = await state.get_data()
        await state.finish()
        task = client.get_card(user_data['task_id'])
        task.comment(comment_text=f"[{msg.from_user.username}]: " + user_data['comment'])
        message = "✅ Комментарий добавлен к задаче"
        await msg.answer(message)
        if str(msg.from_user.id) in TG_WORKERS_CHAT_ID:
            task_db = get_task(user_data['task_id'])
            await bot.forward_message(task_db[3], task_db[3], int(task_db[8]))
            message = f"❕❕❕ Задача прокомментирована\nАвтор комментария: @{msg.from_user.username}"
            await bot.send_message(task_db[3], message)
            await bot.send_message(task_db[3], f"Комментарий: '{user_data['comment']}'")
            for id in TG_WORKERS_CHAT_ID:
                if str(msg.from_user.id) != id:
                    await bot.forward_message(task_db[3], id, int(task_db[8]))
                    message = f"❕❕❕ Задача прокомментирована.\nАвтор комментария: @{msg.from_user.username}"
                    await bot.send_message(id, message)
                    await bot.send_message(id, f"Комментарий: '{user_data['comment']}'")
            message, keyboard = main_keyboard_admin()
        else:
            task_db = get_task(user_data['task_id'])
            for id in TG_WORKERS_CHAT_ID:
                await bot.forward_message(id, task_db[3], int(task_db[8]))
                message = f"❕❕❕ Задача прокомментирована\nАвтор комментария: @{msg.from_user.username}"
                await bot.send_message(id, message)
                await bot.send_message(id, f"Комментарий: '{user_data['comment']}'")
            message, keyboard = main_keyboard_user()
        insert_comment(user_data['task_id'], user_data['comment'], msg.from_user.id, msg.from_user.username)
        await msg.answer(message, reply_markup=keyboard)


@dp.message_handler(state=AddComment.waiting_for_files, content_types=types.ContentTypes.ANY)
async def procces_add_comment_step_3(msg: types.Message, state: FSMContext):
    user_data = await state.get_data()
    main_dir = BASE_PATH + "files/" + str(msg.from_user.id) + "/" + user_data['uid']
    if not os.path.exists(BASE_PATH + "files/" + str(msg.from_user.id)):
        os.mkdir(BASE_PATH + "files/" + str(msg.from_user.id))
    if not os.path.exists(main_dir):
        os.mkdir(main_dir)
    if msg.content_type == 'photo':
        photo = msg.photo.pop()
        if not os.path.exists(main_dir + "/photo"):
            os.mkdir(main_dir + "/photo")
        await photo.download(main_dir + "/photo/" + str(photo.file_id) + ".jpg")
    elif msg.content_type == 'document':
        if not os.path.exists(main_dir + "/document"):
            os.mkdir(main_dir + "/document")
        user_data = await state.get_data()
        user_data['docs'].update({str(msg.document.file_name): str(msg.document.mime_type)})
        await state.update_data(docs=user_data['docs'])
        await msg.document.download(main_dir + "/document/" + str(msg.document.file_name))
    elif msg.content_type == 'text' and msg.text.startswith("🤲"):
        list_of_photos = []
        list_of_documents = []
        task = client.get_card(user_data['task_id'])
        task.comment(comment_text=f"[{msg.from_user.username}]: " + user_data['comment'])

        message = "✅ Комментарий добавлен к задаче"
        await state.finish()
        await msg.answer(message)
        if str(msg.from_user.id) in TG_WORKERS_CHAT_ID:
            task_db = get_task(user_data['task_id'])
            if task_db[3] != str(msg.from_user.id):
                await bot.forward_message(task_db[3], task_db[3], int(task_db[8]))
                message = f"❕❕❕ Задача прокомментирована\nАвтор комментария: @{msg.from_user.username}"
                await bot.send_message(task_db[3], message)
                await bot.send_message(task_db[3], f"Комментарий: '{user_data['comment']}'")
                if user_data['uid'] != '':
                    await bot.send_message(task_db[3], "Вложения:")
                    photo_dir = BASE_PATH + 'files/' + str(msg.from_user.id) + '/' + user_data['uid'] + "/photo"
                    document_dir = BASE_PATH + 'files/' + str(msg.from_user.id) + '/' + user_data[
                        'uid'] + "/document"
                    if os.path.exists(photo_dir):
                        list_of_photos = os.listdir(photo_dir)
                        for file in list_of_photos:
                            task.attach(name=file, file=open(photo_dir + "/" + file, mode='rb'),
                                        mimeType='image/jpeg')
                        photos = os.listdir(photo_dir)
                        media = types.MediaGroup()
                        for photo in photos:
                            media.attach_photo(types.InputFile(photo_dir + "/" + photo))
                        await bot.send_media_group(task_db[3], media=media)

                    if os.path.exists(document_dir):
                        list_of_documents = os.listdir(document_dir)
                        for file in list_of_documents:
                            task.attach(name=file, file=open(document_dir + "/" + file, mode='rb'),
                                        mimeType=user_data['docs'][file])

                        docs = os.listdir(document_dir)
                        for doc in docs:
                            await bot.send_document(task_db[3],
                                                    document=types.InputFile(document_dir + "/" + doc))
            for id in TG_WORKERS_CHAT_ID:
                if str(msg.from_user.id) != id:
                    await bot.forward_message(task_db[3], id, int(task_db[8]))
                    message = f"❕❕❕ Задача прокомментирована.\nАвтор комментария: @{msg.from_user.username}"
                    await bot.send_message(id, message)
                    await bot.send_message(id, f"Комментарий: '{user_data['comment']}'")
                    if user_data['uid'] != '':
                        await bot.send_message(id, "Вложения:")
                        photo_dir = BASE_PATH + 'files/' + str(msg.from_user.id) + '/' + user_data['uid'] + "/photo"
                        document_dir = BASE_PATH + 'files/' + str(msg.from_user.id) + '/' + user_data[
                            'uid'] + "/document"
                        if os.path.exists(photo_dir):
                            list_of_photos = os.listdir(photo_dir)
                            for file in list_of_photos:
                                task.attach(name=file, file=open(photo_dir + "/" + file, mode='rb'),
                                            mimeType='image/jpeg')
                            photos = os.listdir(photo_dir)
                            media = types.MediaGroup()
                            for photo in photos:
                                media.attach_photo(types.InputFile(photo_dir + "/" + photo))
                            await bot.send_media_group(msg.from_user.id, media=media)

                        if os.path.exists(document_dir):
                            list_of_documents = os.listdir(document_dir)
                            for file in list_of_documents:
                                task.attach(name=file, file=open(document_dir + "/" + file, mode='rb'),
                                            mimeType=user_data['docs'][file])

                            docs = os.listdir(document_dir)
                            for doc in docs:
                                await bot.send_document(msg.from_user.id,
                                                        document=types.InputFile(document_dir + "/" + doc))
            message, keyboard = main_keyboard_admin()
        else:
            list_of_photos = []
            list_of_documents = []
            task_db = get_task(user_data['task_id'])
            for id in TG_WORKERS_CHAT_ID:
                await bot.forward_message(id, task_db[3], int(task_db[8]))
                message = f"❕❕❕ Задача прокомментирована\nАвтор комментария: @{msg.from_user.username}"
                await bot.send_message(id, message)
                await bot.send_message(id, f"Комментарий: '{user_data['comment']}'")
                if user_data['uid'] != '':
                    await bot.send_message(id, "Вложения:")
                    photo_dir = BASE_PATH + 'files/' + str(msg.from_user.id) + '/' + user_data['uid'] + "/photo"
                    document_dir = BASE_PATH + 'files/' + str(msg.from_user.id) + '/' + user_data['uid'] + "/document"
                    if os.path.exists(photo_dir):
                        list_of_photos = os.listdir(photo_dir)
                        for file in list_of_photos:
                            task.attach(name=file, file=open(photo_dir + "/" + file, mode='rb'), mimeType='image/jpeg')
                        photos = os.listdir(photo_dir)
                        media = types.MediaGroup()
                        for photo in photos:
                            media.attach_photo(types.InputFile(photo_dir + "/" + photo))
                        await bot.send_media_group(msg.from_user.id, media=media)

                    if os.path.exists(document_dir):
                        list_of_documents = os.listdir(document_dir)
                        for file in list_of_documents:
                            task.attach(name=file, file=open(document_dir + "/" + file, mode='rb'),
                                        mimeType=user_data['docs'][file])

                        docs = os.listdir(document_dir)
                        for doc in docs:
                            await bot.send_document(msg.from_user.id,
                                                    document=types.InputFile(document_dir + "/" + doc))
            message, keyboard = main_keyboard_user()
        insert_comment(user_data['task_id'], user_data['comment'], msg.from_user.id, msg.from_user.username,
                       files_uid=user_data['uid'])
        await msg.answer(message, reply_markup=keyboard)
    else:
        message = "Доступны лишь фото и документы"
        await msg.answer(message)
        return


@dp.message_handler(state=TaskEdit.waiting_for_edited, content_types=types.ContentTypes.TEXT)
async def procces_edit_task(msg: types.Message, state: FSMContext):
    user_data = await state.get_data()
    card = client.get_card(user_data['task_id'])
    card.set_description(msg.text)
    message = f"Описание задачи '{card.name}' успешно обновлено ✅"
    await msg.answer(message, reply_markup=None)
    await state.finish()
    if str(msg.from_user.id) in TG_WORKERS_CHAT_ID:
        message, keyboard = main_keyboard_admin()
    else:
        message, keyboard = main_keyboard_user()

    await msg.answer(message, reply_markup=keyboard)


if __name__ == '__main__':
    asyncio.gather(update_auto())
    executor.start_polling(dp)
