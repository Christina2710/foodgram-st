from django.urls import include, path

from rest_framework.routers import DefaultRouter

from .views import RecipeViewSet, IngredientViewSet, CustomUserViewSet
from .views import recipe_redirect_view

router = DefaultRouter()
router.register(r'recipes', RecipeViewSet, basename='recipes')
router.register(r'ingredients', IngredientViewSet, basename='ingredients')
router.register(r'users', CustomUserViewSet, basename='users')

urlpatterns = [
    path('', include(router.urls)),
    path('auth/', include('djoser.urls.authtoken')),
    path('s/<int:recipe_id>/', recipe_redirect_view, name='recipe_redirect')
]
