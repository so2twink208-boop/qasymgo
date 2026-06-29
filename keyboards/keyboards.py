# keyboards/keyboards.py — Все клавиатуры QasymGo (InlineKeyboard + ReplyKeyboard)

from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder


# ─── Подтверждение смены роли ─────────────────────────────────────────────────
def confirm_changerole_keyboard(new_role: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить", callback_data=f"changerole:{new_role}")
    builder.button(text="❌ Отмена",      callback_data="changerole:cancel")
    builder.adjust(2)
    return builder.as_markup()


# ─── Удалить клавиатуру ───────────────────────────────────────────────────────
def remove_keyboard() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()


# ─── Выбор роли ───────────────────────────────────────────────────────────────
def role_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🚕 Водитель",   callback_data="role:driver")
    builder.button(text="🧍 Пассажир",  callback_data="role:passenger")
    builder.adjust(2)
    return builder.as_markup()


# ─── Главное меню водителя ────────────────────────────────────────────────────
def driver_menu() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text="📋 Мой профиль")
    builder.button(text="💰 Баланс")
    builder.button(text="📜 История")
    builder.button(text="🚕 Активные заказы")
    builder.button(text="💳 Пополнить баланс")
    builder.button(text="✏️ Редактировать профиль")
    builder.button(text="🔄 Сменить роль")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)


# ─── Главное меню пассажира ───────────────────────────────────────────────────
def passenger_menu() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text="➕ Создать заказ")
    builder.button(text="📜 История поездок")
    builder.button(text="👤 Профиль")
    builder.button(text="🔄 Сменить роль")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)


# ─── Отмена активного заказа пассажиром ──────────────────────────────────────
def cancel_active_order_keyboard(order_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отменить заказ", callback_data=f"cancel_order:{order_id}")
    builder.adjust(1)
    return builder.as_markup()


# ─── Подтверждение заказа ─────────────────────────────────────────────────────
def confirm_order_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить", callback_data="order:confirm")
    builder.button(text="❌ Отмена",      callback_data="order:cancel")
    builder.adjust(2)
    return builder.as_markup()


# ─── Кнопки для водителей (принять / отказаться) ─────────────────────────────
def driver_order_keyboard(order_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Принять",    callback_data=f"driver_accept:{order_id}")
    builder.button(text="❌ Отказаться", callback_data=f"driver_decline:{order_id}")
    builder.adjust(2)
    return builder.as_markup()


# ─── Кнопка пассажира «Выбрать водителя» ─────────────────────────────────────
def select_driver_keyboard(order_id: int, driver_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="✅ Выбрать этого водителя",
        callback_data=f"select_driver:{order_id}:{driver_id}",
    )
    builder.adjust(1)
    return builder.as_markup()


# ─── Отмена активной поездки пассажиром ──────────────────────────────────────
def cancel_trip_passenger_keyboard(order_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🏁 Завершить поездку", callback_data=f"finish_trip:{order_id}")
    builder.button(text="❌ Отменить поездку",  callback_data=f"cancel_trip_passenger:{order_id}")
    builder.adjust(1)
    return builder.as_markup()


# ─── Отмена активной поездки водителем ───────────────────────────────────────
def cancel_trip_driver_keyboard(order_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отменить поездку", callback_data=f"cancel_trip_driver:{order_id}")
    builder.adjust(1)
    return builder.as_markup()


# ─── Завершить поездку ────────────────────────────────────────────────────────
def finish_trip_keyboard(order_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🏁 Завершить поездку", callback_data=f"finish_trip:{order_id}")
    builder.adjust(1)
    return builder.as_markup()


# ─── Оценка (звёзды) ──────────────────────────────────────────────────────────
def rating_keyboard(order_id: int, driver_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    stars = ["⭐", "⭐⭐", "⭐⭐⭐", "⭐⭐⭐⭐", "⭐⭐⭐⭐⭐"]
    for i, s in enumerate(stars, start=1):
        builder.button(text=s, callback_data=f"rate:{order_id}:{driver_id}:{i}")
    builder.adjust(5)
    return builder.as_markup()


# ─── Пропустить комментарий ───────────────────────────────────────────────────
def skip_comment_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="⏭ Пропустить", callback_data="review:skip_comment")
    builder.adjust(1)
    return builder.as_markup()
