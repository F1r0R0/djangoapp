"""DRF views."""
from __future__ import annotations

from datetime import date, timedelta

from django.contrib.auth import authenticate, login, logout
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from habits.api.serializers import (
    AchievementSerializer,
    HabitLogSerializer,
    HabitSerializer,
    InsightSerializer,
    LoginSerializer,
    RegisterSerializer,
    TagCategorySerializer,
    TagSerializer,
    UserAchievementSerializer,
    UserProfileSerializer,
)
from habits.models import (
    Achievement,
    Habit,
    HabitLog,
    Tag,
    TagCategory,
    UserAchievement,
    UserInsight,
    UserProfile,
)
from habits.services.analytics import (
    completion_rate_for_habit,
    habit_completed_count,
    habit_heatmap,
    habit_total_minutes,
    user_summary,
)
from habits.services.streak import habit_best_streak, habit_current_streak


# ---------------------------------------------------------------------------
# Auth.
# ---------------------------------------------------------------------------


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        login(request, user)
        return Response(UserProfileSerializer(user.profile).data, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(
            username=serializer.validated_data['username'],
            password=serializer.validated_data['password'],
        )
        if user is None:
            return Response({'detail': 'Неверный логин или пароль'}, status=status.HTTP_401_UNAUTHORIZED)
        login(request, user)
        return Response(UserProfileSerializer(user.profile).data)


class LogoutView(APIView):
    def post(self, request):
        logout(request)
        return Response({'detail': 'ok'})


class MeView(APIView):
    def get(self, request):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        return Response(UserProfileSerializer(profile).data)


# ---------------------------------------------------------------------------
# Habits & habit logs.
# ---------------------------------------------------------------------------


class HabitViewSet(viewsets.ModelViewSet):
    serializer_class = HabitSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Habit.objects.filter(user=self.request.user).prefetch_related('tags').select_related('schedule')

    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        habit = self.get_object()
        return Response({
            'completion_pct': completion_rate_for_habit(habit, days=30),
            'completion_pct_90': completion_rate_for_habit(habit, days=90),
            'total_minutes': habit_total_minutes(habit),
            'completed_count': habit_completed_count(habit),
            'current_streak': habit_current_streak(habit),
            'best_streak': habit_best_streak(habit),
            'heatmap': habit_heatmap(habit, days=90),
        })


class HabitLogViewSet(viewsets.ModelViewSet):
    serializer_class = HabitLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = HabitLog.objects.filter(user=self.request.user)
        habit_id = self.request.query_params.get('habit_id')
        if habit_id:
            qs = qs.filter(habit_id=habit_id)
        log_date = self.request.query_params.get('log_date')
        if log_date:
            qs = qs.filter(log_date=log_date)
        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


# ---------------------------------------------------------------------------
# Reference data.
# ---------------------------------------------------------------------------


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.select_related('activity_type').all()
    serializer_class = TagSerializer
    permission_classes = [IsAuthenticated]


class TagCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TagCategory.objects.all()
    serializer_class = TagCategorySerializer
    permission_classes = [IsAuthenticated]


class AchievementViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Achievement.objects.all()
    serializer_class = AchievementSerializer
    permission_classes = [IsAuthenticated]


# ---------------------------------------------------------------------------
# Aggregates.
# ---------------------------------------------------------------------------


class DashboardView(APIView):
    def get(self, request):
        today: date = timezone.localdate()
        habits = list(
            Habit.objects.filter(user=request.user, is_active=True).select_related('schedule').prefetch_related('tags')
        )
        logs_today = {
            log.habit_id: log
            for log in HabitLog.objects.filter(user=request.user, log_date=today)
        }
        items = []
        due_today = 0
        done_today = 0
        for habit in habits:
            schedule = getattr(habit, 'schedule', None)
            is_due = True if schedule is None else schedule.is_due_on(today)
            log = logs_today.get(habit.id)
            done = bool(log and log.status in {'done', 'partial'})
            if is_due:
                due_today += 1
            if done:
                done_today += 1
            items.append({
                'id': habit.id,
                'title': habit.title,
                'icon': habit.icon,
                'color': habit.color,
                'target_type': habit.target_type,
                'target_value': habit.target_value,
                'target_unit': habit.target_unit,
                'is_due_today': is_due,
                'is_done_today': done,
                'tags': [t.name for t in habit.tags.all()],
            })
        weekly_completion_rate = 0
        seven_days_ago = today - timedelta(days=6)
        weekly_logs = HabitLog.objects.filter(
            user=request.user, log_date__gte=seven_days_ago, log_date__lte=today
        )
        weekly_total = weekly_logs.count()
        weekly_done = weekly_logs.filter(status__in=['done', 'partial']).count()
        if weekly_total:
            weekly_completion_rate = int(100 * weekly_done / weekly_total)
        insights = list(
            UserInsight.objects.filter(user=request.user).order_by('-created_at')[:3].values(
                'id', 'insight_type', 'title', 'message', 'created_at'
            )
        )
        return Response({
            'today': today.isoformat(),
            'due_today': due_today,
            'done_today': done_today,
            'weekly_completion_rate': weekly_completion_rate,
            'habits': items,
            'insights': insights,
        })


class AnalyticsSummaryView(APIView):
    def get(self, request):
        period = request.query_params.get('period', 'week')
        days = {'week': 7, 'month': 30, 'year': 365}.get(period, 30)
        return Response(user_summary(request.user, days=days))


class UserAchievementsView(APIView):
    def get(self, request):
        unlocked = UserAchievement.objects.filter(user=request.user).select_related('achievement')
        unlocked_data = UserAchievementSerializer(unlocked, many=True).data
        all_a = Achievement.objects.all()
        all_data = AchievementSerializer(all_a, many=True).data
        return Response({'all': all_data, 'unlocked': unlocked_data})


class UserInsightsView(APIView):
    def get(self, request):
        qs = UserInsight.objects.filter(user=request.user).order_by('-created_at')[:20]
        return Response(InsightSerializer(qs, many=True).data)
