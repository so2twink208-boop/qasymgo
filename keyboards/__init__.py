# keyboards/__init__.py
from .keyboards import (
    remove_keyboard, role_keyboard,
    driver_menu, passenger_menu,
    confirm_order_keyboard, driver_order_keyboard,
    select_driver_keyboard, finish_trip_keyboard,
    rating_keyboard, skip_comment_keyboard,
    cancel_active_order_keyboard,
    cancel_trip_passenger_keyboard, cancel_trip_driver_keyboard,
    confirm_changerole_keyboard,
)

__all__ = [
    "remove_keyboard", "role_keyboard",
    "driver_menu", "passenger_menu",
    "confirm_order_keyboard", "driver_order_keyboard",
    "select_driver_keyboard", "finish_trip_keyboard",
    "rating_keyboard", "skip_comment_keyboard",
    "cancel_active_order_keyboard",
    "cancel_trip_passenger_keyboard", "cancel_trip_driver_keyboard",
    "confirm_changerole_keyboard",
]
