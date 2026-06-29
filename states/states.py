# states/states.py — Состояния FSM для aiogram 3.x

from aiogram.fsm.state import State, StatesGroup


class RegistrationStates(StatesGroup):
    choosing_role = State()


class DriverRegStates(StatesGroup):
    """Регистрация водителя."""
    waiting_phone = State()
    waiting_car   = State()


class EditProfileStates(StatesGroup):
    """Редактирование профиля водителя."""
    waiting_phone = State()
    waiting_car   = State()


class OrderStates(StatesGroup):
    """Создание заказа пассажиром."""
    waiting_from  = State()
    waiting_to    = State()
    waiting_price = State()
    confirming    = State()


class ReviewStates(StatesGroup):
    """Отзыв после поездки."""
    waiting_rating  = State()
    waiting_comment = State()


class AdminStates(StatesGroup):
    """Состояния для админ-команд."""
    waiting_broadcast = State()
