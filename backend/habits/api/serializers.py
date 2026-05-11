"""DRF serializers."""
from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from habits.models import (
    Achievement,
    Habit,
    HabitLog,
    HabitSchedule,
    Tag,
    TagCategory,
    UserAchievement,
    UserInsight,
    UserProfile,
)


User = get_user_model()


class TagSerializer(serializers.ModelSerializer):
    activity_type = serializers.StringRelatedField()

    class Meta:
        model = Tag
        fields = ['id', 'name', 'slug', 'activity_type', 'hint']


class TagCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = TagCategory
        fields = ['id', 'name', 'slug', 'parent']


class HabitScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = HabitSchedule
        fields = [
            'frequency_type',
            'days_of_week',
            'times_per_period',
            'reminder_time',
            'window_start',
            'window_end',
            'start_date',
            'end_date',
        ]


class HabitSerializer(serializers.ModelSerializer):
    schedule = HabitScheduleSerializer(required=False)
    tag_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Tag.objects.all(), source='tags', required=False, write_only=True
    )
    tags = TagSerializer(many=True, read_only=True)

    class Meta:
        model = Habit
        fields = [
            'id',
            'title',
            'description',
            'target_type',
            'target_value',
            'target_unit',
            'color',
            'icon',
            'tags',
            'tag_ids',
            'is_active',
            'created_at',
            'schedule',
        ]
        read_only_fields = ['created_at']

    def create(self, validated_data):
        schedule_data = validated_data.pop('schedule', None) or {}
        tags = validated_data.pop('tags', [])
        request = self.context['request']
        habit = Habit.objects.create(user=request.user, **validated_data)
        if tags:
            habit.tags.set(tags)
        HabitSchedule.objects.create(habit=habit, **schedule_data)
        return habit

    def update(self, instance, validated_data):
        schedule_data = validated_data.pop('schedule', None)
        tags = validated_data.pop('tags', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if tags is not None:
            instance.tags.set(tags)
        if schedule_data is not None:
            schedule, _ = HabitSchedule.objects.get_or_create(habit=instance)
            for attr, value in schedule_data.items():
                setattr(schedule, attr, value)
            schedule.save()
        return instance


class HabitLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = HabitLog
        fields = [
            'id',
            'habit',
            'log_date',
            'status',
            'value',
            'duration_minutes',
            'note',
            'mood_score',
        ]

    def validate_habit(self, habit: Habit) -> Habit:
        # The default ``habit`` field accepts any PK in ``Habit.objects.all()``,
        # which would let an authenticated user log against someone else's
        # habit (IDOR). Restrict it to habits owned by the current user.
        request = self.context.get('request')
        if request is None or habit.user_id != request.user.id:
            raise serializers.ValidationError('Habit not found.')
        return habit

    def create(self, validated_data):
        request = self.context['request']
        validated_data['user'] = request.user
        return HabitLog.objects.update_or_create(
            habit=validated_data['habit'],
            log_date=validated_data.get('log_date'),
            defaults=validated_data,
        )[0]


class UserProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)
    xp_for_next_level = serializers.IntegerField(read_only=True)
    level_progress_pct = serializers.IntegerField(read_only=True)

    class Meta:
        model = UserProfile
        fields = [
            'username',
            'email',
            'level',
            'xp',
            'xp_for_next_level',
            'level_progress_pct',
            'current_streak',
            'best_streak',
            'mascot_name',
            'mascot_mood',
        ]


class AchievementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Achievement
        fields = ['id', 'code', 'title', 'description', 'condition_type', 'condition_value', 'xp_reward', 'icon']


class UserAchievementSerializer(serializers.ModelSerializer):
    achievement = AchievementSerializer(read_only=True)

    class Meta:
        model = UserAchievement
        fields = ['achievement', 'unlocked_at']


class InsightSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserInsight
        fields = ['id', 'insight_type', 'title', 'message', 'payload', 'is_read', 'created_at']


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=64)
    email = serializers.EmailField(required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, validators=[validate_password])

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email') or '',
            password=validated_data['password'],
        )
        return user


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
