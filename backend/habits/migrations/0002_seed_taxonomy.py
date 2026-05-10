"""Data migration: populate the tag taxonomy and core achievements on first migrate."""
from django.core.management import call_command
from django.db import migrations


def seed(apps, schema_editor):
    call_command('seed_taxonomy')


def unseed(apps, schema_editor):
    Tag = apps.get_model('habits', 'Tag')
    TagCategory = apps.get_model('habits', 'TagCategory')
    ActivityType = apps.get_model('habits', 'ActivityType')
    Achievement = apps.get_model('habits', 'Achievement')
    Tag.objects.all().delete()
    TagCategory.objects.all().delete()
    ActivityType.objects.all().delete()
    Achievement.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('habits', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
