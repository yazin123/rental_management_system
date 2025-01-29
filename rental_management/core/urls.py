# core/urls.py
from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
]

urlpatterns += [
    path('maintenance/', views.maintenance_list, name='maintenance_list'),
    path('maintenance/create/', views.create_maintenance, name='create_maintenance'),
    path('maintenance/<int:request_id>/', views.maintenance_detail, name='maintenance_detail'),
    path('maintenance/<int:request_id>/update/', views.update_maintenance, name='update_maintenance'),
]

urlpatterns += [
    path('bills/', views.bill_list, name='bill_list'),
    path('bills/<int:bill_id>/', views.bill_detail, name='bill_detail'),
    path('bills/create/', views.create_bill, name='create_bill'),
    path('bills/<int:bill_id>/pay/', views.make_payment, name='make_payment'),
    path('bills/payment/<int:payment_id>/', views.payment_detail, name='payment_detail'),
]

urlpatterns += [
    path('reports/', views.report_list, name='report_list'),
    path('reports/generate/', views.generate_report, name='generate_report'),
    path('reports/<int:report_id>/', views.report_detail, name='report_detail'),
    path('reports/download/<int:report_id>/', views.download_report, name='download_report'),
    path('analytics/', views.analytics_dashboard, name='analytics_dashboard'),
]
urlpatterns += [
    path('rooms/', views.room_list, name='room_list'),
    path('rooms/assign/<int:room_id>/', views.assign_room, name='assign_room'),
]

urlpatterns += [

    path('rooms/create/', views.create_room, name='create_room'),
    path('rooms/edit/<int:room_id>/', views.edit_room, name='edit_room'),
    path('rooms/delete/<int:room_id>/', views.delete_room, name='delete_room'),
]

urlpatterns += [
    path('maintenance/<int:request_id>/assign/', views.assign_maintenance, name='assign_maintenance'),
    path('maintenance/<int:request_id>/update-status/', views.staff_update_maintenance, name='staff_update_maintenance'),
]