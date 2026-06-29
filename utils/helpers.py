# utils/helpers.py — Вспомогательные утилиты QasymGo

import logging
from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest

logger = logging.getLogger(__name__)


def stars(rating: float) -> str:
    """Преобразует числовой рейтинг в строку со звёздами."""
    full = int(round(rating))
    return "⭐" * full + "☆" * (5 - full)


def format_order(order: dict) -> str:
    """Форматирует краткое описание заказа."""
    status_emoji = {
        "pending":   "🕐",
        "active":    "🚗",
        "completed": "✅",
        "cancelled": "❌",
    }
    emoji = status_emoji.get(order["status"], "❓")
    return (
        f"{emoji} Заказ #{order['id']}\n"
        f"📍 Откуда: {order['from_address']}\n"
        f"📍 Куда:   {order['to_address']}\n"
        f"💰 Цена:   {order['price']} ₸\n"
        f"📅 {order['created_at'][:16]}"
    )


async def safe_send(bot: Bot, chat_id: int, text: str, **kwargs) -> bool:
    """Отправляет сообщение, игнорируя ошибки «бот заблокирован» и т.п."""
    try:
        await bot.send_message(chat_id, text, **kwargs)
        return True
    except TelegramForbiddenError:
        logger.warning("Пользователь %s заблокировал бота.", chat_id)
    except TelegramBadRequest as e:
        logger.warning("Bad request для chat_id %s: %s", chat_id, e)
    except Exception as e:
        logger.error("Ошибка отправки для chat_id %s: %s", chat_id, e)
    return False
