# handlers/passenger.py — Весь функционал пассажира

import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database.db import (
    get_user, create_order, get_passenger_orders, cancel_order,
    get_all_drivers, get_order,
)
from keyboards import (
    confirm_order_keyboard, passenger_menu, driver_order_keyboard,
    cancel_active_order_keyboard,
)
from utils.middleware import MENU_BUTTONS
from states import OrderStates
from utils import format_order, safe_send, stars
from config import COMMISSION_RATE

logger = logging.getLogger(__name__)
router = Router()


# ─── Профиль пассажира ────────────────────────────────────────────────────────
@router.message(F.text == "👤 Профиль")
async def passenger_profile(message: Message) -> None:
    user = await get_user(message.from_user.id)
    if not user:
        return
    await message.answer(
        f"👤 <b>Профиль</b>\n\n"
        f"🔖 Имя: {user['name']}\n"
        f"⭐ Рейтинг: {user['rating']} {stars(user['rating'])}\n"
        f"📅 Дата регистрации: {user['created_at'][:10]}",
        parse_mode="HTML",
    )


# ─── История поездок пассажира ────────────────────────────────────────────────
@router.message(F.text == "📜 История поездок")
async def passenger_history(message: Message) -> None:
    user = await get_user(message.from_user.id)
    if not user:
        return
    orders = await get_passenger_orders(user["id"])
    if not orders:
        await message.answer("📭 У вас ещё нет поездок.")
        return
    text = "📜 <b>Ваши поездки:</b>\n\n" + "\n\n".join(format_order(o) for o in orders)
    await message.answer(text, parse_mode="HTML")


# ─── Создание заказа: Шаг 1 ───────────────────────────────────────────────────
@router.message(F.text == "➕ Создать заказ")
async def order_start(message: Message, state: FSMContext) -> None:
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Сначала запустите бота командой /start")
        return

    # Проверка долга
    if user.get("debt", 0) > 0:
        await message.answer(
            f"❌ У вас есть неоплаченный долг: <b>{user['debt']} ₸</b>\n\n"
            f"Создание заказов заблокировано до погашения долга.\n"
            f"Обратитесь к администратору @Daniyar21_06",
            parse_mode="HTML",
        )
        return

    await state.set_state(OrderStates.waiting_from)
    await message.answer(
        "📍 <b>Шаг 1 из 4</b>\n\nВведите адрес <b>отправления</b>:",
        parse_mode="HTML",
    )


# ─── Шаг 2: Адрес назначения ──────────────────────────────────────────────────
@router.message(OrderStates.waiting_from)
async def order_from(message: Message, state: FSMContext) -> None:
    if message.text in MENU_BUTTONS:
        return
    if not message.text or len(message.text.strip()) < 3:
        await message.answer("❗ Пожалуйста, введите корректный адрес.")
        return
    await state.update_data(from_address=message.text.strip())
    await state.set_state(OrderStates.waiting_to)
    await message.answer(
        "📍 <b>Шаг 2 из 4</b>\n\nВведите адрес <b>назначения</b>:",
        parse_mode="HTML",
    )


# ─── Шаг 3: Стоимость ─────────────────────────────────────────────────────────
@router.message(OrderStates.waiting_to)
async def order_to(message: Message, state: FSMContext) -> None:
    if message.text in MENU_BUTTONS:
        return
    if not message.text or len(message.text.strip()) < 3:
        await message.answer("❗ Пожалуйста, введите корректный адрес.")
        return
    await state.update_data(to_address=message.text.strip())
    await state.set_state(OrderStates.waiting_price)
    await message.answer(
        "💰 <b>Шаг 3 из 4</b>\n\nВведите <b>стоимость поездки</b> (тенге):",
        parse_mode="HTML",
    )


# ─── Шаг 4: Подтверждение ─────────────────────────────────────────────────────
@router.message(OrderStates.waiting_price)
async def order_price(message: Message, state: FSMContext) -> None:
    if message.text in MENU_BUTTONS:
        return
    # Валидация суммы
    try:
        price = float(message.text.replace(",", ".").strip())
        if price <= 0:
            raise ValueError
    except (ValueError, AttributeError):
        await message.answer("❗ Введите корректную сумму, например: 500")
        return

    await state.update_data(price=price)
    data = await state.get_data()
    await state.set_state(OrderStates.confirming)

    await message.answer(
        f"📋 <b>Шаг 4 из 4 — Подтверждение заказа</b>\n\n"
        f"📍 Откуда: {data['from_address']}\n"
        f"📍 Куда:   {data['to_address']}\n"
        f"💰 Цена:   {price} ₸\n\n"
        f"Всё верно?",
        reply_markup=confirm_order_keyboard(),
        parse_mode="HTML",
    )


# ─── Подтверждение: принять ───────────────────────────────────────────────────
@router.callback_query(OrderStates.confirming, F.data == "order:confirm")
async def order_confirm(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()
    await state.clear()

    passenger = await get_user(callback.from_user.id)

    # Создаём заказ в БД
    order_id = await create_order(
        passenger_id=passenger["id"],
        from_addr=data["from_address"],
        to_addr=data["to_address"],
        price=data["price"],
    )

    await callback.message.edit_text(
        f"✅ Заказ #{order_id} создан!\nИщем водителя...\n\n"
        f"Если хотите отменить — нажмите кнопку ниже.",
        reply_markup=cancel_active_order_keyboard(order_id),
        parse_mode="HTML",
    )
    await callback.answer()

    # Уведомляем администраторов о новом заказе
    from config import ADMIN_IDS
    for admin_id in ADMIN_IDS:
        await safe_send(
            bot,
            admin_id,
            f"📦 <b>Новый заказ #{order_id}</b>\n\n"
            f"👤 Пассажир: {passenger['name']}\n"
            f"📍 Откуда: {data['from_address']}\n"
            f"📍 Куда:   {data['to_address']}\n"
            f"💰 Цена:   {data['price']} ₸",
            parse_mode="HTML",
        )

    # Рассылка всем водителям
    drivers = await get_all_drivers()
    if not drivers:
        await callback.message.answer("😔 Водителей пока нет. Попробуйте позже.")
        await cancel_order(order_id)
        return

    broadcast_text = (
        f"🚕 <b>Новый заказ #{order_id}</b>\n\n"
        f"📍 Откуда: {data['from_address']}\n"
        f"📍 Куда:   {data['to_address']}\n"
        f"💰 Цена:   {data['price']} ₸"
    )

    sent = 0
    for driver in drivers:
        ok = await safe_send(
            bot,
            driver["telegram_id"],
            broadcast_text,
            reply_markup=driver_order_keyboard(order_id),
            parse_mode="HTML",
        )
        if ok:
            sent += 1

    logger.info("Заказ #%s разослан %d водителям.", order_id, sent)

    if sent == 0:
        await callback.message.answer(
            "😔 Не удалось связаться с водителями. Попробуйте позже."
        )
        await cancel_order(order_id)


# ─── Отмена активного заказа пассажиром ──────────────────────────────────────
@router.callback_query(F.data.startswith("cancel_order:"))
async def cancel_active_order(callback: CallbackQuery) -> None:
    order_id = int(callback.data.split(":")[1])
    order = await get_order(order_id)

    if not order:
        await callback.answer("❌ Заказ не найден.", show_alert=True)
        return

    if order["status"] != "pending":
        await callback.answer("⚠️ Заказ уже принят, отменить нельзя.", show_alert=True)
        return

    await cancel_order(order_id)
    await callback.message.edit_text(f"❌ Заказ #{order_id} отменён.")
    await callback.answer()
    await callback.message.answer("Меню:", reply_markup=passenger_menu())


# ─── Пополнение баланса (инструкция Kaspi) ───────────────────────────────────
@router.message(F.text == "💳 Пополнить баланс")
async def kaspi_info(message: Message) -> None:
    await message.answer(
        "💳 <b>Пополнение баланса через Kaspi</b>\n\n"
        "Переведите нужную сумму по номеру:\n"
        "<b>4400430335989056</b> (QasymGo)\n\n"
        "После перевода отправьте скриншот чека администратору:\n"
        "@Daniyar21_06\n\n"
        "⏱ Баланс пополняется в течение 30 минут.",
        parse_mode="HTML",
    )
@router.callback_query(OrderStates.confirming, F.data == "order:cancel")
async def order_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("❌ Заказ отменён.")
    await callback.answer()
    await callback.message.answer("Меню:", reply_markup=passenger_menu())
