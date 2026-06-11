import os
import random
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.db import connections
from django.db.models import Q, Case, When, Value, IntegerField
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.core.cache import cache
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from .models import Landlord, Property, Report, Advertisement, Location
from .forms import LandlordForm, PropertyForm
from .notifications import (
    notify_new_property, 
    notify_new_report, 
    notify_upgrade_request,
    notify_payment_confirmed
)


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')


def debug_info(request):
    User = get_user_model()
    data = {
        'database_engine': connections['default'].settings_dict['ENGINE'],
        'database_name': connections['default'].settings_dict['NAME'],
        'superuser_count': User.objects.filter(is_superuser=True).count(),
        'superuser_names': [u.username for u in User.objects.filter(is_superuser=True)],
        'debug_mode': settings.DEBUG,
        'database_url_set': bool(os.environ.get('DATABASE_URL')),
    }
    return JsonResponse(data)


def home(request):
    """Landing page with four main categories: Rent, Lease, Airbnb, Conference."""
    recent_rent = Property.objects.filter(
        is_approved=True, is_active=True, property_type='rent'
    ).order_by('-created_at')[:3]
    recent_lease = Property.objects.filter(
        is_approved=True, is_active=True, property_type='lease'
    ).order_by('-created_at')[:3]
    recent_airbnb = Property.objects.filter(
        is_approved=True, is_active=True, property_type='airbnb'
    ).order_by('-created_at')[:3]
    recent_conference = Property.objects.filter(
        is_approved=True, is_active=True, property_type='conference'
    ).order_by('-created_at')[:3]

    context = {
        'recent_rent': recent_rent,
        'recent_lease': recent_lease,
        'recent_airbnb': recent_airbnb,
        'recent_conference': recent_conference,
    }
    return render(request, 'enyumba/home.html', context)


def browse_by_location(request):
    """Browse properties by village/neighbourhood"""
    villages = Location.objects.filter(location_type='village', is_active=True)
    
    location_data = []
    for village in villages:
        property_count = Property.objects.filter(
            is_approved=True, 
            is_active=True,
            location_neighbourhood__icontains=village.name
        ).count()
        
        location_data.append({
            'id': village.id,
            'name': village.name,
            'description': village.description,
            'count': property_count,
            'has_properties': property_count > 0,
        })
    
    landmarks = Location.objects.filter(location_type='landmark', is_active=True)
    
    context = {
        'villages': location_data,
        'landmarks': landmarks,
        'total_villages': len(location_data),
        'villages_with_properties': sum(1 for v in location_data if v['has_properties']),
    }
    return render(request, 'enyumba/browse_locations.html', context)


def landlord_start(request):
    if request.method == 'POST':
        form = LandlordForm(request.POST)
        if form.is_valid():
            phone = form.cleaned_data['phone']
            name = form.cleaned_data['name']
            alt_phone = form.cleaned_data['alt_phone']
            
            landlord, created = Landlord.objects.get_or_create(
                phone=phone,
                defaults={'name': name, 'alt_phone': alt_phone, 'is_verified': True}
            )
            if not created and not landlord.is_verified:
                landlord.is_verified = True
                landlord.save()
            
            request.session['landlord_id'] = landlord.id
            messages.success(request, "Phone verified! Now list your property.")
            return redirect('enyumba:add_property')
    else:
        form = LandlordForm()
    return render(request, 'enyumba/landlord_start.html', {'form': form})


def verify_phone(request):
    if request.method == 'POST':
        entered = request.POST.get('code')
        expected = request.session.get('verification_code')
        if entered == expected:
            data = request.session.get('landlord_data')
            landlord, created = Landlord.objects.get_or_create(
                phone=data['phone'],
                defaults={'name': data['name'], 'alt_phone': data['alt_phone'], 'is_verified': True}
            )
            if not created and not landlord.is_verified:
                landlord.is_verified = True
                landlord.save()
            request.session['landlord_id'] = landlord.id
            del request.session['landlord_data']
            del request.session['verification_code']
            messages.success(request, "Phone verified! Now list your property.")
            return redirect('enyumba:add_property')
        else:
            messages.error(request, "Wrong code. Try again.")
    return render(request, 'enyumba/verify_phone.html')


def add_property(request):
    landlord_id = request.session.get('landlord_id')
    if not landlord_id:
        return redirect('enyumba:landlord_start')
    landlord = get_object_or_404(Landlord, id=landlord_id)
    
    if request.method == 'POST':
        form = PropertyForm(request.POST, request.FILES)
        if form.is_valid():
            prop = form.save(commit=False)
            prop.landlord = landlord
            prop.save()
            
            # Send notification to admin
            notify_new_property(prop)
            
            messages.success(request, "Property submitted! It will appear after admin approval.")
            del request.session['landlord_id']
            return redirect('enyumba:property_thanks', prop_id=prop.id)
    else:
        form = PropertyForm()
    
    context = {
        'form': form,
        'landlord': landlord,
        'villages': Location.objects.filter(location_type='village', is_active=True),
        'landmarks': Location.objects.filter(location_type='landmark', is_active=True),
    }
    return render(request, 'enyumba/add_property.html', context)


def property_thanks(request, prop_id):
    prop = get_object_or_404(Property, id=prop_id)
    share_url = request.build_absolute_uri(reverse('enyumba:property_detail', args=[prop.id]))
    return render(request, 'enyumba/thanks.html', {'property': prop, 'share_url': share_url})


def ad_click(request, ad_id):
    ad = get_object_or_404(Advertisement, pk=ad_id, status='active')
    ad.clicks += 1
    ad.save()
    return redirect(ad.link_url)


def upgrade_listing(request, property_id):
    """Allow landlord to upgrade their listing to a paid tier"""
    prop = get_object_or_404(Property, id=property_id)
    
    # Verify landlord owns this property
    landlord_id = request.session.get('landlord_id')
    if not landlord_id or prop.landlord.id != landlord_id:
        messages.error(request, "You don't have permission to upgrade this listing.")
        return redirect('enyumba:property_detail', pk=property_id)
    
    if request.method == 'POST':
        tier = request.POST.get('tier')
        
        # Prices mapping
        prices = {
            'standard': 100,
            'featured': 300,
            'premium': 500,
        }
        
        amount = prices.get(tier, 0)
        
        if tier == 'free':
            # Downgrade to free
            prop.listing_tier = 'free'
            prop.tier_expiry = None
            prop.save()
            messages.success(request, "Your listing has been downgraded to Free.")
            return redirect('enyumba:property_detail', pk=property_id)
        
        # Send upgrade request notification to admin
        notify_upgrade_request(prop, tier)
        
        # Generate unique transaction ID
        import uuid
        transaction_id = f"eNYUMBA-{prop.id}-{uuid.uuid4().hex[:8].upper()}"
        
        # Store payment intent in session
        request.session['pending_payment'] = {
            'property_id': prop.id,
            'tier': tier,
            'amount': amount,
            'transaction_id': transaction_id,
        }
        
        # For demo: auto-confirm payment (in production, integrate M-Pesa)
        # Remove this in production and use real M-Pesa callback
        if settings.DEBUG:
            return confirm_payment(request)
        
        return render(request, 'enyumba/payment_instructions.html', {
            'property': prop,
            'tier': tier,
            'amount': amount,
            'transaction_id': transaction_id,
            'paybill': 'eNyumba Paybill: 123456',
            'account_no': transaction_id,
        })
    
    context = {
        'property': prop,
        'current_tier': prop.listing_tier,
        'prices': {
            'standard': 100,
            'featured': 300,
            'premium': 500,
        },
    }
    return render(request, 'enyumba/upgrade_listing.html', context)


def confirm_payment(request):
    """Confirm payment and upgrade the listing"""
    payment_data = request.session.get('pending_payment')
    if not payment_data:
        messages.error(request, "No pending payment found.")
        return redirect('enyumba:search')
    
    prop = Property.objects.get(id=payment_data['property_id'])
    
    # Update property with paid tier
    prop.listing_tier = payment_data['tier']
    prop.tier_expiry = timezone.now() + timedelta(days=30)
    prop.payment_reference = payment_data['transaction_id']
    prop.payment_confirmed = True
    prop.promotion_start = timezone.now()
    prop.total_paid = (prop.total_paid or 0) + payment_data['amount']
    prop.save()
    
    # Send payment confirmation notification
    # Create a payment record first (you'll need to implement Payment model)
    # notify_payment_confirmed(payment_record)
    
    # Clear session
    del request.session['pending_payment']
    
    messages.success(request, f"Payment confirmed! Your listing is now {prop.listing_tier.upper()} for 30 days.")
    return redirect('enyumba:property_detail', pk=prop.id)


def search_properties(request):
    properties = Property.objects.filter(is_approved=True, is_active=True)

    # Expire any paid listings that have passed their expiry date
    for prop in properties.filter(listing_tier__in=['standard', 'featured', 'premium']):
        if prop.tier_expiry and prop.tier_expiry < timezone.now():
            prop.listing_tier = 'free'
            prop.save()

    # Property type filter
    property_type = request.GET.get('property_type')
    if property_type in ['rent', 'lease', 'airbnb', 'conference']:
        properties = properties.filter(property_type=property_type)

    # Location search
    location_q = request.GET.get('location_q')
    if location_q:
        properties = properties.filter(
            Q(location_neighbourhood__icontains=location_q) |
            Q(location_landmark__icontains=location_q) |
            Q(title__icontains=location_q)
        )

    # Text search
    q = request.GET.get('q')
    if q:
        properties = properties.filter(
            Q(title__icontains=q) | Q(description__icontains=q) |
            Q(location_neighbourhood__icontains=q) | Q(location_landmark__icontains=q)
        )

    # House type
    house_type = request.GET.get('house_type')
    if house_type:
        properties = properties.filter(property_type__in=['rent', 'lease', 'airbnb'], house_type=house_type)

    # Neighbourhood filter
    neighbourhood = request.GET.get('neighbourhood')
    if neighbourhood:
        properties = properties.filter(location_neighbourhood=neighbourhood)

    # Compound filters
    compound_only = request.GET.get('compound_only')
    if compound_only == 'yes':
        properties = properties.filter(property_type__in=['rent', 'lease'], is_in_compound=True)
    standalone_only = request.GET.get('standalone_only')
    if standalone_only == 'yes':
        properties = properties.filter(property_type__in=['rent', 'lease'], is_in_compound=False)

    # Furnished filter
    is_furnished = request.GET.get('is_furnished')
    if is_furnished == 'yes':
        properties = properties.filter(property_type='rent', is_furnished=True)

    # Price filtering
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    
    if min_price:
        min_price = int(min_price)
        price_filter = Q(
            Q(property_type='rent', monthly_rent__gte=min_price) |
            Q(property_type='lease', monthly_rent__gte=min_price) |
            Q(property_type='airbnb', nightly_rate__gte=min_price) |
            Q(property_type='conference', hourly_rate__gte=min_price)
        )
        properties = properties.filter(price_filter)
    if max_price:
        max_price = int(max_price)
        price_filter = Q(
            Q(property_type='rent', monthly_rent__lte=max_price) |
            Q(property_type='lease', monthly_rent__lte=max_price) |
            Q(property_type='airbnb', nightly_rate__lte=max_price) |
            Q(property_type='conference', hourly_rate__lte=max_price)
        )
        properties = properties.filter(price_filter)

    # Feature filters
    has_tiles = request.GET.get('has_tiles')
    if has_tiles == 'yes':
        properties = properties.filter(property_type__in=['rent', 'lease', 'airbnb'], has_tiles=True)

    has_terrazzo = request.GET.get('has_terrazzo')
    if has_terrazzo == 'yes':
        properties = properties.filter(property_type__in=['rent', 'lease', 'airbnb'], has_terrazzo=True)

    has_water = request.GET.get('has_water')
    if has_water == 'yes':
        properties = properties.filter(property_type__in=['rent', 'lease', 'airbnb'], has_water=True)

    has_hot_shower = request.GET.get('has_hot_shower')
    if has_hot_shower == 'yes':
        properties = properties.filter(property_type__in=['rent', 'lease', 'airbnb'], has_hot_shower=True)

    has_internet = request.GET.get('has_internet')
    if has_internet == 'yes':
        properties = properties.filter(property_type__in=['rent', 'lease', 'airbnb'], has_internet=True)

    parking = request.GET.get('parking')
    if parking == 'yes':
        properties = properties.filter(property_type__in=['rent', 'lease', 'airbnb'], parking_capacity__gt=0)

    # Airbnb specific filters
    bedrooms = request.GET.get('bedrooms')
    if bedrooms:
        properties = properties.filter(property_type='airbnb', bedrooms__gte=bedrooms)

    beds = request.GET.get('beds')
    if beds:
        properties = properties.filter(property_type='airbnb', beds__gte=beds)

    max_guests = request.GET.get('max_guests')
    if max_guests:
        properties = properties.filter(property_type='airbnb', max_guests__gte=max_guests)

    baths = request.GET.get('baths')
    if baths:
        properties = properties.filter(property_type='airbnb', baths__gte=baths)

    has_kitchen = request.GET.get('has_kitchen')
    if has_kitchen == 'yes':
        properties = properties.filter(property_type='airbnb', has_kitchen=True)

    has_tv = request.GET.get('has_tv')
    if has_tv == 'yes':
        properties = properties.filter(property_type='airbnb', has_tv=True)

    # Conference specific filters
    capacity_range = request.GET.get('capacity_range')
    if capacity_range:
        properties = properties.filter(property_type='conference', capacity_range=capacity_range)

    has_projector = request.GET.get('has_projector')
    if has_projector == 'yes':
        properties = properties.filter(property_type='conference', has_projector=True)

    has_sound_system = request.GET.get('has_sound_system')
    if has_sound_system == 'yes':
        properties = properties.filter(property_type='conference', has_sound_system=True)

    has_whiteboard = request.GET.get('has_whiteboard')
    if has_whiteboard == 'yes':
        properties = properties.filter(property_type='conference', has_whiteboard=True)

    catering_available = request.GET.get('catering_available')
    if catering_available == 'yes':
        properties = properties.filter(property_type='conference', catering_available=True)

    # Sort by priority tier (premium first, then featured, then standard, then free)
    tier_order = Case(
        When(listing_tier='premium', then=Value(1)),
        When(listing_tier='featured', then=Value(2)),
        When(listing_tier='standard', then=Value(3)),
        default=Value(4),
        output_field=IntegerField(),
    )
    
    properties = properties.annotate(
        tier_priority=tier_order
    ).order_by('tier_priority', '-created_at')

    # Add share URL to each property
    for prop in properties:
        prop.share_url = request.build_absolute_uri(reverse('enyumba:property_detail', args=[prop.id]))

    # Get distinct neighbourhoods
    neighbourhoods = Property.objects.filter(
        is_approved=True, is_active=True
    ).values_list('location_neighbourhood', flat=True).distinct()
    neighbourhoods = sorted([n for n in neighbourhoods if n])

    # Popular areas
    popular_areas = ['Nawoitorong', 'Jobag', 'Galilee', 'Kanamkemer', 'Lodwar Town', 'Kwa Governor', 'Harmony', 'Kambi Mpya']

    context = {
        'properties': properties,
        'filters': request.GET,
        'house_type_choices': Property.HOUSE_TYPES,
        'property_type_choices': Property.PROPERTY_TYPES,
        'capacity_range_choices': Property.CAPACITY_RANGES,
        'neighbourhoods': neighbourhoods,
        'popular_areas': popular_areas,
    }
    return render(request, 'enyumba/search.html', context)


def property_detail(request, pk):
    prop = get_object_or_404(Property, pk=pk, is_approved=True, is_active=True)
    share_url = request.build_absolute_uri(reverse('enyumba:property_detail', args=[prop.id]))

    show_contact = False
    contact_message = None
    ip = get_client_ip(request)
    cache_key = f'enyumba_contact_{ip}'
    reveal_count = cache.get(cache_key, 0)

    if request.GET.get('reveal') == '1':
        if reveal_count < settings.CONTACT_REVEAL_LIMIT:
            show_contact = True
            cache.set(cache_key, reveal_count + 1, timeout=settings.CONTACT_REVEAL_WINDOW)
        else:
            contact_message = "Daily contact limit reached. Try tomorrow."

    # Price display
    if prop.property_type in ['rent', 'lease']:
        price_display = f"KES {prop.monthly_rent}/month"
    elif prop.property_type == 'airbnb':
        price_display = f"KES {prop.nightly_rate}/night"
    else:
        price_display = f"KES {prop.hourly_rate}/hour" if prop.hourly_rate else "Contact for pricing"

    context = {
        'property': prop,
        'share_url': share_url,
        'price_display': price_display,
        'show_contact': show_contact,
        'contact_message': contact_message,
        'landlord_phone': prop.landlord.phone if show_contact else None,
        'landlord_alt_phone': prop.landlord.alt_phone if show_contact else None,
        'reveal_count': reveal_count,
        'reveal_limit': settings.CONTACT_REVEAL_LIMIT,
        'landlord_id': prop.landlord.id,
    }
    return render(request, 'enyumba/detail.html', context)


def report_property(request, pk):
    if request.method == 'POST':
        prop = get_object_or_404(Property, pk=pk)
        reason = request.POST.get('reason')
        ip = get_client_ip(request)
        report = Report.objects.create(property=prop, reporter_ip=ip, reason=reason)
        prop.flag_count += 1
        prop.save()
        
        # Send notification to admin
        notify_new_report(report)
        
        messages.success(request, "Thank you for reporting.")
        return redirect('enyumba:property_detail', pk=pk)
    return redirect('enyumba:property_detail', pk=pk)