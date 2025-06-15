from django.db import models
from uuid import uuid4


class Listing(models.Model):
    """
    class defining the listing model
    """
    # id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    name = models.Charfield(max_length=255)
    description = models.TextField(blank=True, null=True)
    location = models.Charfield(max_length=255)
    pricepernight = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "My Listing"
        verbose_name_plural = "My Listings"
        ordering = ['-created_at', 'pricepernight']

    def __str__(self):
        return self.name

class Booking(models.Model):
    """
    class defining the booking model
    """
    STATUS = [
        ('⏰', 'pending'),
        ('✅', 'confirmed'), 
         ('❌', 'cancelled'),
    ]
    listing_id = models.ForeignKey(Listing, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    total_price = models.FloatField()
    status = models.CharField(max_length=255, choices=STATUS)

class Review(models.Model):
    """
    class defining the review model
    """
    listing_id = models.ForeignKey(Listing, on_delete=models.CASCADE)
    rating = models.IntegerField()
    comment = models.TextField(blank=True, null=True)
