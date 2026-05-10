"""
Django admin for HabitHamster.

Полная админка через ``ModelAdmin``: списки с фильтрами/поиском, инлайны
для связанных моделей (расписание, теги привычки, веса категорий),
``autocomplete_fields`` для FK, ``readonly_fields`` для системных полей,
групповые действия и читаемые представления.
"""
from __future__ import annotations

from django.contrib import admin, messages
from django.db.models import Count
from django.utils.html import format_html

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


# ---------------------------------------------------------------------------
# Site customisation.
# ---------------------------------------------------------------------------


admin.site.site_header = 'HabitHamster — админка'
admin.site.site_title = 'HabitHamster admin'
admin.site.index_title = 'Управление данными HabitHamster'
admin.site.empty_value_display = '—'


class BrandedAdminMixin:
    """Adds the project's green admin polish stylesheet to every changelist/form."""

    class Media:
        css = {'all': ('admin/css/custom.css',)}


# ---------------------------------------------------------------------------
# Inlines.
# ---------------------------------------------------------------------------


class HabitScheduleInline(admin.StackedInline):
    model = HabitSchedule
    extra = 0
    can_delete = False
    fk_name = 'habit'
    fields = (
        'frequency_type',
        'days_of_week',
        'times_per_period',
        'reminder_time',
        ('window_start', 'window_end'),
        ('start_date', 'end_date'),
    )


class HabitTagInline(admin.TabularInline):
    model = HabitTag
    extra = 1
    autocomplete_fields = ('tag',)
    verbose_name = 'Тег привычки'
    verbose_name_plural = 'Теги привычки'


class HabitLogInline(admin.TabularInline):
    model = HabitLog
    extra = 0
    fk_name = 'habit'
    fields = ('log_date', 'status', 'value', 'duration_minutes', 'mood_score')
    readonly_fields = ('log_date',)
    show_change_link = True
    ordering = ('-log_date',)
    max_num = 20
    verbose_name = 'Запись выполнения'
    verbose_name_plural = 'Последние записи (макс. 20)'


class TagCategoryWeightInline(admin.TabularInline):
    model = TagCategoryWeight
    extra = 1
    autocomplete_fields = ('category',)


# ---------------------------------------------------------------------------
# UserProfile.
# ---------------------------------------------------------------------------


@admin.register(UserProfile)
class UserProfileAdmin(BrandedAdminMixin, admin.ModelAdmin):
    list_display = (
        'user',
        'level',
        'xp',
        'xp_progress_bar',
        'current_streak',
        'best_streak',
        'mascot_mood',
        'updated_at',
    )
    list_filter = ('mascot_mood', 'level')
    search_fields = ('user__username', 'user__email', 'mascot_name')
    list_select_related = ('user',)
    autocomplete_fields = ('user',)
    readonly_fields = ('created_at', 'updated_at', 'xp_for_next_level', 'level_progress_pct')
    fieldsets = (
        ('Пользователь', {'fields': ('user',)}),
        (
            'Прогресс',
            {
                'fields': (
                    ('level', 'xp'),
                    ('xp_for_next_level', 'level_progress_pct'),
                    ('current_streak', 'best_streak'),
                ),
            },
        ),
        ('Маскот', {'fields': (('mascot_name', 'mascot_mood'),)}),
        ('Системное', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )
    actions = ('reset_xp_to_zero', 'reset_streaks')

    @admin.display(description='Прогресс уровня')
    def xp_progress_bar(self, obj: UserProfile) -> str:
        pct = max(0, min(100, obj.level_progress_pct))
        return format_html(
            '<div style="width:120px;background:#eee;border-radius:6px;overflow:hidden">'
            '<div style="width:{}%;background:#4CAF50;height:8px"></div>'
            '</div><span style="font-size:11px;color:#666">{}%</span>',
            pct,
            pct,
        )

    @admin.action(description='Обнулить XP и уровень')
    def reset_xp_to_zero(self, request, queryset):
        updated = queryset.update(xp=0, level=1)
        self.message_user(request, f'Обнулено профилей: {updated}', messages.SUCCESS)

    @admin.action(description='Сбросить серии (current/best)')
    def reset_streaks(self, request, queryset):
        updated = queryset.update(current_streak=0, best_streak=0)
        self.message_user(request, f'Серии сброшены у профилей: {updated}', messages.SUCCESS)


# ---------------------------------------------------------------------------
# Habits.
# ---------------------------------------------------------------------------


@admin.register(Habit)
class HabitAdmin(BrandedAdminMixin, admin.ModelAdmin):
    list_display = (
        'title',
        'user',
        'colored_icon',
        'target_type',
        'target_value',
        'target_unit',
        'is_active',
        'logs_count',
        'created_at',
    )
    list_filter = ('is_active', 'target_type', 'target_unit', 'color', 'icon', 'created_at')
    search_fields = ('title', 'description', 'user__username')
    list_select_related = ('user',)
    autocomplete_fields = ('user',)
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at')
    inlines = (HabitScheduleInline, HabitTagInline, HabitLogInline)
    fieldsets = (
        ('Основное', {'fields': ('user', 'title', 'description', 'is_active')}),
        ('Цель', {'fields': (('target_type', 'target_value', 'target_unit'),)}),
        ('Внешний вид', {'fields': (('icon', 'color'),)}),
        ('Системное', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )
    actions = ('make_active', 'make_inactive')
    list_per_page = 50

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(_logs_count=Count('logs'))

    @admin.display(description='Лого', ordering='icon')
    def colored_icon(self, obj: Habit) -> str:
        palette = {
            'green': '#4CAF50',
            'blue': '#42A5F5',
            'orange': '#FB8C00',
            'purple': '#AB47BC',
            'red': '#EF5350',
            'pink': '#EC407A',
        }
        bg = palette.get(obj.color, '#9E9E9E')
        return format_html(
            '<span style="display:inline-flex;align-items:center;gap:6px">'
            '<span style="width:16px;height:16px;border-radius:50%;background:{}"></span>'
            '<code style="font-size:11px">{}</code></span>',
            bg,
            obj.icon,
        )

    @admin.display(description='Записей', ordering='_logs_count')
    def logs_count(self, obj: Habit) -> int:
        return getattr(obj, '_logs_count', obj.logs.count())

    @admin.action(description='Активировать выбранные привычки')
    def make_active(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'Активировано: {updated}', messages.SUCCESS)

    @admin.action(description='Архивировать выбранные привычки')
    def make_inactive(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'Архивировано: {updated}', messages.SUCCESS)


@admin.register(HabitSchedule)
class HabitScheduleAdmin(BrandedAdminMixin, admin.ModelAdmin):
    list_display = (
        'habit',
        'frequency_type',
        'days_of_week',
        'times_per_period',
        'reminder_time',
        'window_start',
        'window_end',
        'start_date',
        'end_date',
    )
    list_filter = ('frequency_type', 'start_date')
    search_fields = ('habit__title', 'habit__user__username')
    autocomplete_fields = ('habit',)
    list_select_related = ('habit', 'habit__user')


@admin.register(HabitLog)
class HabitLogAdmin(BrandedAdminMixin, admin.ModelAdmin):
    list_display = (
        'habit',
        'user',
        'log_date',
        'status_badge',
        'value',
        'duration_minutes',
        'mood_score',
        'created_at',
    )
    list_filter = ('status', 'log_date')
    search_fields = ('habit__title', 'user__username', 'note')
    list_select_related = ('habit', 'user')
    autocomplete_fields = ('habit', 'user')
    date_hierarchy = 'log_date'
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Кому/Что/Когда', {'fields': (('user', 'habit'), 'log_date')}),
        ('Результат', {'fields': (('status', 'value', 'duration_minutes'), 'mood_score', 'note')}),
        ('Системное', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )
    actions = ('mark_done', 'mark_skipped')

    @admin.display(description='Статус', ordering='status')
    def status_badge(self, obj: HabitLog) -> str:
        colors = {
            'done': '#4CAF50',
            'partial': '#FFA000',
            'skipped': '#90A4AE',
            'missed': '#E53935',
        }
        bg = colors.get(obj.status, '#9E9E9E')
        return format_html(
            '<span style="background:{};color:white;padding:2px 8px;border-radius:10px;'
            'font-size:11px;font-weight:600">{}</span>',
            bg,
            obj.get_status_display(),
        )

    @admin.action(description='Отметить как «Выполнено»')
    def mark_done(self, request, queryset):
        updated = queryset.update(status='done')
        self.message_user(request, f'Отмечено выполнено: {updated}', messages.SUCCESS)

    @admin.action(description='Отметить как «Пропущено»')
    def mark_skipped(self, request, queryset):
        updated = queryset.update(status='skipped')
        self.message_user(request, f'Помечено пропуском: {updated}', messages.SUCCESS)


@admin.register(HabitTag)
class HabitTagAdmin(BrandedAdminMixin, admin.ModelAdmin):
    list_display = ('habit', 'tag')
    search_fields = ('habit__title', 'tag__name')
    autocomplete_fields = ('habit', 'tag')
    list_select_related = ('habit', 'tag')


# ---------------------------------------------------------------------------
# Taxonomy: ActivityType / TagCategory / Tag / TagCategoryWeight.
# ---------------------------------------------------------------------------


@admin.register(ActivityType)
class ActivityTypeAdmin(BrandedAdminMixin, admin.ModelAdmin):
    list_display = ('emoji', 'name', 'tags_count')
    search_fields = ('name',)
    ordering = ('name',)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_tags_count=Count('tags'))

    @admin.display(description='Тегов', ordering='_tags_count')
    def tags_count(self, obj: ActivityType) -> int:
        return getattr(obj, '_tags_count', obj.tags.count())


@admin.register(TagCategory)
class TagCategoryAdmin(BrandedAdminMixin, admin.ModelAdmin):
    list_display = ('name', 'slug', 'parent', 'color', 'children_count', 'created_at')
    list_filter = ('parent',)
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    autocomplete_fields = ('parent',)
    ordering = ('name',)
    readonly_fields = ('created_at',)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_children=Count('children'))

    @admin.display(description='Подкатегорий', ordering='_children')
    def children_count(self, obj: TagCategory) -> int:
        return getattr(obj, '_children', obj.children.count())


@admin.register(Tag)
class TagAdmin(BrandedAdminMixin, admin.ModelAdmin):
    list_display = ('name', 'slug', 'activity_type', 'habits_count', 'created_at')
    list_filter = ('activity_type',)
    search_fields = ('name', 'slug', 'hint')
    prepopulated_fields = {'slug': ('name',)}
    autocomplete_fields = ('activity_type',)
    inlines = (TagCategoryWeightInline,)
    ordering = ('name',)
    readonly_fields = ('created_at',)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_habits=Count('habits'))

    @admin.display(description='Привычек', ordering='_habits')
    def habits_count(self, obj: Tag) -> int:
        return getattr(obj, '_habits', obj.habits.count())


@admin.register(TagCategoryWeight)
class TagCategoryWeightAdmin(BrandedAdminMixin, admin.ModelAdmin):
    list_display = ('tag', 'category', 'weight')
    list_filter = ('category',)
    search_fields = ('tag__name', 'category__name')
    autocomplete_fields = ('tag', 'category')
    list_select_related = ('tag', 'category')


# ---------------------------------------------------------------------------
# Achievements / Challenges.
# ---------------------------------------------------------------------------


@admin.register(Achievement)
class AchievementAdmin(BrandedAdminMixin, admin.ModelAdmin):
    list_display = ('code', 'title', 'condition_type', 'condition_value', 'xp_reward', 'unlocked_count')
    list_filter = ('condition_type',)
    search_fields = ('code', 'title', 'description')
    prepopulated_fields = {'code': ('title',)}
    readonly_fields = ('created_at',)
    fieldsets = (
        ('Основное', {'fields': ('code', 'title', 'description', 'icon')}),
        ('Условие', {'fields': (('condition_type', 'condition_value'), 'xp_reward')}),
        ('Системное', {'fields': ('created_at',), 'classes': ('collapse',)}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_unlocked=Count('unlocks'))

    @admin.display(description='Получено пользователями', ordering='_unlocked')
    def unlocked_count(self, obj: Achievement) -> int:
        return getattr(obj, '_unlocked', obj.unlocks.count())


@admin.register(UserAchievement)
class UserAchievementAdmin(BrandedAdminMixin, admin.ModelAdmin):
    list_display = ('user', 'achievement', 'unlocked_at')
    list_filter = ('achievement', 'unlocked_at')
    search_fields = ('user__username', 'achievement__code', 'achievement__title')
    autocomplete_fields = ('user', 'achievement')
    list_select_related = ('user', 'achievement')
    date_hierarchy = 'unlocked_at'
    readonly_fields = ('unlocked_at',)


@admin.register(Challenge)
class ChallengeAdmin(BrandedAdminMixin, admin.ModelAdmin):
    list_display = (
        'title',
        'condition_type',
        'condition_value',
        'tag',
        'xp_reward',
        'is_active',
        'start_date',
        'end_date',
        'participants_count',
    )
    list_filter = ('is_active', 'condition_type', 'tag')
    search_fields = ('title', 'description')
    autocomplete_fields = ('tag',)
    readonly_fields = ('created_at',)
    fieldsets = (
        ('Основное', {'fields': ('title', 'description', 'is_active')}),
        ('Условие', {'fields': (('condition_type', 'condition_value', 'tag'), 'xp_reward')}),
        ('Период', {'fields': (('start_date', 'end_date'),)}),
        ('Системное', {'fields': ('created_at',), 'classes': ('collapse',)}),
    )
    actions = ('activate_challenges', 'deactivate_challenges')

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_participants=Count('participants'))

    @admin.display(description='Участников', ordering='_participants')
    def participants_count(self, obj: Challenge) -> int:
        return getattr(obj, '_participants', obj.participants.count())

    @admin.action(description='Включить выбранные челленджи')
    def activate_challenges(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'Включено: {updated}', messages.SUCCESS)

    @admin.action(description='Выключить выбранные челленджи')
    def deactivate_challenges(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'Выключено: {updated}', messages.SUCCESS)


@admin.register(UserChallenge)
class UserChallengeAdmin(BrandedAdminMixin, admin.ModelAdmin):
    list_display = ('user', 'challenge', 'status', 'progress', 'joined_at', 'completed_at')
    list_filter = ('status', 'challenge')
    search_fields = ('user__username', 'challenge__title')
    autocomplete_fields = ('user', 'challenge')
    list_select_related = ('user', 'challenge')
    readonly_fields = ('joined_at',)
    date_hierarchy = 'joined_at'


# ---------------------------------------------------------------------------
# Insights.
# ---------------------------------------------------------------------------


@admin.register(UserInsight)
class UserInsightAdmin(BrandedAdminMixin, admin.ModelAdmin):
    list_display = ('title', 'user', 'insight_type', 'is_read', 'period_start', 'period_end', 'created_at')
    list_filter = ('insight_type', 'is_read', 'created_at')
    search_fields = ('title', 'message', 'user__username')
    autocomplete_fields = ('user',)
    list_select_related = ('user',)
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at',)
    actions = ('mark_as_read', 'mark_as_unread')

    @admin.action(description='Отметить как прочитанные')
    def mark_as_read(self, request, queryset):
        updated = queryset.update(is_read=True)
        self.message_user(request, f'Отмечено прочитанными: {updated}', messages.SUCCESS)

    @admin.action(description='Отметить как непрочитанные')
    def mark_as_unread(self, request, queryset):
        updated = queryset.update(is_read=False)
        self.message_user(request, f'Сброшен признак прочтения: {updated}', messages.SUCCESS)
