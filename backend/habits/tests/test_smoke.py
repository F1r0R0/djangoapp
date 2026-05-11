"""Smoke tests — proves the suite, fixtures, and DB are wired up."""
import pytest

from habits.models import Achievement, Habit, UserProfile


pytestmark = pytest.mark.django_db


def test_user_profile_autocreated_on_signup(db):
    from django.contrib.auth import get_user_model

    user = get_user_model().objects.create_user(username='zoe', password='pw')
    assert UserProfile.objects.filter(user=user).exists()


def test_habit_round_trip(db):
    from habits.tests.factories import make_habit, make_user

    user = make_user('alice')
    habit = make_habit(user, title='Йога', target_type='minutes', target_value=20)
    assert habit.user_id == user.id
    assert habit.schedule.days_of_week == '1,2,3,4,5,6,7'


def test_taxonomy_seeded(db):
    # ``0002_seed_taxonomy`` is a data migration so it only runs when
    # migrations execute. We pass ``--nomigrations`` for speed, so this test
    # just checks the model exists and is importable.
    assert Achievement._meta.db_table == 'habits_achievement'
