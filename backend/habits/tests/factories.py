"""Tiny hand-rolled factories — no factory_boy dependency."""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any

from django.contrib.auth import get_user_model
from django.utils import timezone

from habits.models import Habit, HabitLog, HabitSchedule, UserProfile


User = get_user_model()


def make_user(username: str = 'alice', password: str = 'pw') -> Any:
    """Create or fetch a user, eagerly ensuring a profile exists.

    The ``post_save`` signal already does this, but the test suite uses
    ``--nomigrations`` so some edge cases bypass it; fall back to
    ``get_or_create`` for safety.
    """
    user, _ = User.objects.get_or_create(username=username)
    user.set_password(password)
    user.save()
    UserProfile.objects.get_or_create(user=user)
    return user


def make_habit(
    user,
    title: str = 'Test habit',
    target_type: str = 'minutes',
    target_value: int = 15,
    target_unit: str = 'minutes',
    frequency_type: str = 'daily',
    days_of_week: str = '1,2,3,4,5,6,7',
    window_start: time | None = None,
    window_end: time | None = None,
    schedule_start: date | None = None,
) -> Habit:
    habit = Habit.objects.create(
        user=user,
        title=title,
        target_type=target_type,
        target_value=target_value,
        target_unit=target_unit,
    )
    HabitSchedule.objects.update_or_create(
        habit=habit,
        defaults={
            'frequency_type': frequency_type,
            'days_of_week': days_of_week,
            'window_start': window_start,
            'window_end': window_end,
            # Backdated by default so factory-created habits are "due" for
            # historical dates in tests (avoids needing every test to pass an
            # explicit start_date).
            'start_date': schedule_start or (timezone.localdate() - timedelta(days=365)),
        },
    )
    return habit


def make_log(
    habit: Habit,
    log_date: date | None = None,
    status: str = 'done',
    duration_minutes: int = 0,
    created_at: datetime | None = None,
) -> HabitLog:
    log_date = log_date or timezone.localdate()
    log = HabitLog.objects.create(
        user=habit.user,
        habit=habit,
        log_date=log_date,
        status=status,
        value=habit.target_value if status == 'done' else 0,
        duration_minutes=duration_minutes,
    )
    if created_at is not None:
        # ``auto_now_add`` / ``default=timezone.now`` overwrites whatever we
        # pass into the constructor, so we patch it post-save.
        HabitLog.objects.filter(pk=log.pk).update(created_at=created_at)
        log.refresh_from_db()
    return log


def days_ago(n: int) -> date:
    return timezone.localdate() - timedelta(days=n)
