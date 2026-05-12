FROM python:3.12-slim
ENV PYTHONUNBUFFERED 1
ENV LANG ru_RU.UTF-8

RUN apt update -y
RUN apt upgrade -y
RUN apt install --no-install-recommends -y \
    libpq-dev \
    python3-dev \
    build-essential \
    curl \
    git

WORKDIR /backend

COPY ./requirements.txt ./
RUN pip install uv && uv pip install --system --no-cache-dir -r requirements.txt
COPY ./ ./

EXPOSE 8000

# Default command runs migrations then gunicorn. docker-compose.prod.yml
# overrides this with a longer boot sequence (collectstatic, seed_taxonomy,
# create superuser), so this default is only the bare minimum useful when
# the image is run standalone.
CMD ["bash", "-lc", "python manage.py migrate --noinput && exec gunicorn core.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 60"]