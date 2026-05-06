# UGC Service

Микросервис для хранения пользовательского контента: оценки фильмов, рецензии и закладки.

## Технологии

- **FastAPI** — веб-фреймворк
- **MongoDB** (Motor) — хранилище данных
- **Pydantic v2 / pydantic-settings** — валидация и конфигурация
- **pytest + httpx** — тестирование

---

## Быстрый старт

### 1. Клонировать и настроить окружение

```bash
cp .env.example .env
```

Для локального запуска (без Docker) значения по умолчанию уже подходят.  
Для запуска через Docker Compose установите `MONGODB__HOST=mongodb` в `.env`.

### 2. Запустить MongoDB

```bash
docker compose up -d mongodb
```

### 3. Установить зависимости

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Запустить сервис

```bash
uvicorn main:app --reload
```

Swagger UI доступен по адресу: **http://localhost:8000/docs**

### Запуск всего стека через Docker Compose

```bash
docker compose up --build
```

---

## Конфигурация

Все настройки задаются через переменные окружения (файл `.env`).  
Вложенные модели разделяются через `__`.

| Переменная | По умолчанию | Описание |
|---|---|---|
| `MONGODB__HOST` | `localhost` | Хост MongoDB |
| `MONGODB__PORT` | `27017` | Порт MongoDB |
| `MONGODB__DB` | `ugc_db` | Имя базы данных |
| `MONGODB__TEST_DB` | `ugc_test_db` | База для тестов |
| `MONGODB__COLLECTIONS__FILM_RATINGS` | `film_ratings` | Коллекция оценок |
| `MONGODB__COLLECTIONS__REVIEWS` | `reviews` | Коллекция рецензий |
| `MONGODB__COLLECTIONS__REVIEW_LIKES` | `review_likes` | Коллекция голосов за рецензии |
| `MONGODB__COLLECTIONS__BOOKMARKS` | `bookmarks` | Коллекция закладок |
| `AUTH__SERVICE_URL` | `http://localhost:8001` | URL сервиса авторизации |
| `AUTH__INTROSPECT_PATH` | `/api/v1/auth/introspect` | Путь introspection endpoint |
| `APP_PORT` | `8000` | Порт приложения (docker compose) |

---

## Авторизация

Все защищённые эндпоинты требуют заголовок:

```
Authorization: Bearer <jwt_token>
```

Сервис проверяет токен через introspection endpoint авторизационного сервиса.  
Ответ introspection должен содержать `{ "active": true, "sub": "<user_id>" }`.

---

## API

### Оценки фильмов

Оценка — целое число от **0 до 10**.  
`≥ 6` считается лайком, `≤ 4` — дизлайком, `= 5` — нейтральным.

| Метод | Путь | Auth | Описание |
|---|---|---|---|
| `GET` | `/api/v1/films/{film_id}/ratings/stats` | — | Статистика оценок фильма |
| `POST` | `/api/v1/films/{film_id}/ratings` | ✓ | Добавить или изменить оценку |
| `DELETE` | `/api/v1/films/{film_id}/ratings` | ✓ | Удалить свою оценку |
| `GET` | `/api/v1/users/me/liked-films` | ✓ | Список понравившихся фильмов (оценка ≥ 6) |

#### GET `/api/v1/films/{film_id}/ratings/stats`

```json
{
  "film_id": "abc123",
  "total_ratings": 1250,
  "likes_count": 890,
  "dislikes_count": 210,
  "neutral_count": 150,
  "average_rating": 7.34
}
```

#### POST `/api/v1/films/{film_id}/ratings`

Тело запроса:
```json
{ "rating": 8 }
```

Ответ `200`:
```json
{
  "id": "...",
  "user_id": "...",
  "film_id": "abc123",
  "rating": 8,
  "created_at": "2026-05-06T10:00:00Z",
  "updated_at": "2026-05-06T10:00:00Z"
}
```

#### GET `/api/v1/users/me/liked-films`

Query-параметры: `limit` (1–200, default 50), `skip` (default 0)

```json
[
  { "film_id": "abc123", "rating": 8, "created_at": "..." },
  { "film_id": "xyz789", "rating": 7, "created_at": "..." }
]
```

---

### Рецензии

| Метод | Путь | Auth | Описание |
|---|---|---|---|
| `GET` | `/api/v1/films/{film_id}/reviews` | — | Список рецензий к фильму |
| `POST` | `/api/v1/films/{film_id}/reviews` | ✓ | Написать рецензию |
| `GET` | `/api/v1/reviews/{review_id}` | — | Получить рецензию по ID |
| `POST` | `/api/v1/reviews/{review_id}/likes` | ✓ | Поставить лайк / дизлайк рецензии |
| `DELETE` | `/api/v1/reviews/{review_id}/likes` | ✓ | Убрать свой голос |

#### GET `/api/v1/films/{film_id}/reviews`

Query-параметры:

| Параметр | Значения | По умолчанию |
|---|---|---|
| `sort_by` | `published_at`, `likes_count`, `film_rating` | `published_at` |
| `order` | `asc`, `desc` | `desc` |
| `limit` | 1–100 | `20` |
| `skip` | ≥ 0 | `0` |

#### POST `/api/v1/films/{film_id}/reviews`

```json
{
  "author": "Иван Петров",
  "text": "Отличный фильм, рекомендую!",
  "film_rating": 9
}
```

`film_rating` — опциональное поле (0–10).

#### POST `/api/v1/reviews/{review_id}/likes`

```json
{ "is_like": true }
```

`is_like: true` — лайк, `false` — дизлайк. Повторный запрос с тем же значением идемпотентен; с противоположным — переключает голос.

---

### Закладки

| Метод | Путь | Auth | Описание |
|---|---|---|---|
| `GET` | `/api/v1/users/me/bookmarks` | ✓ | Список закладок |
| `POST` | `/api/v1/users/me/bookmarks` | ✓ | Добавить закладку |
| `DELETE` | `/api/v1/users/me/bookmarks/{film_id}` | ✓ | Удалить закладку |

#### POST `/api/v1/users/me/bookmarks`

```json
{ "film_id": "abc123" }
```

Повторное добавление той же закладки возвращает `409 Conflict`.

Query-параметры для GET: `limit` (1–200, default 50), `skip` (default 0). Сортировка по дате добавления (новые первые).

---

## Тестирование

Тесты требуют запущенного MongoDB (`docker compose up -d mongodb`).

```bash
pytest tests/ -v
```

Тесты используют отдельную базу (`MONGODB__TEST_DB`), которая очищается после каждого теста.  
Зависимость авторизации (`get_current_user`) замещается mock-функцией — auth-сервис не нужен.

```
tests/test_likes.py      — 11 тестов (оценки и статистика)
tests/test_reviews.py    — 13 тестов (рецензии и голоса)
tests/test_bookmarks.py  —  8 тестов (закладки)
```

---

## Генерация тестовых данных

```bash
python -m scripts.generate_data
```

Генерирует:
- 10 000 пользователей × 1 000 фильмов
- ~200 000 оценок фильмов
- ~50 000 рецензий
- ~100 000 закладок

---

## Тест производительности

```bash
# Сначала сгенерировать данные
python -m scripts.generate_data

# Затем запустить замеры
python -m scripts.performance_test
```

Замеряет avg / min / max / p95 задержки для 4 сценариев чтения (100 итераций каждый) и end-to-end задержку записи (50 итераций):

```
READ SCENARIOS (pre-loaded data)
=================================================================
[1] Liked films list (rating >= 6)
    avg=1.23ms  min=0.91ms  max=4.10ms  p95=2.87ms

[2] Film likes/dislikes count + average rating
    avg=0.98ms  min=0.74ms  max=3.22ms  p95=2.01ms

[3] Bookmarks list
    avg=1.05ms  min=0.83ms  max=3.88ms  p95=2.44ms

[4] Average film rating
    avg=0.87ms  min=0.71ms  max=2.95ms  p95=1.76ms

WRITE + IMMEDIATE READ LATENCY (50 iterations)
=================================================================
[5] Add rating (upsert)
    write:            avg=1.44ms  min=1.10ms  max=5.30ms  p95=3.21ms
    read after write: avg=0.92ms  min=0.71ms  max=2.88ms  p95=1.95ms
```

---

## Структура проекта

```
├── main.py                   # Точка входа FastAPI
├── core/
│   └── settings.py           # Конфигурация (Pydantic Settings)
├── db/
│   └── mongodb.py            # Подключение и индексы MongoDB
├── schemas/
│   ├── likes.py
│   ├── reviews.py
│   └── bookmarks.py
├── utils/
│   ├── auth.py               # JWT introspection dependency
│   └── helpers.py            # Вспомогательные функции
├── api/v1/
│   ├── likes.py
│   ├── reviews.py
│   └── bookmarks.py
├── tests/
│   ├── conftest.py
│   ├── test_likes.py
│   ├── test_reviews.py
│   └── test_bookmarks.py
├── scripts/
│   ├── generate_data.py      # Генератор тестовых данных
│   └── performance_test.py   # Замер производительности
├── Dockerfile
├── docker-compose.yml
└── .env.example
```
