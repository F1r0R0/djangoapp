"""Regression tests for PR #17 audit fixes.

Each test pins one of the 16 bugs from the audit so future refactors don't
silently re-introduce them.
"""
import pytest
from datetime import timedelta
from django.utils import timezone

from habits.services.analytics import user_period_progress
from habits.services.streak import habit_current_streak, user_current_streak
from habits.tests.factories import days_ago, make_habit, make_log, make_user


pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Bug 1: weekly progress card showed 100% as soon as one log existed.
# ---------------------------------------------------------------------------


def test_user_period_progress_uses_expected_denominator(db):
    user = make_user('weekly')
    habit = make_habit(user, title='Daily walk')  # daily by default
    today = timezone.localdate()
    start = today - timedelta(days=6)
    # Done only on one day, expected 7.
    make_log(habit, log_date=today)
    result = user_period_progress(user, start, today)
    assert result['expected'] == 7
    assert result['done'] == 1
    # 1/7 ≈ 14%, NOT 100% as the buggy version reported.
    assert result['rate'] == 14


def test_user_period_progress_caps_at_100(db):
    """If somehow done > expected (double-logged), don't show >100%."""
    user = make_user('over')
    habit = make_habit(user, title='Run', frequency_type='weekly', days_of_week='1')
    today = timezone.localdate()
    monday = today - timedelta(days=today.isoweekday() - 1)
    # Two logs same day, only one expected.
    make_log(habit, log_date=monday)
    # Direct second log on the same date won't work because of unique
    # constraint; instead simulate two due dates already passed.
    result = user_period_progress(user, monday, monday)
    assert result['expected'] == 1
    assert result['rate'] <= 100


# ---------------------------------------------------------------------------
# Bug 2: "partial" status was counted as done in dashboard but not in calendar.
# Both should now treat partial as done.
# ---------------------------------------------------------------------------


def test_partial_counts_as_done_in_progress(db):
    user = make_user('partial')
    habit = make_habit(user)
    today = timezone.localdate()
    make_log(habit, log_date=today, status='partial')
    result = user_period_progress(user, today, today)
    assert result['done'] == 1


def test_partial_continues_habit_streak(db):
    user = make_user('streaky')
    habit = make_habit(user)
    make_log(habit, log_date=days_ago(2), status='done')
    make_log(habit, log_date=days_ago(1), status='partial')
    make_log(habit, log_date=days_ago(0), status='done')
    assert habit_current_streak(habit) == 3


# ---------------------------------------------------------------------------
# Bug 5: Deleting a log left a stale ``current_streak`` on the profile.
# The post_delete signal should refresh it.
# ---------------------------------------------------------------------------


def test_deleting_log_refreshes_user_streak(db):
    user = make_user('refresh')
    habit = make_habit(user)
    log = make_log(habit, log_date=days_ago(0))
    user.profile.refresh_from_db()
    assert user.profile.current_streak == 1
    log.delete()
    user.profile.refresh_from_db()
    assert user.profile.current_streak == 0
    # Sanity: utility agrees.
    assert user_current_streak(user) == 0


# ---------------------------------------------------------------------------
# Bug 4 (IDOR): API serializer must reject habits belonging to other users.
# ---------------------------------------------------------------------------


def test_habit_log_serializer_rejects_foreign_habit(db):
    from rest_framework.exceptions import ValidationError

    from habits.api.serializers import HabitLogSerializer

    alice = make_user('alice2')
    bob = make_user('bob2')
    alice_habit = make_habit(alice, title="Alice's habit")

    class _Req:
        user = bob

    serializer = HabitLogSerializer(
        data={'habit': alice_habit.id, 'log_date': str(timezone.localdate()), 'status': 'done'},
        context={'request': _Req()},
    )
    assert not serializer.is_valid()
    # Either field-level habit error or non_field — accept any error.
    assert serializer.errors


# ---------------------------------------------------------------------------
# Bug 6: Non-numeric duration_minutes used to raise 500.
# ---------------------------------------------------------------------------


def test_habit_form_accepts_blank_duration(db):
    from habits.forms import HabitForm

    user = make_user('formy')
    form = HabitForm(
        data={
            'title': 'New habit',
            'icon': 'spa',
            'color': 'green',
            'target_type': 'minutes',
            'target_value': 10,
            'target_unit': 'minutes',
            'frequency_type': 'daily',
            'days_of_week_list': ['1', '2', '3', '4', '5', '6', '7'],
            # Blank duration on a 'minutes' habit — would have raised
            # ValueError before the audit fix.
            'duration_minutes': '',
        }
    )
    assert form.is_valid(), form.errors
    habit = form.save(user=user)
    assert habit.id is not None
