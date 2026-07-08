# handlers/driver.py — Весь функционал водителя

import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery

from database.db import (
    get_user, get_order, set_order_driver, update_balance,
    get_driver_orders, get_pending_orders,
    has_applied, add_application, clear_applications,
    add_warning, add_driver_cancel, cancel_order,
)
from keyboards import (
    driver_menu, select_driver_keyboard, finish_trip_keyboard,
    cancel_trip_passenger_keyboard, cancel_trip_driver_keyboard,
)
from utils import format_order, safe_send, stars
from config import COMMISSION_RATE, ROLE_DRIVER

logger = logging.getLogger(__name__)
router = Router()


# ─── Пополнение баланса (инструкция Kaspi) для водителя ──────────────────────
@router.message(F.text == "💳 Пополнить баланс")
async def driver_kaspi(message: Message) -> None:
    await message.answer(
        "💳 <b>Пополнение баланса через Kaspi</b>\n\n"
        "Переведите нужную сумму по номеру:\n"
        "<b>4400 4303 3598 9056</b> (QasymGo)\n\n"
        "После перевода отправьте скриншот чека администратору:\n"
        "@Daniyar21_06\n\n"
        "⏱ Баланс пополняется в течение 30 минут.",
        parse_mode="HTML",
    )


# ─── Профиль водителя ─────────────────────────────────────────────────────────
@router.message(F.text == "📋 Мой профиль")
async def driver_profile(message: Message) -> None:
    user = await get_user(message.from_user.id)
    if not user or user["role"] != ROLE_DRIVER:
        return
    phone_str = user.get("phone") or "не указан"
    car_str   = user.get("car_info") or "не указана"
    await message.answer(
        f"📋 <b>Профиль водителя</b>\n\n"
        f"👤 Имя: {user['name']}\n"
        f"📱 Телефон: {phone_str}\n"
        f"🚗 Машина: {car_str}\n"
        f"⭐ Рейтинг: {user['rating']} {stars(user['rating'])}\n"
        f"💰 Баланс: {user['balance']} ₸\n"
        f"📅 Дата регистрации: {user['created_at'][:10]}",
        parse_mode="HTML",
    )


# ─── Баланс ───────────────────────────────────────────────────────────────────
@router.message(F.text == "💰 Баланс")
async def driver_balance(message: Message) -> None:
    user = await get_user(message.from_user.id)
    if not user or user["role"] != ROLE_DRIVER:
        return
    await message.answer(
        f"💰 <b>Ваш баланс:</b> {user['balance']} ₸\n\n"
        f"ℹ️ Комиссия сервиса: <b>5%</b> от стоимости заказа.\n"
        f"Пополнение баланса — через администратора.",
        parse_mode="HTML",
    )


# ─── История поездок водителя ─────────────────────────────────────────────────
@router.message(F.text == "📜 История")
async def driver_history(message: Message) -> None:
    user = await get_user(message.from_user.id)
    if not user or user["role"] != ROLE_DRIVER:
        return
    orders = await get_driver_orders(user["id"])
    if not orders:
        await message.answer("📭 У вас ещё нет завершённых поездок.")
        return
    text = "📜 <b>История поездок:</b>\n\n" + "\n\n".join(format_order(o) for o in orders)
    await message.answer(text, parse_mode="HTML")


# ─── Активные заказы (доступные для принятия) ────────────────────────────────
@router.message(F.text == "🚕 Активные заказы")
async def active_orders(message: Message) -> None:
    user = await get_user(message.from_user.id)
    if not user or user["role"] != ROLE_DRIVER:
        return
    orders = await get_pending_orders()
    if not orders:
        await message.answer("📭 Активных заказов нет.")
        return
    for order in orders[:5]:  # показываем максимум 5
        from keyboards import driver_order_keyboard
        await message.answer(
            f"🚕 <b>Заказ #{order['id']}</b>\n\n"
            f"📍 Откуда: {order['from_address']}\n"
            f"📍 Куда:   {order['to_address']}\n"
            f"💰 Цена:   {order['price']} ₸",
            reply_markup=driver_order_keyboard(order["id"]),
            parse_mode="HTML",
        )


# ─── Водитель нажал «Принять» ─────────────────────────────────────────────────
@router.callback_query(F.data.startswith("driver_accept:"))
async def driver_accept(callback: CallbackQuery, bot: Bot) -> None:
    order_id = int(callback.data.split(":")[1])

    driver = await get_user(callback.from_user.id)
    order  = await get_order(order_id)

    # Проверки
    if not driver or driver["role"] != ROLE_DRIVER:
        await callback.answer("Вы не являетесь водителем.", show_alert=True)
        return

    if not order:
        await callback.answer("❌ Заказ не найден.", show_alert=True)
        return

    if order["status"] != "pending":
        await callback.answer("⚠️ Заказ уже принят или отменён.", show_alert=True)
        return

    # Защита от двойной заявки
    if await has_applied(order_id, driver["id"]):
        await callback.answer("⚠️ Вы уже подали заявку на этот заказ.", show_alert=True)
        return

    # Проверка баланса
    commission = round(order["price"] * COMMISSION_RATE, 2)
    if driver["balance"] < commission:
        await callback.answer(
            f"❌ Недостаточно средств!\n"
            f"Комиссия: {commission} ₸\n"
            f"Ваш баланс: {driver['balance']} ₸\n\n"
            f"Пополните баланс у администратора.",
            show_alert=True,
        )
        return

    # Всё ок — отправляем карточку водителя пассажиру
    from database.db import get_user_by_id
    passenger = await get_user_by_id(order["passenger_id"])

    await safe_send(
        bot,
        passenger["telegram_id"],
        f"🚕 <b>Водитель найден!</b>\n\n"
        f"👤 Имя: {driver['name']}\n"
        f"⭐ Рейтинг: {driver['rating']} {stars(driver['rating'])}\n"
        f"💰 Баланс: {driver['balance']} ₸",
        reply_markup=select_driver_keyboard(order_id, driver["id"]),
        parse_mode="HTML",
    )

    await callback.message.edit_text(
        f"⏳ Ваша заявка на заказ #{order_id} отправлена пассажиру.\n"
        f"Ждите подтверждения..."
    )
    await callback.answer("✅ Заявка отправлена пассажиру!")

    # Записываем заявку — водитель не сможет подать повторно
    await add_application(order_id, driver["id"])
    logger.info("Водитель %s принял заказ #%s", driver["name"], order_id)


# ─── Водитель нажал «Отказаться» ─────────────────────────────────────────────
@router.callback_query(F.data.startswith("driver_decline:"))
async def driver_decline(callback: CallbackQuery) -> None:
    order_id = int(callback.data.split(":")[1])
    await callback.message.edit_text(f"❌ Вы отказались от заказа #{order_id}.")
    await callback.answer()


# ─── Пассажир нажал «Выбрать водителя» ───────────────────────────────────────
@router.callback_query(F.data.startswith("select_driver:"))
async def select_driver(callback: CallbackQuery, bot: Bot) -> None:
    _, order_id_str, driver_id_str = callback.data.split(":")
    order_id  = int(order_id_str)
    driver_id = int(driver_id_str)

    order  = await get_order(order_id)
    driver = await get_user_by_id_local(driver_id)

    if not order or order["status"] != "pending":
        await callback.answer("⚠️ Заказ уже недоступен.", show_alert=True)
        return

    # Списываем комиссию с водителя
    commission = round(order["price"] * COMMISSION_RATE, 2)
    new_balance = await update_balance(driver_id, -commission)

    # Обновляем заказ
    await set_order_driver(order_id, driver_id)

    from database.db import get_user_by_id
    passenger = await get_user_by_id(order["passenger_id"])

    # Пассажиру — контакт водителя + кнопки завершения/отмены
    driver_tg = f"@{driver['username']}" if driver.get("username") else "—"
    phone_str = driver.get("phone") or "не указан"
    car_str   = driver.get("car_info") or "не указана"
    await callback.message.edit_text(
        f"✅ <b>Водитель выбран!</b>\n\n"
        f"👤 Имя: {driver['name']}\n"
        f"📱 Телефон: {phone_str}\n"
        f"🚗 Машина: {car_str}\n"
        f"💬 Telegram: {driver_tg}\n\n"
        f"Хорошей поездки! 🚗",
        reply_markup=cancel_trip_passenger_keyboard(order_id),
        parse_mode="HTML",
    )

    # Водителю — контакт пассажира + кнопка отмены
    passenger_tg = f"@{passenger['username']}" if passenger.get("username") else passenger["name"]
    await safe_send(
        bot,
        driver["telegram_id"],
        f"✅ <b>Пассажир выбрал вас!</b>\n\n"
        f"📍 Откуда: {order['from_address']}\n"
        f"📍 Куда:   {order['to_address']}\n"
        f"💰 Цена:   {order['price']} ₸\n"
        f"👤 Пассажир: {passenger_tg}\n\n"
        f"💸 Комиссия {commission} ₸ списана.\n"
        f"Остаток баланса: {new_balance} ₸",
        reply_markup=cancel_trip_driver_keyboard(order_id),
        parse_mode="HTML",
    )

    await callback.answer()
    # Очищаем все заявки на этот заказ
    await clear_applications(order_id)
    logger.info(
        "Пассажир выбрал водителя #%s для заказа #%s. Комиссия: %s ₸",
        driver_id, order_id, commission,
    )


# ─── Пассажир завершил поездку ────────────────────────────────────────────────
@router.callback_query(F.data.startswith("finish_trip:"))
async def finish_trip(callback: CallbackQuery, bot: Bot) -> None:
    from database.db import complete_order, get_user_by_id
    from keyboards import rating_keyboard

    order_id = int(callback.data.split(":")[1])
    order = await complete_order(order_id)

    if not order or not order["selected_driver"]:
        await callback.answer("❌ Ошибка.", show_alert=True)
        return

    driver = await get_user_by_id(order["selected_driver"])

    # Уведомляем водителя
    await safe_send(
        bot,
        driver["telegram_id"],
        f"🏁 Поездка #{order_id} завершена!\nСпасибо за работу. 🙌",
    )

    # Просим оценку от пассажира
    await callback.message.edit_text(
        f"🏁 Поездка завершена!\n\nПожалуйста, оцените водителя <b>{driver['name']}</b>:",
        reply_markup=rating_keyboard(order_id, driver["id"]),
        parse_mode="HTML",
    )
    await callback.answer()


# ─── Пассажир отменяет поездку после выбора водителя ─────────────────────────
@router.callback_query(F.data.startswith("cancel_trip_passenger:"))
async def cancel_trip_passenger(callback: CallbackQuery, bot: Bot) -> None:
    from database.db import get_user_by_id
    from keyboards import passenger_menu

    order_id = int(callback.data.split(":")[1])
    order = await get_order(order_id)

    if not order or order["status"] != "active":
        await callback.answer("⚠️ Поездка уже завершена или отменена.", show_alert=True)
        return

    await cancel_order(order_id)

    # Возвращаем комиссию водителю
    if order["selected_driver"]:
        commission = round(order["price"] * COMMISSION_RATE, 2)
        await update_balance(order["selected_driver"], commission)

    # Предупреждение
    updated = await add_warning(callback.from_user.id)
    warnings = updated["warnings"]
    debt = updated["debt"]

    # warnings сбросился до 0 значит только что получил штраф
    if debt > 0 and warnings == 0:
        await callback.message.edit_text(
            f"❌ Поездка отменена.\n\n"
            f"⚠️ Вы получили 5 предупреждений.\n"
            f"💸 Штраф: <b>100 ₸</b>\n\n"
            f"Создание заказов заблокировано до оплаты.\n"
            f"Обратитесь к @Daniyar21_06",
            parse_mode="HTML",
        )
    else:
        await callback.message.edit_text(
            f"❌ Поездка отменена.\n\n"
            f"⚠️ Предупреждение {warnings}/5\n"
            f"При 5 предупреждениях — штраф 100 ₸.",
            parse_mode="HTML",
        )
    await callback.answer()

    # Уведомляем водителя
    if order["selected_driver"]:
        commission = round(order["price"] * COMMISSION_RATE, 2)
        driver = await get_user_by_id_local(order["selected_driver"])
        if driver:
            await safe_send(
                bot, driver["telegram_id"],
                f"❌ Пассажир отменил поездку #{order_id}.\n"
                f"💸 Комиссия {commission} ₸ возвращена на ваш баланс.\n"
                f"Пассажир получил предупреждение.",
            )


# ─── Водитель отменяет поездку после принятия ─────────────────────────────────
@router.callback_query(F.data.startswith("cancel_trip_driver:"))
async def cancel_trip_driver(callback: CallbackQuery, bot: Bot) -> None:
    from database.db import get_user_by_id, ban_user

    order_id = int(callback.data.split(":")[1])
    order = await get_order(order_id)
    driver = await get_user(callback.from_user.id)

    if not order or order["status"] != "active":
        await callback.answer("⚠️ Поездка уже завершена или отменена.", show_alert=True)
        return

    # Возвращаем комиссию и списываем штраф 50 ₸
    commission = round(order["price"] * COMMISSION_RATE, 2)
    await update_balance(driver["id"], commission)
    new_balance = await update_balance(driver["id"], -50)

    cancel_count = await add_driver_cancel(callback.from_user.id)
    await cancel_order(order_id)

    if cancel_count >= 3:
        await ban_user(callback.from_user.id)
        await callback.message.edit_text(
            f"❌ Поездка отменена.\n\n"
            f"💸 Комиссия возвращена, штраф 50 ₸ списан.\n"
            f"🚫 3 отмены — <b>аккаунт заблокирован</b>.\n"
            f"Обратитесь к @Daniyar21_06",
            parse_mode="HTML",
        )
    else:
        await callback.message.edit_text(
            f"❌ Поездка #{order_id} отменена.\n\n"
            f"💸 Комиссия возвращена, штраф 50 ₸ списан.\n"
            f"💰 Баланс: {new_balance} ₸\n"
            f"⚠️ Отмен: {cancel_count}/3",
            parse_mode="HTML",
        )
    await callback.answer()

    # Уведомляем пассажира
    passenger = await get_user_by_id_local(order["passenger_id"])
    if passenger:
        await safe_send(
            bot, passenger["telegram_id"],
            f"❌ Водитель отменил поездку #{order_id}.\n"
            f"Создайте новый заказ.",
        )


# ─── Вспомогательный импорт (чтобы не было цикла) ────────────────────────────
async def get_user_by_id_local(user_id: int):
    from database.db import get_user_by_id
    return await get_user_by_id(user_id)
