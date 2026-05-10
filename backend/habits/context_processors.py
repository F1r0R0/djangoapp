"""Inject the user's profile into every template context."""
from habits.models import UserProfile


def profile_context(request):
    if not getattr(request, 'user', None) or not request.user.is_authenticated:
        return {}
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    return {
        'profile': profile,
    }
