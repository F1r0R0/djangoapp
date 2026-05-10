"""Generate user-facing insights based on history."""
from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from habits.models import UserInsight
from habits.services.analytics import user_best_days, user_category_breakdown


def generate_insights(user) -> list[UserInsight]:
    """Re-generate the latest set of insights for a user (idempotent for today)."""
    today = timezone.localdate()
    UserInsight.objects.filter(user=user, created_at__date=today).delete()

    new_insights: list[UserInsight] = []

    best_days = user_best_days(user, days=30)
    if best_days and best_days[0]['rate'] > 0:
        best = best_days[0]
        new_insights.append(UserInsight.objects.create(
            user=user,
            insight_type='best_day',
            title='Лучший день недели',
            message=f'{best["name"]} — твой самый продуктивный день. {best["rate"]}% выполнения.',
            payload={'weekday': best['weekday'], 'rate': best['rate']},
            period_start=today - timedelta(days=29),
            period_end=today,
        ))
        weak = best_days[-1]
        if weak['rate'] < best['rate']:
            new_insights.append(UserInsight.objects.create(
                user=user,
                insight_type='weak_day',
                title='Слабый день недели',
                message=f'{weak["name"]} — самый слабый день, всего {weak["rate"]}%. Может, стоит запланировать что-то лёгкое?',
                payload={'weekday': weak['weekday'], 'rate': weak['rate']},
                period_start=today - timedelta(days=29),
                period_end=today,
            ))

    breakdown = user_category_breakdown(user, days=30)
    if breakdown:
        top = breakdown[0]
        new_insights.append(UserInsight.objects.create(
            user=user,
            insight_type='tag_analytics',
            title=f'Топ-категория: {top["name"]}',
            message=f'{int(top["pct"])}% твоих привычек относятся к "{top["name"]}". Хороший фокус!',
            payload={'category': top['name'], 'pct': top['pct']},
            period_start=today - timedelta(days=29),
            period_end=today,
        ))

    return new_insights
