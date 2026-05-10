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

CMD [ "/backend/.dockerinit.sh" ]
EXPOSE 8000