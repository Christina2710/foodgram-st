# Foodgram Final Project

«Фудграм» — сайто, на котором пользователи будут публиковать свои рецепты, добавлять чужие рецепты в избранное и подписываться на публикации других авторов. Зарегистрированным пользователям также будет доступен сервис «Список покупок». Он позволит создавать список продуктов, которые нужно купить для приготовления выбранных блюд.

### Как запустить проект:

Клонировать репозиторий и перейти в него в командной строке:
```
git clone https://github.com/Christina2710/foodgram-st.git
```
Перейдите в директорию infra и создайте файл .env на примере .env.example.
```
cd infra
```
```
touch .env
```
Запустите проект с помощью
```
docker-compose up 
```
Выполните миграции
```
docker-compose exec backend python manage.py migrate 
```
Заполните базу данных ингредиентами
```
docker-compose exec backend python manage.py import_ingredients
```
[Интерфейс веб-приложения](http://localhost)
[Спецификация API](http://localhost/api/docs/)
[Администрирование](http://localhost/admin/)
