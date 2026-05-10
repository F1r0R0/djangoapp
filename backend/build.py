"""
Vercel build script for HabitHamster.

Vercel calls this once during deployment (configured via
``[tool.vercel.scripts] build = "python build.py"`` in ``pyproject.toml``).

It prepares a self-contained SQLite database bundled into the function image:

  1. Runs ``manage.py migrate`` to create all tables.
  2. Runs ``manage.py seed_demo --reset`` to populate demo data.
  3. Creates a superuser ``admin / admin`` so the deployed admin panel is
     immediately usable.

At runtime ``core/wsgi.py`` copies the resulting ``db.sqlite3`` file from the
read-only function image to ``/tmp`` so Django can read & write to it.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent


def main() -> None:
    os.chdir(HERE)
    sys.path.insert(0, str(HERE))

    # Force SQLite during the build, regardless of any DB_* env vars Vercel may
    # have provisioned.
    os.environ['DJANGO_SETTINGS_MODULE'] = 'core.settings'
    os.environ['USE_SQLITE'] = 'True'
    os.environ.pop('DB_NAME', None)
    # Pretend we are NOT on Vercel during the build so the seeded SQLite file
    # lives at BASE_DIR/db.sqlite3 (where wsgi.py picks it up at runtime),
    # rather than at /tmp/db.sqlite3 which would be wiped between invocations.
    os.environ.pop('VERCEL', None)

    import django

    django.setup()

    from django.contrib.auth import get_user_model
    from django.core.management import call_command

    print('==> migrate')
    call_command('migrate', '--noinput')

    print('==> seed_demo --reset')
    call_command('seed_demo', '--reset')

    print('==> create superuser admin/admin')
    User = get_user_model()
    user, created = User.objects.get_or_create(
        username='admin',
        defaults={'email': 'admin@example.com', 'is_staff': True, 'is_superuser': True},
    )
    user.is_staff = True
    user.is_superuser = True
    user.set_password('admin')
    user.save()
    print(f'    admin user {"created" if created else "updated"}: {user.username}')

    print('==> collecting demo summary')
    from django.contrib.auth import get_user_model

    print(f'    users in DB: {get_user_model().objects.count()}')

    print('==> build complete')


if __name__ == '__main__':
    main()
