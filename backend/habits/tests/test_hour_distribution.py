"""habit_hour_distribution: hour-of-day analytics for a single habit."""
import pytest
from django.utils import timezone

from habits.services.analytics import habit_hour_distribution
from habits.tests.factories import make_habit, make_log, make_user


pytestmark = pytest.mark.django_db


def _log_at(habit, hour: int, day_offset: int = 0, status: str = 'done'):
    """Create a log on ``today - day_offset`` with created_at set to ``hour``."""
    today = timezone.localdate()
    log_date = today - timezone.timedelta(days=day_offset)
    tz = timezone.get_current_timezone()
    local_dt = timezone.datetime(
        log_date.year, log_date.month, log_date.day, hour, 0, 0, tzinfo=tz
    )
    return make_log(habit, log_date=log_date, status=status, created_at=local_dt)


def test_empty_distribution(db):
    user = make_user('emp')
    habit = make_habit(user)
    dist = habit_hour_distribution(habit, days=90)
    assert dist['total'] == 0
    assert dist['peak_hour'] is None
    assert dist['peak_bucket'] is None
    assert dist['hours'] == [0] * 24


def test_morning_peak_detected(db):
    user = make_user('morning')
    habit = make_habit(user)
    # Three logs at 7am over three days, one log in the evening.
    _log_at(habit, hour=7, day_offset=3)
    _log_at(habit, hour=7, day_offset=2)
    _log_at(habit, hour=7, day_offset=1)
    _log_at(habit, hour=20, day_offset=0)
    dist = habit_hour_distribution(habit, days=30)
    assert dist['total'] == 4
    assert dist['peak_hour'] == 7
    assert dist['peak_bucket'] == 'Утро'
    assert dist['hours'][7] == 3
    assert dist['hours'][20] == 1
    # Morning bucket should hold 75% of activity.
    morning = next(b for b in dist['buckets'] if b['label'] == 'Утро')
    assert morning['pct'] == 75


def test_night_bucket_wraps_midnight(db):
    user = make_user('night-owl')
    habit = make_habit(user)
    _log_at(habit, hour=23, day_offset=1)
    _log_at(habit, hour=2, day_offset=0)
    dist = habit_hour_distribution(habit, days=30)
    night = next(b for b in dist['buckets'] if b['label'] == 'Ночь')
    assert night['count'] == 2
    assert night['pct'] == 100


def test_skipped_logs_excluded(db):
    user = make_user('skipper')
    habit = make_habit(user)
    _log_at(habit, hour=8, status='done')
    _log_at(habit, hour=9, status='skipped', day_offset=1)
    dist = habit_hour_distribution(habit, days=30)
    assert dist['total'] == 1
    assert dist['hours'][8] == 1
    assert dist['hours'][9] == 0
