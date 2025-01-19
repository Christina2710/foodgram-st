from django.contrib import admin
from .models import (Recipe, Ingredient, FavoriteRecipe,
                     ShoppingCart, Subscribe, RecipeIngredient, User)

# Вместо пустого значения в админке будет отображена строка "Не задано"
admin.site.empty_value_display = 'Не задано'


class IngredientInline(admin.StackedInline):
    model = RecipeIngredient
    extra = 0
    fields = ('ingredient', 'amount')


# Модель Recipe для вставки на страницу других моделей
class RecipeInline(admin.StackedInline):
    model = Recipe
    extra = 0


class FavoriteRecipeInline(admin.TabularInline):
    model = FavoriteRecipe
    extra = 0


class ShoppingCartInline(admin.TabularInline):
    model = ShoppingCart


class RecipeAdmin(admin.ModelAdmin):
    # Поля, которые будут показаны на странице списка объектов
    list_display = ('name', 'author', 'get_favorites_count')
    # Поля, по которым можно искать
    search_fields = ('name', 'author__username')
    # Поля для фильтрации
    list_filter = ('author', 'pub_date')
    inlines = (IngredientInline, FavoriteRecipeInline, ShoppingCartInline)

    # Метод для получения общего числа добавлений рецепта в избранное
    @admin.display(description='Число добавлений в избранное')
    def get_favorites_count(self, obj):
        return obj.favorited_by.count()


class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'measurement_unit')
    search_fields = ('name',)


class FavoriteRecipeAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe')
    search_fields = ('user__username', 'recipe__name')


class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe')
    search_fields = ('user__username', 'recipe__name')


class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'date_joined')
    search_fields = ('username', 'email')
    list_filter = ('date_joined', 'is_staff')


# Регистрируем модели в админке
admin.site.register(Recipe, RecipeAdmin)
admin.site.register(Ingredient, IngredientAdmin)
admin.site.register(FavoriteRecipe, FavoriteRecipeAdmin)
admin.site.register(ShoppingCart, ShoppingCartAdmin)
admin.site.register(Subscribe)
admin.site.register(User, UserAdmin)
