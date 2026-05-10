"""Signals: profile auto-creation, gamification on log save."""
from django.conf import settings
from django.db.models.signals import post_save
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
