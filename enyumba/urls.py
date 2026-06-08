from django.urls import path
from . import views

app_name = 'enyumba'
urlpatterns = [
    path('', views.home, name='home'),                     # Homepage with categories
    path('search/', views.search_properties, name='search'),  # Search results page
    path('landlord/start/', views.landlord_start, name='landlord_start'),
    #path('landlord/verify/', views.verify_phone, name='verify_phone'),
    path('landlord/add/', views.add_property, name='add_property'),
    path('landlord/thanks/<int:prop_id>/', views.property_thanks, name='property_thanks'),
    path('property/<int:pk>/', views.property_detail, name='property_detail'),
    path('property/<int:pk>/report/', views.report_property, name='report_property'),
    path('ad/<int:ad_id>/click/', views.ad_click, name='ad_click'),
]