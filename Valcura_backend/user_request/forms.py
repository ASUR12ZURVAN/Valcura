from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import HospitalUser, ClinicProfile


class HospitalRegistrationForm(forms.ModelForm):
    """Form for hospital/clinic registration"""
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Confirm Password', widget=forms.PasswordInput)
    
    class Meta:
        model = ClinicProfile
        fields = [
            'clinic_name', 'city', 'locality', 'clinic_type', 
            'chair_count', 'primary_specialty', 'monthly_revenue_baseline_inr',
            'reception_team_size', 'crm_status', 'crm_name', 'crm_integration_mode',
            'valcura_plan'
        ]
        widgets = {
            'monthly_revenue_baseline_inr': forms.NumberInput(attrs={'step': '0.01'}),
            'onboarding_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean_clinic_name(self):
        clinic_name = self.cleaned_data.get('clinic_name')
        if ClinicProfile.objects.filter(clinic_name__iexact=clinic_name).exists():
            raise forms.ValidationError('A clinic with this name already exists.')
        return clinic_name

    def save(self, commit=True):
        clinic = super().save(commit=False)
        # Generate clinic_id from clinic name
        clinic_id = clinic_name_to_id(clinic.clinic_name)
        clinic.clinic_id = clinic_id
        if commit:
            clinic.save()
        return clinic


class HospitalUserForm(forms.ModelForm):
    """Form for creating hospital user accounts"""
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Confirm Password', widget=forms.PasswordInput)
    
    class Meta:
        model = HospitalUser
        fields = ['username', 'email', 'first_name', 'last_name', 'phone_number', 'role', 'clinic']
        widgets = {
            'clinic': forms.Select(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-control'}),
        }

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
        return user


class ClinicProfileForm(forms.ModelForm):
    """Form for editing clinic profile"""
    
    class Meta:
        model = ClinicProfile
        fields = [
            'clinic_name', 'city', 'locality', 'clinic_type',
            'chair_count', 'primary_specialty', 'monthly_revenue_baseline_inr',
            'reception_team_size', 'crm_status', 'crm_name', 'crm_integration_mode',
            'valcura_plan', 'active_status'
        ]
        widgets = {
            'monthly_revenue_baseline_inr': forms.NumberInput(attrs={'step': '0.01'}),
        }


def clinic_name_to_id(clinic_name):
    """Generate a clinic ID from clinic name"""
    import re
    # Remove special characters and spaces, convert to uppercase
    clean_name = re.sub(r'[^a-zA-Z0-9]', '', clinic_name).upper()
    return f"CLN{clean_name[:10]}"
