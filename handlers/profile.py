# handlers/profile.py — Редактирование профиля и смена роли

import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database.db import get_user, update_driver_info, change_role
from keyboards import driver_menu, passenger_menu, confirm_changerole_keyboard
from states import EditProfileStates
from config import ROLE_DRIVER, ROLE_PASSENGER
from utils.middleware import MENU_BUTTONS

logger = logging.getLogger(__name__)
router = Router()


# ─── Редактировать профиль ────────────────────────────────────────────────────
@router.message(F.text == "✏️ Редактировать профиль")
async def edit_profile_start(message: Message, state: FSMContext) -> None:
    user = await get_user(message.from_user.id)
    if not user or user["role"] != ROLE_DRIVER:
        return
    await state.set_state(EditProfileStates.waiting_phone)
    await message.answer(
        f"✏️ <b>Редактирование профиля</b>\n\n"
        f"Текущий телефон: {user.get('phone') or '—'}\n\n"
        f"📱 Введите новый номер телефона:",
        parse_mode="HTML",
    )


@router.message(EditProfileStates.waiting_phone)
async def edit_profile_phone(message: Message, state: FSMContext) -> None:
    if message.text in MENU_BUTTONS:
        await state.clear()
        return
    phone = message.text.strip() if message.text else ""
    if len(phone) < 10:
        await message.answer("❗ Введите корректный номер, например: +77001234567")
        return
    await state.update_data(phone=phone)
    await state.set_state(EditProfileStates.waiting_car)
    user = await get_user(message.from_user.id)
    await message.answer(
        f"🚗 Текущая машина: {user.get('car_info') or '—'}\n\n"
        f"Введите новую марку и цвет:",
        parse_mode="HTML",
    )


@router.message(EditProfileStates.waiting_car)
async def edit_profile_car(message: Message, state: FSMContext) -> None:
    if message.text in MENU_BUTTONS:
        await state.clear()
        return
    car = message.text.strip() if message.text else ""
    if len(car) < 3:
        await message.answer("❗ Введите марку и цвет, например: Toyota Camry, белый")
        return
    data = await state.get_data()
    await state.clear()
    await update_driver_info(message.from_user.id, data["phone"], car)
    await message.answer(
        f"✅ <b>Профиль обновлён!</b>\n\n"
        f"📱 Телефон: {data['phone']}\n"
        f"🚗 Машина: {car}",
        parse_mode="HTML",
        reply_markup=driver_menu(),
    )
    logger.info("Водитель %s обновил профиль", message.from_user.id)


# ─── Сменить роль ─────────────────────────────────────────────────────────────
@router.message(F.text == "🔄 Сменить роль")
async def changerole_start(message: Message, state: FSMContext) -> None:
    user = await get_user(message.from_user.id)
    if not user:
        return

    if user["role"] == ROLE_DRIVER:
        new_role = ROLE_PASSENGER
        role_text = "пассажира 🧍"
    else:
        new_role = ROLE_DRIVER
        role_text = "водителя 🚕"

    await message.answer(
        f"🔄 Вы хотите сменить роль на <b>{role_text}</b>?\n\n"
        f"⚠️ Ваш баланс и история сохранятся.",
        reply_markup=confirm_changerole_keyboard(new_role),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("changerole:"))
async def changerole_confirm(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    new_role = callback.data.split(":")[1]

    if new_role == "cancel":
        await callback.message.edit_text("❌ Смена роли отменена.")
        await callback.answer()
        user = await get_user(callback.from_user.id)
        if user["role"] == ROLE_DRIVER:
            await callback.message.answer("Меню:", reply_markup=driver_menu())
        else:
            await callback.message.answer("Меню:", reply_markup=passenger_menu())
        return

    await change_role(callback.from_user.id, new_role)

    if new_role == ROLE_DRIVER:
        user = await get_user(callback.from_user.id)
        await callback.message.edit_text(
            "✅ Вы теперь <b>водитель</b>!\n\n"
            "Заполните профиль через кнопку ✏️ Редактировать профиль",
            parse_mode="HTML",
        )
        await callback.message.answer("🚕 Меню водителя:", reply_markup=driver_menu())
    else:
        await callback.message.edit_text(
            "✅ Вы теперь <b>пассажир</b>!",
            parse_mode="HTML",
        )
        await callback.message.answer("🧍 Меню пассажира:", reply_markup=passenger_menu())

    await callback.answer()
    logger.info("Пользователь %s сменил роль на %s", callback.from_user.id, new_role)
