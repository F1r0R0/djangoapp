"""Analytics helpers — completion %, heatmap, best days, category breakdown."""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from django.db.models import Count, Sum
from django.utils import timezone

from habits.models import Habit, HabitLog, TagCategoryWeight


WEEKDAY_RU = {1: 'Пн', 2: 'Вт', 3: 'Ср', 4: 'Чт', 5: 'Пт', 6: 'Сб', 7: 'Вс'}
WEEKDAY_FULL_RU = {
    1: 'Понедельник', 2: 'Вторник', 3: 'Среда', 4: 'Четверг',
    5: 'Пятница', 6: 'Суббота', 7: 'Воскресенье',
}


def completion_rate_for_habit(habit: Habit, days: int = 30) -> int:
    """Percent of expected days the habit was done in the last `days` days."""
    today = timezone.localdate()
    schedule = getattr(habit, 'schedule', None)
    expected = 0
    done = 0
    cursor = today - timedelta(days=days - 1)
    while cursor <= today:
        if schedule is None or schedule.is_due_on(cursor):
            expected += 1
            log = HabitLog.objects.filter(habit=habit, log_date=cursor).first()
            if log and log.status in {'done', 'partial'}:
                done += 1
        cursor += timedelta(days=1)
    if expected == 0:
        return 0
    return int(100 * done / expected)


def habit_total_minutes(habit: Habit) -> int:
    return habit.logs.filter(status__in=['done', 'partial']).aggregate(
        total=Sum('duration_minutes')
    )['total'] or 0


def habit_completed_count(habit: Habit) -> int:
    return habit.logs.filter(status__in=['done', 'partial']).count()


def habit_heatmap(habit: Habit, days: int = 90) -> list[dict]:
    today = timezone.localdate()
    start = today - timedelta(days=days - 1)
    logs = {
        log.log_date: log.status
        for log in habit.logs.filter(log_date__gte=start, log_date__lte=today)
    }
    cells: list[dict] = []
    cursor = start
    while cursor <= today:
        status = logs.get(cursor, 'missed')
        intensity = 0
        if status == 'done':
            intensity = 3
        elif status == 'partial':
            intensity = 2
        elif status == 'skipped':
            intensity = 1
        cells.append({'date': cursor, 'status': status, 'intensity': intensity})
        cursor += timedelta(days=1)
    return cells


def user_activity_per_day(user, days: int = 30) -> list[dict]:
    """List of {date, count} for last `days` days for charting."""
    today = timezone.localdate()
    start = today - timedelta(days=days - 1)
    counts = defaultdict(int)
    qs = HabitLog.objects.filter(
        user=user, log_date__gte=start, log_date__lte=today, status__in=['done', 'partial']
    ).values('log_date').annotate(c=Count('id'))
    for row in qs:
        counts[row['log_date']] = row['c']
    out: list[dict] = []
    cursor = start
    while cursor <= today:
        out.append({'date': cursor, 'count': counts.get(cursor, 0)})
        cursor += timedelta(days=1)
    return out


def user_best_days(user, days: int = 90) -> list[dict]:
    """Completion rate by weekday over last `days` days."""
    today = timezone.localdate()
    start = today - timedelta(days=days - 1)
    expected_per_day = defaultdict(int)
    done_per_day = defaultdict(int)
    cursor = start
    habits = list(Habit.objects.filter(user=user, is_active=True).select_related('schedule'))
    while cursor <= today:
        wd = cursor.isoweekday()
        for habit in habits:
            schedule = getattr(habit, 'schedule', None)
            if schedule is None or schedule.is_due_on(cursor):
                expected_per_day[wd] += 1
        cursor += timedelta(days=1)
    qs = HabitLog.objects.filter(
        user=user, log_date__gte=start, log_date__lte=today, status__in=['done', 'partial']
    )
    for log in qs.values_list('log_date', flat=True):
        done_per_day[log.isoweekday()] += 1
    rows: list[dict] = []
    for wd in range(1, 8):
        expected = expected_per_day[wd]
        done = done_per_day[wd]
        rate = int(100 * done / expected) if expected else 0
        rows.append({
            'weekday': wd,
            'short': WEEKDAY_RU[wd],
            'name': WEEKDAY_FULL_RU[wd],
            'rate': rate,
            'done': done,
            'expected': expected,
        })
    rows.sort(key=lambda r: r['rate'], reverse=True)
    return rows


def user_category_breakdown(user, days: int = 30) -> list[dict]:
    """Completion-weighted breakdown of last `days` days across analytical categories."""
    today = timezone.localdate()
    start = today - timedelta(days=days - 1)
    qs = HabitLog.objects.filter(
        user=user,
        log_date__gte=start,
        log_date__lte=today,
        status__in=['done', 'partial'],
    ).select_related('habit')
    weights_by_tag = defaultdict(list)
    for w in TagCategoryWeight.objects.select_related('tag', 'category'):
        weights_by_tag[w.tag_id].append((w.category, w.weight))

    category_totals = defaultdict(float)
    for log in qs:
        habit_tags = list(log.habit.tags.all())
        if not habit_tags:
            category_totals['Без категории'] += 1.0
            continue
        # Weight per tag, then divide by tag count to keep per-log total at 1.
        per_tag = 1.0 / len(habit_tags)
        for tag in habit_tags:
            weights = weights_by_tag.get(tag.id, [])
            if not weights:
                category_totals['Без категории'] += per_tag
                continue
            for category, weight in weights:
                category_totals[category.name] += per_tag * weight
    total = sum(category_totals.values()) or 1.0
    rows = [
        {'name': name, 'value': round(value, 2), 'pct': int(100 * value / total)}
        for name, value in category_totals.items()
    ]
    rows.sort(key=lambda r: r['pct'], reverse=True)
    return rows


def user_summary(user, days: int = 30) -> dict:
    """High-level stats for analytics page."""
    today = timezone.localdate()
    start = today - timedelta(days=days - 1)
    logs = HabitLog.objects.filter(
        user=user, log_date__gte=start, log_date__lte=today
    )
    done = logs.filter(status__in=['done', 'partial']).count()
    total = logs.count() or 1
    avg_completion = int(100 * done / total) if total else 0
    total_minutes = logs.filter(status__in=['done', 'partial']).aggregate(
        total=Sum('duration_minutes')
    )['total'] or 0
    return {
        'period_days': days,
        'completion_rate': avg_completion,
        'total_minutes': int(total_minutes),
        'logs': done,
        'best_days': user_best_days(user, days=days),
        'category_breakdown': user_category_breakdown(user, days=days),
        'activity_per_day': user_activity_per_day(user, days=days),
    }


def time_of_day_bucket(time_obj) -> str:
    if time_obj is None:
        return 'unknown'
    hour = time_obj.hour
    if 5 <= hour < 12:
        return 'morning'
    if 12 <= hour < 17:
        return 'afternoon'
    if 17 <= hour < 22:
        return 'evening'
    return 'night'
