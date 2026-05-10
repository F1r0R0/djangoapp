.PHONY: build up down logs shell migrate seed-demo

build:
	docker compose -f docker-compose.dev.yml build

up:
	docker compose -f docker-compose.dev.yml up -d --force-recreate

down:
	docker compose -f docker-compose.dev.yml down

logs:
	docker compose -f docker-compose.dev.yml logs -f backend

shell:
	docker compose -f docker-compose.dev.yml exec backend python manage.py shell

migrate:
	docker compose -f docker-compose.dev.yml exec backend python manage.py migrate

seed-demo:
	docker compose -f docker-compose.dev.yml exec backend python manage.py seed_demo --reset
