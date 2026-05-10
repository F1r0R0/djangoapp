"""Inject the user's profile and a shared "add habit" form into templates."""
from habits.forms import HabitForm
from habits.models import UserProfile


def profile_context(request):
    if not getattr(request, 'user', None) or not request.user.is_authenticated:
        return {}
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    return {
        'profile': profile,
        # Always available so the shared "create habit" modal in base.html
        # works on every authenticated page (dashboard, habit_detail, …).
        'add_form': HabitForm(),
    }
