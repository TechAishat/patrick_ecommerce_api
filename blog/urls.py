from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'categories', views.CategoryViewSet)
router.register(r'tags', views.TagViewSet)
router.register(r'posts', views.PostViewSet)
router.register(r'posts/(?P<post_id>\d+)/comments', views.CommentViewSet, basename='post-comments')

urlpatterns = [
    path('', include(router.urls)),
]