TAIL=100

migrate:
	docker exec habithamster-backend /bin/bash -c 'python manage.py migrate'
migrations:
	docker exec habithamster-backend /bin/bash -c 'python manage.py makemigrations'
shell:
	docker exec habithamster-backend /bin/bash -c 'python manage.py shell'
logs:
	docker logs --tail=$(TAIL) -f habithamster-backend
