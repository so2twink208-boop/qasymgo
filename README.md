# 🚕 QasymGo — Taxi Bot для посёлка Касым Кайсенов

Telegram-бот для локального сервиса такси на Python 3.12 + aiogram 3.x + SQLite.

---

## 📁 Структура проекта

```
qasymgo/
├── bot.py                  # Точка входа, запуск polling
├── config.py               # Настройки (токен, комиссия, роли)
├── .env                    # Секреты (создать из .env.example)
├── .env.example            # Шаблон переменных окружения
├── requirements.txt        # Зависимости Python
├── qasymgo.db              # SQLite база (создаётся автоматически)
├── qasymgo.log             # Лог-файл (создаётся автоматически)
│
├── database/
│   ├── __init__.py
│   └── db.py               # Все SQL-запросы (users, orders, reviews)
│
├── handlers/
│   ├── __init__.py
│   ├── registration.py     # /start, выбор роли
│   ├── passenger.py        # Создание заказа (FSM 4 шага), история
│   ├── driver.py           # Принятие заказов, профиль, баланс
│   ├── reviews.py          # Система отзывов и рейтингов
│   ├── admin.py            # Команды администратора
│   └── common.py           # /help, /menu, fallback
│
├── keyboards/
│   ├── __init__.py
│   └── keyboards.py        # Все InlineKeyboard и ReplyKeyboard
│
├── states/
│   ├── __init__.py
│   └── states.py           # FSM состояния (aiogram 3.x)
│
└── utils/
    ├── __init__.py
    └── helpers.py          # stars(), format_order(), safe_send()
```

---

## 🚀 Запуск на Windows

### 1. Установить Python 3.12

Скачать с [python.org](https://www.python.org/downloads/) и установить.
При установке поставить галочку **"Add Python to PATH"**.

### 2. Создать токен бота

Написать [@BotFather](https://t.me/BotFather) → `/newbot` → скопировать токен.

### 3. Клонировать / скопировать проект

```cmd
cd %USERPROFILE%\Desktop
mkdir qasymgo && cd qasymgo
:: скопируйте все файлы проекта сюда
```

### 4. Создать виртуальное окружение

```cmd
python -m venv venv
venv\Scripts\activate
```

### 5. Установить зависимости

```cmd
pip install -r requirements.txt
```

### 6. Настроить переменные окружения

```cmd
copy .env.example .env
notepad .env
```

Заполните `.env`:
```
BOT_TOKEN=ваш_токен_от_BotFather
ADMIN_IDS=ваш_telegram_id
```

> Свой Telegram ID узнайте у [@userinfobot](https://t.me/userinfobot)

### 7. Запустить бота

```cmd
python bot.py
```

---

## ⚙️ Конфигурация (config.py)

| Параметр | Значение | Описание |
|---|---|---|
| `DRIVER_BONUS_BALANCE` | 500 | Бонус при регистрации водителя (₸) |
| `COMMISSION_RATE` | 0.05 | Комиссия сервиса (5%) |
| `DEFAULT_RATING` | 5.0 | Начальный рейтинг |

---

## 👑 Команды администратора

| Команда | Описание |
|---|---|
| `/addbalance <tg_id> <сумма>` | Пополнить баланс водителя |
| `/removebalance <tg_id> <сумма>` | Списать с баланса |
| `/stats` | Общая статистика сервиса |
| `/drivers` | Список всех водителей |
| `/orders` | Активные заказы |
| `/ban <tg_id>` | Заблокировать пользователя |

---

## 🔄 Логика комиссии

1. Пассажир создаёт заказ → рассылка всем водителям
2. Водитель нажимает **Принять** → бот проверяет баланс (нужна комиссия: цена × 5%)
3. Пассажир выбирает водителя → комиссия **списывается** с баланса водителя
4. После поездки пассажир ставит оценку → рейтинг водителя пересчитывается

---

## 🛠 Остановка / перезапуск

```cmd
:: Остановить: Ctrl+C в окне терминала

:: Перезапустить:
venv\Scripts\activate
python bot.py
```
