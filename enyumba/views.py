import random
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.core.cache import cache
from django.db.models import Q
from django.conf import settings
from .models import Landlord, Property, Report, Advertisement
from .forms import LandlordForm, PropertyForm
from django.urls import reverse


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')

def landlord_start(request):
    if request.method == 'POST':
        form = LandlordForm(request.POST)
        if form.is_valid():
            request.session['landlord_data'] = {
                'name': form.cleaned_data['name'],
                'phone': form.cleaned_data['phone'],
                'alt_phone': form.cleaned_data['alt_phone'],
            }
            code = str(random.randint(100000, 999999))
            request.session['verification_code'] = code
            print(f"=== eNYUMBA VERIFICATION CODE for {form.cleaned_data['phone']}: {code} ===")
            messages.success(request, "Enter the 6‑digit code sent to your phone (simulated).")
            return redirect('enyumba:verify_phone')
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
            return redirect('enyumba:property_thanks')
    else:
        form = PropertyForm()
    return render(request, 'enyumba/add_property.html', {'form': form, 'landlord': landlord})
def ad_click(request, ad_id):
    ad = get_object_or_404(Advertisement, pk=ad_id, status='active')
    ad.clicks += 1
    ad.save()
    return redirect(ad.link_url)
def property_thanks(request, prop_id):
    prop = get_object_or_404(Property, id=prop_id)
    share_url = request.build_absolute_uri(reverse('enyumba:property_detail', args=[prop.id]))
    return render(request, 'enyumba/thanks.html', {'property': prop, 'share_url': share_url})

def search_properties(request):
    properties = Property.objects.filter(is_approved=True, is_active=True).order_by('-created_at')
    
    # Filters
    q = request.GET.get('q')
    house_type = request.GET.get('house_type')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    has_tiles = request.GET.get('has_tiles')
    has_water = request.GET.get('has_water')
    has_hot_shower = request.GET.get('has_hot_shower')
    has_internet = request.GET.get('has_internet')
    parking = request.GET.get('parking')
    
    if q:
        properties = properties.filter(
            Q(title__icontains=q) | Q(description__icontains=q) |
            Q(location_neighbourhood__icontains=q) | Q(location_landmark__icontains=q)
        )
    if house_type:
        properties = properties.filter(house_type=house_type)
    if min_price:
        properties = properties.filter(monthly_rent__gte=min_price)
    if max_price:
        properties = properties.filter(monthly_rent__lte=max_price)
    if has_tiles == 'yes':
        properties = properties.filter(has_tiles=True)
    if has_water == 'yes':
        properties = properties.filter(has_water=True)
    if has_hot_shower == 'yes':
        properties = properties.filter(has_hot_shower=True)
    if has_internet == 'yes':
        properties = properties.filter(has_internet=True)
    if parking == 'yes':
        properties = properties.filter(parking_capacity__gt=0)
    
    context = {
        'properties': properties,
        'filters': request.GET,
        'house_type_choices': Property.HOUSE_TYPES,
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
    
    context = {
        'property': prop,
        'share_url': share_url,
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