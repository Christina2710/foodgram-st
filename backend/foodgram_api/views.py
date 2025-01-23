from datetime import datetime
from io import BytesIO

from django.db.models import OuterRef, Exists, F, Sum
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.http import FileResponse

from rest_framework import status, viewsets
from rest_framework.pagination import (
    LimitOffsetPagination, PageNumberPagination)
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import (
    IsAuthenticated, IsAuthenticatedOrReadOnly)
from rest_framework.views import APIView

from djoser.views import UserViewSet

from recipes.models import (
    Recipe,
    Ingredient,
    FavoriteRecipe,
    ShoppingCart,
    Subscribe,
    RecipeIngredient
)

from .permissions import IsAuthorOrReadOnly
from .serializers import (
    RecipeSerializer,
    IngredientSerializer,
    AvatarSerializer,
    RecipeBasicSerializer,
    UserDetailSerializer,
    CustomUserSerializer
)

from .renderers import render_shopping_list


User = get_user_model()


class CustomUserViewSet(UserViewSet):
    queryset = User.objects.all()
    serializer_class = CustomUserSerializer

    @action(detail=False, methods=['put', 'delete'], url_path='me/avatar',
            permission_classes=[IsAuthenticated])
    def avatar(self, request):
        user = request.user
        if request.method == 'PUT':
            serializer = AvatarSerializer(user, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        user.avatar.delete(save=False)

        # Теперь обнуляем поле аватара в базе данных
        user.avatar = None
        user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=[IsAuthenticated])
    def subscribe(self, request, id):
        user = request.user
        author = get_object_or_404(User, id=id)

        if request.method == 'POST':
            if user == author:
                return Response(
                    {'error': 'Вы не можете подписаться на себя!'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            subscription, created = Subscribe.objects.get_or_create(
                user=user,
                author=author
            )

            if not created:
                return Response(
                    {'error': f'Вы уже подписаны на пользователя {author}!'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Если подписка была успешно создана
            serializer = UserDetailSerializer(
                author,
                context={'request': request}
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        get_object_or_404(
            Subscribe,
            user=user,
            author=author
        ).delete()
        return Response(
            {'success': 'Подписка удалена!'},
            status=status.HTTP_204_NO_CONTENT
        )

    @action(detail=False, methods=['get'],
            permission_classes=[IsAuthenticated])
    def subscriptions(self, request):
        user = request.user

        subscriptions = user.users.all()
        users = [subscription.author for subscription in subscriptions]

        # Пагинация пользователей
        paginator = PageNumberPagination()
        # По умолчанию 10 объектов на странице
        paginator.page_size = request.GET.get('limit', 10)
        paginated_users = paginator.paginate_queryset(users, request)

        return paginator.get_paginated_response(
            UserDetailSerializer(
                paginated_users,
                context={'request': request},
                many=True
            ).data
        )


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


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    pagination_class = LimitOffsetPagination
    permission_classes = (IsAuthorOrReadOnly, IsAuthenticatedOrReadOnly)

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

    @action(detail=False, permission_classes=[IsAuthenticated])
    def download_shopping_cart(self, request):
        user = request.user

        # Получаем список ингредиентов с сортировкой по названиям
        ingredients = RecipeIngredient.objects.filter(
            recipe__in=user.shoppingcarts.values('recipe')
        ).values(
            name=F('ingredient__name'),
            measurement_unit=F('ingredient__measurement_unit')
        ).annotate(
            amount=Sum('amount')
        ).order_by('name')  # Добавлена сортировка по названию ингредиента

        recipes = user.shoppingcarts.values_list('recipe__name', flat=True)

        # Используем функцию рендера для создания содержимого
        content = render_shopping_list(ingredients, recipes)

        # Создаем поток BytesIO для передачи файла
        buffer = BytesIO()
        buffer.write(content.encode('utf-8'))
        buffer.seek(0)

        # Возвращаем файл как ответ
        return FileResponse(
            buffer,
            as_attachment=True,
            filename=f'Shopping_cart_{datetime.now().strftime("%Y%m%d%H%M%S")}.txt'
        )

    @action(detail=True, methods=['get'], url_path='get-link')
    def get_link(self, request, pk=None):
        # Проверяем наличие записи с указанным ключом
        exists = Recipe.objects.filter(id=pk).exists()

        if not exists:
            return Response(
                {'detail': f'Рецепт {pk} не найден'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Формируем короткую ссылку с использованием имени маршрута
        short_link = request.build_absolute_uri(reverse(
            'recipe_redirect',
            kwargs={'recipe_id': pk})
        )

        return Response({'short-link': short_link})

    @staticmethod
    def add_to_collection(model_class, user, recipe, error_message):
        relation, created = model_class.objects.get_or_create(
            user=user,
            recipe=recipe
        )
        if not created:
            return Response(
                {'error': error_message.format(recipe=recipe)},
                status=status.HTTP_400_BAD_REQUEST
            )
        serializer = RecipeBasicSerializer(recipe)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @staticmethod
    def remove_from_collection(user, collection_name, recipe_id):

        get_object_or_404(
            getattr(user, collection_name), recipe_id=recipe_id).delete()

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def shopping_cart(self, request, pk):
        recipe = get_object_or_404(Recipe, id=pk)
        return self.add_to_collection(
            model_class=ShoppingCart,
            user=request.user,
            recipe=recipe,
            error_message='Вы уже добавили рецепт {recipe} в список покупок!'
        )

    @shopping_cart.mapping.delete
    def delete_shopping_cart(self, request, pk):
        user = request.user
        self.remove_from_collection(user, 'shoppingcarts', pk)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def favorite(self, request, pk):
        recipe = get_object_or_404(Recipe, id=pk)
        return self.add_to_collection(
            model_class=FavoriteRecipe,
            user=request.user,
            recipe=recipe,
            error_message='Вы уже добавили рецепт {recipe} в избранное!'
        )

    @favorite.mapping.delete
    def delete_favorite(self, request, pk):
        user = request.user
        self.remove_from_collection(user, 'favoriterecipes', pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


def recipe_redirect_view(request, recipe_id):
    # Проверяем, существует ли рецепт с указанным recipe_id
    recipe = get_object_or_404(Recipe, id=recipe_id)
    # Перенаправляем на детальную страницу рецепта
    return redirect(f'/recipes/{recipe.id}/')
