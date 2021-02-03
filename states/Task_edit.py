from aiogram.dispatcher.filters.state import State, StatesGroup


class TaskEdit(StatesGroup):
    waiting_for_edited = State()