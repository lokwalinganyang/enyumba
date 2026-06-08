import os
import random
from django.contrib.auth import get_user_model
from django.db import connections
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.core.cache import cache
from django.db.models import Q
from django.conf import settings
from django.urls import reverse
from .models import Landlord, Property, Report, Advertisement
from .forms import LandlordForm, PropertyForm


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
    """Landing page with three main categories: Lease, Airbnb, Conference."""
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
        'recent_lease': recent_lease,
        'recent_airbnb': recent_airbnb,
        'recent_conference': recent_conference,
    }
    return render(request, 'enyumba/home.html', context)


def landlord_start(request):
    if request.method == 'POST':
        form = LandlordForm(request.POST)
        if form.is_valid():
            phone = form.cleaned_data['phone']
            name = form.cleaned_data['name']
            alt_phone = form.cleaned_data['alt_phone']
            
            # Create or get landlord, mark as verified immediately
            landlord, created = Landlord.objects.get_or_create(
                phone=phone,
                defaults={'name': name, 'alt_phone': alt_phone, 'is_verified': True}
            )
            if not created and not landlord.is_verified:
                landlord.is_verified = True
                landlord.save()
            
            # Store landlord ID in session and redirect to add property
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
            messages.success(request, "Property submitted! It will appear after admin approval.")
            del request.session['landlord_id']
            return redirect('enyumba:property_thanks', prop_id=prop.id)
    else:
        form = PropertyForm()
    return render(request, 'enyumba/add_property.html', {'form': form, 'landlord': landlord})


def property_thanks(request, prop_id):
    prop = get_object_or_404(Property, id=prop_id)
    share_url = request.build_absolute_uri(reverse('enyumba:property_detail', args=[prop.id]))
    return render(request, 'enyumba/thanks.html', {'property': prop, 'share_url': share_url})


def ad_click(request, ad_id):
    ad = get_object_or_404(Advertisement, pk=ad_id, status='active')
    ad.clicks += 1
    ad.save()
    return redirect(ad.link_url)


def search_properties(request):
    properties = Property.objects.filter(is_approved=True, is_active=True).order_by('-created_at')

    # 1. Property type filter
    property_type = request.GET.get('property_type')
    if property_type in ['lease', 'airbnb', 'conference']:
        properties = properties.filter(property_type=property_type)

    # 2. Text search
    q = request.GET.get('q')
    if q:
        properties = properties.filter(
            Q(title__icontains=q) | Q(description__icontains=q) |
            Q(location_neighbourhood__icontains=q) | Q(location_landmark__icontains=q)
        )

    # 3. House type (only for lease/airbnb)
    house_type = request.GET.get('house_type')
    if house_type:
        properties = properties.filter(house_type=house_type)

    # 4. Neighbourhood filter (dropdown)
    neighbourhood = request.GET.get('neighbourhood')
    if neighbourhood:
        properties = properties.filter(location_neighbourhood=neighbourhood)

    # 5. Compound filter
    compound_only = request.GET.get('compound_only')
    if compound_only == 'yes':
        properties = properties.filter(is_in_compound=True)
    standalone_only = request.GET.get('standalone_only')
    if standalone_only == 'yes':
        properties = properties.filter(is_in_compound=False)

    # 6. Price filtering (type‑aware)
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    if min_price:
        min_price = int(min_price)
        price_filter = Q(
            Q(property_type='lease', monthly_rent__gte=min_price) |
            Q(property_type='airbnb', nightly_rate__gte=min_price) |
            Q(property_type='conference', hourly_rate__gte=min_price)
        )
        properties = properties.filter(price_filter)
    if max_price:
        max_price = int(max_price)
        price_filter = Q(
            Q(property_type='lease', monthly_rent__lte=max_price) |
            Q(property_type='airbnb', nightly_rate__lte=max_price) |
            Q(property_type='conference', hourly_rate__lte=max_price)
        )
        properties = properties.filter(price_filter)

    # 7. Feature filters (only for lease/airbnb)
    has_tiles = request.GET.get('has_tiles')
    if has_tiles == 'yes':
        properties = properties.filter(property_type__in=['lease', 'airbnb'], has_tiles=True)

    has_terrazzo = request.GET.get('has_terrazzo')
    if has_terrazzo == 'yes':
        properties = properties.filter(property_type__in=['lease', 'airbnb'], has_terrazzo=True)

    has_water = request.GET.get('has_water')
    if has_water == 'yes':
        properties = properties.filter(property_type__in=['lease', 'airbnb'], has_water=True)

    has_hot_shower = request.GET.get('has_hot_shower')
    if has_hot_shower == 'yes':
        properties = properties.filter(property_type__in=['lease', 'airbnb'], has_hot_shower=True)

    has_internet = request.GET.get('has_internet')
    if has_internet == 'yes':
        properties = properties.filter(property_type__in=['lease', 'airbnb'], has_internet=True)

    parking = request.GET.get('parking')
    if parking == 'yes':
        properties = properties.filter(property_type__in=['lease', 'airbnb'], parking_capacity__gt=0)

    # 8. Conference capacity range filter
    capacity_range = request.GET.get('capacity_range')
    if capacity_range:
        properties = properties.filter(property_type='conference', capacity_range=capacity_range)

    # 9. Add share URL to each property
    for prop in properties:
        prop.share_url = request.build_absolute_uri(reverse('enyumba:property_detail', args=[prop.id]))

    # Get distinct neighbourhoods for filter dropdown
    neighbourhoods = Property.objects.filter(
        is_approved=True, is_active=True
    ).values_list('location_neighbourhood', flat=True).distinct()
    neighbourhoods = sorted([n for n in neighbourhoods if n])

    context = {
        'properties': properties,
        'filters': request.GET,
        'house_type_choices': Property.HOUSE_TYPES,
        'property_type_choices': Property.PROPERTY_TYPES,
        'capacity_range_choices': Property.CAPACITY_RANGES,
        'neighbourhoods': neighbourhoods,
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
    if prop.property_type == 'lease':
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
    }
    return render(request, 'enyumba/detail.html', context)


def report_property(request, pk):
    if request.method == 'POST':
        prop = get_object_or_404(Property, pk=pk)
        reason = request.POST.get('reason')
        ip = get_client_ip(request)
        Report.objects.create(property=prop, reporter_ip=ip, reason=reason)
        prop.flag_count += 1
        prop.save()
        messages.success(request, "Thank you for reporting.")
        return redirect('enyumba:property_detail', pk=pk)
    return redirect('enyumba:property_detail', pk=pk)