# SupportHub - Telegram Support Bot

Telegram-бот для клиентской поддержки с использованием групповых тем (Topics).

## Возможности

- **Для пользователей:**
  - Простой интерфейс в личных сообщениях с ботом
  - Поддержка текста, фото, видео, документов, голосовых сообщений и стикеров
  - Уведомления о статусе заявок

- **Для команды поддержки:**
  - Автоматическое создание тем под каждого клиента
  - Централизованное место для всех обращений
  - Команды управления заявками: `/close`, `/open`, `/info`, `/stats`

- **Админ-панель:**
  - Dashboard со статистикой заявок
  - Просмотр списка заявок с фильтрацией
  - Детальный просмотр заявок и истории сообщений
  - Авторизация по логину/паролю

## Требования

- Python 3.10+
- Telegram Bot Token (от @BotFather)
- Telegram-группа с включёнными темами (Topics)

## Установка

1. Клонируйте репозиторий:
```bash
git clone <repository-url>
cd tg_bot_group
```

2. Создайте виртуальное окружение:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows
```

3. Установите зависимости:
```bash
pip install -r requirements.txt
```

4. Создайте файл `.env` на основе `.env.example`:
```bash
cp .env.example .env
```

5. Настройте переменные в `.env`:
```
BOT_TOKEN=your_bot_token_here
SUPPORT_GROUP_ID=-1001234567890
```

## Настройка группы поддержки

1. Создайте группу в Telegram или используйте существующую
2. Преобразуйте её в супергруппу (Settings → Group Type → Public/Private)
3. Включите темы (Topics): Settings → Topics → Enable
4. Добавьте бота в группу как администратора с правами:
   - Manage Topics (обязательно)
   - Send Messages
   - Delete Messages

5. Получите ID группы:
   - Добавьте бота @getmyid_bot в группу
   - Он покажет ID группы (начинается с -100...)

## Запуск

### Telegram-бот
```bash
python run.py
```

### Админ-панель
```bash
python run_admin.py
```

Админ-панель будет доступна по адресу: http://localhost:8000

**Учётные данные по умолчанию:**
- Login: `admin`
- Password: `admin`

(Измените в `.env` для production!)

## Команды бота

### Для пользователей (в личных сообщениях):
- `/start` — начать работу с ботом
- `/help` — справка
- `/my_tickets` — мои заявки

### Для операторов (в группе поддержки):
- `/close` — закрыть заявку (в теме) или `/close #0001`
- `/open` — открыть закрытую заявку
- `/info` — информация о заявке
- `/stats` — статистика заявок

## Структура проекта

```
tg_bot_group/
├── bot/
│   ├── __init__.py
│   ├── main.py           # Точка входа бота
│   ├── config.py         # Конфигурация
│   ├── handlers/
│   │   ├── user.py       # Обработчики для пользователей
│   │   └── group.py      # Обработчики для группы
│   ├── database/
│   │   ├── models.py     # SQLAlchemy модели
│   │   ├── session.py    # Сессия БД
│   │   └── crud.py       # CRUD операции
│   ├── services/
│   │   └── ticket.py     # Логика заявок
│   └── utils/
│       └── helpers.py
├── admin_panel/
│   ├── main.py           # FastAPI приложение
│   ├── config.py         # Конфигурация
│   ├── auth.py           # Авторизация
│   ├── database.py       # Подключение к БД
│   ├── routes/
│   │   ├── auth.py       # Login/Logout
│   │   ├── dashboard.py  # Dashboard
│   │   └── tickets.py    # Список и детали заявок
│   ├── templates/        # Jinja2 шаблоны
│   └── static/           # CSS стили
├── requirements.txt
├── run.py                # Запуск бота
├── run_admin.py          # Запуск админки
├── .env.example
└── README.md
```

## Roadmap

- [x] MVP: Базовый функционал (создание тем, пересылка сообщений)
- [x] Команды управления заявками
- [x] Поддержка всех типов медиа
- [x] Веб-панель администратора
- [ ] Автоматические уведомления (SLA alerts)
- [ ] Система приоритетов заявок
- [ ] API для интеграций

## Лицензия

MIT
