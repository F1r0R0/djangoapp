# Deploying HabitHamster on a VPS

The repo ships a production Docker stack — Postgres + Django (gunicorn) +
nginx — driven by `docker-compose.prod.yml`. Data lives in named Docker
volumes, so the database survives container restarts and host reboots.

## Prereqs on the host

Tested on Ubuntu 24.04. Install Docker and the compose plugin:

```bash
apt-get update
apt-get install -y ca-certificates curl gnupg git
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" \
  | tee /etc/apt/sources.list.d/docker.list > /dev/null
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

## First-time deploy

```bash
git clone https://github.com/F1r0R0/djangoapp.git /opt/habithamster
cd /opt/habithamster

# Edit secrets — at minimum SECRET_KEY, POSTGRES_PASSWORD, ALLOWED_HOSTS.
cp .env.prod.example .env.prod
${EDITOR:-nano} .env.prod

docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
```

The `web` container does the following on every boot:

- `collectstatic --noinput` — gathers static assets into the shared volume.
- `migrate --noinput` — applies pending migrations to Postgres.
- `seed_taxonomy` — idempotent; populates default activity types/tags.
- `createsuperuser --noinput` — creates the admin user (only on first run;
  silently fails afterwards because the username already exists).

Visit `http://<host>/` to use the app and `http://<host>/admin/` for the
Django admin (default `admin` / `admin` — **change the password immediately**).

## Updating

```bash
cd /opt/habithamster
git pull
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
```

## Backups

The Postgres data lives in the `db_data` Docker volume. A simple manual
backup:

```bash
docker exec habithamster-db pg_dump -U habithamster habithamster \
  | gzip > /var/backups/habithamster-$(date +%F).sql.gz
```

## Logs

```bash
docker compose -f docker-compose.prod.yml logs -f web
docker compose -f docker-compose.prod.yml logs -f nginx
docker compose -f docker-compose.prod.yml logs -f db
```
