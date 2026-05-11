"""Signals: profile auto-creation, gamification on log save / delete."""
from django.conf import settings
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from habits.models import HabitLog, UserProfile
from habits.services.gamification import award_xp_for_log, check_achievements, refresh_streaks
from habits.services.insights import generate_insights


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def ensure_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)


@receiver(post_save, sender=HabitLog)
def on_habit_log_saved(sender, instance: HabitLog, created, **kwargs):
    profile, _ = UserProfile.objects.get_or_create(user=instance.user)
    if created and instance.status in {'done', 'partial'}:
        award_xp_for_log(profile, instance)
    refresh_streaks(profile)
    check_achievements(profile)
    if created:
        generate_insights(instance.user)


@receiver(post_delete, sender=HabitLog)
def on_habit_log_deleted(sender, instance: HabitLog, **kwargs):
    # When a log is removed (undo button, admin action, cascade from habit
    # destroy) the cached ``current_streak`` / ``best_streak`` on the user's
    # profile would otherwise stay at their pre-delete values. Recompute so
    # the dashboard "Серия N дн." pill reflects reality.
    profile = UserProfile.objects.filter(user=instance.user).first()
    if profile is not None:
        refresh_streaks(profile)
