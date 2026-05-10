"""XP, levels and achievements."""
from __future__ import annotations

from django.db.models import Sum
from django.utils import timezone

from habits.models import Achievement, HabitLog, UserAchievement, UserProfile
from habits.services.streak import user_current_streak


XP_PER_DONE = 10
XP_PER_PARTIAL = 4
XP_PER_MINUTE = 1


def award_xp_for_log(profile: UserProfile, log: HabitLog) -> int:
    """Award XP for a saved HabitLog. Returns delta XP."""
    delta = 0
    if log.status == 'done':
        delta += XP_PER_DONE
    elif log.status == 'partial':
        delta += XP_PER_PARTIAL
    delta += min(log.duration_minutes, 60) * XP_PER_MINUTE // 4  # mild bonus for time
    if delta <= 0:
        return 0
    profile.xp += delta
    while profile.xp >= profile.xp_for_next_level:
        profile.xp -= profile.xp_for_next_level
        profile.level += 1
    profile.save(update_fields=['xp', 'level', 'updated_at'])
    return delta


def refresh_streaks(profile: UserProfile) -> None:
    streak = user_current_streak(profile.user)
    profile.current_streak = streak
    if streak > profile.best_streak:
        profile.best_streak = streak
    if streak >= 5:
        profile.mascot_mood = 'excited'
    elif streak >= 1:
        profile.mascot_mood = 'happy'
    else:
        profile.mascot_mood = 'sad'
    profile.save(update_fields=['current_streak', 'best_streak', 'mascot_mood', 'updated_at'])


def check_achievements(profile: UserProfile) -> list[Achievement]:
    """Unlock any achievements whose conditions the user has now met."""
    user = profile.user
    unlocked_codes = set(
        UserAchievement.objects.filter(user=user).values_list('achievement__code', flat=True)
    )
    candidates = Achievement.objects.exclude(code__in=unlocked_codes)
    newly_unlocked: list[Achievement] = []
    completion_count = HabitLog.objects.filter(user=user, status__in=['done', 'partial']).count()
    total_minutes = HabitLog.objects.filter(
        user=user, status__in=['done', 'partial']
    ).aggregate(total=Sum('duration_minutes'))['total'] or 0
    for achievement in candidates:
        unlocked = False
        if achievement.condition_type == 'streak':
            unlocked = profile.best_streak >= achievement.condition_value
        elif achievement.condition_type == 'completion_count':
            unlocked = completion_count >= achievement.condition_value
        elif achievement.condition_type == 'total_time':
            unlocked = total_minutes >= achievement.condition_value
        elif achievement.condition_type == 'xp':
            unlocked = profile.level >= achievement.condition_value
        if unlocked:
            UserAchievement.objects.create(
                user=user, achievement=achievement, unlocked_at=timezone.now()
            )
            profile.xp += achievement.xp_reward
            newly_unlocked.append(achievement)
    if newly_unlocked:
        # Re-level after bonus XP.
        while profile.xp >= profile.xp_for_next_level:
            profile.xp -= profile.xp_for_next_level
            profile.level += 1
        profile.save(update_fields=['xp', 'level', 'updated_at'])
    return newly_unlocked
