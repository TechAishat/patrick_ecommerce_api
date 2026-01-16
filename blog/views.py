from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from django.utils import timezone

from .models import Post, Category, Tag, Comment
from .serializers import (
    PostListSerializer, PostDetailSerializer, PostCreateUpdateSerializer,
    CategorySerializer, TagSerializer,
    CommentSerializer, CommentCreateSerializer, CommentUpdateSerializer
)
from .permissions import IsAuthorOrReadOnly, IsBlogEditor, IsCommentAuthorOrEditor


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated & (IsBlogEditor | IsAdminUser)]
    lookup_field = 'slug'
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'description']


class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [IsAuthenticated & (IsBlogEditor | IsAdminUser)]
    lookup_field = 'slug'
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']


class PostViewSet(viewsets.ModelViewSet):
    queryset = Post.objects.all()  # Add this line
    serializer_class = PostListSerializer
    permission_classes = [IsAuthenticated & (IsAuthorOrReadOnly | IsBlogEditor | IsAdminUser)]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'author', 'categories', 'tags']
    search_fields = ['title', 'content', 'excerpt']
    ordering_fields = ['publish_date', 'created_at', 'updated_at', 'view_count']
    ordering = ['-publish_date']

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # For non-authenticated users, only show published posts
        if not self.request.user.is_authenticated:
            queryset = queryset.filter(status='published', publish_date__lte=timezone.now())
        # For non-editor users, only show published posts or their own drafts
        elif not (hasattr(self.request.user, 'is_blog_editor') and self.request.user.is_blog_editor) and not self.request.user.is_staff:
            queryset = queryset.filter(
                Q(status='published', publish_date__lte=timezone.now()) | 
                Q(author=self.request.user, status='draft')
            )
        
        return queryset

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return PostDetailSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return PostCreateUpdateSerializer
        return super().get_serializer_class()

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        post = self.get_object()
        if post.status != 'published':
            post.status = 'published'
            if not post.publish_date:
                post.publish_date = timezone.now()
            post.save()
            return Response({'status': 'post published'})
        return Response({'status': 'post was already published'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def unpublish(self, request, pk=None):
        post = self.get_object()
        if post.status == 'published':
            post.status = 'draft'
            post.save()
            return Response({'status': 'post unpublished'})
        return Response({'status': 'post was not published'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def increment_views(self, request, pk=None):
        post = self.get_object()
        post.view_count += 1
        post.save(update_fields=['view_count'])
        return Response({'view_count': post.view_count})


class CommentViewSet(viewsets.ModelViewSet):
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated & (IsCommentAuthorOrEditor | IsBlogEditor | IsAdminUser)]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['post', 'author', 'is_approved']
    ordering_fields = ['created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        queryset = Comment.objects.all()
        
        # For non-authenticated users, only show approved comments
        if not self.request.user.is_authenticated:
            queryset = queryset.filter(is_approved=True)
        # For non-editor users, only show approved comments or their own
        elif not (hasattr(self.request.user, 'is_blog_editor') and self.request.user.is_blog_editor) and not self.request.user.is_staff:
            queryset = queryset.filter(
                Q(is_approved=True) | 
                Q(author=self.request.user)
            )
        
        return queryset

    def get_serializer_class(self):
        if self.action in ['create']:
            return CommentCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return CommentUpdateSerializer
        return super().get_serializer_class()

    def perform_create(self, serializer):
        post_id = self.kwargs.get('post_id')
        post = Post.objects.get(id=post_id)
        serializer.save(author=self.request.user, post=post)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        if not (hasattr(request.user, 'is_blog_editor') and request.user.is_blog_editor) and not request.user.is_staff:
            return Response(
                {'error': 'You do not have permission to perform this action.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        comment = self.get_object()
        comment.is_approved = True
        comment.save()
        return Response({'status': 'comment approved'})

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        if not (hasattr(request.user, 'is_blog_editor') and request.user.is_blog_editor) and not request.user.is_staff:
            return Response(
                {'error': 'You do not have permission to perform this action.'},
                status=status.HTTP_403_FORBIDDEN
            )  # Added missing closing parenthesis here
    
        comment = self.get_object()
        comment.is_approved = False
        comment.save()
        return Response({'status': 'comment rejected'})