# 🍴 Foodgram — социальная сеть для обмена рецептами

[![Main Foodgram workflow](https://github.com/LessTalkRus/foodgram/actions/workflows/main.yml/badge.svg)](https://github.com/LessTalkRus/foodgram/actions/workflows/main.yml)

### 🌐 Адрес проекта:
[Foodgram by VIacheslav Maximov](https://foodgram67.ddns.net/)

---

## 📖 Описание проекта

**Foodgram** — это онлайн-платформа, где пользователи могут:

- 🍳 Публиковать и редактировать собственные рецепты  
- ⭐ Добавлять чужие рецепты в избранное  
- 🧺 Создавать список покупок для выбранных блюд  
- 👥 Подписываться на любимых авторов  

Зарегистрированные пользователи могут формировать список продуктов, необходимых для приготовления выбранных блюд, а гости — просматривать рецепты и страницы авторов.

---

## 🧰 Технологии проекта

| Компонент | Технология / Версия |
|-----------|----------------------|
| Backend | **Python 3.10+, Django 4.2, DRF 3.16** |
| Frontend | **React, JavaScript (ES6+)** |
| База данных | **PostgreSQL 13.10** |
| Контейнеризация | **Docker, Docker Compose** |
| Веб-сервер | **Nginx** |
| CI/CD | **GitHub Actions** |
| Уведомления | **Telegram Bot API** |

---

## ⚙️ Установка и запуск локально

### 1️⃣ Клонировать репозиторий
```bash
git clone https://github.com/LessTalkRus/foodgram.git
cd foodgram
```

### 2️⃣ Создать файл `.env`
```env
SECRET_KEY=your_django_secret_key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DB_ENGINE=django.db.backends.sqlite3
DB_NAME=db.sqlite3
```

### 3️⃣ Установить зависимости и выполнить миграции
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py load_data --data_type=tags
python manage.py load_data --data_type=ingredients
```

### 4️⃣ Запустить проекты
Backend:
```bash
python manage.py runserver
```
Frontend:
```bash
cd ../frontend
npm install
npm start
```

После запуска сайт будет доступен по адресу:  
👉 http://localhost:3000

---

## 🐳 Развёртывание на сервере (Docker + CI/CD)

> 💡 Требуется установленный Docker и Docker Compose, а также доступ по SSH.

### 1️⃣ Клонировать проект и перейти в каталог
```bash
git clone https://github.com/LessTalkRus/foodgram.git
cd foodgram
```

### 2️⃣ Создать файл `.env` (пример ниже)
```env
SECRET_KEY=your_django_secret_key
DEBUG=False
ALLOWED_HOSTS=your_domain.com,localhost,127.0.0.1
DB_ENGINE=django.db.backends.postgresql
DB_NAME=foodgram_db
POSTGRES_USER=foodgram_user
POSTGRES_PASSWORD=foodgram_pass
DB_HOST=db
DB_PORT=5432
```

### 3️⃣ Настроить Secrets в GitHub
| Secret | Назначение |
|--------|-------------|
| `DOCKER_USERNAME` | Логин Docker Hub |
| `DOCKER_PASSWORD` | Пароль Docker Hub |
| `HOST` | IP или домен сервера |
| `USER` | Пользователь SSH |
| `SSH_KEY` | Приватный SSH-ключ |
| `SSH_PASSPHRASE` | Пароль к ключу (если есть) |
| `TELEGRAM_TO` | ID чата Telegram |
| `TELEGRAM_TOKEN` | Токен Telegram-бота |

### 4️⃣ Автоматический деплой (CI/CD)
После пуша в ветку `main`:
1. 🧹 Проверка кода линтером `flake8`
2. 🐳 Сборка Docker-образов:
   - `lesstalkrus/foodgram_backend:latest`
   - `lesstalkrus/foodgram_frontend:latest`
   - `lesstalkrus/foodgram_gateway:latest`
3. 📦 Публикация на Docker Hub  
4. 🚀 Автоматический деплой на сервер  
5. 🤖 Уведомление в Telegram об успешном обновлении

---

## 🧩 Структура контейнеров

| Контейнер | Назначение |
|------------|-------------|
| `backend` | Django REST API |
| `frontend` | React SPA |
| `db` | PostgreSQL |
| `gateway` | Nginx-прокси |

---

## 🧾 Команды для ручного деплоя
```bash
sudo docker compose -f docker-compose.production.yml pull
sudo docker compose -f docker-compose.production.yml down
sudo docker compose -f docker-compose.production.yml up -d
```

---

## 📄 Пример `.env.example`
```env
SECRET_KEY=your_django_secret_key
DEBUG=False
ALLOWED_HOSTS=your_domain.com,localhost,127.0.0.1
DB_ENGINE=django.db.backends.postgresql
DB_NAME=foodgram_db
POSTGRES_USER=foodgram_user
POSTGRES_PASSWORD=foodgram_pass
DB_HOST=db
DB_PORT=5432
```

---

## 📚 Примеры API-запросов

**Получить список рецептов**
```http
GET /api/recipes/
```

**Создать новый рецепт**
```http
POST /api/recipes/
Content-Type: application/json

{
  "name": "Паста Карбонара",
  "text": "Классический рецепт с беконом и сливками",
  "cooking_time": 25,
  "ingredients": [
    {"id": 1, "amount": 200},
    {"id": 5, "amount": 50}
  ],
  "tags": [1, 2],
  "image": "base64string"
}
```

**Добавить рецепт в избранное**
```http
POST /api/recipes/{id}/favorite/
```

**Скачать список покупок**
```http
GET /api/recipes/download_shopping_cart/
```

---

## 🌍 Доступ и документация

- **Главная страница:** https://your-domain.com  
- **Админ-панель:** https://your-domain.com/admin/  
- **Документация API:** `/api/docs/` или `/redoc/`

---

## 👨‍💻 Автор проекта

**LessTalkRus**  
🔗 GitHub: [https://github.com/LessTalkRus](https://github.com/LessTalkRus)  
📦 Репозиторий: [https://github.com/LessTalkRus/foodgram](https://github.com/LessTalkRus/foodgram)

---

## 📜 Лицензия

Проект распространяется под лицензией **MIT License**.  
Вы можете свободно использовать и модифицировать код при сохранении авторства.
