from django import forms
from .models import Property, Landlord

class LandlordForm(forms.ModelForm):
    class Meta:
        model = Landlord
        fields = ['name', 'phone', 'alt_phone']

    def clean_phone(self):
        phone = self.cleaned_data['phone']
        if not phone.startswith('07') and not phone.startswith('01') and not phone.startswith('+254'):
            raise forms.ValidationError("Enter a valid Kenyan phone number")
        return phone

class PropertyForm(forms.ModelForm):
    class Meta:
        model = Property
        fields = [
            'title', 'description', 'house_type', 'monthly_rent',
            'location_neighbourhood', 'location_landmark',
            'has_tiles', 'has_water', 'water_source', 'water_schedule',
            'has_hot_shower', 'has_internet', 'parking_capacity',
            'electricity_billing', 'has_shop_room', 'extra_features',
            'image1', 'image2', 'image3', 'image4'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'extra_features': forms.Textarea(attrs={'rows': 3, 'placeholder': '✓ Large compound\n✓ Gaach\n✓ Security wall'}),
        }