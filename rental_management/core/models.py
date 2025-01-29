# core/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    USER_TYPE_CHOICES = [
        ('ADMIN', 'Admin'),
        ('STAFF', 'Staff'),
        ('TENANT', 'Tenant')
    ]
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES)
    phone = models.CharField(max_length=15, blank=True)

class Room(models.Model):
    number = models.CharField(max_length=10, unique=True)
    floor = models.IntegerField()
    rent_amount = models.DecimalField(max_digits=10, decimal_places=2)
    is_occupied = models.BooleanField(default=False)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"Room {self.number}"

class Tenant(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True, blank=True)
    emergency_contact = models.CharField(max_length=100)
    emergency_phone = models.CharField(max_length=15)
    lease_start = models.DateField()
    lease_end = models.DateField()
    documents = models.FileField(upload_to='tenant_documents/', blank=True)

    def __str__(self):
        return f"{self.user.get_full_name()} - Room {self.room.number if self.room else 'Not assigned'}"

class Bill(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PAID', 'Paid'),
        ('OVERDUE', 'Overdue')
    ]
    
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    bill_date = models.DateField()
    due_date = models.DateField()
    rent_amount = models.DecimalField(max_digits=10, decimal_places=2)
    electricity_amount = models.DecimalField(max_digits=10, decimal_places=2)
    water_amount = models.DecimalField(max_digits=10, decimal_places=2)
    other_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    paid_date = models.DateField(null=True, blank=True)
    
    @property
    def total_amount(self):
        return (self.rent_amount + self.electricity_amount + 
                self.water_amount + self.other_charges)
    

class Maintenance(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled')
    ]
    
    PRIORITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High')
    ]
    
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    issue_type = models.CharField(max_length=100)
    description = models.TextField()
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='MEDIUM')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    reported_date = models.DateTimeField(auto_now_add=True)
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    resolved_date = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True)

class Payment(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('CASH', 'Cash'),
        ('BANK_TRANSFER', 'Bank Transfer'),
        ('ONLINE', 'Online Payment')
    ]
    
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    transaction_id = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)

class Report(models.Model):
    REPORT_TYPES = [
        ('FINANCIAL', 'Financial Report'),
        ('MAINTENANCE', 'Maintenance Report'),
        ('OCCUPANCY', 'Occupancy Report')
    ]
    
    title = models.CharField(max_length=200)
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES)
    date_generated = models.DateTimeField(auto_now_add=True)
    date_range_start = models.DateField()
    date_range_end = models.DateField()
    generated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    file = models.FileField(upload_to='reports/')