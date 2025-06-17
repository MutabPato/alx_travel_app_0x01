from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import Listing, Booking, Review


User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """
    User model serializer, exposes only essential fields
    """
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name']

class ReviewSerializer(serializers.ModelSerializer):
    """
    Review model serializer
    Includes author's details
    """
    author = UserSerializer(read_only=True)

    class Meta:
        model = Review
        fields = ['id', 'rating', 'comment', 'author', 'created_at']
        read_only_fields = ['author', 'created_at']


class ListingSerializer(serializers.ModelSerializer):
    """
    Listing model serializer, provides concise overview of each listing.
    """
    owner = UserSerializer(read_only=True)
    average_rating = serializers.SerializerMethodField()

    class Meta:
        model = Listing
        fields = ['id','name', 'description', 'location',
                  'price_per_night', 'is_available', 'owner', 'average_rating']

    def get_average_rating(self, obj):
        """
        Calculates average rating from all reviews for the listing.
        Returns none if no reviews.
        """
        from django.db.models import Avg
        average = obj.reviews.aggregate(Avg('rating')).get('rating__avg')
        if average is None:
            return None
        
        return round(average, 2)


class ListingDetailSerializer(serializers.ModelSerializer):
    """
    More detailed serializer for a single listing instance.
    Inherits from ListingSerializer and adds full description of nested reviews
    """
    review = ReviewSerializer(many=True, read_only=True)

    class Meta(ListingSerializer.Meta):
         fields = ListingSerializer.Meta.fields + ['description', 'reviews', 'created_at']


class BookingSerializer(serializers.ModelSerializer):
    """
    Booking model serializer
    Handles creation, data-validation and representation for booking-related operations
    """
    # Using nested serializers for read operations to provide richer context
    guest = UserSerializer(read_only=True)
    listing = ListingSerializer(read_only=True)

    # Using a write-only field to accept the listing's ID during creation.
    listing_id = serializers.PrimaryKeyRelatedField(
        queryset=Listing.objects.all(), source='listing', write_only=True
    )
    number_of_nights = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = ['id', 'listing', 'listing_id', 'guest','start_date' ,'end_date',
                  'number_of_guests', 'total_price', 'status', 'number_of_nights',
                  'created_at'
                  ]
        # total price and status should not be set directly by the user on creation
        read_only_fields = ['total_price', 'status', 'guest']

    def get_number_of_nights(self, obj):
        """Calculates number of nights for the booking"""
        return (obj.end_date - obj.start_date).days
    
    def validate(self, data):
        """
        Provides comprehensive validation for booking creation.
        1. Checks that start_date is not in the past.
        2. Checks that the listing is available for booking.
        3. Checks for booking conflicts with existing bookings.
        """
        listing = data.get('listing')
        start_date = data.get('start_date')
        end_date = data.get('end_date')

        if start_date < timezone.now().date():
            raise serializers.ValidationError("Booking cannot be made for a past date.")
        
        if not listing.is_available:
            raise serializers.ValidationError("This listing is not available for booking.")
        
        # Checking for overlapping bookings for the same listing
        conflicting_bookings = Booking.objects.filter(
            listing=listing,
            start_date__lt=end_date,
            end_date__gt=start_date,
            status__in=[Booking.BookingStatus.CONFIRMED, Booking.BookingStatus.PENDING]
        ).exists()

        if conflicting_bookings:
            raise serializers.ValidationError("These dates are already booked for this listing.")
        
        return data
    
    def create(self, validated_data):
        """
        Custom create method to handle booking creation logic
        - Sets the guest for the request context.
        - Calculates the toatl price.
        - Creates the booking instance.
        """
        listing = validated_data.get('listing')
        duration = (validated_data.get('end_date') - validated_data.get('start_date')).days

        total_price = listing.price_per_night * duration
        validated_data['total_price'] = total_price

        validated_data['guest'] = self.context['request'].user

        return super.create(validated_data)
