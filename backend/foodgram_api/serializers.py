import base64
from django.core.files.base import ContentFile
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from djoser.serializers import UserSerializer

from recipes.models import Recipe, Ingredient, RecipeIngredient

from django.contrib.auth import get_user_model

User = get_user_model()


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)
        return super().to_internal_value(data)


class CustomUserSerializer(UserSerializer):
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id',
            'email',
            'username',
            'first_name',
            'last_name',
            'avatar',
            'is_subscribed'
        )

    def get_is_subscribed(self, author):
        user = self.context['request'].user
        is_authenticated = user.is_authenticated
        is_subscribed = user.subscribed_to_users.filter(
            author=author).exists() if is_authenticated else False
        return is_authenticated and is_subscribed


class AvatarSerializer(serializers.ModelSerializer):
    avatar = Base64ImageField(required=True)

    class Meta:
        model = User
        fields = ('avatar',)


class RecipeBasicSerializer(serializers.ModelSerializer):

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')
        read_only_fields = ('id', 'name', 'image', 'cooking_time')


class UserDetailSerializer(CustomUserSerializer):
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(
        source='recipes.count',
        read_only=True
    )

    class Meta:
        model = User
        fields = (
            'id',
            'email',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'recipes',
            'recipes_count',
            'avatar',
        )

    def get_recipes(self, obj):
        return RecipeBasicSerializer(
            obj.recipes.all()[:int(
                self.context['request'].query_params.get(
                    'recipes_limit', 10**10
                )
            )],
            many=True
        ).data


class IngredientSerializer(serializers.ModelSerializer):

    class Meta:
        model = Ingredient
        fields = '__all__'


class RecipeIngredientSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(),
    )
    name = serializers.CharField(
        source='ingredient.name',
        read_only=True
    )
    measurement_unit = serializers.CharField(
        source='ingredient.measurement_unit',
        read_only=True
    )

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')

    def validate_measurement_unit(self, value):
        valid_units = ['г', 'шт', 'кг', 'мл', 'ст. л.', 'ч. л.', 'капля']
        if value not in valid_units:
            raise serializers.ValidationError(
                f"Единица измерения '{value}' недопустима.\n"
                f"Допустимые значения: {', '.join(valid_units)}."
            )
        return value


class RecipeSerializer(serializers.ModelSerializer):
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    author = CustomUserSerializer(read_only=True)
    ingredients = RecipeIngredientSerializer(
        source='recipe_ingredients',
        many=True,
        required=True
    )
    image = Base64ImageField(allow_null=True)

    class Meta:
        model = Recipe
        fields = (
            'id',
            'author',
            'ingredients',
            'is_favorited',
            'is_in_shopping_cart',
            'name',
            'image',
            'text',
            'cooking_time',
        )
        # Эти поля нельзя изменять через API
        read_only_fields = ('author', )

    def validate(self, data):
        if 'recipe_ingredients' not in data:
            raise ValidationError(
                {'ingredients': 'Поле ingredients обязательно для заполнения.'})

        ingredients = data.get('recipe_ingredients', [])
        if not ingredients:
            raise ValidationError(
                {'ingredients': 'Необходимо указать хотя бы один ингредиент.'})

        ingredient_ids = [ingredient['id'] for ingredient in ingredients]
        duplicate_ids = [
            ingredient_id for ingredient_id in set(ingredient_ids)
            if ingredient_ids.count(ingredient_id) > 1
        ]

        if duplicate_ids:
            raise ValidationError(
                {'ingredients': f'Ингредиенты не должны повторяться. '
                                f'Дубли: {", ".join(map(str, duplicate_ids))}'}
            )

        return data

    def validate_cooking_time(self, value):
        if value < 1:
            raise serializers.ValidationError(
                "Время приготовления должно быть не менее 1 минуты.")
        return value

    def save_recipe_ingredients(self, recipe, ingredients_data):

        # Удаляем старые ингредиенты
        RecipeIngredient.objects.filter(recipe=recipe).delete()

        # Создаем новые ингредиенты
        recipe_ingredients = [
            RecipeIngredient(
                recipe=recipe,
                ingredient=ingredient_data['id'],
                amount=ingredient_data['amount']
            )
            for ingredient_data in ingredients_data
        ]

        # Массовая вставка новых записей
        RecipeIngredient.objects.bulk_create(recipe_ingredients)

    def create(self, validated_data):
        ingredients_data = validated_data.pop('recipe_ingredients')

        # Создаем объект Recipe через базовый метод сериализатора
        recipe = super().create(validated_data)

        # Обрабатываем ингредиенты
        self.save_recipe_ingredients(recipe, ingredients_data)

        return recipe

    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop('recipe_ingredients')

        # Обрабатываем ингредиенты
        self.save_recipe_ingredients(instance, ingredients_data)

        # Обновляем основной объект
        return super().update(instance, validated_data)

    def get_is_favorited(self, recipe):
        user = self.context['request'].user
        is_authenticated = user.is_authenticated
        is_favorited = user.favoriterecipes.filter(
            recipe=recipe).exists() if is_authenticated else False
        return is_authenticated and is_favorited

    def get_is_in_shopping_cart(self, recipe):
        user = self.context['request'].user
        is_authenticated = user.is_authenticated
        is_favorited = user.shoppingcarts.filter(
            recipe=recipe).exists() if is_authenticated else False
        return is_authenticated and is_favorited
