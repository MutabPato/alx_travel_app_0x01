from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth import get_user_model
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAuthenticatedOrReadOnly
from rest_framework.decorators import action
from .models import Listing, Booking, Review
from .serializers import (
    UserSerializer,
    ListingSerializer,
    ListingDetailSerializer,
    BookingSerializer,
    ReviewSerializer
    )
from .permissions import IsOwnerOrReadOnly

User = get_user_model()

class UserViewset(viewsets.ModelViewSet):
    """
    Simple viewset for viewing user accounts.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]


class ListingViewset(viewsets.ModelViewSet):
    queryset = Listing.objects.all()
    lookkup_field = 'slug'

    def get_serializer_class(self):
        """
        Returns the appropriate serializer class based on the action.
        - 'ListingDetailSerializer' for retrieve (detail) view.
        - 'ListingSerializer' for all other actions (list, create, etc.).
        """
        if self.action == 'retireve':
            return ListingDetailSerializer
        return ListingSerializer
    
    def get_permissions(self):
        """
        Assigns permission based on the action.
        - 'AllowAny' for safe methods (list, retrieve).
        - 'IsAuthenticated' and 'IsOwnerOrReadOnly' for other actions.
        """
        if self.action in ['list', 'retrieve']:
            self.permissions_classes = [AllowAny]
        else:
            self.permissions_classes = [IsAuthenticated, IsOwnerOrReadOnly]
        return super().get_permissions()

    def perform_create(self, serializer):
        """Sets the owner of the listing to the current authenticated user."""
        serializer.save(owner=self.request.user)


class BookingViewset(viewsets.ModelViewSet):
    """
    ViewSet for handling Bookings.
    - Users can only see their own bookings.
    - Users can create bookings.
    - Users can cancel their bookings.
    """
    serializer_class = BookingSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]

    def get_queryset(self):
        """This view returns a list of all the bookings for current authenticated user"""
        return Booking.objects.filter(guest=self.request.user)
    
    def perform_create(self, serializer):
        """Passes the request context to the serializer for validation and creation."""
        serializer.save(guest=self.request.user)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Custom action to cancel a ooking."""
        booking = self.get_object()
        if booking.status == Booking.BookingStatus.CONFIRMED:
            booking.status == Booking.BookingStatus.CANCELLED
            booking.save()
            return Response({'status': 'Booking cancelled'}, status=status.HTTP_200_OK)
        return Response({'error': 'Booking cannot be cancelled'}, status=status.HTT_400_BAD_REQUEST)


class ReviewViewSet(viewsets.ModelViewSet):
    """
    ViewSet for handling reviews for a specific listing.
    - 'api/listings/{slug}/reviews'
    """
    serializer_class = ReviewSerializer
    permission_class = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]

    def get_queryset(self):
        """Returns all reviews for a specific listing, identified by 'listing_slug' from the url."""
        return Review.objects.filter(listing__slug=self.kwargs['listing_slug'])
    
    def perform_create(self, serializer):
        """Creates a review and associates it with the listing from the url and the authenticated user."""
        listing = Listing.objects.get(slug=self.kwargs['listing<-slug'])
        serializer.save(author=self.request.user, listing=listing)