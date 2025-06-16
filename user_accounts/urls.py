from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'user_accounts'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='user_accounts:login'), name='logout'),
    path('profile/', views.profile, name='profile'),
    path('', views.user_list, name='user_list'),
    path('new/', views.user_new, name='user_new'),
    path('<int:pk>/', views.user_detail, name='user_detail'),
    path('<int:pk>/edit/', views.user_edit, name='user_edit'),
    path('<int:pk>/delete/', views.user_delete, name='user_delete'),
    path('<int:pk>/toggle-active/', views.user_toggle_active, name='user_toggle_active'),
]