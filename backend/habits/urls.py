from django.urls import path

from habits import views


urlpatterns = [
    path('', views.landing, name='landing'),
    path('accounts/login/', views.HHLoginView.as_view(), name='login'),
    path('accounts/logout/', views.HHLogoutView.as_view(), name='logout'),
    path('accounts/register/', views.register_view, name='register'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('calendar/', views.calendar_view, name='calendar'),
    path('habits/new/', views.habit_create, name='habit_create'),
    path('habits/<int:habit_id>/', views.habit_detail, name='habit_detail'),
    path('habits/<int:habit_id>/log/', views.habit_log_today, name='habit_log_today'),
    path('habits/<int:habit_id>/log/undo/', views.habit_log_undo, name='habit_log_undo'),
    path('habits/<int:habit_id>/delete/', views.habit_delete, name='habit_delete'),
    path('habits/<int:habit_id>/restore/', views.habit_restore, name='habit_restore'),
    path('habits/<int:habit_id>/destroy/', views.habit_destroy, name='habit_destroy'),
    path('habits/archive/', views.habit_archive_list, name='habit_archive'),
    path('analytics/', views.analytics, name='analytics'),
]
