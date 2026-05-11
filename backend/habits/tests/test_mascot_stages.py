"""Mascot evolution: level decides stage, streak decides vibe."""
import pytest

from habits.tests.factories import make_user


pytestmark = pytest.mark.django_db


def _profile(level: int = 1, streak: int = 0):
    user = make_user(f'user-l{level}-s{streak}')
    profile = user.profile
    profile.level = level
    profile.current_streak = streak
    profile.save()
    return profile


def test_level_1_starts_as_newborn(db):
    stage = _profile(level=1).mascot_stage
    assert stage['key'] == 'newborn'
    assert stage['next_title'] == 'Хомячок-ученик'
    assert stage['stage_progress_pct'] == 0


def test_level_5_is_athlete_not_master(db):
    stage = _profile(level=5).mascot_stage
    assert stage['key'] == 'athlete'
    assert stage['icon'] == 'fa-dumbbell'
    # Level 5 of 4..7 → 1/4 of the way to master.
    assert stage['stage_progress_pct'] == 25
    assert stage['next_title'] == 'Хомячок-мастер'


def test_level_15_is_legend_and_capped(db):
    stage = _profile(level=15).mascot_stage
    assert stage['key'] == 'legend'
    assert stage['next_title'] is None
    assert stage['stage_progress_pct'] == 100


def test_streak_drives_vibe_independent_of_level(db):
    calm = _profile(level=10, streak=0).mascot_stage
    spark = _profile(level=10, streak=3).mascot_stage
    fire = _profile(level=10, streak=7).mascot_stage
    stellar = _profile(level=10, streak=20).mascot_stage
    assert (calm['vibe'], spark['vibe'], fire['vibe'], stellar['vibe']) == (
        'calm', 'spark', 'fire', 'stellar'
    )
    assert calm['vibe_icon'] == ''
    assert fire['vibe_icon'] == 'fa-fire'
    assert stellar['vibe_icon'] == 'fa-star'
