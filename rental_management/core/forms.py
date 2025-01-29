# core/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, Tenant, Maintenance, Payment, Bill, Room
from .models import Bill, Payment, Report


class CustomUserCreationForm(UserCreationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email', 'phone', 'user_type', 'first_name', 'last_name')

class TenantForm(forms.ModelForm):
    class Meta:
        model = Tenant
        fields = ['emergency_contact', 'emergency_phone', 'lease_start', 'lease_end', 'documents']
        widgets = {
            'lease_start': forms.DateInput(attrs={'type': 'date'}),
            'lease_end': forms.DateInput(attrs={'type': 'date'}),
        }

class MaintenanceRequestForm(forms.ModelForm):
    class Meta:
        model = Maintenance
        fields = ['issue_type', 'description', 'priority']
        widgets = {
            'issue_type': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'priority': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if user and user.user_type == 'TENANT':
            self.tenant = user.tenant
            self.room = self.tenant.room

class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['amount', 'payment_method', 'transaction_id', 'notes']

class BillForm(forms.ModelForm):
    class Meta:
        model = Bill
        fields = ['tenant', 'bill_date', 'due_date', 'rent_amount', 
                 'electricity_amount', 'water_amount', 'other_charges']
        widgets = {
            'bill_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'due_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'rent_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'electricity_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'water_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'other_charges': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'tenant': forms.Select(attrs={'class': 'form-control'})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show tenants with assigned rooms
        self.fields['tenant'].queryset = Tenant.objects.filter(room__isnull=False)
        # Add rent amount data to tenant options
        self.fields['tenant'].choices = [
            (t.id, f"{t.user.get_full_name()} - Room {t.room.number}")
            for t in self.fields['tenant'].queryset
        ]

    def clean(self):
        cleaned_data = super().clean()
        bill_date = cleaned_data.get('bill_date')
        due_date = cleaned_data.get('due_date')

        if bill_date and due_date and due_date < bill_date:
            raise forms.ValidationError("Due date cannot be earlier than bill date")

        # Ensure amounts are non-negative
        for field in ['rent_amount', 'electricity_amount', 'water_amount', 'other_charges']:
            amount = cleaned_data.get(field)
            if amount and amount < 0:
                self.add_error(field, "Amount cannot be negative")

        return cleaned_data

class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['amount', 'payment_method', 'transaction_id', 'notes']
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'payment_method': forms.Select(attrs={'class': 'form-control'}),
            'transaction_id': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
        }

class ReportForm(forms.Form):
    report_type = forms.ChoiceField(
        choices=Report.REPORT_TYPES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    date_range_start = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    date_range_end = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    title = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )


class RoomForm(forms.ModelForm):
    class Meta:
        model = Room
        fields = ['number', 'floor', 'rent_amount', 'description']
        widgets = {
            'number': forms.TextInput(attrs={'class': 'form-control'}),
            'floor': forms.NumberInput(attrs={'class': 'form-control'}),
            'rent_amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class StaffMaintenanceUpdateForm(forms.ModelForm):
    class Meta:
        model = Maintenance
        fields = ['status', 'resolution_notes']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-control'}),
            'resolution_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class AssignStaffForm(forms.Form):
    staff = forms.ModelChoiceField(
        queryset=User.objects.filter(user_type='STAFF'),
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label="Select Staff Member"
    )