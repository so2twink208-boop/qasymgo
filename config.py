# config.py — Конфигурация бота QasymGo
# Все настройки берутся из переменных окружения или задаются здесь напрямую

import os
from dotenv import load_dotenv

load_dotenv()

# ── Telegram ──────────────────────────────────────────────────────────────────
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# ── Администраторы ────────────────────────────────────────────────────────────
# Перечислите Telegram ID администраторов через запятую в .env:
# ADMIN_IDS=123456789,987654321
_raw_admins = os.getenv("ADMIN_IDS", "")
ADMIN_IDS: list[int] = [int(x.strip()) for x in _raw_admins.split(",") if x.strip().isdigit()]

# ── База данных ───────────────────────────────────────────────────────────────
DB_PATH: str = os.getenv("DB_PATH", "qasymgo.db")

# ── Бизнес-логика ─────────────────────────────────────────────────────────────
DRIVER_BONUS_BALANCE: int = 500          # тенге — бонус при регистрации водителя
COMMISSION_RATE: float = 0.05           # 5% комиссия с завершённого заказа
DEFAULT_RATING: float = 5.0             # начальный рейтинг

# ── Роли ─────────────────────────────────────────────────────────────────────
ROLE_DRIVER = "driver"
ROLE_PASSENGER = "passenger"

# ── Статусы заказа ────────────────────────────────────────────────────────────
ORDER_PENDING = "pending"       # ожидает водителя
ORDER_ACTIVE = "active"        # водитель выбран, едут
ORDER_COMPLETED = "completed"  # завершён
ORDER_CANCELLED = "cancelled"  # отменён
