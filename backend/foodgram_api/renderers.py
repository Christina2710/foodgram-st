from datetime import datetime

# Заготовки для текста
SHOPPING_LIST_HEADER = "Список покупок (составлен: {date}):"
PRODUCT_ITEM = "{index}. {name} - {amount} {unit}"
RECIPE_LIST_HEADER = "Для следующих рецептов:"
RECIPE_ITEM = "- {recipe}"
EMPTY_LIST_MESSAGE = "Список покупок пуст."


def render_shopping_list(ingredients, recipes):
    """
    Рендерит список покупок в текстовом формате
    с датой, нумерацией и перечнем рецептов.
    """
    if not ingredients:
        return EMPTY_LIST_MESSAGE

    # Текущая дата
    date_now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Формируем отчет одной операцией
    return '\n'.join([
        # Заголовок списка покупок
        SHOPPING_LIST_HEADER.format(date=date_now),

        # Продукты с нумерацией
        *[
            PRODUCT_ITEM.format(
                index=i + 1,
                name=ingredient["name"].capitalize(),
                amount=ingredient["amount"],
                unit=ingredient["measurement_unit"]
            )
            for i, ingredient in enumerate(ingredients)
        ],

        # Заголовок рецептов, если они есть
        RECIPE_LIST_HEADER if recipes else '',

        # Список рецептов
        *[
            RECIPE_ITEM.format(recipe=recipe)
            for recipe in recipes
        ]
    ])
