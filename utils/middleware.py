# utils/middleware.py — Middleware для сброса FSM при нажатии кнопок меню

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject
from aiogram.fsm.context import FSMContext
from typing import Callable, Dict, Any, Awaitable

# Все кнопки меню которые должны сбрасывать FSM
MENU_BUTTONS = {
    "📋 Мой профиль",
    "💰 Баланс",
    "📜 История",
    "🚕 Активные заказы",
    "💳 Пополнить баланс",
    "✏️ Редактировать профиль",
    "🔄 Сменить роль",
    "➕ Создать заказ",
    "📜 История поездок",
    "👤 Профиль",
}


class ResetFSMMiddleware(BaseMiddleware):
    """Сбрасывает FSM ДО выполнения хендлера если нажата кнопка меню."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:
        if isinstance(event, Message) and event.text in MENU_BUTTONS:
            state: FSMContext = data.get("state")
            if state:
                # Сбрасываем ПЕРЕД передачей хендлеру
                await state.clear()

        # Передаём управление хендлеру уже с чистым состоянием
        return await handler(event, data)
