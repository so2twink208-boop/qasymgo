# handlers/common.py — Общие обработчики (fallback, /help, проверка бана)

import logging
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command

from database.db import get_user
from keyboards import driver_menu, passenger_menu
from config import ROLE_DRIVER

logger = logging.getLogger(__name__)
router = Router()


# ─── /help ────────────────────────────────────────────────────────────────────
@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "ℹ️ <b>QasymGo — такси посёлка Касым Кайсенов</b>\n\n"
        "Используйте кнопки меню для навигации.\n\n"
        "<b>Пассажирам:</b> создавайте заказы, отслеживайте историю.\n"
        "<b>Водителям:</b> принимайте заказы, следите за балансом.\n\n"
        "По вопросам обратитесь к администратору.",
        parse_mode="HTML",
    )


# ─── /menu — показать меню вручную ───────────────────────────────────────────
@router.message(Command("menu"))
async def cmd_menu(message: Message) -> None:
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Сначала запустите бота командой /start")
        return
    if user["is_banned"]:
        await message.answer("🚫 Ваш аккаунт заблокирован.")
        return
    if user["role"] == ROLE_DRIVER:
        await message.answer("🚕 Меню водителя:", reply_markup=driver_menu())
    else:
        await message.answer("🧍 Меню пассажира:", reply_markup=passenger_menu())


# ─── Fallback: любое нераспознанное сообщение ─────────────────────────────────
@router.message()
async def fallback(message: Message) -> None:
    user = await get_user(message.from_user.id)
    if user and user["is_banned"]:
        await message.answer("🚫 Ваш аккаунт заблокирован.")
        return
    if not user:
        await message.answer("👋 Введите /start для начала работы.")
        return
    # Пользователь зарегистрирован — напомним про меню
    await message.answer(
        "❓ Не понял команду. Используйте кнопки меню или /menu для его отображения."
    )
