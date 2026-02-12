from rest_framework import serializers
from .models import Post, Category, Tag, Comment
from django.contrib.auth import get_user_model

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']
        read_only_fields = ['id', 'username', 'email', 'first_name', 'last_name']
        ref_name = 'blog_User' 


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description']
        read_only_fields = ['id', 'slug']


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name', 'slug']
        read_only_fields = ['id', 'slug']


class CommentSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    
    class Meta:
        model = Comment
        fields = ['id', 'author', 'content', 'is_approved', 'created_at', 'updated_at']
        read_only_fields = ['id', 'author', 'created_at', 'updated_at']


class PostListSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    categories = CategorySerializer(many=True, read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    comment_count = serializers.SerializerMethodField()
    excerpt = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            'id', 'title', 'slug', 'excerpt', 'featured_image',
            'status', 'view_count', 'publish_date', 'author',
            'categories', 'tags', 'comment_count', 'created_at'
        ]
        read_only_fields = ['id', 'slug', 'view_count', 'created_at', 'author']

    def get_comment_count(self, obj):
        return obj.comments.filter(is_approved=True).count()
        
    def get_excerpt(self, obj):
        return obj.excerpt or (obj.content[:200] + '...' if len(obj.content) > 200 else obj.content)


class PostDetailSerializer(PostListSerializer):
    content = serializers.CharField()
    comments = CommentSerializer(many=True, read_only=True, source='approved_comments')

    class Meta(PostListSerializer.Meta):
        fields = PostListSerializer.Meta.fields + ['content', 'allow_comments', 'comments']


class PostCreateUpdateSerializer(serializers.ModelSerializer):
    categories = serializers.PrimaryKeyRelatedField(
        many=True, 
        queryset=Category.objects.all(),
        required=False
    )
    tags = serializers.SlugRelatedField(
        many=True,
        slug_field='name',
        queryset=Tag.objects.all(),
        required=False
    )

    class Meta:
        model = Post
        fields = [
            'title', 'content', 'excerpt', 'featured_image',
            'status', 'allow_comments', 'publish_date',
            'categories', 'tags'
        ]
        extra_kwargs = {
            'publish_date': {'required': False}
        }

    def create(self, validated_data):
        categories = validated_data.pop('categories', [])
        tags = validated_data.pop('tags', [])
        
        # Set the current user as the author
        validated_data['author'] = self.context['request'].user
        
        post = Post.objects.create(**validated_data)
        post.categories.set(categories)
        
        # Create tags that don't exist
        tag_objs = []
        for tag_name in tags:
            tag, created = Tag.objects.get_or_create(
                name=tag_name,
                defaults={'slug': tag_name.lower().replace(' ', '-')}
            )
            tag_objs.append(tag)
        post.tags.set(tag_objs)
        
        return post

    def update(self, instance, validated_data):
        categories = validated_data.pop('categories', None)
        tags = validated_data.pop('tags', None)
        
        # Update post fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        if categories is not None:
            instance.categories.set(categories)
            
        if tags is not None:
            # Create tags that don't exist
            tag_objs = []
            for tag_name in tags:
                tag, created = Tag.objects.get_or_create(
                    name=tag_name,
                    defaults={'slug': tag_name.lower().replace(' ', '-')}
                )
                tag_objs.append(tag)
            instance.tags.set(tag_objs)
        
        instance.save()
        return instance


class CommentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ['content']
        
    def create(self, validated_data):
        post_id = self.context['view'].kwargs.get('post_id')
        post = Post.objects.get(id=post_id)
        validated_data['post'] = post
        validated_data['author'] = self.context['request'].user
        return super().create(validated_data)


class CommentUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ['content', 'is_approved']
        read_only_fields = ['content']  # Only allow changing is_approved