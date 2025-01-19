from django.core.exceptions import PermissionDenied
from django.db.models import OuterRef, Exists
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import api_view
from rest_framework.pagination import (
    LimitOffsetPagination, PageNumberPagination)
from rest_framework.response import Response

from recipes.models import (
    Recipe,
    Ingredient,
    User,
    FavoriteRecipe,
    ShoppingCart,
    Subscribe,
    RecipeIngredient
)
from .serializers import (
    RecipeSerializer,
    IngredientSerializer,
    AvatarSerializer,
    RecipeBasicSerializer,
    UserDetailSerializer
)


@api_view(['GET'])
def download_shopping_list(request):
    if not request.user.is_authenticated:
        return HttpResponse(
            "Вы должны войти в систему, чтобы получить список покупок.",
            content_type="text/plain"
        )

    # Получаем все рецепты в корзине текущего пользователя
    cart_items = ShoppingCart.objects.filter(user=request.user)

    if not cart_items.exists():
        return HttpResponse(
            "Ваш список покупок пуст.",
            content_type="text/plain"
        )

    ingredients = {}

    # Получаем ингредиенты из всех рецептов в корзине
    for item in cart_items:
        recipe = item.recipe
        recipe_ingredients = RecipeIngredient.objects.filter(recipe=recipe)

        for recipe_ingredient in recipe_ingredients:
            ingredient = recipe_ingredient.ingredient
            amount = recipe_ingredient.amount

            # Если ингредиент уже есть в списке, суммируем количество
            if ingredient.name in ingredients:
                ingredients[ingredient.name] += amount
            else:
                ingredients[ingredient.name] = amount

    # Формируем текстовый файл со списком покупок
    shopping_list = "\n".join(
        f"{name} ({ingredient.measurement_unit}) — {amount}"
        for name, amount in ingredients.items()
        for ingredient in Ingredient.objects.filter(name=name)
    )

    # Создаём HTTP-ответ с файлом
    response = HttpResponse(
        shopping_list,
        content_type="text/plain"
    )

    response['Content-Disposition'] = (
        'attachment; '
        'filename="shopping_list.txt"'
    )

    return response


@api_view(['GET'])
def get_link(request, recipe_id):
    recipe = get_object_or_404(Recipe, id=recipe_id)
    # Преобразуем id в шестнадцатеричную строку
    short_id = format(recipe.id, 'x')
    # Получаем хост с текущего запроса
    host = request.get_host()
    # Формируем короткую ссылку
    short_link = f'{host}/s/{short_id}'
    return Response({'short-link': short_link}, status=status.HTTP_200_OK)


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    pagination_class = LimitOffsetPagination

    def get_queryset(self):
        user = self.request.user

        queryset = super().get_queryset()

        if user.is_authenticated:
            is_favorited = self.request.query_params.get('is_favorited')
            if is_favorited is not None:
                is_favorited = is_favorited in ['1', 'true', 'True']
                queryset = queryset.annotate(
                    favorited=Exists(
                        FavoriteRecipe.objects.filter(
                            user=user,
                            recipe=OuterRef('pk')
                        )
                    )
                ).filter(favorited=is_favorited)

            # Фильтрация по is_in_shopping_cart
            is_in_shopping_cart = self.request.query_params.get(
                'is_in_shopping_cart')
            if is_in_shopping_cart is not None:
                is_in_shopping_cart = is_in_shopping_cart in [
                    '1', 'true', 'True']
                queryset = queryset.annotate(
                    in_shopping_cart=Exists(
                        ShoppingCart.objects.filter(
                            user=user,
                            recipe=OuterRef('pk')
                        )
                    )
                ).filter(in_shopping_cart=is_in_shopping_cart)

        # Фильтрация по author
        author_param = self.request.query_params.get('author')
        if author_param:
            queryset = queryset.filter(author_id=author_param)

        return queryset

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def perform_update(self, serializer):
        # Проверяем, что пользователь - автор рецепта
        if serializer.instance.author != self.request.user:
            raise PermissionDenied('Изменение чужого контента запрещено!')
        # Если авторизация пройдена, вызываем стандартное обновление
        super(RecipeViewSet, self).perform_update(serializer)

    def perform_destroy(self, instance):
        if instance.author != self.request.user:
            raise PermissionDenied('Изменение чужого контента запрещено!')
        super(RecipeViewSet, self).perform_destroy(instance)


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    pagination_class = None

    def get_queryset(self):
        queryset = super().get_queryset()

        # Получаем параметр 'name' из запроса
        name_param = self.request.query_params.get('name', None)

        if name_param:
            # Фильтруем ингредиенты, чье имя начинается с 'name_param'
            queryset = queryset.filter(name__istartswith=name_param)

        return queryset


class AvatarViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = AvatarSerializer

    def get_object(self):
        # Возвращаем текущего авторизированного пользователя
        return self.request.user

    def update(self, request):
        user = self.get_object()
        serializer = AvatarSerializer(user, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request):
        user = self.get_object()
        user.avatar = None  # Удаляем аватар, обнуляя поле
        user.save()  # Сохраняем изменения в базе данных
        return Response(status=status.HTTP_204_NO_CONTENT)


class FavoriteViewSet(viewsets.ModelViewSet):
    queryset = FavoriteRecipe.objects.all()

    def create(self, request, recipe_id):
        recipe = get_object_or_404(Recipe, id=recipe_id)
        user = request.user
        if FavoriteRecipe.objects.filter(user=user, recipe=recipe).exists():
            return Response(
                {'error': 'Вы уже добавили данный рецепт в избранное!'},
                status=status.HTTP_400_BAD_REQUEST
            )
        FavoriteRecipe.objects.create(user=user, recipe=recipe)
        serializer = RecipeBasicSerializer(recipe)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def destroy(self, request, recipe_id):
        requested_recipe = get_object_or_404(Recipe, id=recipe_id)

        user = request.user

        if not user.favorite_recipes.filter(recipe_id=requested_recipe.id).exists():
            return Response(
                {'detail': 'Рецепт не был добавлен в избранное.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Если подписка существует, удаляем её
        favorite_recipe = get_object_or_404(
            user.favorite_recipes,
            recipe_id=recipe_id,
        )
        favorite_recipe.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ShoppingCartViewSet(viewsets.ModelViewSet):
    queryset = ShoppingCart.objects.all()

    def create(self, request, recipe_id):
        recipe = get_object_or_404(Recipe, id=recipe_id)
        user = request.user
        # Проверяем, есть ли уже запись в ShoppingCart
        if ShoppingCart.objects.filter(user=user, recipe=recipe).exists():
            return Response(
                {'error': 'Вы уже добавили данный рецепт в избранное!'},
                status=status.HTTP_400_BAD_REQUEST
            )
        ShoppingCart.objects.create(user=user, recipe=recipe)
        serializer = RecipeBasicSerializer(recipe)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def destroy(self, request, recipe_id):

        requested_recipe = get_object_or_404(Recipe, id=recipe_id)

        user = request.user

        # Проверяем, есть ли подписка на найденного пользователя
        if not user.shopping_cart.filter(
                recipe_id=requested_recipe.id).exists():
            return Response(
                {'detail': 'Рецепт не был добавлен в список покупок.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Если подписка существует, удаляем её
        shopping_cart_recipe = get_object_or_404(
            user.shopping_cart,
            recipe_id=recipe_id,
        )
        shopping_cart_recipe.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class RecipesLimitMixin:
    def get_recipes_limit(self, request):
        recipes_limit = request.GET.get('recipes_limit')
        try:
            return int(recipes_limit) if recipes_limit else None
        except ValueError:
            return None


class SubscribeViewSet(viewsets.ModelViewSet, RecipesLimitMixin):
    queryset = Subscribe.objects.all()

    def create(self, request, user_id):
        recipes_limit = self.get_recipes_limit(request)
        subscribed_to = get_object_or_404(
            User,
            id=self.kwargs['user_id'],
        )
        user = request.user

        if self.queryset.filter(user=user,
                                subscribed_to=subscribed_to).exists():
            return Response(
                {'error': 'Вы уже подписаны на этого пользователя!'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if user == subscribed_to:
            return Response(
                {'error': 'Вы не можете подписаться на себя!'},
                status=status.HTTP_400_BAD_REQUEST
            )
        Subscribe.objects.create(user=user, subscribed_to=subscribed_to)
        serializer = UserDetailSerializer(
            subscribed_to,
            context={'request': request, 'recipes_limit': recipes_limit}
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def destroy(self, request, user_id):

        requested_user = get_object_or_404(User, id=user_id)

        user = request.user

        # Проверяем, есть ли подписка на найденного пользователя
        if not user.subscriptions.filter(
                subscribed_to=requested_user).exists():
            return Response(
                {'detail': 'Подписка не существует.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Если подписка существует, удаляем её
        subscription = get_object_or_404(
            user.subscriptions,
            subscribed_to=requested_user,
        )
        subscription.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class SubscribtionListViewSet(viewsets.ModelViewSet, RecipesLimitMixin):
    queryset = Subscribe.objects.all()

    def list(self, request, *args, **kwargs):
        user = request.user

        subscriptions = user.subscriptions.all()
        users = [subscription.subscribed_to for subscription in subscriptions]

        # Параметры лимита рецептов
        recipes_limit = self.get_recipes_limit(request)

        # Пагинация пользователей
        paginator = PageNumberPagination()
        # По умолчанию 10 объектов на странице
        paginator.page_size = request.GET.get('limit', 10)
        paginated_users = paginator.paginate_queryset(users, request)

        serializer = UserDetailSerializer(
            paginated_users,
            context={'request': request, 'recipes_limit': recipes_limit},
            many=True
        )

        # Формируем ответ с пагинацией
        return paginator.get_paginated_response(serializer.data)
