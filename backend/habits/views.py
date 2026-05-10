"""HTML views for HabitHamster."""
from __future__ import annotations

from datetime import date, datetime, timedelta

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_POST

from habits.forms import HabitForm, LoginForm, RegisterForm
from habits.models import Achievement, Habit, HabitLog, UserAchievement, UserInsight
from habits.services.analytics import (
    completion_rate_for_habit,
    habit_completed_count,
    habit_heatmap,
    habit_total_minutes,
    user_activity_per_day,
    user_best_days,
    user_category_breakdown,
)
from habits.services.streak import habit_best_streak, habit_current_streak


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

    weekly_total = HabitLog.objects.filter(
        user=request.user,
        log_date__gte=today - timedelta(days=6),
        log_date__lte=today,
    )
    wt_total = weekly_total.count() or 1
    wt_done = weekly_total.filter(status__in=['done', 'partial']).count()
    weekly_completion_rate = int(100 * wt_done / wt_total)

    insights = UserInsight.objects.filter(user=request.user).order_by('-created_at')[:3]

    add_form = HabitForm()

    context = {
        'today': today,
        'habits': items,
        'due_today': due_today,
        'done_today': done_today,
        'weekly_completion_rate': weekly_completion_rate,
        'wt_done': wt_done,
        'wt_total': max(weekly_total.count(), 1),
        'wt_total_real': weekly_total.count(),
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
        return {
            'habit': habit,
            'time': schedule.reminder_time if schedule else None,
            'is_done': bool(log and log.status in {'done', 'partial'}),
            'is_planned': not bool(log and log.status in {'done', 'partial'}),
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

    # Weekly progress card on the banner.
    week_start, week_end = _week_bounds(today)
    week_logs = HabitLog.objects.filter(
        user=request.user,
        log_date__gte=week_start,
        log_date__lte=week_end,
    )
    wt_total_real = week_logs.count()
    wt_done = week_logs.filter(status__in=['done', 'partial']).count()
    weekly_completion_rate = int(100 * wt_done / wt_total_real) if wt_total_real else 0

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
    return redirect(request.POST.get('next') or 'dashboard')


@login_required
@require_POST
def habit_log_today(request, habit_id: int):
    habit = get_object_or_404(Habit, id=habit_id, user=request.user)
    today = timezone.localdate()
    status = request.POST.get('status', 'done')
    duration = int(request.POST.get('duration_minutes') or 0)
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
    messages.success(request, f'Отметка для "{habit.title}" сохранена ({status}).')
    return redirect(request.POST.get('next') or 'dashboard')


@login_required
@require_POST
def habit_delete(request, habit_id: int):
    habit = get_object_or_404(Habit, id=habit_id, user=request.user)
    habit.is_active = False
    habit.save(update_fields=['is_active', 'updated_at'])
    messages.success(request, f'Привычка "{habit.title}" архивирована.')
    return redirect('dashboard')


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
    achievements_data = [
        {
            'achievement': a,
            'unlocked': a.id in unlocked_ids,
        }
        for a in achievements
    ]
    # Average completion rate.
    if best_days:
        avg = round(sum(b['rate'] for b in best_days) / len(best_days))
    else:
        avg = 0

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
    morning_done = HabitLog.objects.filter(
        user=request.user,
        status__in=['done', 'partial'],
        log_date__gte=timezone.localdate() - timedelta(days=days - 1),
        created_at__hour__lt=12,
    ).count()
    total_done = HabitLog.objects.filter(
        user=request.user,
        status__in=['done', 'partial'],
        log_date__gte=timezone.localdate() - timedelta(days=days - 1),
    ).count()
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
    }
    return render(request, 'analytics.html', context)
