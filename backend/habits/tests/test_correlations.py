"""user_habit_correlations: pair lift analytics."""
import pytest
from django.utils import timezone

from habits.services.analytics import user_habit_correlations
from habits.tests.factories import make_habit, make_log, make_user, days_ago


pytestmark = pytest.mark.django_db


def test_no_correlations_when_one_habit(db):
    user = make_user('solo')
    habit = make_habit(user, title='Run')
    for d in range(0, 10):
        make_log(habit, log_date=days_ago(d))
    assert user_habit_correlations(user, days=30) == []


def test_perfect_pair_surfaces_first(db):
    user = make_user('pair')
    coffee = make_habit(user, title='Кофе')
    meditate = make_habit(user, title='Медитация')
    unrelated = make_habit(user, title='Холодный душ')

    # 10 days where coffee + meditation happen together.
    for d in range(0, 10):
        make_log(coffee, log_date=days_ago(d))
        make_log(meditate, log_date=days_ago(d))
    # Cold shower only on 2 unrelated days — should not pair strongly.
    make_log(unrelated, log_date=days_ago(15))
    make_log(unrelated, log_date=days_ago(16))

    rows = user_habit_correlations(user, days=30, min_pairs=3)
    assert len(rows) >= 2
    top = rows[0]
    # The strongest pair should be coffee → meditation (or vice versa)
    titles = {top['a_title'], top['b_title']}
    assert titles == {'Кофе', 'Медитация'}
    assert top['conditional_pct'] == 100
    assert top['together'] == 10


def test_min_pairs_filters_noise(db):
    user = make_user('noise')
    a = make_habit(user, title='A')
    b = make_habit(user, title='B')
    # Only 2 days of A — below min_pairs threshold of 5.
    for d in range(0, 2):
        make_log(a, log_date=days_ago(d))
        make_log(b, log_date=days_ago(d))
    rows = user_habit_correlations(user, days=30, min_pairs=5)
    assert rows == []


def test_skipped_logs_do_not_count(db):
    user = make_user('strict')
    a = make_habit(user, title='A')
    b = make_habit(user, title='B')
    for d in range(0, 10):
        make_log(a, log_date=days_ago(d), status='done')
        make_log(b, log_date=days_ago(d), status='skipped')
    rows = user_habit_correlations(user, days=30, min_pairs=3)
    # ``b`` has zero "done"/"partial" logs → no pair gets emitted because
    # ``together`` is always zero.
    assert rows == []
