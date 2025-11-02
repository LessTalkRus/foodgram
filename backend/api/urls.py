from django.urls import include, path
from rest_framework import routers

from .views import (
    IngredientViewSet, TagViewSet, RecipeViewSet,
    CustomUsersViewSet
)

app_name = 'api'

router = routers.DefaultRouter()
router.register('users', CustomUsersViewSet, basename='users')
router.register('tags', TagViewSet, basename='tags')
router.register('ingredients', IngredientViewSet, basename='ingredients')
router.register('recipes', RecipeViewSet, basename='recipes')


urlpatterns = [
    path('', include(router.urls)),
    path('', include('djoser.urls')),
    path('auth/', include('djoser.urls.authtoken')),
]
