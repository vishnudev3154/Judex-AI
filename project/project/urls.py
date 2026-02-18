from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from app import views  # Make sure 'app' is the name of your Django app

urlpatterns = [
    # ==============================
    # 1. CORE & AUTHENTICATION
    # ==============================
    path('admin/', admin.site.urls),  # Standard Django Admin
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('system/admin/login/', views.login_admin, name='login_admin'), # New Admin Login
    
    # Registration
    path('register/', views.register_client, name='register'), # Default register link
    path('register/client/', views.register_client, name='register_client'),
    path('register/lawyer/', views.register_lawyer, name='register_lawyer'),
    
    # Lawyer Specific Login
    path('lawyer-login/', views.login_lawyer, name='lawyer_login'),

    # ==============================
    # 2. CLIENT DASHBOARD & CASES
    # ==============================
    path('userpage/', views.user_dashboard, name='user_dashboard'),
    path('my-cases/', views.my_cases_view, name='my_cases'),
    # app/urls.py
    path('create-case/', views.create_case_view, name='create_case'),
    path('forward-case/', views.forward_case_to_lawyer, name='forward_case_to_lawyer'),
    
    
    # Case Analysis (AI Report)
    path('case-analysis/<int:case_id>/', views.case_analysis_view, name='case_analysis'),
    
    # Predictions
    path('predictions/', views.predictions_view, name='predictions'),

    # ==============================
    # 3. LAWYER DASHBOARD & ACTIONS
    # ==============================
    path('dashboard/lawyer/', views.lawyer_dashboard, name='lawyer_dashboard'),
    path('messages/', views.client_messages_view, name='client_messages'),
    
    # Lawyer Accept/Reject Case
    path('case/update/<int:case_id>/<str:status>/', views.update_case_status, name='update_case_status'),

    # ==============================
    # 4. HIRING & COMMUNICATION
    # ==============================
    path('find-lawyer/', views.find_lawyer, name='find_lawyer'),
    path('hire-lawyer/<int:lawyer_id>/', views.send_hiring_request, name='hire_lawyer'),
    
    # Chat between Client and Lawyer (Human Chat)
    path('case-chat/<int:case_id>/', views.case_chat_view, name='case_chat'),
    path('load-to-court/<int:case_id>/', views.load_client_case_to_court, name='load_client_case_to_court'),

    # ==============================
    # 5. AI FEATURES & VIRTUAL COURT
    # ==============================
    # AI Assistant Chat
    path('chat/', views.chat_view, name='chat'),
    path('chat/history/<int:session_id>/', views.get_chat_history, name='get_chat_history'),

    # Virtual Court (Specific Case ID required)
    path('virtual-court/<int:case_id>/', views.virtual_court_view, name='virtual_court_view'),
    
    # Generic Virtual Court (Optional: Enable if you want a demo mode without a specific case)
    path('virtual-court/', views.virtual_court, name='virtual_court'),
    path('api/chat/send/<int:case_id>/', views.api_send_case_message, name='api_send_case_message'),
    path('api/chat/get/<int:case_id>/', views.api_get_case_messages, name='api_get_case_messages'),
    path('share-transcript/<int:case_id>/', views.share_court_transcript, name='share_court_transcript'),
    # ==============================
    # 6. CUSTOM ADMIN DASHBOARD
    # ==============================
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('manage-users/', views.manage_users, name='manage_users'),
    path('toggle-user-status/<int:user_id>/', views.toggle_user_status, name='toggle_user_status'),
    path('all-cases/', views.all_cases_view, name='all_cases'),
    path('user-history/<int:user_id>/', views.view_user_history, name='view_user_history'),
]

# Media Files Configuration (For file uploads)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)