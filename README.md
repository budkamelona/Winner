# Winner Bot — Telegram Giveaway Bot

## Стек

- Python 3.12, aiogram 3.x, PostgreSQL 16, SQLAlchemy 2.x async, Alembic, APScheduler, Docker

---

## 1. Создание бота через BotFather

1. Откройте [@BotFather](https://t.me/BotFather) в Telegram.
2. Отправьте `/newbot`.
3. Введите имя бота (например, `My Giveaway Bot`).
4. Введите username (например, `my_giveaway_bot`).
5. Скопируйте полученный **токен** — это значение `BOT_TOKEN`.
6. `BOT_USERNAME` — это username без `@` (например, `my_giveaway_bot`).

---

## 2. Добавление бота администратором в канал

1. Откройте ваш Telegram-канал.
2. Перейдите в **Управление каналом → Администраторы → Добавить администратора**.
3. Найдите вашего бота по username.
4. Дайте боту право **Публикация сообщений** (Post Messages).
5. Сохраните.

---

## 3. Добавление канала в бота

1. Откройте бота и нажмите **📢 Мои каналы → Добавить канал**.
2. Введите `@username` канала **или** перешлите любое сообщение из этого канала.
3. Бот проверит:
   - что он является администратором канала с правом публикации;
   - что вы тоже являетесь администратором этого канала.
4. Если проверки пройдены — канал сохраняется.

---

## 4. Настройка переменных окружения

Скопируйте `.env.example` в `.env`:

```bash
cp .env.example .env
```

Заполните `.env`:

```env
BOT_TOKEN=1234567890:AAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
BOT_USERNAME=your_bot_username

POSTGRES_USER=botuser
POSTGRES_PASSWORD=botpassword
POSTGRES_DB=winner_bot

DATABASE_URL=postgresql+asyncpg://botuser:botpassword@db/winner_bot
TIMEZONE=Europe/Moscow
```

Важно:
- не коммитьте `.env` в GitHub;
- храните реальные `BOT_TOKEN`, `ADMIN_TELEGRAM_ID` и пароли только в секретах GitHub/Railway.

---

## 5. Запуск через docker-compose

```bash
docker-compose up --build
```

При запуске:
1. Стартует PostgreSQL.
2. Применяются миграции (`alembic upgrade head`).
3. Запускается бот.

Остановка:

```bash
docker-compose down
```

С удалением данных:

```bash
docker-compose down -v
```

---

## 6. Проведение розыгрыша

### Шаг 1 — Добавьте канал

- `/start` → **📢 Мои каналы** → **Добавить канал**
- Введите `@username` или перешлите сообщение из канала

### Шаг 2 — Создайте розыгрыш

- **🎁 Создать розыгрыш**
- Выберите канал
- Введите текст поста
- Укажите количество победителей
- Выберите режим завершения:
  - **Вручную** — вы сами нажимаете «Завершить»
  - **По времени** — укажите дату и время в UTC (`ДД.ММ.ГГГГ ЧЧ:ММ`)
- Выберите режим выбора победителей:
  - **Случайным образом** — бот выберет сам
  - **Вручную** — вы укажете победителей сами

### Шаг 3 — Участники присоединяются

- Бот публикует пост в канал с кнопкой **🎁 Участвовать (0)**
- Пользователи нажимают кнопку → переходят в личный чат с ботом → проходят математическую капчу
- После капчи участник добавляется, счётчик на кнопке обновляется

### Шаг 4 — Завершение

- **Вручную**: **🗒 Мои розыгрыши** → выберите розыгрыш → **Завершить**
- **По времени**: бот автоматически завершит в указанное время

### Шаг 5 — Результаты

- Бот публикует результаты в канале ответом на исходный пост
- Формат:
  ```
  🎉 Розыгрыш завершён!
  
  Победители:
  1. @username
  2. ID: 123456789
  
  Количество участников: N
  ```
- Если победители выбраны вручную — добавляется строка:
  ```
  ℹ️ Победители были выбраны администратором вручную.
  ```

---

## Архитектура

```
app/
  main.py                    — точка входа, настройка бота и планировщика
  config.py                  — pydantic-settings конфигурация

  bot/
    routers/
      start.py               — /start, главное меню
      channels.py            — управление каналами
      giveaway_create.py     — создание розыгрыша (FSM)
      giveaway_manage.py     — просмотр и завершение розыгрышей
      participation.py       — участие и капча
    keyboards/               — InlineKeyboardMarkup
    states/                  — FSM States
    tasks.py                 — APScheduler задачи

  application/services/      — бизнес-логика
  infrastructure/
    database.py              — SQLAlchemy engine/session
    models.py                — ORM модели
    repositories/            — CRUD операции
    telegram/                — обёртка над Bot API

migrations/                  — Alembic миграции
```

## Публикация на GitHub

Проект уже подготовлен к публикации:
- `.env`, `.venv`, `.idea`, `.DS_Store` и другой локальный мусор исключаются через `.gitignore`;
- шаблон `.env.example` безопасен для коммита;
- `.dockerignore` уменьшает контекст сборки при деплое.

Базовые команды:

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin git@github.com:YOUR_USERNAME/winner_bot.git
git push -u origin main
```
