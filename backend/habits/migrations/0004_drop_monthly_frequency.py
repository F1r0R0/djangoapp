"""Convert legacy 'monthly' schedules to 'daily' and tighten choices."""
from django.db import migrations, models


def monthly_to_daily(apps, schema_editor):
    HabitSchedule = apps.get_model('habits', 'HabitSchedule')
    HabitSchedule.objects.filter(frequency_type='monthly').update(frequency_type='daily')


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('habits', '0003_habitschedule_window_end_habitschedule_window_start'),
    ]

    operations = [
        migrations.RunPython(monthly_to_daily, noop),
        migrations.AlterField(
            model_name='habitschedule',
            name='frequency_type',
            field=models.CharField(
                choices=[
                    ('daily', 'Ежедневно'),
                    ('weekly', 'По дням недели'),
                    ('custom', 'Кастомно'),
                ],
                default='daily',
                max_length=16,
            ),
        ),
    ]
