"""HTML views for HabitHamster."""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_POST

from habits.forms import HabitForm, LoginForm, RegisterForm
from habits.models import Achievement, Habit, HabitLog, UserAchievement, UserInsight
from habits.services.analytics import (
    completion_rate_for_habit,
    habit_completed_count,
    habit_heatmap,
    habit_hour_distribution,
    habit_total_minutes,
    user_activity_per_day,
    user_best_days,
    user_category_breakdown,
    user_habit_correlations,
    user_period_progress,
)
from habits.services.streak import habit_best_streak, habit_current_streak
from django.utils.http import url_has_allowed_host_and_scheme


# ---------------------------------------------------------------------------
# Auth pages.
# ---------------------------------------------------------------------------


class HHLoginView(LoginView):
    template_name = 'auth/login.html'
    authentication_form = LoginForm
    redirect_authenticated_user = True


class HHLogoutView(LogoutView):
    next_page = reverse_lazy('landing')


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Добро пожаловать в HabitHamster!')
            return redirect('dashboard')
    else:
        form = RegisterForm()
    return render(request, 'auth/register.html', {'form': form})


# ---------------------------------------------------------------------------
# Pages.
# ---------------------------------------------------------------------------


def landing(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'landing.html')


@login_required
def dashboard(request):
    today: date = timezone.localdate()
    now = timezone.localtime()
    habits = list(
        Habit.objects.filter(user=request.user, is_active=True).select_related('schedule').prefetch_related('tags')
    )
    logs_today = {log.habit_id: log for log in HabitLog.objects.filter(user=request.user, log_date=today)}
    items = []
    due_today = 0
    done_today = 0
    for habit in habits:
        schedule = getattr(habit, 'schedule', None)
        is_due = True if schedule is None else schedule.is_due_on(today)
        is_active_now = True if schedule is None else schedule.is_active_at(now)
        log = logs_today.get(habit.id)
        is_done = bool(log and log.status in {'done', 'partial'})
        if is_due:
            due_today += 1
        if is_done:
            done_today += 1
        items.append(
            {
                'habit': habit,
                'is_due': is_due,
                'is_active_now': is_active_now,
                'is_done': is_done,
                'today_status': log.status if log else None,
                'log': log,
            }
        )

    # Mini month calendar with intensity.
    cal_start = today.replace(day=1)
    next_month = cal_start.replace(day=28) + timedelta(days=4)
    cal_end = next_month - timedelta(days=next_month.day)
    cal_logs = HabitLog.objects.filter(
        user=request.user,
        log_date__gte=cal_start,
        log_date__lte=cal_end,
        status__in=['done', 'partial'],
    ).values_list('log_date', flat=True)
    cal_active = set(cal_logs)
    # Build an array of {date, in_month, has_activity, is_today}.
    calendar_cells: list[dict] = []
    # Pad to start on Monday.
    start_offset = cal_start.isoweekday() - 1  # Mon=0
    pad_start = cal_start - timedelta(days=start_offset)
    cursor = pad_start
    while cursor <= cal_end or cursor.isoweekday() != 1:
        calendar_cells.append(
            {
                'date': cursor,
                'in_month': cursor.month == today.month,
                'has_activity': cursor in cal_active,
                'is_today': cursor == today,
            }
        )
        cursor += timedelta(days=1)
        if len(calendar_cells) >= 42:
            break

    # Weekly progress card. Use the current ISO week (Mon–Sun) for parity
    # with the calendar page, and the expected-vs-done denominator from
    # services.analytics so the rate isn't inflated to ~100% just because
    # the user only ever logs successful completions.
    week_start, week_end = _week_bounds(today)
    week_progress = user_period_progress(request.user, week_start, week_end)

    insights = UserInsight.objects.filter(user=request.user).order_by('-created_at')[:3]

    add_form = HabitForm()

    context = {
        'today': today,
        'habits': items,
        'due_today': due_today,
        'done_today': done_today,
        'weekly_completion_rate': week_progress['rate'],
        'wt_done': week_progress['done'],
        'wt_total': max(week_progress['expected'], 1),
        'wt_total_real': week_progress['expected'],
        'calendar_cells': calendar_cells,
        'calendar_month': today,
        'insights': insights,
        'add_form': add_form,
    }
    return render(request, 'dashboard.html', context)


# ---------------------------------------------------------------------------
# Calendar.
# ---------------------------------------------------------------------------


_CALENDAR_HOUR_RANGE = list(range(6, 24))  # 06:00 — 23:00
_WEEKDAY_LABELS = ['ПН', 'ВТ', 'СР', 'ЧТ', 'ПТ', 'СБ', 'ВС']
_RUSSIAN_MONTHS = [
    'Январь',
    'Февраль',
    'Март',
    'Апрель',
    'Май',
    'Июнь',
    'Июль',
    'Август',
    'Сентябрь',
    'Октябрь',
    'Ноябрь',
    'Декабрь',
]


def _parse_anchor_date(raw: str | None, fallback: date) -> date:
    """Parse ?date=YYYY-MM-DD into a real date, falling back to today."""
    if not raw:
        return fallback
    try:
        return datetime.strptime(raw, '%Y-%m-%d').date()
    except ValueError:
        return fallback


def _week_bounds(anchor: date) -> tuple[date, date]:
    """Return (Monday, Sunday) of the ISO week that contains ``anchor``."""
    monday = anchor - timedelta(days=anchor.isoweekday() - 1)
    sunday = monday + timedelta(days=6)
    return monday, sunday


def _month_grid_bounds(anchor: date) -> tuple[date, date]:
    """Return the (first_visible_monday, last_visible_sunday) for a 6x7 grid."""
    first_of_month = anchor.replace(day=1)
    pad_days = first_of_month.isoweekday() - 1
    grid_start = first_of_month - timedelta(days=pad_days)
    grid_end = grid_start + timedelta(days=6 * 7 - 1)
    return grid_start, grid_end


@login_required
def calendar_view(request):
    """Calendar page — day / week / month views with habit pills in a time grid.

    Driven by query parameters:
      * ``view``  — ``week`` (default) | ``day`` | ``month``
      * ``date``  — ``YYYY-MM-DD`` anchor inside the period to render
    """
    today = timezone.localdate()
    anchor = _parse_anchor_date(request.GET.get('date'), today)
    view_mode = request.GET.get('view', 'week')
    if view_mode not in {'day', 'week', 'month'}:
        view_mode = 'week'

    habits = list(
        Habit.objects.filter(user=request.user, is_active=True).select_related('schedule').prefetch_related('tags')
    )

    # Period bounds + previous / next anchors for the toolbar.
    if view_mode == 'day':
        period_start = period_end = anchor
        prev_anchor = anchor - timedelta(days=1)
        next_anchor = anchor + timedelta(days=1)
    elif view_mode == 'month':
        period_start, period_end = _month_grid_bounds(anchor)
        first_of_month = anchor.replace(day=1)
        # Step a month back / forward by sticking close to the 1st-of-month.
        prev_anchor = (first_of_month - timedelta(days=1)).replace(day=1)
        last_of_month = first_of_month.replace(day=28) + timedelta(days=4)
        last_of_month = last_of_month - timedelta(days=last_of_month.day)
        next_anchor = last_of_month + timedelta(days=1)
    else:  # week
        period_start, period_end = _week_bounds(anchor)
        prev_anchor = period_start - timedelta(days=7)
        next_anchor = period_start + timedelta(days=7)

    # Pull all logs for the visible period in a single query.
    period_logs = HabitLog.objects.filter(
        user=request.user,
        log_date__gte=period_start,
        log_date__lte=period_end,
    )
    log_lookup: dict[tuple[int, date], HabitLog] = {(log.habit_id, log.log_date): log for log in period_logs}

    def _pill_for(habit: Habit, day: date) -> dict | None:
        schedule = getattr(habit, 'schedule', None)
        if schedule and not schedule.is_due_on(day):
            return None
        log = log_lookup.get((habit.id, day))
        slot_time = None
        if schedule:
            slot_time = schedule.window_start or schedule.reminder_time
        # Both 'done' and 'partial' count as a completed pill so the calendar
        # matches the dashboard's "сегодня X / Y" counters. A 'partial' log
        # still represents progress toward the habit and should not look like
        # an unchecked slot.
        is_done = bool(log and log.status in {'done', 'partial'})
        return {
            'habit': habit,
            'time': slot_time,
            'is_done': is_done,
            'is_planned': not is_done,
            'log': log,
        }

    # --- Day / Week shared structure: time-grid columns. -------------------
    grid_days: list[dict] = []
    if view_mode in {'day', 'week'}:
        col_count = 1 if view_mode == 'day' else 7
        for offset in range(col_count):
            day = period_start + timedelta(days=offset)
            slots: dict[int, list[dict]] = {h: [] for h in _CALENDAR_HOUR_RANGE}
            untimed: list[dict] = []
            day_done = 0
            day_total = 0
            for habit in habits:
                pill = _pill_for(habit, day)
                if pill is None:
                    continue
                day_total += 1
                if pill['is_done']:
                    day_done += 1
                if pill['time'] is None:
                    untimed.append(pill)
                else:
                    hour = pill['time'].hour
                    if hour < _CALENDAR_HOUR_RANGE[0]:
                        slots[_CALENDAR_HOUR_RANGE[0]].append(pill)
                    elif hour > _CALENDAR_HOUR_RANGE[-1]:
                        slots[_CALENDAR_HOUR_RANGE[-1]].append(pill)
                    else:
                        slots[hour].append(pill)
            grid_days.append(
                {
                    'date': day,
                    'weekday_label': _WEEKDAY_LABELS[day.isoweekday() - 1],
                    'is_today': day == today,
                    'is_weekend': day.isoweekday() >= 6,
                    'slots': [{'hour': h, 'pills': slots[h]} for h in _CALENDAR_HOUR_RANGE],
                    'untimed': untimed,
                    'day_done': day_done,
                    'day_total': day_total,
                }
            )

    # --- Month grid: 6 rows of 7 days, each cell shows up to 3 habit pills.
    month_cells: list[dict] = []
    if view_mode == 'month':
        cursor = period_start
        while cursor <= period_end:
            cell_pills: list[dict] = []
            for habit in habits:
                pill = _pill_for(habit, cursor)
                if pill is None:
                    continue
                cell_pills.append(pill)
            month_cells.append(
                {
                    'date': cursor,
                    'in_month': cursor.month == anchor.month,
                    'is_today': cursor == today,
                    'pills': cell_pills[:3],
                    'extra_count': max(len(cell_pills) - 3, 0),
                }
            )
            cursor += timedelta(days=1)

    # Weekly progress card on the banner. The denominator is the number of
    # (active habit × due day) pairs in the current ISO week — see the
    # docstring of ``user_period_progress`` for why we don't divide by the
    # raw log count.
    week_start, week_end = _week_bounds(today)
    week_progress = user_period_progress(request.user, week_start, week_end)
    weekly_completion_rate = week_progress['rate']
    wt_done = week_progress['done']
    wt_total_real = week_progress['expected']

    # Display title ("Ноябрь 2023" / a date / a week range).
    if view_mode == 'day':
        period_title = f'{anchor.day} {_RUSSIAN_MONTHS[anchor.month - 1]} {anchor.year}'
    elif view_mode == 'month':
        period_title = f'{_RUSSIAN_MONTHS[anchor.month - 1]} {anchor.year}'
    else:
        if period_start.month == period_end.month:
            period_title = (
                f'{period_start.day}–{period_end.day} ' f'{_RUSSIAN_MONTHS[period_start.month - 1]} {period_start.year}'
            )
        else:
            period_title = (
                f'{period_start.day} {_RUSSIAN_MONTHS[period_start.month - 1]} – '
                f'{period_end.day} {_RUSSIAN_MONTHS[period_end.month - 1]} {period_start.year}'
            )

    context = {
        'today': today,
        'anchor': anchor,
        'view_mode': view_mode,
        'period_title': period_title,
        'prev_anchor': prev_anchor.isoformat(),
        'next_anchor': next_anchor.isoformat(),
        'today_anchor': today.isoformat(),
        'grid_days': grid_days,
        'hours': _CALENDAR_HOUR_RANGE,
        'month_cells': month_cells,
        'weekday_labels': _WEEKDAY_LABELS,
        'weekly_completion_rate': weekly_completion_rate,
        'wt_done': wt_done,
        'wt_total_real': wt_total_real,
        'add_form': HabitForm(),
    }
    return render(request, 'calendar.html', context)


@login_required
@require_POST
def habit_create(request):
    form = HabitForm(request.POST)
    if form.is_valid():
        form.save(user=request.user)
        messages.success(request, 'Привычка создана. Вперёд к серии!')
    else:
        errors = '; '.join(msg for msgs in form.errors.values() for msg in msgs)
        messages.error(request, f'Не удалось создать привычку: {errors}')
    return redirect(_safe_next(request))


_STATUS_LABELS = {
    'done': 'выполнено',
    'partial': 'частично',
    'skipped': 'пропущено',
}


def _undo_extra_tags(url: str, label: str = 'Отменить') -> str:
    """Encode an undo action for a flash toast (parsed by base.html JS)."""
    return json.dumps({'undo': url, 'label': label}, ensure_ascii=False)


def _safe_next(request, fallback: str = 'dashboard') -> str:
    """Return a same-origin ``next`` URL or fall back to a named route.

    ``next`` is propagated through hidden form inputs in many templates; an
    attacker could craft a link with ``?next=https://evil.example`` and a
    successful POST would redirect there. ``url_has_allowed_host_and_scheme``
    guards against that classic open-redirect pattern.
    """
    raw = request.POST.get('next') or request.GET.get('next')
    if raw and url_has_allowed_host_and_scheme(
        raw, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return raw
    return fallback


@login_required
@require_POST
def habit_log_today(request, habit_id: int):
    habit = get_object_or_404(Habit, id=habit_id, user=request.user)
    today = timezone.localdate()
    status = request.POST.get('status', 'done')
    if status not in {'done', 'partial', 'skipped'}:
        status = 'done'
    try:
        duration = max(int(request.POST.get('duration_minutes') or 0), 0)
    except (TypeError, ValueError):
        duration = 0
    note = request.POST.get('note', '')
    HabitLog.objects.update_or_create(
        habit=habit,
        log_date=today,
        defaults={
            'user': request.user,
            'status': status,
            'value': duration if habit.target_type == 'minutes' else habit.target_value,
            'duration_minutes': duration,
            'note': note,
        },
    )
    label = _STATUS_LABELS.get(status, status)
    messages.success(
        request,
        f'Отметка для "{habit.title}" — {label}.',
        extra_tags=_undo_extra_tags(reverse('habit_log_undo', args=[habit.id]), 'Отменить'),
    )
    return redirect(_safe_next(request))


@login_required
@require_POST
def habit_log_undo(request, habit_id: int):
    habit = get_object_or_404(Habit, id=habit_id, user=request.user)
    today = timezone.localdate()
    deleted, _ = HabitLog.objects.filter(habit=habit, user=request.user, log_date=today).delete()
    if deleted:
        # The post_delete signal recomputes current_streak / best_streak for us
        # so the dashboard pill stays accurate.
        messages.success(request, f'Отметка для "{habit.title}" снята.')
    else:
        messages.info(request, f'У "{habit.title}" сегодня и так не было отметки.')
    return redirect(_safe_next(request))


@login_required
@require_POST
def habit_delete(request, habit_id: int):
    habit = get_object_or_404(Habit, id=habit_id, user=request.user)
    habit.is_active = False
    habit.save(update_fields=['is_active', 'updated_at'])
    messages.success(
        request,
        f'Привычка "{habit.title}" архивирована.',
        extra_tags=_undo_extra_tags(reverse('habit_restore', args=[habit.id]), 'Вернуть'),
    )
    return redirect(_safe_next(request))


@login_required
@require_POST
def habit_restore(request, habit_id: int):
    habit = get_object_or_404(Habit, id=habit_id, user=request.user)
    habit.is_active = True
    habit.save(update_fields=['is_active', 'updated_at'])
    messages.success(request, f'Привычка "{habit.title}" возвращена в активные.')
    return redirect(_safe_next(request))


@login_required
@require_POST
def habit_destroy(request, habit_id: int):
    habit = get_object_or_404(Habit, id=habit_id, user=request.user)
    title = habit.title
    habit.delete()
    messages.success(request, f'Привычка "{title}" удалена безвозвратно.')
    return redirect(_safe_next(request))


@login_required
def habit_archive_list(request):
    archived = (
        Habit.objects.filter(user=request.user, is_active=False)
        .select_related('schedule')
        .prefetch_related('tags')
        .order_by('-updated_at')
    )
    items: list[dict] = []
    for habit in archived:
        items.append(
            {
                'habit': habit,
                'completed_count': habit_completed_count(habit),
                'total_minutes': habit_total_minutes(habit),
            }
        )
    return render(request, 'habits_archive.html', {'items': items})


@login_required
def habit_detail(request, habit_id: int):
    habit = get_object_or_404(Habit, id=habit_id, user=request.user)
    today = timezone.localdate()
    today_log = habit.logs.filter(log_date=today).first()

    # Heatmap covering last 90 days, organised into 13 weekly columns of 7 cells.
    heatmap = habit_heatmap(habit, days=91)
    # Group into rows by weekday.
    by_weekday: list[list[dict]] = [[], [], [], [], [], [], []]
    for cell in heatmap:
        by_weekday[cell['date'].isoweekday() - 1].append(cell)

    # Last 7 days intensity (Mon..Sun bar chart on the detail page).
    last7_logs = habit.logs.filter(log_date__gte=today - timedelta(days=6))
    weekday_minutes = [0] * 7
    for log in last7_logs:
        if log.status in {'done', 'partial'}:
            idx = log.log_date.isoweekday() - 1
            weekday_minutes[idx] += log.duration_minutes or habit.target_value or 1
    max_min = max(weekday_minutes) or 1
    intensity_bars = [
        {
            'label': label,
            'minutes': mins,
            'pct': max(int(100 * mins / max_min), 8 if mins else 4),
        }
        for label, mins in zip(['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'], weekday_minutes)
    ]

    history = habit.logs.order_by('-log_date')[:8]

    # Hour-of-day distribution — "когда я обычно это делаю" over last 90 days.
    hour_dist = habit_hour_distribution(habit, days=90)
    max_hour_count = max(hour_dist['hours']) or 1
    peak_hour = hour_dist['peak_hour']
    best_window = hour_dist['best_window']
    hour_bars = [
        {
            'hour': h,
            'count': cnt,
            # Reserve a tiny min height for non-empty hours so single logs
            # are still visible on the chart.
            'pct': max(int(100 * cnt / max_hour_count), 6 if cnt else 0),
            'is_peak': (peak_hour is not None and h == peak_hour),
            'in_window': (
                best_window is not None
                and (
                    (best_window['start'] <= best_window['end_exclusive'] and best_window['start'] <= h < best_window['end_exclusive'])
                    or (best_window['start'] > best_window['end_exclusive'] and (h >= best_window['start'] or h < best_window['end_exclusive']))
                )
            ),
            'bg': hour_dist['hour_bg'][h],
            'label': f'{h:02d}:00',
        }
        for h, cnt in enumerate(hour_dist['hours'])
    ]
    peak_hour_label = f'{peak_hour:02d}:00' if peak_hour is not None else None

    context = {
        'habit': habit,
        'today_log': today_log,
        'today': today,
        'completion_pct_30': completion_rate_for_habit(habit, days=30),
        'completion_pct_90': completion_rate_for_habit(habit, days=90),
        'total_minutes': habit_total_minutes(habit),
        'completed_count': habit_completed_count(habit),
        'current_streak': habit_current_streak(habit),
        'best_streak': habit_best_streak(habit),
        'heatmap_rows': by_weekday,
        'intensity_bars': intensity_bars,
        'history': history,
        'hour_bars': hour_bars,
        'hour_buckets': hour_dist['buckets'],
        'peak_hour_label': peak_hour_label,
        'peak_bucket': hour_dist['peak_bucket'],
        'hour_total': hour_dist['total'],
        'best_window': best_window,
    }
    return render(request, 'habit_detail.html', context)


@login_required
def analytics(request):
    period = request.GET.get('period', 'month')
    days = {'week': 7, 'month': 30, 'year': 365}.get(period, 30)
    activity = user_activity_per_day(request.user, days=days)
    best_days = user_best_days(request.user, days=days)
    breakdown = user_category_breakdown(request.user, days=days)
    insights = UserInsight.objects.filter(user=request.user).order_by('-created_at')[:5]
    achievements = Achievement.objects.all()
    unlocked_ids = set(UserAchievement.objects.filter(user=request.user).values_list('achievement_id', flat=True))
    # Map condition_type → Tailwind colour pair. The template can't compute
    # this dynamically because Tailwind's JIT only emits classes it sees as
    # literal strings — interpolating "bg-{{type}}-100" produced invalid
    # classes like `bg-streak-100` that silently fall back to no colour.
    _BADGE_PALETTE = {
        'streak': ('bg-orange-100', 'text-orange-600'),
        'completion_count': ('bg-green-100', 'text-green-600'),
        'total_time': ('bg-blue-100', 'text-blue-600'),
        'xp': ('bg-purple-100', 'text-purple-600'),
        'custom': ('bg-amber-100', 'text-amber-600'),
    }
    achievements_data = []
    for a in achievements:
        bg, fg = _BADGE_PALETTE.get(a.condition_type, ('bg-green-100', 'text-green-600'))
        achievements_data.append(
            {
                'achievement': a,
                'unlocked': a.id in unlocked_ids,
                'badge_bg': bg,
                'badge_fg': fg,
            }
        )
    # Average completion rate. Naively averaging each weekday's percentage
    # double-counts days where the user has no due habits at all (rate=0
    # because expected=0) and silently drags the headline number down. Weight
    # the average by the actual number of expected slots instead.
    total_expected = sum(b['expected'] for b in best_days)
    total_done = sum(b['done'] for b in best_days)
    avg = int(100 * total_done / total_expected) if total_expected else 0

    # Donut chart needs cumulative offsets.
    chart_categories = []
    cumulative = 0
    palette = ['#4CAF50', '#FFB74D', '#64B5F6', '#BA68C8', '#FF8A65', '#F06292']
    for idx, row in enumerate(breakdown):
        chart_categories.append(
            {
                **row,
                'color': palette[idx % len(palette)],
                'offset': cumulative,
            }
        )
        cumulative += row['pct']

    # Find best/weak day for the highlight card.
    best_day = best_days[0] if best_days else None
    # "Morning %" — share of successful logs created before local-noon. We have
    # to compute the hour in the user's timezone in Python because Django's
    # ``__hour`` ORM lookup extracts in the database's connection timezone
    # (UTC), which on a Europe/Moscow site shifts "morning" by +3h.
    recent_done_logs = HabitLog.objects.filter(
        user=request.user,
        status__in=['done', 'partial'],
        log_date__gte=timezone.localdate() - timedelta(days=days - 1),
    ).only('created_at')
    total_done = 0
    morning_done = 0
    for log in recent_done_logs:
        total_done += 1
        if timezone.localtime(log.created_at).hour < 12:
            morning_done += 1
    morning_pct = int(100 * morning_done / total_done) if total_done else 0

    # Build chart bars (downsample if too many).
    max_count = max((row['count'] for row in activity), default=0) or 1
    chart_bars = [
        {
            'date': row['date'],
            'count': row['count'],
            'height_pct': max(int(100 * row['count'] / max_count), 3 if row['count'] else 0),
        }
        for row in activity
    ]

    # Habit pair correlations — only meaningful on the month/year periods
    # where the user has enough history. Skip on the 7-day view.
    correlations = []
    if days >= 14:
        correlations = user_habit_correlations(request.user, days=days)

    context = {
        'period': period,
        'days': days,
        'activity': activity,
        'chart_bars': chart_bars,
        'best_days': best_days,
        'breakdown': breakdown,
        'chart_categories': chart_categories,
        'achievements_data': achievements_data,
        'insights': insights,
        'best_day': best_day,
        'avg_completion': avg,
        'morning_pct': morning_pct,
        'correlations': correlations,
    }
    return render(request, 'analytics.html', context)
