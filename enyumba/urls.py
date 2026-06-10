from django.urls import path
from . import views

app_name = 'enyumba'
urlpatterns = [
    # Home and search
    path('', views.home, name='home'),
    path('search/', views.search_properties, name='search'),
    path('locations/', views.browse_by_location, name='browse_locations'),
    
    # Landlord routes
    path('landlord/start/', views.landlord_start, name='landlord_start'),
    # path('landlord/verify/', views.verify_phone, name='verify_phone'),  # Commented out - SMS bypassed
    path('landlord/add/', views.add_property, name='add_property'),
    path('landlord/thanks/<int:prop_id>/', views.property_thanks, name='property_thanks'),
    
    # Property routes
    path('property/<int:pk>/', views.property_detail, name='property_detail'),
    path('property/<int:pk>/report/', views.report_property, name='report_property'),
    
    # Ad routes
    path('ad/<int:ad_id>/click/', views.ad_click, name='ad_click'),
    
    # Debug route (optional - remove in production)
    path('debug/', views.debug_info, name='debug_info'),
    path('property/<int:property_id>/upgrade/', views.upgrade_listing, name='upgrade_listing'),
path('payment/confirm/', views.confirm_payment, name='confirm_payment'),
]