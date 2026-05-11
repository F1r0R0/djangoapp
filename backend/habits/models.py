"""
HabitHamster ORM models.

Mapped from `backend/bd_concept/readme.md`. We use Django's built-in
`auth.User` instead of a custom `users` table; all per-user product data
lives in `UserProfile` and the related models below.
"""
from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone


# ---------------------------------------------------------------------------
# User profile (XP, level, mascot, streaks).
# ---------------------------------------------------------------------------


class UserProfile(models.Model):
    MASCOT_MOOD_CHOICES = [
        ('happy', 'Happy'),
        ('neutral', 'Neutral'),
        ('sad', 'Sad'),
        ('excited', 'Excited'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    level = models.PositiveIntegerField(default=1)
    xp = models.PositiveIntegerField(default=0)
    current_streak = models.PositiveIntegerField(default=0)
    best_streak = models.PositiveIntegerField(default=0)
    mascot_name = models.CharField(max_length=64, default='Хома')
    mascot_mood = models.CharField(max_length=16, choices=MASCOT_MOOD_CHOICES, default='happy')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Профиль'
        verbose_name_plural = 'Профили'

    def __str__(self) -> str:
        return f'Profile<{self.user.username}>'

    @property
    def xp_for_next_level(self) -> int:
        # XP required to reach next level — quadratic but gentle.
        return 100 * self.level + 100

    @property
    def level_progress_pct(self) -> int:
        if self.xp_for_next_level == 0:
            return 0
        return int(100 * self.xp / self.xp_for_next_level)

    # -----------------------------------------------------------------------
    # Mascot evolution.
    #
    # The hamster has one base PNG, but we overlay accessories (FontAwesome
    # icons) and tweak filters / glow so it visibly evolves with the user's
    # progress. ``mascot_stage`` returns a dict describing the current stage
    # so templates don't have to encode the thresholds.
    # -----------------------------------------------------------------------

    MASCOT_STAGES = [
        # (min_level, key, title, accessory icon, accessory css, halo css)
        (1, 'newborn', 'Хомячок-новичок', '', '', ''),
        (2, 'student', 'Хомячок-ученик', 'fa-book', 'bg-blue-500 text-white', 'ring-2 ring-blue-200'),
        (4, 'athlete', 'Хомячок-атлет', 'fa-dumbbell', 'bg-orange-500 text-white', 'ring-2 ring-orange-200'),
        (8, 'master', 'Хомячок-мастер', 'fa-graduation-cap', 'bg-purple-500 text-white', 'ring-2 ring-purple-200'),
        (15, 'legend', 'Хомячок-легенда', 'fa-crown', 'bg-yellow-400 text-white', 'ring-4 ring-yellow-200'),
    ]

    @property
    def mascot_stage(self) -> dict:
        stage = self.MASCOT_STAGES[0]
        for candidate in self.MASCOT_STAGES:
            if self.level >= candidate[0]:
                stage = candidate
        min_level, key, title, icon, icon_css, halo_css = stage
        # Vibe modifier driven by current streak.
        if self.current_streak >= 14:
            vibe = 'stellar'
            vibe_icon = 'fa-star'
            vibe_css = 'text-yellow-400'
        elif self.current_streak >= 5:
            vibe = 'fire'
            vibe_icon = 'fa-fire'
            vibe_css = 'text-orange-500'
        elif self.current_streak >= 1:
            vibe = 'spark'
            vibe_icon = 'fa-bolt'
            vibe_css = 'text-yellow-500'
        else:
            vibe = 'calm'
            vibe_icon = ''
            vibe_css = ''
        # XP-to-next-stage progress so the UI can show a real bar.
        next_threshold = None
        for candidate in self.MASCOT_STAGES:
            if candidate[0] > self.level:
                next_threshold = candidate
                break
        if next_threshold is None:
            stage_progress_pct = 100
            next_title = None
        else:
            span = next_threshold[0] - min_level
            stage_progress_pct = int(100 * (self.level - min_level) / span) if span else 0
            next_title = next_threshold[2]
        return {
            'key': key,
            'title': title,
            'icon': icon,
            'icon_css': icon_css,
            'halo_css': halo_css,
            'vibe': vibe,
            'vibe_icon': vibe_icon,
            'vibe_css': vibe_css,
            'next_title': next_title,
            'stage_progress_pct': max(0, min(stage_progress_pct, 100)),
        }


# ---------------------------------------------------------------------------
# Tags / categories / activity types.
# ---------------------------------------------------------------------------


class ActivityType(models.Model):
    """Hidden grouping of tags by activity nature (физическая, когнитивная …)."""

    name = models.CharField(max_length=64, unique=True)
    emoji = models.CharField(max_length=8, blank=True, default='')

    class Meta:
        verbose_name = 'Тип активности'
        verbose_name_plural = 'Типы активности'

    def __str__(self) -> str:
        return self.name


class TagCategory(models.Model):
    """Top-level analytical category (здоровье, обучение …)."""

    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
    )
    name = models.CharField(max_length=64, unique=True)
    slug = models.SlugField(max_length=64, unique=True)
    color = models.CharField(max_length=16, blank=True, default='')
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        ordering = ['name']

    def __str__(self) -> str:
        return self.name


class Tag(models.Model):
    """Concrete tag (бег, чтение, медитация …)."""

    name = models.CharField(max_length=64, unique=True)
    slug = models.SlugField(max_length=80, unique=True)
    activity_type = models.ForeignKey(
        ActivityType,
        on_delete=models.PROTECT,
        related_name='tags',
        null=True,
        blank=True,
    )
    hint = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'
        ordering = ['name']

    def __str__(self) -> str:
        return self.name


class TagCategoryWeight(models.Model):
    """Weight of a tag inside a category, sums to ~1.0 for a tag."""

    tag = models.ForeignKey(Tag, on_delete=models.CASCADE, related_name='category_weights')
    category = models.ForeignKey(TagCategory, on_delete=models.CASCADE, related_name='tag_weights')
    weight = models.FloatField(default=0.0)

    class Meta:
        unique_together = ('tag', 'category')
        verbose_name = 'Вес тега'
        verbose_name_plural = 'Веса тегов'

    def __str__(self) -> str:
        return f'{self.tag.name} → {self.category.name} ({self.weight})'


# ---------------------------------------------------------------------------
# Habits / schedules / logs.
# ---------------------------------------------------------------------------


class Habit(models.Model):
    TARGET_TYPE_CHOICES = [
        ('check', 'check'),
        ('minutes', 'minutes'),
        ('count', 'count'),
    ]
    TARGET_UNIT_CHOICES = [
        ('times', 'раз'),
        ('minutes', 'минут'),
        ('pages', 'страниц'),
        ('steps', 'шагов'),
        ('glasses', 'стаканов'),
        ('kilometers', 'км'),
    ]
    ICON_CHOICES = [
        ('spa', 'Йога'),
        ('dumbbell', 'Спорт'),
        ('book', 'Чтение'),
        ('water', 'Вода'),
        ('brain', 'Мышление'),
        ('heart', 'Здоровье'),
        ('code', 'Работа'),
        ('music', 'Музыка'),
        ('palette', 'Творчество'),
        ('leaf', 'Природа'),
        ('moon', 'Сон'),
        ('utensils', 'Питание'),
    ]
    COLOR_CHOICES = [
        ('green', 'Зелёный'),
        ('blue', 'Синий'),
        ('orange', 'Оранжевый'),
        ('purple', 'Фиолетовый'),
        ('red', 'Красный'),
        ('pink', 'Розовый'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='habits',
    )
    title = models.CharField(max_length=120)
    description = models.TextField(blank=True, default='')
    target_type = models.CharField(max_length=16, choices=TARGET_TYPE_CHOICES, default='check')
    target_value = models.PositiveIntegerField(default=1)
    target_unit = models.CharField(max_length=16, choices=TARGET_UNIT_CHOICES, default='times')
    color = models.CharField(max_length=16, choices=COLOR_CHOICES, default='green')
    icon = models.CharField(max_length=32, choices=ICON_CHOICES, default='spa')
    tags = models.ManyToManyField(Tag, through='HabitTag', related_name='habits', blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Привычка'
        verbose_name_plural = 'Привычки'
        ordering = ['-created_at']

    def __str__(self) -> str:
        return self.title


class HabitSchedule(models.Model):
    FREQUENCY_CHOICES = [
        ('daily', 'Ежедневно'),
        ('weekly', 'По дням недели'),
        ('custom', 'Кастомно'),
    ]

    habit = models.OneToOneField(Habit, on_delete=models.CASCADE, related_name='schedule')
    frequency_type = models.CharField(max_length=16, choices=FREQUENCY_CHOICES, default='daily')
    # Stored as comma-separated ints "1,2,3,4,5,6,7" (Mon=1 .. Sun=7).
    days_of_week = models.CharField(max_length=32, blank=True, default='1,2,3,4,5,6,7')
    times_per_period = models.PositiveIntegerField(default=1)
    reminder_time = models.TimeField(null=True, blank=True)
    # Optional time-of-day window: when both are set, the habit is considered
    # "active now" only between window_start and window_end on a due day.
    # Both blank => habit is active for the whole day (legacy behaviour).
    window_start = models.TimeField(null=True, blank=True)
    window_end = models.TimeField(null=True, blank=True)
    start_date = models.DateField(default=timezone.localdate)
    end_date = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = 'Расписание привычки'
        verbose_name_plural = 'Расписания привычек'

    def __str__(self) -> str:
        return f'Schedule<{self.habit.title}>'

    @property
    def days_list(self) -> list[int]:
        return [int(x) for x in self.days_of_week.split(',') if x.strip().isdigit()]

    def is_due_on(self, date) -> bool:
        if self.start_date and date < self.start_date:
            return False
        if self.end_date and date > self.end_date:
            return False
        if self.frequency_type == 'daily':
            return True
        if self.frequency_type == 'weekly':
            # Python isoweekday: Mon=1, Sun=7.
            return date.isoweekday() in self.days_list
        # monthly / custom: treat as "any day" by default for MVP.
        return True

    @property
    def has_window(self) -> bool:
        return bool(self.window_start and self.window_end)

    def is_active_at(self, when=None) -> bool:
        """Return True if a habit is currently inside its time-of-day window.

        - If no window is configured, falls back to ``is_due_on`` for the date.
        - If ``window_start <= window_end``, the window is a normal intra-day
          range (e.g. 13:00..14:00).
        - If ``window_start > window_end``, the window wraps past midnight
          (e.g. 22:00..06:00) and matches either side of midnight.
        """
        when = when or timezone.localtime()
        if not self.is_due_on(when.date()):
            return False
        if not self.has_window:
            return True
        now_t = when.time()
        start, end = self.window_start, self.window_end
        if start <= end:
            return start <= now_t <= end
        # Wrap past midnight.
        return now_t >= start or now_t <= end


class HabitLog(models.Model):
    STATUS_CHOICES = [
        ('done', 'Выполнено'),
        ('partial', 'Частично'),
        ('skipped', 'Пропущено осознанно'),
        ('missed', 'Пропущено'),
    ]

    habit = models.ForeignKey(Habit, on_delete=models.CASCADE, related_name='logs')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='habit_logs')
    log_date = models.DateField(default=timezone.localdate)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default='done')
    value = models.PositiveIntegerField(default=0)
    duration_minutes = models.PositiveIntegerField(default=0)
    note = models.TextField(blank=True, default='')
    mood_score = models.PositiveSmallIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Запись выполнения'
        verbose_name_plural = 'Записи выполнения'
        unique_together = ('habit', 'log_date')
        ordering = ['-log_date']

    def __str__(self) -> str:
        return f'HabitLog<{self.habit.title} @ {self.log_date} = {self.status}>'


class HabitTag(models.Model):
    habit = models.ForeignKey(Habit, on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('habit', 'tag')


# ---------------------------------------------------------------------------
# Achievements & challenges.
# ---------------------------------------------------------------------------


class Achievement(models.Model):
    CONDITION_CHOICES = [
        ('streak', 'Серия дней'),
        ('completion_count', 'Количество выполнений'),
        ('total_time', 'Суммарное время'),
        ('xp', 'Уровень XP'),
        ('custom', 'Кастомная логика'),
    ]

    code = models.SlugField(max_length=64, unique=True)
    title = models.CharField(max_length=120)
    description = models.TextField(blank=True, default='')
    condition_type = models.CharField(max_length=32, choices=CONDITION_CHOICES, default='streak')
    condition_value = models.PositiveIntegerField(default=1)
    xp_reward = models.PositiveIntegerField(default=50)
    icon = models.CharField(max_length=64, blank=True, default='medal')
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = 'Достижение'
        verbose_name_plural = 'Достижения'
        ordering = ['condition_value']

    def __str__(self) -> str:
        return self.title


class UserAchievement(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='user_achievements')
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE, related_name='unlocks')
    unlocked_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('user', 'achievement')
        ordering = ['-unlocked_at']

    def __str__(self) -> str:
        return f'{self.user.username} → {self.achievement.code}'


class Challenge(models.Model):
    CONDITION_CHOICES = [
        ('completion_count', 'completion_count'),
        ('tag_completion_count', 'tag_completion_count'),
        ('streak', 'streak'),
        ('total_time', 'total_time'),
        ('custom', 'custom'),
    ]

    title = models.CharField(max_length=120)
    description = models.TextField(blank=True, default='')
    condition_type = models.CharField(max_length=32, choices=CONDITION_CHOICES, default='completion_count')
    condition_value = models.PositiveIntegerField(default=1)
    tag = models.ForeignKey(Tag, on_delete=models.SET_NULL, null=True, blank=True, related_name='challenges')
    xp_reward = models.PositiveIntegerField(default=200)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = 'Челлендж'
        verbose_name_plural = 'Челленджи'
        ordering = ['-created_at']

    def __str__(self) -> str:
        return self.title


class UserChallenge(models.Model):
    STATUS_CHOICES = [
        ('active', 'Активен'),
        ('completed', 'Завершён'),
        ('failed', 'Провален'),
        ('cancelled', 'Отменён'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='user_challenges')
    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE, related_name='participants')
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default='active')
    progress = models.PositiveIntegerField(default=0)
    joined_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('user', 'challenge')
        ordering = ['-joined_at']

    def __str__(self) -> str:
        return f'{self.user.username} @ {self.challenge.title} = {self.status}'


# ---------------------------------------------------------------------------
# Insights.
# ---------------------------------------------------------------------------


class UserInsight(models.Model):
    INSIGHT_TYPE_CHOICES = [
        ('weak_day', 'Слабый день недели'),
        ('best_day', 'Лучший день недели'),
        ('streak', 'Серия выполнений'),
        ('tag_analytics', 'Аналитика по тегам'),
        ('mascot_message', 'Сообщение маскота'),
        ('custom', 'Кастом'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='insights')
    insight_type = models.CharField(max_length=32, choices=INSIGHT_TYPE_CHOICES, default='custom')
    title = models.CharField(max_length=160)
    message = models.TextField()
    payload = models.JSONField(default=dict, blank=True)
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = 'Инсайт'
        verbose_name_plural = 'Инсайты'
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'{self.insight_type}: {self.title}'
