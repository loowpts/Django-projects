# Django-projects

Учебные проекты на Django: каждый в своей папке, со своими настройками (`config/`),
приложениями (`apps/`) и `requirements.txt`.

![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django_5.1-092E20?logo=django&logoColor=white)
![DRF](https://img.shields.io/badge/DRF-A30000?logo=django&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?logo=postgresql&logoColor=white)
![Celery](https://img.shields.io/badge/Celery-37814A?logo=celery&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-DC382D?logo=redis&logoColor=white)

| Проект | Что это | Приложения |
|---|---|---|
| [prjctBlog](prjctBlog) | блог, есть Docker | `blog`, `users` |
| [PrjctEvent](PrjctEvent) | мероприятия и билеты | `events`, `tickets`, `chat`, `notifications`, `analytics`, `users` |
| [prjctSchool](prjctSchool) | онлайн-школа | `courses`, `enrollments`, `comments`, `dashboard`, `api`, `core`, `users` |
| [prjctShop](prjctShop) | интернет-магазин, есть Dockerfile, нужен PostgreSQL | `products`, `cart`, `orders`, `payments`, `reviews`, `main`, `users` |
| [prjctTodo](prjctTodo) | список задач | `todo`, `users` |

## Запуск проекта

```bash
git clone https://github.com/loowpts/Django-projects.git
cd Django-projects/<проект>
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # при необходимости поправить значения
python manage.py migrate
python manage.py runserver
```

prjctBlog можно поднять в Docker: `cp .env.example .env && docker compose up --build`.
