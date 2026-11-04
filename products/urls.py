from django.urls import path
from products import views

urlpatterns = [
    # Public Pages
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('service/', views.service, name='service'),
    path('menu/', views.menu, name='menu'),
    path('contact/', views.contact, name='contact'),
    path('testimonial/', views.testimonial, name='testimonial'),
    path('reservation/', views.reservation, name='reservation'),

    # Customer Authentication
    path('login/', views.login_view, name='login'),
    path('customer-login/', views.login_view, name='customer_login'),
    path('logout/', views.user_logout, name='logout'),
    path('signup/', views.signup, name='signup'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('resend-otp/', views.resend_otp, name='resend_otp'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('reset-password/', views.reset_password, name='reset_password'),

    # Admin Dashboard (Access via /admin/ or /dashboard/)
    path('admin/', views.dashboard, name='dashboard'),
    path('admin/login/', views.admin_login_view, name='admin_login_alias'),
    path('admin-login/', views.admin_login_view, name='admin_login'),
    path('admin-logout/', views.admin_logout, name='admin_logout'),

    # Admin Management Pages (Both /admin/ and /dashboard/ paths supported)
    path('admin/users/', views.users_page, name='admin_users_page'),
    path('admin/users/create-admin/', views.create_admin, name='admin_create_admin'),
    path('admin/users/toggle/<int:pk>/', views.toggle_user_status, name='admin_toggle_user_status'),
    path('admin/users/delete/<int:pk>/', views.delete_user, name='admin_delete_user'),
    path('admin/reservations/', views.reservations_page, name='admin_reservations_page'),
    path('admin/contacts/', views.contacts_page, name='admin_contacts_page'),

    # Backward-compatible Dashboard routes
    path('dashboard/', views.dashboard, name='legacy_dashboard'),
    path('dashboard/login/', views.admin_login_view, name='dashboard_login'),
    path('dashboard/users/', views.users_page, name='users_page'),
    path('dashboard/users/create-admin/', views.create_admin, name='create_admin'),
    path('dashboard/users/toggle/<int:pk>/', views.toggle_user_status, name='toggle_user_status'),
    path('dashboard/users/delete/<int:pk>/', views.delete_user, name='delete_user'),
    path('dashboard/reservations/', views.reservations_page, name='reservations_page'),
    path('dashboard/contacts/', views.contacts_page, name='contacts_page'),

    # Admin Reservation Details & Editing
    path('view-reservation/<int:pk>/', views.view_reservation, name='view_reservation'),
    path('edit-reservation/<int:pk>/', views.edit_reservation, name='edit_reservation'),
    path('delete-reservation/<int:pk>/', views.delete_reservation, name='delete_reservation'),

    # Admin Contact Inquiries
    path('view-contact/<int:pk>/', views.view_contact, name='view_contact'),
    path('edit-contact/<int:pk>/', views.edit_contact, name='edit_contact'),
    path('delete-contact/<int:pk>/', views.delete_contact, name='delete_contact'),

    # Admin Product Management
    path('products/add/', views.add_product, name='add_product'),
    path('products/', views.product_list, name='product_list'),
    path('products/edit/<int:pk>/', views.edit_product, name='edit_product'),
    path('products/delete/<int:pk>/', views.delete_product, name='delete_product'),
]
