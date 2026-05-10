"""
Create a demo user with some habits and back-filled history so the dashboard
and analytics pages have something interesting to show.

Usage:
    python manage.py seed_demo --username demo --password demopass123
"""
from __future__ import annotations

import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from habits.models import Habit, HabitLog, HabitSchedule, Tag


User = get_user_model()


HABIT_RECIPES = [
    {
        'title': 'Утренняя йога',
        'description': '15 минут, спокойная музыка, без телефона.',
        'icon': 'spa',
        'color': 'green',
        'target_type': 'minutes',
        'target_value': 15,
        'target_unit': 'minutes',
        'tags': ['йога', 'растяжка'],
        'prob': 0.85,
    },
    {
        'title': 'Прочитать 10 страниц',
        'description': 'Художественная книга или нон-фикшн.',
        'icon': 'book',
        'color': 'blue',
        'target_type': 'count',
        'target_value': 10,
        'target_unit': 'pages',
        'tags': ['чтение (книги)'],
        'prob': 0.7,
    },
    {
        'title': 'Силовая тренировка',
        'description': 'Гантели или собственный вес.',
        'icon': 'dumbbell',
        'color': 'orange',
        'target_type': 'minutes',
        'target_value': 45,
        'target_unit': 'minutes',
        'tags': ['силовая тренировка'],
        'prob': 0.4,
    },
    {
        'title': 'Медитация',
        'description': '10 минут наблюдения за дыханием.',
        'icon': 'brain',
        'color': 'purple',
        'target_type': 'minutes',
        'target_value': 10,
        'target_unit': 'minutes',
        'tags': ['медитация', 'дыхательная практика'],
        'prob': 0.6,
    },
    {
        'title': 'Стакан воды',
        'description': '8 стаканов в день.',
        'icon': 'water',
        'color': 'blue',
        'target_type': 'count',
        'target_value': 8,
        'target_unit': 'glasses',
        'tags': ['вода'],
        'prob': 0.9,
    },
    {
        'title': 'Глубокая работа',
        'description': '90 минут без уведомлений.',
        'icon': 'code',
        'color': 'purple',
        'target_type': 'minutes',
        'target_value': 90,
        'target_unit': 'minutes',
        'tags': ['deep work', 'планирование'],
        'prob': 0.55,
    },
]


class Command(BaseCommand):
    help = 'Create or refresh a demo user with seeded habits and ~60 days of history.'

    def add_arguments(self, parser):
        parser.add_argument('--username', default='demo')
        parser.add_argument('--password', default='demopass123')
        parser.add_argument('--days', type=int, default=60)
        parser.add_argument('--reset', action='store_true', help='Wipe existing demo data first.')

    def handle(self, *args, **options):
        username = options['username']
        password = options['password']
        days = options['days']

        user, created = User.objects.get_or_create(
            username=username,
            defaults={'email': f'{username}@example.com'},
        )
        if created:
            user.set_password(password)
            user.save()
        elif options['reset']:
            user.habits.all().delete()
            user.set_password(password)
            user.save()

        # Re-seed taxonomy if any tag is missing.
        from django.core.management import call_command

        if not Tag.objects.exists():
            call_command('seed_taxonomy')

        # Build habits.
        habits: list[tuple[Habit, dict]] = []
        backdate = timezone.now() - timedelta(days=days + 5)
        for recipe in HABIT_RECIPES:
            habit, _ = Habit.objects.update_or_create(
                user=user,
                title=recipe['title'],
                defaults={
                    'description': recipe['description'],
                    'icon': recipe['icon'],
                    'color': recipe['color'],
                    'target_type': recipe['target_type'],
                    'target_value': recipe['target_value'],
                    'target_unit': recipe['target_unit'],
                    'is_active': True,
                    'created_at': backdate,
                },
            )
            HabitSchedule.objects.update_or_create(
                habit=habit,
                defaults={
                    'frequency_type': 'daily',
                    'days_of_week': '1,2,3,4,5,6,7',
                    'start_date': timezone.localdate() - timedelta(days=days + 5),
                },
            )
            tag_objs = list(Tag.objects.filter(name__in=recipe['tags']))
            habit.tags.set(tag_objs)
            habits.append((habit, recipe))

        # Backfill history.
        today = timezone.localdate()
        random.seed(42)
        created_logs = 0
        for habit, recipe in habits:
            prob = recipe['prob']
            for offset in range(1, days + 1):
                date = today - timedelta(days=offset)
                # Slight weekday slump for some habits.
                weekday = date.isoweekday()
                p = prob - (0.15 if weekday >= 6 else 0.0)
                if random.random() < p:
                    duration = recipe['target_value'] if recipe['target_type'] == 'minutes' else 0
                    HabitLog.objects.update_or_create(
                        habit=habit,
                        log_date=date,
                        defaults={
                            'user': user,
                            'status': 'done' if random.random() < 0.85 else 'partial',
                            'duration_minutes': duration,
                            'value': recipe['target_value'],
                        },
                    )
                    created_logs += 1
        self.stdout.write(self.style.SUCCESS(
            f'Demo user "{username}" ready: {len(habits)} habits, '
            f'{created_logs} historical logs over last {days} days.'
        ))
        self.stdout.write(self.style.WARNING(
            f'Login as {username} / {password}'
        ))
