# database/db.py — Все операции с базой данных QasymGo
# Используем aiosqlite для асинхронного доступа к SQLite

import aiosqlite
import logging
from datetime import datetime
from config import DB_PATH, DEFAULT_RATING, DRIVER_BONUS_BALANCE, COMMISSION_RATE

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# ИНИЦИАЛИЗАЦИЯ
# ═══════════════════════════════════════════════════════════════════════════════

async def init_db() -> None:
    """Создаёт таблицы, если они ещё не существуют."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA journal_mode=WAL")  # лучшая параллельность
        await db.execute("PRAGMA foreign_keys=ON")

        # ── Пользователи (водители и пассажиры) ──────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                name        TEXT    NOT NULL,
                username    TEXT,
                role        TEXT    NOT NULL,
                phone       TEXT,
                car_info    TEXT,
                balance     REAL    DEFAULT 0,
                rating      REAL    DEFAULT 5.0,
                is_banned   INTEGER DEFAULT 0,
                ban_until   TEXT,                          -- дата окончания бана (для автобана)
                warnings    INTEGER DEFAULT 0,             -- предупреждения пассажира
                debt        REAL    DEFAULT 0,             -- долг пассажира (штраф)
                cancel_count INTEGER DEFAULT 0,            -- счётчик отмен водителя
                created_at  TEXT    DEFAULT (datetime('now'))
            )
        """)
        # Миграция — добавляем новые колонки если базы уже существует
        for col, definition in [
            ("phone", "TEXT"), ("car_info", "TEXT"),
            ("ban_until", "TEXT"), ("warnings", "INTEGER DEFAULT 0"),
            ("debt", "REAL DEFAULT 0"), ("cancel_count", "INTEGER DEFAULT 0"),
        ]:
            try:
                await db.execute(f"ALTER TABLE users ADD COLUMN {col} {definition}")
            except Exception:
                pass

        # ── Заказы ────────────────────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                passenger_id    INTEGER NOT NULL REFERENCES users(id),
                from_address    TEXT    NOT NULL,
                to_address      TEXT    NOT NULL,
                price           REAL    NOT NULL,
                status          TEXT    DEFAULT 'pending',
                selected_driver INTEGER REFERENCES users(id),
                created_at      TEXT    DEFAULT (datetime('now'))
            )
        """)

        # ── Заявки водителей на заказ (защита от двойного принятия) ─────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS driver_applications (
                order_id   INTEGER NOT NULL,
                driver_id  INTEGER NOT NULL,
                PRIMARY KEY (order_id, driver_id)
            )
        """)

        # ── Отзывы ────────────────────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS reviews (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                driver_id   INTEGER NOT NULL REFERENCES users(id),
                passenger_id INTEGER NOT NULL REFERENCES users(id),
                order_id    INTEGER REFERENCES orders(id),
                rating      INTEGER NOT NULL,          -- 1..5
                comment     TEXT,
                created_at  TEXT DEFAULT (datetime('now'))
            )
        """)

        await db.commit()
    logger.info("База данных инициализирована.")


# ═══════════════════════════════════════════════════════════════════════════════
# ПОЛЬЗОВАТЕЛИ
# ═══════════════════════════════════════════════════════════════════════════════

async def get_user(telegram_id: int) -> dict | None:
    """Возвращает пользователя по Telegram ID или None."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def get_user_by_id(user_id: int) -> dict | None:
    """Возвращает пользователя по внутреннему ID."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def create_user(telegram_id: int, name: str, username: str | None, role: str) -> dict:
    """Создаёт нового пользователя и возвращает его данные."""
    balance = DRIVER_BONUS_BALANCE if role == "driver" else 0
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO users (telegram_id, name, username, role, balance, rating)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (telegram_id, name, username, role, balance, DEFAULT_RATING),
        )
        await db.commit()
    return await get_user(telegram_id)


async def get_all_drivers() -> list[dict]:
    """Возвращает всех активных (не забаненных) водителей."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE role = 'driver' AND is_banned = 0"
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def update_balance(user_id: int, delta: float) -> float:
    """Изменяет баланс пользователя на delta (может быть отрицательным).
    Возвращает новый баланс."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET balance = balance + ? WHERE id = ?", (delta, user_id)
        )
        await db.commit()
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT balance FROM users WHERE id = ?", (user_id,)
        ) as cur:
            row = await cur.fetchone()
            return row["balance"]


async def add_warning(telegram_id: int) -> dict:
    """Добавляет предупреждение пассажиру.
    При 3 предупреждениях — штраф 200 ₸ и сброс счётчика."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET warnings = warnings + 1 WHERE telegram_id = ?",
            (telegram_id,),
        )
        await db.commit()
    user = await get_user(telegram_id)
    # При 5 предупреждениях — штраф 100 ₸ и сброс
    if user and user["warnings"] >= 5:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE users SET warnings = 0, debt = debt + 100 WHERE telegram_id = ?",
                (telegram_id,),
            )
            await db.commit()
        user = await get_user(telegram_id)
    return user


async def clear_warnings(telegram_id: int) -> bool:
    """Сбрасывает предупреждения и долг пассажира (только для админа)."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "UPDATE users SET warnings = 0, debt = 0, is_banned = 0 WHERE telegram_id = ?",
            (telegram_id,),
        )
        await db.commit()
        return cur.rowcount > 0


async def add_driver_cancel(telegram_id: int) -> int:
    """Увеличивает счётчик отмен водителя. Возвращает новое значение."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET cancel_count = cancel_count + 1 WHERE telegram_id = ?",
            (telegram_id,),
        )
        await db.commit()
    user = await get_user(telegram_id)
    return user["cancel_count"] if user else 0


async def reset_driver_cancels(telegram_id: int) -> None:
    """Сбрасывает счётчик отмен водителя."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET cancel_count = 0 WHERE telegram_id = ?",
            (telegram_id,),
        )
        await db.commit()


async def change_role(telegram_id: int, new_role: str) -> None:
    """Меняет роль пользователя."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET role = ? WHERE telegram_id = ?",
            (new_role, telegram_id),
        )
        await db.commit()


async def update_driver_info(telegram_id: int, phone: str, car_info: str) -> None:
    """Сохраняет телефон и машину водителя."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET phone = ?, car_info = ? WHERE telegram_id = ?",
            (phone, car_info, telegram_id),
        )
        await db.commit()


async def ban_user(telegram_id: int) -> bool:
    """Блокирует пользователя. Возвращает True если найден."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "UPDATE users SET is_banned = 1 WHERE telegram_id = ?", (telegram_id,)
        )
        await db.commit()
        return cur.rowcount > 0


async def update_rating(driver_id: int) -> None:
    """Пересчитывает рейтинг водителя из таблицы отзывов."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT AVG(rating) as avg_r FROM reviews WHERE driver_id = ?", (driver_id,)
        ) as cur:
            row = await cur.fetchone()
            avg = row[0] if row and row[0] is not None else DEFAULT_RATING
        await db.execute(
            "UPDATE users SET rating = ? WHERE id = ?", (round(avg, 2), driver_id)
        )
        await db.commit()


# ═══════════════════════════════════════════════════════════════════════════════
# ЗАКАЗЫ
# ═══════════════════════════════════════════════════════════════════════════════

async def create_order(passenger_id: int, from_addr: str, to_addr: str, price: float) -> int:
    """Создаёт новый заказ и возвращает его ID."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """INSERT INTO orders (passenger_id, from_address, to_address, price)
               VALUES (?, ?, ?, ?)""",
            (passenger_id, from_addr, to_addr, price),
        )
        await db.commit()
        return cur.lastrowid


async def get_order(order_id: int) -> dict | None:
    """Возвращает заказ по ID."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM orders WHERE id = ?", (order_id,)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def get_pending_orders() -> list[dict]:
    """Возвращает все заказы в статусе 'pending'."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM orders WHERE status = 'pending' ORDER BY created_at DESC"
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def get_passenger_orders(passenger_id: int) -> list[dict]:
    """История заказов пассажира."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM orders WHERE passenger_id = ? ORDER BY created_at DESC LIMIT 20",
            (passenger_id,),
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def get_driver_orders(driver_id: int) -> list[dict]:
    """История заказов водителя."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT * FROM orders
               WHERE selected_driver = ? AND status IN ('active','completed')
               ORDER BY created_at DESC LIMIT 20""",
            (driver_id,),
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def set_order_driver(order_id: int, driver_id: int) -> None:
    """Устанавливает водителя и меняет статус на 'active'."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE orders SET selected_driver = ?, status = 'active' WHERE id = ?",
            (driver_id, order_id),
        )
        await db.commit()


async def complete_order(order_id: int) -> dict | None:
    """Завершает заказ и возвращает его."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE orders SET status = 'completed' WHERE id = ?", (order_id,)
        )
        await db.commit()
    return await get_order(order_id)


async def cancel_order(order_id: int) -> None:
    """Отменяет заказ."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE orders SET status = 'cancelled' WHERE id = ?", (order_id,)
        )
        await db.commit()


async def has_applied(order_id: int, driver_id: int) -> bool:
    """Проверяет, подавал ли водитель уже заявку на этот заказ."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT 1 FROM driver_applications WHERE order_id=? AND driver_id=?",
            (order_id, driver_id),
        ) as cur:
            return await cur.fetchone() is not None


async def add_application(order_id: int, driver_id: int) -> None:
    """Записывает заявку водителя на заказ."""
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute(
                "INSERT INTO driver_applications (order_id, driver_id) VALUES (?, ?)",
                (order_id, driver_id),
            )
            await db.commit()
        except Exception:
            pass  # заявка уже существует


async def clear_applications(order_id: int) -> None:
    """Удаляет все заявки на заказ после его завершения."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM driver_applications WHERE order_id=?", (order_id,)
        )
        await db.commit()


# ═══════════════════════════════════════════════════════════════════════════════
# ОТЗЫВЫ
# ═══════════════════════════════════════════════════════════════════════════════

async def add_review(driver_id: int, passenger_id: int, order_id: int,
                     rating: int, comment: str | None) -> None:
    """Добавляет отзыв и обновляет рейтинг водителя."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO reviews (driver_id, passenger_id, order_id, rating, comment)
               VALUES (?, ?, ?, ?, ?)""",
            (driver_id, passenger_id, order_id, rating, comment),
        )
        await db.commit()
    await update_rating(driver_id)


async def cancel_old_orders(minutes: int = 10) -> list[int]:
    """Отменяет заказы в статусе pending старше N минут.
    Возвращает список ID отменённых заказов."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT id FROM orders
               WHERE status = 'pending'
               AND (strftime('%s', 'now') - strftime('%s', created_at)) > ?""",
            (minutes * 60,),
        ) as cur:
            rows = await cur.fetchall()
        ids = [r["id"] for r in rows]
        if ids:
            await db.execute(
                f"UPDATE orders SET status='cancelled' WHERE id IN ({','.join('?'*len(ids))})",
                ids,
            )
            await db.commit()
    return ids


# ═══════════════════════════════════════════════════════════════════════════════
# СТАТИСТИКА (для /stats)
# ═══════════════════════════════════════════════════════════════════════════════

async def get_stats() -> dict:
    """Возвращает общую статистику сервиса."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        async with db.execute("SELECT COUNT(*) as c FROM users WHERE role='driver'") as cur:
            drivers = (await cur.fetchone())["c"]

        async with db.execute("SELECT COUNT(*) as c FROM users WHERE role='passenger'") as cur:
            passengers = (await cur.fetchone())["c"]

        async with db.execute("SELECT COUNT(*) as c FROM orders") as cur:
            total_orders = (await cur.fetchone())["c"]

        async with db.execute(
            "SELECT COUNT(*) as c FROM orders WHERE status='completed'"
        ) as cur:
            completed = (await cur.fetchone())["c"]

        async with db.execute(
            "SELECT COALESCE(SUM(price * ?), 0) as c FROM orders WHERE status='completed'",
            (COMMISSION_RATE,),
        ) as cur:
            commission = (await cur.fetchone())["c"]

    return {
        "drivers": drivers,
        "passengers": passengers,
        "total_orders": total_orders,
        "completed": completed,
        "commission": round(commission, 2),
    }
