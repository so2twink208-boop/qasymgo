# handlers/registration.py — Регистрация пользователей

import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext

from database.db import get_user, create_user, update_driver_info
from keyboards import role_keyboard, driver_menu, passenger_menu
from states import DriverRegStates
from config import ROLE_DRIVER, ROLE_PASSENGER, DRIVER_BONUS_BALANCE, ADMIN_IDS
from utils import safe_send

logger = logging.getLogger(__name__)
router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    user = await get_user(message.from_user.id)
    if user:
        if user["is_banned"]:
            await message.answer("🚫 Ваш аккаунт заблокирован.")
            return
        await _send_menu(message, user["role"])
        return
    await message.answer(
        "👋 Добро пожаловать в <b>QasymGo</b> — такси посёлка Касым Кайсенов!\n\nКто вы?",
        reply_markup=role_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("role:"))
async def choose_role(callback: CallbackQuery, state: FSMContext) -> None:
    role = callback.data.split(":")[1]
    existing = await get_user(callback.from_user.id)
    if existing:
        await callback.answer("Вы уже зарегистрированы.")
        await _send_menu(callback.message, existing["role"])
        return

    tg_user = callback.from_user
    name = tg_user.full_name or tg_user.username or str(tg_user.id)
    await create_user(telegram_id=tg_user.id, name=name, username=tg_user.username, role=role)

    if role == ROLE_DRIVER:
        await state.set_state(DriverRegStates.waiting_phone)
        await callback.message.edit_text(
            f"✅ Отлично! Вы регистрируетесь как <b>водитель</b>.\n\n"
            f"🎁 Бонус на баланс: <b>{DRIVER_BONUS_BALANCE} ₸</b>\n\n"
            f"📱 Введите ваш <b>номер телефона</b> (например: +77001234567):",
            parse_mode="HTML",
        )
    else:
        await callback.message.edit_text(
            "✅ Вы зарегистрированы как <b>пассажир</b>!\n\nПользование сервисом бесплатно.",
            parse_mode="HTML",
        )
        await _send_menu(callback.message, role)

    await callback.answer()
    logger.info("Новый пользователь: %s (роль: %s)", name, role)


@router.message(DriverRegStates.waiting_phone)
async def driver_phone(message: Message, state: FSMContext) -> None:
    phone = message.text.strip() if message.text else ""
    if len(phone) < 10:
        await message.answer("❗ Введите корректный номер телефона, например: +77001234567")
        return
    await state.update_data(phone=phone)
    await state.set_state(DriverRegStates.waiting_car)
    await message.answer(
        "🚗 Введите <b>марку и цвет автомобиля</b> (например: Toyota Camry, белый):",
        parse_mode="HTML",
    )


@router.message(DriverRegStates.waiting_car)
async def driver_car(message: Message, state: FSMContext, bot: Bot) -> None:
    car = message.text.strip() if message.text else ""
    if len(car) < 3:
        await message.answer("❗ Введите марку и цвет, например: Toyota Camry, белый")
        return

    data = await state.get_data()
    await state.clear()
    await update_driver_info(message.from_user.id, data["phone"], car)

    await message.answer(
        f"✅ <b>Регистрация завершена!</b>\n\n"
        f"📱 Телефон: {data['phone']}\n"
        f"🚗 Машина: {car}\n\n"
        f"Теперь вы можете принимать заказы!",
        parse_mode="HTML",
    )
    await _send_menu(message, ROLE_DRIVER)
    logger.info("Водитель завершил регистрацию: %s %s", data["phone"], car)

    # Уведомляем администраторов
    user = await get_user(message.from_user.id)
    for admin_id in ADMIN_IDS:
        await safe_send(
            bot, admin_id,
            f"🚕 <b>Новый водитель!</b>\n\n"
            f"👤 {user['name']}\n"
            f"📱 {data['phone']}\n"
            f"🚗 {car}\n"
            f"🆔 ID: {message.from_user.id}",
            parse_mode="HTML",
        )


async def _send_menu(message: Message, role: str) -> None:
    if role == ROLE_DRIVER:
        await message.answer("🚕 <b>Меню водителя</b>", reply_markup=driver_menu(), parse_mode="HTML")
    else:
        await message.answer("🧍 <b>Меню пассажира</b>", reply_markup=passenger_menu(), parse_mode="HTML")
