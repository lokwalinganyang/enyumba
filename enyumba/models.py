from django.db import models
from django.contrib.auth.models import User

class Landlord(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15, unique=True)
    alt_phone = models.CharField(max_length=15, blank=True)
    is_verified = models.BooleanField(default=False)
    verification_code = models.CharField(max_length=6, blank=True)
    is_blocked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.phone})"

class Property(models.Model):
    HOUSE_TYPES = [
        ('bedsitter', 'Bedsitter'),
        ('1br', '1 Bedroom'),
        ('2br', '2 Bedroom'),
        ('3br', '3 Bedroom'),
        ('4br', '4+ Bedroom'),
    ]
    ELECTRICITY_CHOICES = [
        ('separate', 'Separate bill (prepaid/postpaid)'),
        ('included', 'Included in rent'),
        ('solar', 'Solar only'),
    ]
    WATER_SOURCE_CHOICES = [
        ('county', 'County supply'),
        ('borehole', 'Borehole'),
        ('tank', 'Raised tank'),
        ('truck', 'Water truck'),
    ]

    landlord = models.ForeignKey(Landlord, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField()
    house_type = models.CharField(max_length=20, choices=HOUSE_TYPES)
    monthly_rent = models.PositiveIntegerField()
    location_neighbourhood = models.CharField(max_length=100, blank=True)
    location_landmark = models.CharField(max_length=200, blank=True)
    
    # Features
    has_tiles = models.BooleanField(default=False)
    has_water = models.BooleanField(default=False)
    water_source = models.CharField(max_length=20, choices=WATER_SOURCE_CHOICES, blank=True)
    water_schedule = models.CharField(max_length=150, blank=True)
    has_hot_shower = models.BooleanField(default=False)
    has_internet = models.BooleanField(default=False)
    parking_capacity = models.PositiveSmallIntegerField(default=0)
    electricity_billing = models.CharField(max_length=20, choices=ELECTRICITY_CHOICES, default='separate')
    has_shop_room = models.BooleanField(default=False)
    extra_features = models.TextField(blank=True, help_text="One per line, e.g. ✓ Large compound")
    
    # Images
    image1 = models.ImageField(upload_to='enyumba/', blank=True)
    image2 = models.ImageField(upload_to='enyumba/', blank=True)
    image3 = models.ImageField(upload_to='enyumba/', blank=True)
    image4 = models.ImageField(upload_to='enyumba/', blank=True)
    
    # Admin
    is_approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    flag_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} - KES {self.monthly_rent}"


class Advertiser(models.Model):
    business_name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.business_name

class Advertisement(models.Model):
    POSITION_CHOICES = [
        ('global', 'Global - All pages (top or bottom)'),
        ('sidebar', 'Sidebar (search page)'),
        ('footer', 'Footer (all pages)'),
        ('between_listings', 'Between property listings'),
        ('home_top', 'Homepage top banner'),
        ('property_sidebar', 'Inside property detail page'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('rejected', 'Rejected'),
    ]
    
    advertiser = models.ForeignKey(Advertiser, on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='ads/', blank=True)  # banner image
    link_url = models.URLField(help_text="Where the ad clicks through (e.g., WhatsApp link, website)")
    
    position = models.CharField(max_length=50, choices=POSITION_CHOICES, default='sidebar')
    display_order = models.PositiveSmallIntegerField(default=0, help_text="Lower numbers show first")
    
    # Pricing & duration
    amount_paid = models.PositiveIntegerField(help_text="KES paid")
    start_date = models.DateField()
    end_date = models.DateField()
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    clicks = models.PositiveIntegerField(default=0)
    impressions = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.title} ({self.position})"

class Report(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE)
    reporter_ip = models.GenericIPAddressField()
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('resolved', 'Resolved'),
        ('dismissed', 'Dismissed'),
    ], default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    resolution_note = models.TextField(blank=True)

    def __str__(self):
        return f"Report on {self.property.title}"