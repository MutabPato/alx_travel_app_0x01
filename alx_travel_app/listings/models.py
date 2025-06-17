from uuid import uuid4
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.text import slugify


User = get_user_model()


class Listing(models.Model):
    """
    Class representing a property listing
    """
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    owner = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='listings')
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=255)
    price_per_night = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "My Listing"
        verbose_name_plural = "My Listings"
        ordering = ['-created_at', 'price_per_night']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Booking(models.Model):
    """
    Class representing a booking made for a listing
    """
    class BookingStatus(models.TextChoices):
        PENDING = 'PENDING', 'pending'
        CONFIRMED = 'CONFIRMED', 'confirmed'
        CANCELLED = 'CANCELLED', 'cancelled'

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    listing = models.ForeignKey(
        Listing, on_delete=models.CASCADE, related_name='bookings')
    guest = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="bookings")
    start_date = models.DateField()
    end_date = models.DateField()
    number_of_guests = models.PositiveIntegerField(
        validators=[MinValueValidator(1)])
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=255, choices=BookingStatus.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Booking"
        verbose_name_plural = "Bookings"
        ordering = ['-created_at']
        constraints = [
            models.CheckConstraint(
                check=models.Q(end_date__gt=models.F('start_date')),
                name='end_date_after_start_date'
                )
        ]

    def __str__(self):
        return f"Booking for {self.listing.name} by {self.guest.username}"


class Review(models.Model):
    """
    Class representing a listing review
    """
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    listing = models.ForeignKey(
        Listing, on_delete=models.CASCADE, related_name="reviews")
    author = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='reviews')
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Review"
        verbose_name_plural = "Reviews"
        ordering = ['-created_at']
        unique_together = ('listing', 'author')  # Avoids duplicate entries

    def __str__(self):
        return f"Review for {self.listing.name} by {self.author.username}"
