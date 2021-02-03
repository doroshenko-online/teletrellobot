from aiogram.dispatcher.filters.state import State, StatesGroup


class Task(StatesGroup):
    waiting_for_select_list = State()
    waiting_for_task_name = State()
    waiting_for_task_desc = State()
    need_files = State()
    waiting_for_files = State()
    waiting_for_task_label = State()
    waiting_for_deadline = State()
    waiting_for_date = State()
    waiting_for_time = State()