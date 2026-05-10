from django.urls import include, path
from rest_framework.routers import DefaultRouter

from habits.api import views


router = DefaultRouter()
router.register(r'habits', views.HabitViewSet, basename='habit')
router.register(r'habit-logs', views.HabitLogViewSet, basename='habit-log')
router.register(r'tags', views.TagViewSet, basename='tag')
router.register(r'tag-categories', views.TagCategoryViewSet, basename='tag-category')
router.register(r'achievements', views.AchievementViewSet, basename='achievement')


urlpatterns = [
    path('auth/register/', views.RegisterView.as_view(), name='api-register'),
    path('auth/login/', views.LoginView.as_view(), name='api-login'),
    path('auth/logout/', views.LogoutView.as_view(), name='api-logout'),
    path('auth/me/', views.MeView.as_view(), name='api-me'),
    path('dashboard/', views.DashboardView.as_view(), name='api-dashboard'),
    path('analytics/summary/', views.AnalyticsSummaryView.as_view(), name='api-analytics-summary'),
    path('achievements/me/', views.UserAchievementsView.as_view(), name='api-my-achievements'),
    path('insights/', views.UserInsightsView.as_view(), name='api-insights'),
    path('', include(router.urls)),
]
