from django.contrib import admin
from .models import (Recipe, Ingredient, FavoriteRecipe,
                     ShoppingCart, Subscribe, RecipeIngredient)
from django.contrib.auth import get_user_model
from django.utils.safestring import mark_safe
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

User = get_user_model()

# Вместо пустого значения в админке будет отображена строка "Не задано"
admin.site.empty_value_display = 'Не задано'


# Модель Ingredient для вставки на страницу других моделей
class IngredientInline(admin.StackedInline):
    model = RecipeIngredient
    extra = 0
    fields = ('ingredient', 'amount')


class FavoriteRecipeInline(admin.TabularInline):
    model = FavoriteRecipe
    extra = 0


class ShoppingCartInline(admin.TabularInline):
    model = ShoppingCart
    extra = 0


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    # Поля, которые будут показаны на странице списка объектов
    list_display = (
        'id',
        'name',
        'author',
        'cooking_time',
        'get_ingredients_html',
        'get_image_html',
        'get_favorites_count'
    )
    # Поля, по которым можно искать
    search_fields = ('name', 'author__username')
    # Поля для фильтрации
    list_filter = ('author', 'pub_date')
    inlines = (IngredientInline, FavoriteRecipeInline, ShoppingCartInline)

    # Метод для получения общего числа добавлений рецепта в избранное
    @admin.display(description='В избранном')
    def get_favorites_count(self, recipe):
        return recipe.favoriterecipes.count()

    # Метод для отображения продуктов в HTML-формате
    @admin.display(description='Продукты')
    @mark_safe
    def get_ingredients_html(self, recipe):
        ingredients = recipe.recipe_ingredients.all()
        ingredients_list = ''.join(
            f'<li>{ingredient.ingredient.name} - {ingredient.amount} '
            f'{ingredient.ingredient.measurement_unit}</li>'
            for ingredient in ingredients
        )
        return f'<ul>{ingredients_list}</ul>'

    # Метод для отображения изображения в HTML-формате
    @admin.display(description='Картинка')
    @mark_safe
    def get_image_html(self, recipe):
        return f'<img src="{recipe.image.url}" style="max-height: 100px;"/>'


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'measurement_unit')
    search_fields = ('name', 'measurement_unit')
    list_filter = ('measurement_unit',)


@admin.register(FavoriteRecipe)
class FavoriteRecipeAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe')
    search_fields = ('user__username', 'recipe__name')


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe')
    search_fields = ('user__username', 'recipe__name')


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'date_joined')
    search_fields = ('username', 'email')
    list_filter = ('date_joined', 'is_staff')


admin.site.register(Subscribe)
