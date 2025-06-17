from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsOwnerOrReadOnly(BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    Assumes the model instance has an 'owner', 'author', or 'guest' attribute.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        
        owner_attribute = None
        if hasattr(obj, 'owner'):
            owner_attribute = obj.owner
        elif hasattr(obj, 'author'):
            owner_attribute = obj.author
        elif hasattr(obj, 'guest'):
            owner_attribute = obj.guest

        return owner_attribute == request.user