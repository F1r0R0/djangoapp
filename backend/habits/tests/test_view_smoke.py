"""End-to-end-ish smoke tests — make sure each major page renders 200.

Covers the new template branches (mascot stage card, hour distribution,
correlations) by rendering pages where they appear.
"""
import pytest
from django.test import Client
from django.urls import reverse

from habits.tests.factories import days_ago, make_habit, make_log, make_user


pytestmark = pytest.mark.django_db


@pytest.fixture
def client_with_data():
    user = make_user('viewer', password='pw')
    Client().force_login(user) if False else None  # placeholder so import isn't unused
    h1 = make_habit(user, title='Зарядка', target_value=10)
    h2 = make_habit(user, title='Чтение', target_value=20)
    # Plenty of pair logs for correlations to surface.
    for d in range(0, 12):
        make_log(h1, log_date=days_ago(d))
        make_log(h2, log_date=days_ago(d))
    # Bump profile so the mascot evolution card has something to render.
    user.profile.level = 5
    user.profile.current_streak = 6
    user.profile.save()

    client = Client()
    client.force_login(user)
    return client, user, h1


def test_dashboard_renders_with_mascot_stage(client_with_data):
    client, _, _ = client_with_data
    response = client.get(reverse('dashboard'))
    assert response.status_code == 200
    content = response.content.decode('utf-8')
    # Stage title for level 5 is "атлет"; vibe icon for streak 6 is fire.
    assert 'Хомячок-атлет' in content
    assert 'fa-fire' in content


def test_habit_detail_renders_hour_distribution(client_with_data):
    client, _, habit = client_with_data
    response = client.get(reverse('habit_detail', kwargs={'habit_id': habit.id}))
    assert response.status_code == 200
    content = response.content.decode('utf-8')
    assert 'Когда ты обычно это делаешь' in content


def test_analytics_renders_correlations_on_month(client_with_data):
    client, _, _ = client_with_data
    response = client.get(reverse('analytics') + '?period=month')
    assert response.status_code == 200
    content = response.content.decode('utf-8')
    assert 'Связи между привычками' in content


def test_analytics_no_correlations_on_week(client_with_data):
    client, _, _ = client_with_data
    response = client.get(reverse('analytics') + '?period=week')
    assert response.status_code == 200
    content = response.content.decode('utf-8')
    # The card is gated by ``days >= 14`` so the week view skips it.
    assert 'Связи между привычками' not in content
