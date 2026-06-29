# handlers/reviews.py — Система отзывов (пассажир оценивает водителя)

import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from database.db import add_review
from keyboards import skip_comment_keyboard, passenger_menu
from states import ReviewStates

logger = logging.getLogger(__name__)
router = Router()


# ─── Пассажир выбрал звёзды ───────────────────────────────────────────────────
@router.callback_query(F.data.startswith("rate:"))
async def handle_rating(callback: CallbackQuery, state: FSMContext) -> None:
    # Формат: rate:{order_id}:{driver_id}:{stars}
    parts    = callback.data.split(":")
    order_id  = int(parts[1])
    driver_id = int(parts[2])
    rating    = int(parts[3])

    # Сохраняем в FSM для последующего комментария
    await state.update_data(
        order_id=order_id,
        driver_id=driver_id,
        rating=rating,
    )
    await state.set_state(ReviewStates.waiting_comment)

    stars_str = "⭐" * rating
    await callback.message.edit_text(
        f"Оценка: {stars_str}\n\nОставьте комментарий о поездке (или пропустите):",
        reply_markup=skip_comment_keyboard(),
    )
    await callback.answer()


# ─── Комментарий введён ───────────────────────────────────────────────────────
@router.message(ReviewStates.waiting_comment)
async def handle_comment(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await state.clear()

    from database.db import get_user
    passenger = await get_user(message.from_user.id)

    await add_review(
        driver_id=data["driver_id"],
        passenger_id=passenger["id"],
        order_id=data["order_id"],
        rating=data["rating"],
        comment=message.text.strip() if message.text else None,
    )

    await message.answer(
        "✅ Спасибо за отзыв! Ваша оценка учтена.",
        reply_markup=passenger_menu(),
    )
    logger.info(
        "Отзыв от пассажира %s: %d ⭐ для водителя #%s",
        passenger["name"], data["rating"], data["driver_id"],
    )


# ─── Пропустить комментарий ───────────────────────────────────────────────────
@router.callback_query(F.data == "review:skip_comment")
async def skip_comment(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    await state.clear()

    from database.db import get_user
    passenger = await get_user(callback.from_user.id)

    await add_review(
        driver_id=data["driver_id"],
        passenger_id=passenger["id"],
        order_id=data["order_id"],
        rating=data["rating"],
        comment=None,
    )

    await callback.message.edit_text("✅ Спасибо за оценку!")
    await callback.answer()
    await callback.message.answer("Меню:", reply_markup=passenger_menu())
