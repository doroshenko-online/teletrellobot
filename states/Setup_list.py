from aiogram.dispatcher.filters.state import State, StatesGroup


class Setup_list(StatesGroup):
    waiting_for_list_name = State()
    waiting_for_list_default = State()
