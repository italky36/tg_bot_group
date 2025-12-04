# SupportHub - Telegram Support Bot

Telegram-бот для клиентской поддержки с использованием групповых тем (Topics).

## Возможности

- **Для пользователей:**
  - **Telegram:** Простой интерфейс в личных сообщениях с ботом
  - **Web-виджет:** Чат прямо на вашем сайте (Tilda и другие платформы)
  - Поддержка текста, фото, видео, документов, голосовых сообщений и стикеров
  - Уведомления о статусе заявок
  - История переписки сохраняется при повторных обращениях

- **Для команды поддержки:**
  - Автоматическое создание тем под каждого клиента (Telegram и Web)
  - Централизованное место для всех обращений в одной Telegram-группе
  - Команды управления заявками: `/close`, `/open`, `/info`, `/stats`, `/rename`
  - Информация о посетителях сайта (URL страницы, email, browser)

- **Web-виджет:**
  - Легкая интеграция на любой сайт (< 100 КБ gzipped)
  - Индикаторы доставки и прочтения сообщений (✓, ✓✓)
  - Уведомления о новых сообщениях
  - Автоматическое переподключение при разрыве связи
  - Адаптивный дизайн для мобильных устройств

- **Админ-панель:**
  - Dashboard со статистикой заявок
  - Просмотр списка заявок с фильтрацией (Telegram и Web)
  - Детальный просмотр заявок и истории сообщений
  - WebSocket сервер для виджета
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
- `/rename [новое название]` — переименовать тему (например, `/rename Клиент: user@example.com`)
- `/info` — информация о заявке (включая источник: Telegram или Web)
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
│   │   ├── models.py     # SQLAlchemy модели (Telegram + Web)
│   │   ├── session.py    # Сессия БД
│   │   └── crud.py       # CRUD операции
│   ├── services/
│   │   ├── ticket.py     # Логика заявок
│   │   └── web_messaging.py # Отправка в виджет
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
│   │   ├── tickets.py    # Список и детали заявок
│   │   └── widget.py     # WebSocket endpoint
│   ├── websocket/
│   │   ├── manager.py    # Менеджер WebSocket соединений
│   │   └── service.py    # Обработка сообщений виджета
│   ├── templates/        # Jinja2 шаблоны
│   └── static/           # CSS стили
├── widget/
│   ├── chat-widget.js    # Виджет чата
│   ├── example.html      # Пример интеграции
│   └── README.md         # Документация виджета
├── requirements.txt
├── run.py                # Запуск бота
├── run_admin.py          # Запуск админки
├── .env.example
└── README.md
```

## Web-виджет

SupportHub теперь включает виджет чата для интеграции на ваш сайт!

### Быстрый старт

1. Добавьте код на сайт перед `</body>`:
```html
<script>
    window.SUPPORTHUB_WS_URL = 'ws://your-domain.com/ws/widget';
    window.SUPPORTHUB_COLOR = '#007bff';
</script>
<script src="http://your-domain.com/widget/chat-widget.js"></script>
```

2. Запустите админ-панель (включает WebSocket сервер):
```bash
python run_admin.py
```

3. Все сообщения от посетителей будут попадать в вашу Telegram-группу!

**Подробная документация:** См. [widget/README.md](widget/README.md)

## Roadmap

- [x] MVP: Базовый функционал (создание тем, пересылка сообщений)
- [x] Команды управления заявками
- [x] Поддержка всех типов медиа
- [x] Веб-панель администратора
- [x] Web-виджет для сайтов с интеграцией Telegram
- [ ] Автоматические уведомления (SLA alerts)
- [ ] Система приоритетов заявок
- [ ] API для интеграций

## Лицензия

MIT
