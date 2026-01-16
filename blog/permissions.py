from rest_framework import permissions

class IsAuthorOrReadOnly(permissions.BasePermission):
    """
    Object-level permission to only allow authors of an object to edit it.
    Assumes the model instance has an `author` attribute.
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True

        # Instance must have an attribute named `author`.
        return obj.author == request.user


class IsBlogEditor(permissions.BasePermission):
    """
    Allows access only to blog editors and admins.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            (hasattr(request.user, 'is_blog_editor') and request.user.is_blog_editor) or
            request.user.is_staff
        )


class IsCommentAuthorOrEditor(permissions.BasePermission):
    """
    Permission to only allow comment author or blog editors to edit/delete comments.
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True

        # Only the comment author, blog editor, or admin can modify/delete
        return (
            obj.author == request.user or
            (hasattr(request.user, 'is_blog_editor') and request.user.is_blog_editor) or
            request.user.is_staff
        )