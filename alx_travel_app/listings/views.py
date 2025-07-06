import requests
import uuid
import logging
from django.conf import settings
from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth import get_user_model
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAuthenticatedOrReadOnly
from rest_framework.decorators import action
from .models import Listing, Booking, Review, Payment
from .serializers import (
    UserSerializer,
    ListingSerializer,
    ListingDetailSerializer,
    BookingSerializer,
    ReviewSerializer,
    PaymentSerializer
    )
from .permissions import IsOwnerOrReadOnly

User = get_user_model()

logger = logging.getLogger(__name__)

# Chapa API Endpoints
CHAPA_INITIALIZE_URL = "https://api.chapa.co/v1/transaction/initialize"
CHAPA_VERIFY_URL = "https://api.chapa.co/v1/transaction/verify/"


class UserViewset(viewsets.ModelViewSet):
    """
    Simple viewset for viewing user accounts.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]


class ListingViewset(viewsets.ModelViewSet):
    # queryset = Listing.objects.all()
    queryset = Listing.objects.select_related('owner').prefetch_related('reviews')
    lookup_field = 'slug'

    def get_serializer_class(self):
        """
        Returns the appropriate serializer class based on the action.
        - 'ListingDetailSerializer' for retrieve (detail) view.
        - 'ListingSerializer' for all other actions (list, create, etc.).
        """
        if self.action == 'retrieve':
            return ListingDetailSerializer
        return ListingSerializer
    
    def get_permissions(self):
        """
        Assigns permission based on the action.
        - 'AllowAny' for safe methods (list, retrieve).
        - 'IsAuthenticated' and 'IsOwnerOrReadOnly' for other actions.
        """
        if self.action in ['list', 'retrieve']:
            permissions_classes = [AllowAny]
        else:
            permissions_classes = [IsAuthenticated, IsOwnerOrReadOnly]
        return [permission() for permission in permissions_classes]

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
        """Custom action to cancel a booking."""
        booking = self.get_object()
        if booking.status in [Booking.BookingStatus.PENDING, Booking.BookingStatus.CONFIRMED]:
            booking.status = Booking.BookingStatus.CANCELLED
            booking.save()
            # Return the updated booking data
            serializer = self.get_serializer(booking)
            # return Response({'status': 'Booking cancelled'}, status=status.HTTP_200_OK)
            return Response(serializer.data)
        
        return Response(
            {'error': f'Booking is already in "{booking.get_status_display()}" state and cannot be cancelled.'},
            status=status.HTTP_400_BAD_REQUEST
            )


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
        listing = Listing.objects.get(slug=self.kwargs['listing-slug'])
        serializer.save(author=self.request.user, listing=listing)


class PaymentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for handling payments
    """
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer

    def get_serializer_context(self):
        """Inject request into the serializer context."""
        return {'request': self.request}

    @action(detail=False, methods=['post'], url_path='initialize-payment')
    def initialize_payment(self, request):
        """
        Custom action to initialize a payment with Chapa.
        Expects 'booking_reference' and 'amount' in the request data.
        """
        logger.debug(request.data)
        booking_id = request.data.get('booking_reference')
        amount = request.data.get('amount')

        if not all([booking_id, amount]):
            return Response(
                {"error": "Booking ID and amount are required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # We assume the user is authenticated to get their details
            user = request.user
            if not user.is_authenticated:
                return Response(
                    {"error": "User authentication is required."},
                    status=status.HTTP_401_UNAUTHORIZED
                    )
            
            # 1. Creating a Payment record in our database
            booking = Booking.objects.get(id=booking_id)
            payment = Payment.objects.create(
                booking_reference=booking,
                amount=amount,
                payment_status=Payment.PaymentStatus.PENDING
            )

            # 2. Preparing the data for Chapa API
            # The trx_ref must be unique for each transaction.
            # We use the payment's UUID (transaction_id) for this.
            tx_ref = str(payment.transaction_id)

            # The callback URL is where Chapa will redirect the user after payment
            # It should point to our verification endpoint
            callback_url = request.build_absolute_uri(f'/api/payments/verify-payment/{tx_ref}/')

            headers = {
                "Authorization": f"Bearer {settings.CHAPA_SECRET_KEY}",
                "Content-Type": "application/json"
            }

            # Preparing the data for Chapa API
            data = {
                "amount": str(amount),
                "currency": "ETB",
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "tx_ref": tx_ref,
                "callback_url": callback_url,
                "return_url": "http://127.0.0.1:8000/api/payments/", # Optional: URL to redirect after success
                "customization[title]": "Payment for Booking",
                "customization[description]": f"Payment for booking reference: {booking.id}"
            }

            # 3. Send the request to Chapa
            response = requests.post(CHAPA_INITIALIZE_URL, json=data, headers=headers)
            
            # Handle potential request errors
            try:
                response.raise_for_status() # Raises an HTTPError for bad responses (4xx or 5xx)
                response_data = response.json()
            except requests.exceptions.RequestException as e:
                payment.payment_status = Payment.PaymentStatus.CANCELLED
                payment.save()
                return Response(
                    {"error": "Failed to connect to Chapa.", "details": str(e)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            except ValueError: # Catches JSON decoding errors
                return Response(
                    {"error": "Invalid response from Chapa."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                ) 

            if response.status_code == 200 and response_data.get("status") == "sucCess":
                # Return the checkout URL to the frontend
                return Response({
                    "message": "Payment initialized",
                    "checkout_url": response_data["data"]["checkout_url"]
                })
            else:
                # If chapa request fails, update payment status
                payment.payment_status = Payment.PaymentStatus.CANCELLED
                payment.save()
                return Response(
                    {"error": "Failed to initialize payment with Chapa.", "details": response_data},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except Booking.DoesNotExist:
            return Response(
                {"error": "Ivalid booking reference ID."},
                status=status.HTTP_404_NOT_FOUND
                )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
    @action(detail=False, methods=['get'], url_path='verify-payment/(?P<tx_ref>[^/.]+)')
    def verify_payment(self, request, tx_ref=None):
        """
        Custom action to verify a payment status with Chapa using the trx_ref.
        This endpoint is typically used as the callback URL.
        """
        headers = {
            "Authorization": f"Bearer {settings.CHAPA_SECRET_KEY}",
        }

        try:
            # 1.Send verfication request to Chapa
            response = requests.get(f"{CHAPA_VERIFY_URL}{tx_ref}", headers=headers)
            response.raise_for_status() # Always check for HTTP errors
            response_data = response.json()

            if response.status_code == 200:
                chapa_status = response_data.get("data", {}).get("status")

                # 2. Updating our Payment record based on the verification status
                payment = Payment.objects.get(transaction_id=tx_ref)

                if chapa_status == "success":
                    payment.payment_status = Payment.PaymentStatus.COMPLETED
                    payment.save()

                    # More logic to be added e.g. sending a confirmation email

                    return Response({
                        "status": "success",
                        "message": "Payment verified and completed successfully."
                    })
                else:
                    payment.payment_status = Payment.PaymentStatus.CANCELLED
                    payment.save()
                    return Response({
                        "status": "cancelled",
                        "message": "Payment was not successful."
                    }, status=status.HTTP_400_BAD_REQUEST)
                
        except Payment.DoesNotExist:
            return Response(
                {"error": "Payment record not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )