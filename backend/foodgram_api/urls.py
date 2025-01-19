from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path

from rest_framework.routers import DefaultRouter

from . import views
from .views import (
    RecipeViewSet,
    IngredientViewSet,
    AvatarViewSet,
    FavoriteViewSet,
    ShoppingCartViewSet,
    SubscribeViewSet,
    SubscribtionListViewSet
)


router = DefaultRouter()
router.register(r'recipes', RecipeViewSet, basename='recipes')
router.register(r'ingredients', IngredientViewSet, basename='ingredients')

urlpatterns = [
    path('recipes/download_shopping_cart/', views.download_shopping_list),
    path('recipes/<int:recipe_id>/get-link/', views.get_link),
    path('users/subscriptions/',
         SubscribtionListViewSet.as_view({'get': 'list'})),
    # Подключаем все маршруты, сгенерированные DefaultRouter
    path('', include(router.urls)),
    path('users/me/avatar/',
         AvatarViewSet.as_view({'put': 'update', 'delete': 'destroy'})),
    path('recipes/<int:recipe_id>/favorite/',
         FavoriteViewSet.as_view({'post': 'create', 'delete': 'destroy'})),
    path('recipes/<int:recipe_id>/shopping_cart/',
         ShoppingCartViewSet.as_view({'post': 'create', 'delete': 'destroy'})),
    path('users/<int:user_id>/subscribe/',
         SubscribeViewSet.as_view({'post': 'create', 'delete': 'destroy'})),
    # Djoser создаст набор необходимых эндпоинтов.
    # базовые, для управления пользователями в Django:
    path('', include('djoser.urls')),
    # Работа с токенами
    path('auth/', include('djoser.urls.authtoken')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)
