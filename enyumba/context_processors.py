from django.utils import timezone
from .models import Advertisement

def ads_context(request):
    now = timezone.now().date()
    ads = Advertisement.objects.filter(status='active', start_date__lte=now, end_date__gte=now)
    return {
        'global_ads': ads.filter(position='global'), 
        'sidebar_ads': ads.filter(position='sidebar'),
        'between_listings_ads': ads.filter(position='between_listings'),
        'footer_ads': ads.filter(position='footer'),
        'property_sidebar_ads': ads.filter(position='property_sidebar'),
    }