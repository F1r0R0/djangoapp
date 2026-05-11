"""Forms for the HTML pages."""
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from habits.models import Habit, HabitSchedule, Tag


User = get_user_model()

# Shared Tailwind class string for text inputs across auth forms.
_INPUT_CSS = (
    'w-full px-4 py-3 rounded-xl border border-gray-200'
    ' focus:border-green-500 focus:ring-2 focus:ring-green-200 outline-none'
)


class RegisterForm(UserCreationForm):
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={'class': _INPUT_CSS, 'placeholder': 'email@example.com'}),
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={'class': _INPUT_CSS, 'placeholder': 'твой_никнейм'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ('password1', 'password2'):
            self.fields[name].widget.attrs.update({'class': _INPUT_CSS, 'placeholder': '••••••••'})


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'class': _INPUT_CSS, 'placeholder': 'логин'})
        self.fields['password'].widget.attrs.update({'class': _INPUT_CSS, 'placeholder': '••••••••'})


FREQUENCY_CHOICES = HabitSchedule.FREQUENCY_CHOICES


class HabitForm(forms.ModelForm):
    duration_minutes = forms.IntegerField(min_value=0, max_value=600, required=False, initial=15)
    frequency_type = forms.ChoiceField(choices=FREQUENCY_CHOICES, initial='daily')
    days_of_week = forms.CharField(required=False, initial='1,2,3,4,5,6,7')
    reminder_time = forms.TimeField(required=False)
    # Optional time-of-day window (e.g. 13:00..14:00). Both blank => all-day.
    window_start = forms.TimeField(required=False, widget=forms.TimeInput(attrs={'type': 'time'}))
    window_end = forms.TimeField(required=False, widget=forms.TimeInput(attrs={'type': 'time'}))
    tag_names = forms.CharField(required=False, help_text='Через запятую: бег, йога, чтение')

    def clean(self):
        cleaned = super().clean()
        # Time window must be specified as a pair, or omitted entirely.
        ws, we = cleaned.get('window_start'), cleaned.get('window_end')
        if (ws and not we) or (we and not ws):
            raise forms.ValidationError(
                'Укажи и время начала, и время конца окна — либо оставь оба поля пустыми.'
            )  # noqa: E501
        return cleaned

    class Meta:
        model = Habit
        fields = ['title', 'description', 'icon', 'color', 'target_type', 'target_value', 'target_unit']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'например: Утренняя медитация'}),
            'description': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Зачем тебе эта привычка?'}),
        }

    def save(self, user, commit=True):
        instance = super().save(commit=False)
        instance.user = user
        # Reconcile target_type / target_value / target_unit. The modal
        # ships hidden defaults of ``target_value=15`` and ``target_unit=minutes``
        # regardless of the chosen type, so we normalise on save:
        #   * minutes → use the duration input as the value, unit = minutes
        #   * check   → boolean done/skip, value/unit are meaningless → 0/'time'
        #   * count   → keep submitted value, default unit to 'times'
        duration = self.cleaned_data.get('duration_minutes') or 0
        if instance.target_type == 'minutes':
            instance.target_value = duration or 15
            instance.target_unit = 'minutes'
        elif instance.target_type == 'check':
            instance.target_value = 1
            if instance.target_unit == 'minutes':
                instance.target_unit = 'times'
        else:  # count
            if not instance.target_value:
                instance.target_value = 1
            if instance.target_unit == 'minutes':
                instance.target_unit = 'times'
        instance.save()
        # Schedule.
        sched, _ = HabitSchedule.objects.get_or_create(habit=instance)
        sched.frequency_type = self.cleaned_data['frequency_type']
        sched.days_of_week = self.cleaned_data['days_of_week'] or '1,2,3,4,5,6,7'
        sched.reminder_time = self.cleaned_data.get('reminder_time') or None
        sched.window_start = self.cleaned_data.get('window_start') or None
        sched.window_end = self.cleaned_data.get('window_end') or None
        sched.save()
        # Tags by name (find or create).
        names_raw = self.cleaned_data.get('tag_names', '') or ''
        names = [n.strip() for n in names_raw.split(',') if n.strip()]
        if names:
            instance.tags.clear()
            for name in names:
                tag, _ = Tag.objects.get_or_create(
                    name=name,
                    defaults={'slug': _slugify_unique(name)},
                )
                instance.tags.add(tag)
        return instance


def _slugify_unique(name: str) -> str:
    from django.utils.text import slugify

    # ``allow_unicode=True`` keeps Cyrillic readable in the URL rather than
    # falling back to the literal 'tag' suffix chain for every tag (every
    # Russian tag would collide on the base "tag" without it).
    base = slugify(name, allow_unicode=True) or 'tag'
    candidate = base
    i = 1
    while Tag.objects.filter(slug=candidate).exists():
        i += 1
        candidate = f'{base}-{i}'
    return candidate
