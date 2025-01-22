import json
from django.core.management.base import BaseCommand
from recipes.models import Ingredient


class Command(BaseCommand):
    help = 'Загрузка ингредиентов из JSON-файла'

    def handle(self, *args, **kwargs):
        try:
            with open(r'C:\Dev\foodgram-st\data\ingredients.json', encoding='utf-8') as file:
                data = json.load(file)

            # Получаем все существующие ингредиенты из базы
            existing_ingredients = Ingredient.objects.values(
                'name', 'measurement_unit')
            existing_ingredients_set = {
                (ing['name'], ing['measurement_unit']) for ing in existing_ingredients}

            # Список для новых ингредиентов
            ingredients_to_create = []

            for item in data:
                name = item['name']
                measurement_unit = item['measurement_unit']

                # Добавляем в список только те ингредиенты, которых нет в базе
                if (name, measurement_unit) not in existing_ingredients_set:
                    ingredient = Ingredient(
                        name=name,
                        measurement_unit=measurement_unit
                    )
                    ingredients_to_create.append(ingredient)

            # Массовое создание новых ингредиентов
            if ingredients_to_create:
                Ingredient.objects.bulk_create(ingredients_to_create)
                self.stdout.write(self.style.SUCCESS(
                    'Данные успешно загружены!'))
            else:
                self.stdout.write(self.style.SUCCESS(
                    'Нет новых данных для загрузки.'))

        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(
                "Файл ingredients.json не найден!"))
        except json.JSONDecodeError:
            self.stdout.write(self.style.ERROR("Ошибка в формате JSON!"))
        except KeyError as e:
            self.stdout.write(self.style.ERROR(
                f'Отсутствует обязательное поле: {str(e)}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Произошла ошибка: {str(e)}'))
