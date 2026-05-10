"""Streak calculation."""
from __future__ import annotations

from datetime import date, timedelta

from django.utils import timezone

from habits.models import Habit, HabitLog


def habit_current_streak(habit: Habit, today: date | None = None) -> int:
    """Count consecutive days up to today that are 'done' or 'partial'."""
    today = today or timezone.localdate()
    streak = 0
    cursor = today
    schedule = getattr(habit, 'schedule', None)
    while True:
        # Skip days the habit isn't due (don't break the streak).
        if schedule and not schedule.is_due_on(cursor):
            cursor -= timedelta(days=1)
            if cursor < habit.created_at.date():
                break
            continue
        log = HabitLog.objects.filter(habit=habit, log_date=cursor).first()
        if log and log.status in {'done', 'partial'}:
            streak += 1
            cursor -= timedelta(days=1)
            continue
        # Special case: if checking today and there's no log yet, slide back
        # by one day so a streak from yesterday is still visible.
        if cursor == today and not log:
            cursor -= timedelta(days=1)
            continue
        break
    return streak


def habit_best_streak(habit: Habit) -> int:
    """Best streak ever for this habit."""
    logs = list(habit.logs.filter(status__in=['done', 'partial']).order_by('log_date'))
    if not logs:
        return 0
    best = 1
    current = 1
    for prev, cur in zip(logs, logs[1:]):
        if (cur.log_date - prev.log_date).days == 1:
            current += 1
            best = max(best, current)
        else:
            current = 1
    return best


def user_current_streak(user, today: date | None = None) -> int:
    """User-level streak: consecutive days where ANY habit was logged 'done'."""
    today = today or timezone.localdate()
    streak = 0
    cursor = today
    while True:
        has_log = HabitLog.objects.filter(
            user=user, log_date=cursor, status__in=['done', 'partial']
        ).exists()
        if has_log:
            streak += 1
            cursor -= timedelta(days=1)
            continue
        if cursor == today:
            cursor -= timedelta(days=1)
            continue
        break
    return streak
