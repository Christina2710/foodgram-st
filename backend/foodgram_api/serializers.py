import base64
from django.core.files.base import ContentFile
from rest_framework import serializers
from rest_framework.exceptions import ValidationError, NotAuthenticated

from djoser.serializers import UserCreateSerializer, UserSerializer

from recipes.models import (
    User, Recipe, Ingredient, Subscribe, RecipeIngredient)


class CreateUserSerializer(UserCreateSerializer):
    class Meta:
        model = User
        fields = (
            'id',
            'email',
            'username',
            'first_name',
            'last_name',
            'password'
        )


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)
        return super().to_internal_value(data)


class MyUserSerializer(UserSerializer):
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

    def to_representation(self, instance):
        request = self.context.get('request')
        # Проверяем, есть ли запрос на `/me/`
        if 'me' in request.path:
            if not request.user.is_authenticated:
                raise NotAuthenticated(
                    'Учетные данные не были предоставлены.')

        # Возвращаем данные, если пользователь авторизован
        return super().to_representation(instance)

    def get_is_subscribed(self, obj):
        # Проверяем, подписан ли текущий пользователь на этого
        user = self.context['request'].user
        if user.is_authenticated:
            # Проверяет, есть ли подписка текущего пользователя на
            # пользователя obj, который обрабатывается сериализатором
            return user.subscriptions.filter(subscribed_to=obj).exists()
        return False


class AvatarSerializer(serializers.ModelSerializer):
    avatar = Base64ImageField(required=True)

    class Meta:
        model = User
        fields = ('avatar',)


class RecipeBasicSerializer(serializers.ModelSerializer):

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class UserDetailSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField(read_only=True)

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

    def get_is_subscribed(self, obj):
        user = self.context['request'].user
        if user.is_authenticated:
            return user.subscriptions.filter(subscribed_to=obj).exists()
        return False

    def get_recipes(self, obj):
        recipes_limit = self.context.get('recipes_limit')
        """Возвращает список рецептов пользователя, на которого подписались."""
        recipes = obj.recipes.all()
        if recipes_limit:
            recipes = recipes[:recipes_limit]
        return RecipeBasicSerializer(recipes, many=True).data

    def get_recipes_count(self, obj):
        """Возвращает количество рецептов пользователя."""
        return obj.recipes.count()

    def validate(self, data):
        # Получаем текущего пользователя из контекста запроса
        user = self.context['request'].user
        # Получаем пользователя, на которого создаётся подписка
        subscribed_to = data['subscribed_to']

        # Проверяем, что пользователь не подписывается на себя
        if user == subscribed_to:
            raise serializers.ValidationError(
                'Вы не можете подписаться на себя!'
            )

        # Проверяем, существует ли уже подписка
        if Subscribe.objects.filter(user=user, subscribed_to=subscribed_to).exists():
            raise serializers.ValidationError(
                'Вы уже подписаны на этого пользователя!'
            )
        # Если все проверки прошли успешно, возвращаем данные
        return data


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


class RecipeSerializer(serializers.ModelSerializer):
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    author = MyUserSerializer(read_only=True)
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
        read_only_fields = ('author', 'is_in_shopping_cart', 'is_favorited')

    def validate(self, data):
        """Проверка обязательных полей."""
        if 'recipe_ingredients' not in data:
            raise ValidationError(
                {'ingredients': 'Поле ingredients обязательно для заполнения.'})

        ingredients = data.get('recipe_ingredients', [])
        if not ingredients:
            raise ValidationError(
                {'ingredients': 'Необходимо указать хотя бы один ингредиент.'})

        ingredient_ids = [ingredient['id'] for ingredient in ingredients]
        if len(ingredient_ids) != len(set(ingredient_ids)):
            raise ValidationError(
                {'ingredients': 'Ингредиенты не должны повторяться.'})

        return data

    def create(self, validated_data):
        ingredients_data = validated_data.pop('recipe_ingredients')
        recipe = Recipe.objects.create(**validated_data)
        for ingredient_data in ingredients_data:
            RecipeIngredient.objects.create(
                recipe=recipe,
                ingredient=ingredient_data['id'],
                amount=ingredient_data['amount']
            )
        return recipe

    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop('recipe_ingredients')
        RecipeIngredient.objects.filter(recipe=instance).delete()
        for ingredient_data in ingredients_data:
            RecipeIngredient.objects.create(
                recipe=instance,
                ingredient=ingredient_data['id'],
                amount=ingredient_data['amount']
            )
        return super().update(instance, validated_data)

    def get_is_favorited(self, obj):
        user = self.context['request'].user
        if user.is_authenticated:
            return user.favorite_recipes.filter(recipe=obj).exists()
        return False

    def get_is_in_shopping_cart(self, obj):
        user = self.context['request'].user
        if user.is_authenticated:
            return user.shopping_cart.filter(recipe=obj).exists()
        return False
