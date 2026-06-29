# bot.py — Точка входа QasymGo Taxi Bot
# Запуск: python bot.py

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from database.db import init_db, cancel_old_orders
from utils.middleware import ResetFSMMiddleware

# ── Подключаем все роутеры ────────────────────────────────────────────────────
from handlers import (
    registration,
    passenger,
    driver,
    reviews,
    admin,
    profile,
    common,
)

# ── Настройка логирования ─────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("qasymgo.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


async def auto_cancel_orders(bot: Bot) -> None:
    """Фоновая задача — каждую минуту отменяет заказы старше 10 минут."""
    while True:
        try:
            cancelled = await cancel_old_orders(minutes=10)
            for order_id in cancelled:
                logger.info("Заказ #%s автоматически отменён (истекло время).", order_id)
                # Уведомляем пассажира
                from database.db import get_order, get_user_by_id
                from utils import safe_send
                order = await get_order(order_id)
                if order:
                    passenger = await get_user_by_id(order["passenger_id"])
                    if passenger:
                        await safe_send(
                            bot,
                            passenger["telegram_id"],
                            f"⏰ Заказ #{order_id} отменён — никто не принял его в течение 10 минут.\n"
                            f"Попробуйте создать новый заказ.",
                        )
        except Exception as e:
            logger.error("Ошибка в auto_cancel_orders: %s", e)
        await asyncio.sleep(60)  # проверяем каждую минуту


async def main() -> None:
    # Проверяем токен
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        logger.error(
            "Токен бота не задан! Создайте файл .env и укажите BOT_TOKEN."
        )
        sys.exit(1)

    # Инициализируем базу данных
    await init_db()

    # Создаём бота с HTML по умолчанию
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    # Диспетчер с хранилищем состояний в памяти
    # (для продакшена замените на RedisStorage)
    dp = Dispatcher(storage=MemoryStorage())

    # Middleware — сброс FSM при нажатии кнопок меню
    dp.message.middleware(ResetFSMMiddleware())

    # ── Регистрация роутеров (порядок важен!) ─────────────────────────────────
    # 1. Регистрация (самый приоритетный — /start)
    dp.include_router(registration.router)
    # 2. Административные команды
    dp.include_router(admin.router)
    # 3. Отзывы (раньше driver, т.к. перехватывает callback rate:*)
    dp.include_router(reviews.router)
    # 4. Функции водителя
    dp.include_router(driver.router)
    # 5. Функции пассажира
    dp.include_router(passenger.router)
    # 6. Профиль и смена роли
    dp.include_router(profile.router)
    # 7. Общие / fallback (всегда последним)
    dp.include_router(common.router)

    logger.info("QasymGo Bot запущен. Нажмите Ctrl+C для остановки.")

    # Запускаем фоновую задачу автоотмены заказов
    asyncio.create_task(auto_cancel_orders(bot))

    # Запускаем polling (long polling)
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()
        logger.info("Бот остановлен.")


if __name__ == "__main__":
    asyncio.run(main())
