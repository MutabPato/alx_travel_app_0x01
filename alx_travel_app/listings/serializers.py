from rest_framework import serializers
from .models import Listing, Booking, Review


class ListingSerializer(serializers.Serializer):
    class Meta:
        model = Listing
        fields = ['id','name', 'description', 'location',
                  'pricepernight']
        read_only_fields = ['created_at', 'updated_at']

class Bookingerializer(serializers.Serializer):
    number_of_nights = serializers.SerializermethodFielf()

    class Meta:
        model = Booking
        fields = ['id', 'listing_id' ,'start_date' ,'end_date',
                  'total_price', 'status']

    def get_number_of_nights(self, obj):
        dt = Booking.end_date - Booking.start_date
        nights = (dt.seconds / 60 / 60 / 24) - 1
        return nights
