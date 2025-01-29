# core/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import CustomUserCreationForm, TenantForm, RoomForm
from .models import Maintenance, Bill, Room
from django.core.files.base import ContentFile
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Maintenance, Tenant
from .forms import MaintenanceRequestForm,AssignStaffForm,StaffMaintenanceUpdateForm
from django.utils import timezone

from .forms import BillForm, PaymentForm, ReportForm
from .models import Bill, Payment,Report
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Sum
from decimal import Decimal


from django.http import HttpResponse
import csv
from io import StringIO
from datetime import datetime, timedelta
from django.db.models import Count, Sum, Q

from django.db.models import F



def home(request):
    return render(request, 'core/home.html')

def register(request):
    if request.method == 'POST':
        user_form = CustomUserCreationForm(request.POST)
        tenant_form = TenantForm(request.POST, request.FILES)
        
        if user_form.is_valid() and tenant_form.is_valid():
            user = user_form.save()
            tenant = tenant_form.save(commit=False)
            tenant.user = user
            tenant.save()
            
            messages.success(request, 'Registration successful. Please login.')
            return redirect('login')
    else:
        user_form = CustomUserCreationForm()
        tenant_form = TenantForm()
    
    return render(request, 'core/register.html', {
        'user_form': user_form,
        'tenant_form': tenant_form
    })

def logout_view(request):
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('home')

@login_required
def dashboard(request):
    context = {}
    
    if request.user.user_type == 'TENANT':
        tenant = request.user.tenant
        context.update({
            'pending_bills': Bill.objects.filter(tenant=tenant, status='PENDING'),
            'maintenance_requests': Maintenance.objects.filter(tenant=tenant).order_by('-reported_date')[:5],
            'room': tenant.room
        })
    elif request.user.user_type == 'STAFF':
        context.update({
            'assigned_maintenance': Maintenance.objects.filter(
                assigned_to=request.user,
                status__in=['PENDING', 'IN_PROGRESS']
            )
        })
    elif request.user.user_type == 'ADMIN':
        context.update({
            'vacant_rooms': Room.objects.filter(is_occupied=False).count(),
            'pending_maintenance': Maintenance.objects.filter(status='PENDING').count(),
            'overdue_bills': Bill.objects.filter(status='OVERDUE').count()
        })
    
    return render(request, 'core/dashboard.html', context)


@login_required
def maintenance_list(request):
    context = {}
    
    if request.user.user_type == 'TENANT':
        maintenance_requests = Maintenance.objects.filter(
            tenant=request.user.tenant
        ).order_by('-reported_date')
    elif request.user.user_type == 'STAFF':
        maintenance_requests = Maintenance.objects.filter(
            assigned_to=request.user
        ).order_by('-reported_date')
    else:  # ADMIN
        maintenance_requests = Maintenance.objects.all().order_by('-reported_date')
    
    context['maintenance_requests'] = maintenance_requests
    return render(request, 'core/maintenance/list.html', context)

@login_required
def create_maintenance(request):
    if request.user.user_type != 'TENANT':
        messages.error(request, 'Only tenants can create maintenance requests.')
        return redirect('maintenance_list')
    
    # Check if tenant has an assigned room
    try:
        tenant = request.user.tenant
        if not tenant.room:
            messages.error(request, 'You must be assigned to a room to create maintenance requests.')
            return redirect('maintenance_list')
    except Tenant.DoesNotExist:
        messages.error(request, 'Tenant profile not found.')
        return redirect('maintenance_list')
    
    if request.method == 'POST':
        form = MaintenanceRequestForm(request.user, request.POST)
        if form.is_valid():
            maintenance = form.save(commit=False)
            maintenance.tenant = tenant
            maintenance.room = tenant.room
            maintenance.save()
            
            messages.success(request, 'Maintenance request submitted successfully.')
            return redirect('maintenance_list')
    else:
        form = MaintenanceRequestForm(request.user)
    
    return render(request, 'core/maintenance/create.html', {
        'form': form,
        'room': tenant.room
    })
@login_required
def maintenance_detail(request, request_id):
    maintenance_request = get_object_or_404(Maintenance, id=request_id)
    
    # Check permissions
    if request.user.user_type == 'TENANT' and maintenance_request.tenant.user != request.user:
        messages.error(request, 'You do not have permission to view this request.')
        return redirect('maintenance_list')
    
    return render(request, 'core/maintenance/detail.html', {
        'maintenance': maintenance_request
    })

@login_required
def update_maintenance(request, request_id):
    maintenance_request = get_object_or_404(Maintenance, id=request_id)
    
    # Only staff and admin can update status
    if request.user.user_type == 'TENANT':
        messages.error(request, 'Only staff can update maintenance requests.')
        return redirect('maintenance_detail', request_id=request_id)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        notes = request.POST.get('resolution_notes', '')
        
        if new_status in dict(Maintenance.STATUS_CHOICES):
            maintenance_request.status = new_status
            maintenance_request.resolution_notes = notes
            
            if new_status == 'COMPLETED':
                maintenance_request.resolved_date = timezone.now()
            
            maintenance_request.save()
            messages.success(request, 'Maintenance request updated successfully.')
        
        return redirect('maintenance_detail', request_id=request_id)
    
    return render(request, 'core/maintenance/update.html', {
        'maintenance': maintenance_request
    })




def is_admin(user):
    return user.is_authenticated and user.user_type == 'ADMIN'

@login_required
def bill_list(request):
    if request.user.user_type == 'TENANT':
        bills = Bill.objects.filter(tenant=request.user.tenant)
    else:
        bills = Bill.objects.all()
    
    return render(request, 'core/bills/list.html', {'bills': bills})

@login_required
def bill_detail(request, bill_id):
    bill = get_object_or_404(Bill, id=bill_id)
    
    # Check permissions
    if request.user.user_type == 'TENANT' and bill.tenant.user != request.user:
        messages.error(request, 'You do not have permission to view this bill.')
        return redirect('bill_list')
    
    payments = Payment.objects.filter(bill=bill)
    total_paid = payments.aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
    remaining_amount = bill.total_amount - total_paid
    
    return render(request, 'core/bills/detail.html', {
        'bill': bill,
        'payments': payments,
        'total_paid': total_paid,
        'remaining_amount': remaining_amount
    })

@user_passes_test(is_admin)
def create_bill(request):
    if request.method == 'POST':
        form = BillForm(request.POST)
        if form.is_valid():
            bill = form.save(commit=False)
            bill.status = 'PENDING'
            bill.save()
            messages.success(request, f'Bill created successfully for {bill.tenant.user.get_full_name()}')
            return redirect('bill_detail', bill_id=bill.id)
    else:
        form = BillForm()
    
    return render(request, 'core/bills/create.html', {'form': form})

@login_required
def make_payment(request, bill_id):
    bill = get_object_or_404(Bill, id=bill_id)
    
    # Only tenant can make payment
    if request.user.user_type != 'TENANT' or bill.tenant.user != request.user:
        messages.error(request, 'You do not have permission to make payments.')
        return redirect('bill_detail', bill_id=bill.id)
    
    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.bill = bill
            
            # Check if payment amount is valid
            total_paid = Payment.objects.filter(bill=bill).aggregate(
                Sum('amount'))['amount__sum'] or Decimal('0')
            remaining_amount = bill.total_amount - total_paid
            
            if payment.amount > remaining_amount:
                messages.error(request, 'Payment amount cannot exceed the remaining balance.')
                return render(request, 'core/bills/make_payment.html', {
                    'form': form, 
                    'bill': bill,
                    'remaining_amount': remaining_amount
                })
            
            payment.save()
            
            # Update bill status if fully paid
            if total_paid + payment.amount >= bill.total_amount:
                bill.status = 'PAID'
                bill.paid_date = timezone.now().date()
                bill.save()
            
            messages.success(request, 'Payment submitted successfully.')
            return redirect('bill_detail', bill_id=bill.id)
    else:
        form = PaymentForm()
    
    total_paid = Payment.objects.filter(bill=bill).aggregate(
        Sum('amount'))['amount__sum'] or Decimal('0')
    remaining_amount = bill.total_amount - total_paid
    
    return render(request, 'core/bills/make_payment.html', {
        'form': form,
        'bill': bill,
        'remaining_amount': remaining_amount
    })

@login_required
def payment_detail(request, payment_id):
    payment = get_object_or_404(Payment, id=payment_id)
    
    # Check permissions
    if request.user.user_type == 'TENANT' and payment.bill.tenant.user != request.user:
        messages.error(request, 'You do not have permission to view this payment.')
        return redirect('bill_list')
    
    return render(request, 'core/bills/payment_detail.html', {'payment': payment})



@login_required
def analytics_dashboard(request):
    # Get date ranges
    today = timezone.now().date()
    month_start = today.replace(day=1)
    last_month_start = (month_start - timedelta(days=1)).replace(day=1)
    
    context = {
        'total_rooms': Room.objects.count(),
        'occupied_rooms': Room.objects.filter(is_occupied=True).count(),
        'pending_maintenance': Maintenance.objects.filter(status='PENDING').count(),
        'overdue_bills': Bill.objects.filter(status='OVERDUE').count(),
        
        # Monthly statistics using annotated query
        'current_month_revenue': Bill.objects.filter(
            bill_date__gte=month_start
        ).aggregate(
            total=Sum(F('rent_amount') + F('electricity_amount') + 
                     F('water_amount') + F('other_charges'))
        )['total'] or 0,
        
        'last_month_revenue': Bill.objects.filter(
            bill_date__gte=last_month_start,
            bill_date__lt=month_start
        ).aggregate(
            total=Sum(F('rent_amount') + F('electricity_amount') + 
                     F('water_amount') + F('other_charges'))
        )['total'] or 0,
        
        'maintenance_by_status': Maintenance.objects.values(
            'status'
        ).annotate(count=Count('id')),
        
        'recent_payments': Payment.objects.select_related(
            'bill__tenant'
        ).order_by('-payment_date')[:5],
    }
    
    return render(request, 'core/analytics/dashboard.html', context)
@user_passes_test(is_admin)
def report_list(request):
    reports = Report.objects.all().order_by('-date_generated')
    return render(request, 'core/reports/list.html', {'reports': reports})

@user_passes_test(is_admin)
def generate_report(request):
    if request.method == 'POST':
        form = ReportForm(request.POST)
        if form.is_valid():
            report_type = form.cleaned_data['report_type']
            start_date = form.cleaned_data['date_range_start']
            end_date = form.cleaned_data['date_range_end']
            
            # Create CSV file
            csv_file = StringIO()
            writer = csv.writer(csv_file)
            
            if report_type == 'FINANCIAL':
                # Financial report headers
                writer.writerow(['Date', 'Tenant', 'Room', 'Bill Amount', 'Amount Paid', 'Status'])
                
                # Get bill data
                bills = Bill.objects.filter(
                    bill_date__range=[start_date, end_date]
                ).select_related('tenant', 'tenant__room')
                
                for bill in bills:
                    writer.writerow([
                        bill.bill_date.strftime('%Y-%m-%d'),
                        bill.tenant.user.get_full_name(),
                        bill.tenant.room.number,
                        bill.total_amount,
                        bill.payment_set.aggregate(total=Sum('amount'))['total'] or 0,
                        bill.status
                    ])
                    
            elif report_type == 'MAINTENANCE':
                # Maintenance report headers
                writer.writerow(['Date', 'Room', 'Issue Type', 'Priority', 'Status', 'Resolution Time'])
                
                maintenance_requests = Maintenance.objects.filter(
                    reported_date__range=[start_date, end_date]
                ).select_related('room', 'tenant')
                
                for request in maintenance_requests:
                    resolution_time = ''
                    if request.resolved_date:
                        resolution_time = (request.resolved_date - request.reported_date).days
                    
                    writer.writerow([
                        request.reported_date.strftime('%Y-%m-%d'),
                        request.room.number,
                        request.issue_type,
                        request.get_priority_display(),
                        request.get_status_display(),
                        f"{resolution_time} days" if resolution_time else 'Not resolved'
                    ])
                    
            elif report_type == 'OCCUPANCY':
                # Occupancy report headers
                writer.writerow(['Room Number', 'Status', 'Current Tenant', 'Lease Start', 'Lease End'])
                
                rooms = Room.objects.all().select_related('tenant')
                
                for room in rooms:
                    tenant = room.tenant_set.first()
                    writer.writerow([
                        room.number,
                        'Occupied' if room.is_occupied else 'Vacant',
                        tenant.user.get_full_name() if tenant else 'N/A',
                        tenant.lease_start.strftime('%Y-%m-%d') if tenant else 'N/A',
                        tenant.lease_end.strftime('%Y-%m-%d') if tenant else 'N/A'
                    ])
            
            # Create report record
            report = Report(
                title=form.cleaned_data['title'],
                report_type=report_type,
                date_range_start=start_date,
                date_range_end=end_date,
                generated_by=request.user
            )
            
            # Save CSV file
            report.file.save(
                f"{report_type.lower()}_{start_date}_{end_date}.csv",
                ContentFile(csv_file.getvalue().encode()),
                save=True
            )
            
            messages.success(request, 'Report generated successfully.')
            return redirect('report_detail', report_id=report.id)
    else:
        form = ReportForm()
    
    return render(request, 'core/reports/generate.html', {'form': form})

@user_passes_test(is_admin)
def report_detail(request, report_id):
    report = get_object_or_404(Report, id=report_id)
    return render(request, 'core/reports/detail.html', {'report': report})

@user_passes_test(is_admin)
def download_report(request, report_id):
    report = get_object_or_404(Report, id=report_id)
    response = HttpResponse(report.file, content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{report.file.name}"'
    return response


# core/views.py
@user_passes_test(is_admin)
def room_list(request):
    rooms = Room.objects.all()
    return render(request, 'core/rooms/list.html', {'rooms': rooms})

@user_passes_test(is_admin)
def assign_room(request, room_id):
    room = get_object_or_404(Room, id=room_id)
    
    if request.method == 'POST':
        tenant_id = request.POST.get('tenant')
        if tenant_id:
            try:
                tenant = Tenant.objects.get(id=tenant_id)
                # Clear previous room assignment if any
                if tenant.room:
                    tenant.room.is_occupied = False
                    tenant.room.save()
                
                # Assign new room
                tenant.room = room
                tenant.save()
                room.is_occupied = True
                room.save()
                
                messages.success(request, f'Room {room.number} assigned to {tenant.user.get_full_name()}')
            except Tenant.DoesNotExist:
                messages.error(request, 'Invalid tenant selected.')
        return redirect('room_list')
    
    # Get list of tenants without rooms
    available_tenants = Tenant.objects.filter(room__isnull=True)
    current_tenant = Tenant.objects.filter(room=room).first()
    
    return render(request, 'core/rooms/assign.html', {
        'room': room,
        'available_tenants': available_tenants,
        'current_tenant': current_tenant
    })


# core/views.py
@user_passes_test(is_admin)
def create_room(request):
    if request.method == 'POST':
        form = RoomForm(request.POST)
        if form.is_valid():
            room = form.save(commit=False)
            room.is_occupied = False
            room.save()
            messages.success(request, f'Room {room.number} created successfully.')
            return redirect('room_list')
    else:
        form = RoomForm()
    
    return render(request, 'core/rooms/create.html', {'form': form})

@user_passes_test(is_admin)
def edit_room(request, room_id):
    room = get_object_or_404(Room, id=room_id)
    
    if request.method == 'POST':
        form = RoomForm(request.POST, instance=room)
        if form.is_valid():
            form.save()
            messages.success(request, f'Room {room.number} updated successfully.')
            return redirect('room_list')
    else:
        form = RoomForm(instance=room)
    
    return render(request, 'core/rooms/edit.html', {'form': form, 'room': room})

@user_passes_test(is_admin)
def delete_room(request, room_id):
    room = get_object_or_404(Room, id=room_id)
    
    if request.method == 'POST':
        if room.is_occupied:
            messages.error(request, 'Cannot delete room while it is occupied.')
            return redirect('room_list')
            
        room_number = room.number
        room.delete()
        messages.success(request, f'Room {room_number} deleted successfully.')
        return redirect('room_list')
    
    return render(request, 'core/rooms/delete.html', {'room': room})


# core/views.py

@user_passes_test(lambda u: u.user_type == 'ADMIN')
def assign_maintenance(request, request_id):
    maintenance_request = get_object_or_404(Maintenance, id=request_id)
    
    if request.method == 'POST':
        form = AssignStaffForm(request.POST)
        if form.is_valid():
            staff = form.cleaned_data['staff']
            maintenance_request.assigned_to = staff
            maintenance_request.status = 'IN_PROGRESS'
            maintenance_request.save()
            
            messages.success(request, f'Request assigned to {staff.get_full_name()}')
            return redirect('maintenance_detail', request_id=request_id)
    else:
        form = AssignStaffForm()
    
    return render(request, 'core/maintenance/assign_staff.html', {
        'form': form,
        'maintenance': maintenance_request
    })

@login_required
def staff_update_maintenance(request, request_id):
    maintenance_request = get_object_or_404(Maintenance, id=request_id)
    
    # Check if the user is the assigned staff member
    if request.user.user_type != 'STAFF' or maintenance_request.assigned_to != request.user:
        messages.error(request, 'You are not authorized to update this request.')
        return redirect('maintenance_detail', request_id=request_id)
    
    if request.method == 'POST':
        form = StaffMaintenanceUpdateForm(request.POST, instance=maintenance_request)
        if form.is_valid():
            maintenance = form.save(commit=False)
            if maintenance.status == 'COMPLETED':
                maintenance.resolved_date = timezone.now()
            maintenance.save()
            
            messages.success(request, 'Maintenance request updated successfully.')
            return redirect('maintenance_detail', request_id=request_id)
    else:
        form = StaffMaintenanceUpdateForm(instance=maintenance_request)
    
    return render(request, 'core/maintenance/staff_update.html', {
        'form': form,
        'maintenance': maintenance_request
    })