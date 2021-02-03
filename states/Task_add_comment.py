from aiogram.dispatcher.filters.state import State, StatesGroup


class AddComment(StatesGroup):
    waiting_for_comment = State()
    add_files = State()
    waiting_for_files = State()