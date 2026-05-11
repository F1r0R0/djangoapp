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


def user_period_progress(user, start: date, end: date) -> dict:
    """Completion progress for ``user`` over the inclusive ``[start, end]`` range.

    Returns a dict with:
      * ``expected``: count of (active habit × day) pairs where the habit's
        schedule says it was due in the period (or no schedule = always due).
        This is the denominator for a fair "x of y" progress card.
      * ``done``: number of HabitLog rows in the period whose status counts
        as success ("done" or "partial").
      * ``rate``: integer 0..100 = ``done / expected`` capped at 100.

    Using ``expected`` (rather than the count of logged rows) is what makes
    the dashboard's weekly progress card honest — otherwise a user who only
    ever clicks "выполнить" would always read 100%.
    """
    habits = list(
        Habit.objects.filter(user=user, is_active=True).select_related('schedule')
    )
    expected = 0
    cursor = start
    while cursor <= end:
        for habit in habits:
            schedule = getattr(habit, 'schedule', None)
            if schedule is None or schedule.is_due_on(cursor):
                expected += 1
        cursor += timedelta(days=1)
    done = HabitLog.objects.filter(
        user=user,
        log_date__gte=start,
        log_date__lte=end,
        status__in=['done', 'partial'],
    ).count()
    rate = min(int(100 * done / expected), 100) if expected else 0
    return {'expected': expected, 'done': done, 'rate': rate}


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


# ---------------------------------------------------------------------------
# Per-habit hour-of-day analytics ("when do I actually do this?").
# ---------------------------------------------------------------------------


_HOUR_BUCKETS = [
    # (start_hour_inclusive, end_hour_exclusive, label, range_label, css)
    (5, 12, 'Утро', '05:00–11:59', 'bg-yellow-100 text-yellow-800'),
    (12, 17, 'День', '12:00–16:59', 'bg-orange-100 text-orange-800'),
    (17, 22, 'Вечер', '17:00–21:59', 'bg-indigo-100 text-indigo-800'),
    (22, 29, 'Ночь', '22:00–04:59', 'bg-slate-200 text-slate-700'),
]

# Background tint that paints behind the 24-bar chart so the bucket boundaries
# are visible without a legend. Indexed by hour-of-day 0..23.
_HOUR_BG = [
    # 00..04 → night
    *['rgba(148,163,184,0.18)'] * 5,
    # 05..11 → morning (yellow)
    *['rgba(250,204,21,0.18)'] * 7,
    # 12..16 → day (orange)
    *['rgba(251,146,60,0.18)'] * 5,
    # 17..21 → evening (indigo)
    *['rgba(99,102,241,0.18)'] * 5,
    # 22..23 → night
    *['rgba(148,163,184,0.18)'] * 2,
]


def habit_hour_distribution(habit: Habit, days: int = 90) -> dict:
    """Hour-of-day completion histogram for a single habit.

    Returns a dict with:
      * ``hours``: list of 24 ints (count of successful logs per local hour).
      * ``buckets``: list of {label, emoji, count, pct} for morning / day / evening / night.
      * ``peak_hour``: integer 0..23 with the most logs, or ``None`` if no logs.
      * ``peak_bucket``: human label for the dominant time of day.
      * ``total``: total number of successful logs considered.

    ``created_at`` is always converted to the user's local time before
    bucketing so the Europe/Moscow site doesn't show midnight bias from
    UTC-stored timestamps.
    """
    today = timezone.localdate()
    start = today - timedelta(days=days - 1)
    logs = HabitLog.objects.filter(
        habit=habit,
        status__in=['done', 'partial'],
        log_date__gte=start,
        log_date__lte=today,
    ).only('created_at')

    hours = [0] * 24
    total = 0
    for log in logs:
        local_dt = timezone.localtime(log.created_at)
        hours[local_dt.hour] += 1
        total += 1

    buckets: list[dict] = []
    for start_h, end_h, label, range_label, css in _HOUR_BUCKETS:
        if end_h > 24:
            count = sum(hours[start_h:24]) + sum(hours[0:end_h - 24])
        else:
            count = sum(hours[start_h:end_h])
        buckets.append(
            {
                'label': label,
                'range_label': range_label,
                'css': css,
                'count': count,
                'pct': int(100 * count / total) if total else 0,
            }
        )

    peak_hour: int | None = None
    if total:
        peak_hour = max(range(24), key=lambda h: hours[h])
    peak_bucket = max(buckets, key=lambda b: b['count'])['label'] if total else None

    # Best 3-hour rolling window (wraps midnight). Used for "Лучшее окно".
    best_window: dict | None = None
    if total:
        best_start = 0
        best_count = -1
        for start in range(24):
            window_count = sum(hours[(start + i) % 24] for i in range(3))
            if window_count > best_count:
                best_count = window_count
                best_start = start
        if best_count > 0:
            window_end = (best_start + 3) % 24
            best_window = {
                'start': best_start,
                'end_exclusive': window_end,
                'count': best_count,
                'pct': int(100 * best_count / total),
                'label': (
                    f"{best_start:02d}:00–{((best_start + 2) % 24):02d}:59"
                ),
            }

    return {
        'hours': hours,
        'buckets': buckets,
        'peak_hour': peak_hour,
        'peak_bucket': peak_bucket,
        'total': total,
        'best_window': best_window,
        'hour_bg': _HOUR_BG,
    }


# ---------------------------------------------------------------------------
# Habit-to-habit correlations ("when I do X, I'm N% more likely to do Y").
# ---------------------------------------------------------------------------


def user_habit_correlations(user, days: int = 60, min_pairs: int = 5) -> list[dict]:
    """Top habit pairs that the user tends to complete on the same day.

    For each ordered pair (a, b) of the user's currently-active habits, compute
    ``conditional = P(b done | a done) - P(b done)``. A positive lift means
    "doing a makes b more likely on the same day". Pairs where ``a`` was logged
    fewer than ``min_pairs`` times are dropped — small denominators produce
    noisy correlations.

    Returns up to 5 strongest pairs as dicts with ``a_title``, ``b_title``,
    ``a_days``, ``together``, ``conditional_pct`` (P(b|a) in 0..100) and
    ``baseline_pct`` (raw P(b) over the same window).
    """
    today = timezone.localdate()
    start = today - timedelta(days=days - 1)
    habits = list(Habit.objects.filter(user=user, is_active=True).only('id', 'title'))
    if len(habits) < 2:
        return []

    # Build "day -> set of habit ids done on that day".
    day_habits: dict[date, set[int]] = defaultdict(set)
    qs = HabitLog.objects.filter(
        user=user,
        status__in=['done', 'partial'],
        log_date__gte=start,
        log_date__lte=today,
    ).values_list('habit_id', 'log_date')
    for habit_id, log_date in qs:
        day_habits[log_date].add(habit_id)

    # Per-habit total days completed in window.
    a_count: dict[int, int] = defaultdict(int)
    for ids in day_habits.values():
        for hid in ids:
            a_count[hid] += 1
    period_days = (today - start).days + 1

    pairs: list[dict] = []
    by_id = {h.id: h for h in habits}
    for a in habits:
        if a_count[a.id] < min_pairs:
            continue
        for b in habits:
            if a.id == b.id:
                continue
            together = sum(1 for ids in day_habits.values() if a.id in ids and b.id in ids)
            if together == 0:
                continue
            p_b_given_a = together / a_count[a.id]
            p_b = a_count[b.id] / period_days
            lift = p_b_given_a - p_b
            pairs.append(
                {
                    'a_id': a.id,
                    'b_id': b.id,
                    'a_title': by_id[a.id].title,
                    'b_title': by_id[b.id].title,
                    'a_days': a_count[a.id],
                    'together': together,
                    'conditional_pct': int(100 * p_b_given_a),
                    'baseline_pct': int(100 * p_b),
                    'lift': lift,
                }
            )

    # Strongest positive lifts first; ties broken by absolute conditional %.
    pairs.sort(key=lambda r: (r['lift'], r['conditional_pct']), reverse=True)
    return pairs[:5]
