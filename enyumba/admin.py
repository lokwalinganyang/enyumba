from django.contrib import admin
from .models import Landlord, Property, Report,Advertiser, Advertisement

@admin.register(Landlord)
class LandlordAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'is_verified', 'is_blocked', 'created_at')
    list_filter = ('is_verified', 'is_blocked')
    search_fields = ('name', 'phone')
    actions = ['verify_landlords', 'block_landlords']

    def verify_landlords(self, request, queryset):
        queryset.update(is_verified=True)
    verify_landlords.short_description = "Verify selected"

    def block_landlords(self, request, queryset):
        queryset.update(is_blocked=True)
@admin.register(Advertiser)
class AdvertiserAdmin(admin.ModelAdmin):
    list_display = ('business_name', 'phone', 'is_active', 'created_at')
    search_fields = ('business_name', 'phone')
    list_filter = ('is_active',)

@admin.register(Advertisement)
class AdvertisementAdmin(admin.ModelAdmin):
    list_display = ('title', 'advertiser', 'position', 'amount_paid', 'start_date', 'end_date', 'status')
    list_filter = ('position', 'status')
    search_fields = ('title', 'advertiser__business_name')
    actions = ['approve_ads', 'reject_ads']
    
    def approve_ads(self, request, queryset):
        queryset.update(status='active')
    approve_ads.short_description = "Approve selected ads"
    
    def reject_ads(self, request, queryset):
        queryset.update(status='rejected')
@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ('title', 'landlord', 'monthly_rent', 'house_type', 'is_approved', 'is_active', 'flag_count')
    list_filter = ('is_approved', 'is_active', 'house_type', 'has_tiles', 'has_water', 'has_hot_shower')
    search_fields = ('title', 'location_neighbourhood')
    actions = ['approve_listings', 'reject_listings']

    def approve_listings(self, request, queryset):
        queryset.update(is_approved=True, approved_by=request.user)
    approve_listings.short_description = "Approve"

    def reject_listings(self, request, queryset):
        queryset.update(is_approved=False)

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('property', 'reason', 'status', 'created_at')
    list_filter = ('status',)