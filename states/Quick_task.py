from aiogram.dispatcher.filters.state import State, StatesGroup


class QuickTask(StatesGroup):
    waiting_for_task_name = State()
    waiting_for_task_label = State()