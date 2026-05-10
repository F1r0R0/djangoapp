from django.contrib import admin

from habits.models import (
    Achievement,
    ActivityType,
    Challenge,
    Habit,
    HabitLog,
    HabitSchedule,
    HabitTag,
    Tag,
    TagCategory,
    TagCategoryWeight,
    UserAchievement,
    UserChallenge,
    UserInsight,
    UserProfile,
)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'level', 'xp', 'current_streak', 'best_streak', 'mascot_mood')
    search_fields = ('user__username',)


@admin.register(Habit)
class HabitAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'target_type', 'target_value', 'is_active', 'created_at')
    list_filter = ('is_active', 'target_type', 'color')
    search_fields = ('title', 'user__username')


@admin.register(HabitSchedule)
class HabitScheduleAdmin(admin.ModelAdmin):
    list_display = ('habit', 'frequency_type', 'days_of_week', 'reminder_time')


@admin.register(HabitLog)
class HabitLogAdmin(admin.ModelAdmin):
    list_display = ('habit', 'user', 'log_date', 'status', 'value', 'duration_minutes')
    list_filter = ('status',)
    search_fields = ('habit__title', 'user__username')


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'activity_type')
    search_fields = ('name',)


@admin.register(TagCategory)
class TagCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'slug')
    search_fields = ('name',)


@admin.register(ActivityType)
class ActivityTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'emoji')


@admin.register(TagCategoryWeight)
class TagCategoryWeightAdmin(admin.ModelAdmin):
    list_display = ('tag', 'category', 'weight')


@admin.register(HabitTag)
class HabitTagAdmin(admin.ModelAdmin):
    list_display = ('habit', 'tag')


@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ('code', 'title', 'condition_type', 'condition_value', 'xp_reward')


@admin.register(UserAchievement)
class UserAchievementAdmin(admin.ModelAdmin):
    list_display = ('user', 'achievement', 'unlocked_at')


@admin.register(Challenge)
class ChallengeAdmin(admin.ModelAdmin):
    list_display = ('title', 'condition_type', 'condition_value', 'is_active')


@admin.register(UserChallenge)
class UserChallengeAdmin(admin.ModelAdmin):
    list_display = ('user', 'challenge', 'status', 'progress')


@admin.register(UserInsight)
class UserInsightAdmin(admin.ModelAdmin):
    list_display = ('user', 'insight_type', 'title', 'is_read', 'created_at')
    list_filter = ('insight_type', 'is_read')
