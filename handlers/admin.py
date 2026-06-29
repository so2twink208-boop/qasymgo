# handlers/admin.py — Команды администратора QasymGo
# Доступны только пользователям из списка ADMIN_IDS

import logging
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

from database.db import (
    get_user, update_balance, ban_user,
    get_all_drivers, get_pending_orders, get_stats,
)
from config import ADMIN_IDS
from utils import stars, safe_send

logger = logging.getLogger(__name__)
router = Router()


# ─── Фильтр: только администраторы ────────────────────────────────────────────
def is_admin(message: Message) -> bool:
    return message.from_user.id in ADMIN_IDS


async def admin_guard(message: Message) -> bool:
    """Проверяет права и отправляет отказ. Возвращает True если доступ разрешён."""
    if not is_admin(message):
        await message.answer("🚫 У вас нет прав администратора.")
        return False
    return True


# ─── /addbalance user_telegram_id amount ─────────────────────────────────────
@router.message(Command("addbalance"))
async def cmd_addbalance(message: Message) -> None:
    if not await admin_guard(message):
        return
    args = message.text.split()[1:]
    if len(args) < 2:
        await message.answer("Использование: /addbalance <telegram_id> <сумма>")
        return
    try:
        tg_id  = int(args[0])
        amount = float(args[1])
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❗ Некорректные аргументы.")
        return

    user = await get_user(tg_id)
    if not user:
        await message.answer("❌ Пользователь не найден.")
        return

    new_balance = await update_balance(user["id"], amount)
    await message.answer(
        f"✅ Баланс пользователя <b>{user['name']}</b> пополнен на <b>{amount} ₸</b>.\n"
        f"Новый баланс: <b>{new_balance} ₸</b>",
        parse_mode="HTML",
    )
    logger.info("Админ пополнил баланс %s на %s ₸", user["name"], amount)


# ─── /removebalance user_telegram_id amount ───────────────────────────────────
@router.message(Command("removebalance"))
async def cmd_removebalance(message: Message) -> None:
    if not await admin_guard(message):
        return
    args = message.text.split()[1:]
    if len(args) < 2:
        await message.answer("Использование: /removebalance <telegram_id> <сумма>")
        return
    try:
        tg_id  = int(args[0])
        amount = float(args[1])
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❗ Некорректные аргументы.")
        return

    user = await get_user(tg_id)
    if not user:
        await message.answer("❌ Пользователь не найден.")
        return

    new_balance = await update_balance(user["id"], -amount)
    await message.answer(
        f"✅ С баланса <b>{user['name']}</b> списано <b>{amount} ₸</b>.\n"
        f"Новый баланс: <b>{new_balance} ₸</b>",
        parse_mode="HTML",
    )
    logger.info("Админ снял %s ₸ с баланса %s", amount, user["name"])


# ─── /stats ───────────────────────────────────────────────────────────────────
@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    if not await admin_guard(message):
        return
    s = await get_stats()
    await message.answer(
        f"📊 <b>Статистика QasymGo</b>\n\n"
        f"🚕 Водителей:       {s['drivers']}\n"
        f"🧍 Пассажиров:      {s['passengers']}\n"
        f"📦 Всего заказов:   {s['total_orders']}\n"
        f"✅ Завершено:       {s['completed']}\n"
        f"💸 Комиссии собрано: {s['commission']} ₸",
        parse_mode="HTML",
    )


# ─── /drivers ─────────────────────────────────────────────────────────────────
@router.message(Command("drivers"))
async def cmd_drivers(message: Message) -> None:
    if not await admin_guard(message):
        return
    drivers = await get_all_drivers()
    if not drivers:
        await message.answer("Водителей нет.")
        return
    lines = []
    for d in drivers:
        tg = f"@{d['username']}" if d.get("username") else "—"
        phone_str = d.get("phone") or "—"
        car_str   = d.get("car_info") or "—"
        lines.append(
            f"• <b>{d['name']}</b> ({tg})\n"
            f"  📱 {phone_str} | 🚗 {car_str}\n"
            f"  ⭐ {d['rating']} | 💰 {d['balance']} ₸ | 🆔 {d['telegram_id']}"
        )
    await message.answer(
        "🚕 <b>Список водителей:</b>\n\n" + "\n\n".join(lines),
        parse_mode="HTML",
    )


# ─── /orders ──────────────────────────────────────────────────────────────────
@router.message(Command("orders"))
async def cmd_orders(message: Message) -> None:
    if not await admin_guard(message):
        return
    from utils import format_order
    orders = await get_pending_orders()
    if not orders:
        await message.answer("📭 Активных заказов нет.")
        return
    text = "📦 <b>Активные заказы:</b>\n\n" + "\n\n".join(format_order(o) for o in orders)
    await message.answer(text, parse_mode="HTML")


# ─── /broadcast текст ─────────────────────────────────────────────────────────
@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message) -> None:
    if not await admin_guard(message):
        return
    text = message.text.removeprefix("/broadcast").strip()
    if not text:
        await message.answer("Использование: /broadcast <текст сообщения>")
        return

    from database.db import get_all_drivers, get_user
    from aiogram import Bot
    bot: Bot = message.bot

    # Получаем всех пользователей
    async with __import__('aiosqlite').connect(__import__('config').DB_PATH) as db:
        db.row_factory = __import__('aiosqlite').Row
        async with db.execute("SELECT telegram_id FROM users WHERE is_banned = 0") as cur:
            users = [dict(r) for r in await cur.fetchall()]

    sent = 0
    failed = 0
    for u in users:
        ok = await safe_send(bot, u["telegram_id"], f"📢 <b>Сообщение от QasymGo:</b>\n\n{text}", parse_mode="HTML")
        if ok:
            sent += 1
        else:
            failed += 1

    await message.answer(
        f"✅ Рассылка завершена.\n"
        f"📨 Отправлено: {sent}\n"
        f"❌ Не доставлено: {failed}"
    )
    logger.info("Админ сделал рассылку: %s символов, %d получателей", len(text), sent)


# ─── /find @username или /find telegram_id ────────────────────────────────────
@router.message(Command("find"))
async def cmd_find(message: Message) -> None:
    if not await admin_guard(message):
        return
    args = message.text.split()[1:]
    if not args:
        await message.answer("Использование: /find <telegram_id> или /find @username")
        return

    query = args[0].lstrip("@")
    user = None

    # Ищем по ID
    if query.isdigit():
        from database.db import get_user
        user = await get_user(int(query))
    else:
        # Ищем по username
        async with __import__('aiosqlite').connect(__import__('config').DB_PATH) as db:
            db.row_factory = __import__('aiosqlite').Row
            async with db.execute(
                "SELECT * FROM users WHERE username = ?", (query,)
            ) as cur:
                row = await cur.fetchone()
                user = dict(row) if row else None

    if not user:
        await message.answer("❌ Пользователь не найден.")
        return

    phone_str = user.get("phone") or "—"
    car_str   = user.get("car_info") or "—"
    banned    = "🚫 Да" if user["is_banned"] else "✅ Нет"
    warnings  = user.get("warnings", 0)
    debt      = user.get("debt", 0)

    await message.answer(
        f"🔍 <b>Пользователь найден</b>\n\n"
        f"👤 Имя: {user['name']}\n"
        f"🆔 Telegram ID: {user['telegram_id']}\n"
        f"📱 Username: @{user.get('username') or '—'}\n"
        f"🎭 Роль: {user['role']}\n"
        f"📞 Телефон: {phone_str}\n"
        f"🚗 Машина: {car_str}\n"
        f"💰 Баланс: {user['balance']} ₸\n"
        f"⭐ Рейтинг: {user['rating']}\n"
        f"⚠️ Предупреждения: {warnings}/3\n"
        f"💸 Долг: {debt} ₸\n"
        f"🚫 Забанен: {banned}\n"
        f"📅 Регистрация: {user['created_at'][:10]}",
        parse_mode="HTML",
    )


# ─── /clearwarnings telegram_id ───────────────────────────────────────────────
@router.message(Command("clearwarnings"))
async def cmd_clearwarnings(message: Message) -> None:
    if not await admin_guard(message):
        return
    args = message.text.split()[1:]
    if not args:
        await message.answer("Использование: /clearwarnings <telegram_id>")
        return
    try:
        tg_id = int(args[0])
    except ValueError:
        await message.answer("❗ Некорректный ID.")
        return

    from database.db import clear_warnings
    success = await clear_warnings(tg_id)
    if success:
        await message.answer(
            f"✅ Предупреждения и долг пользователя {tg_id} сброшены.\n"
            f"Бан снят (если был)."
        )
        logger.info("Админ сбросил предупреждения пользователя %s", tg_id)
    else:
        await message.answer("❌ Пользователь не найден.")


# ─── /ban telegram_id ─────────────────────────────────────────────────────────
@router.message(Command("ban"))
async def cmd_ban(message: Message) -> None:
    if not await admin_guard(message):
        return
    args = message.text.split()[1:]
    if not args:
        await message.answer("Использование: /ban <telegram_id>")
        return
    try:
        tg_id = int(args[0])
    except ValueError:
        await message.answer("❗ Некорректный ID.")
        return

    success = await ban_user(tg_id)
    if success:
        await message.answer(f"🚫 Пользователь {tg_id} заблокирован.")
        logger.warning("Админ заблокировал пользователя %s", tg_id)
    else:
        await message.answer("❌ Пользователь не найден.")
