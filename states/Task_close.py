from aiogram.dispatcher.filters.state import State, StatesGroup


class CloseTask(StatesGroup):
    confirm_close = State()