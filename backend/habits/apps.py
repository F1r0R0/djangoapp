from django.apps import AppConfig


class HabitsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'habits'
    verbose_name = 'HabitHamster'

    def ready(self):
        # Wire up signals (XP / achievements on HabitLog save).
        from habits import signals  # noqa: F401
