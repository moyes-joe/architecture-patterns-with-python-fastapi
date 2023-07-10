FROM python:3.11-slim-buster

# set working directory
WORKDIR /usr/src/app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# install system dependencies
RUN apt-get update \
    && apt-get -y install netcat gcc postgresql libpq-dev \
    && apt-get clean

# install python dependencies
COPY pyproject.toml poetry.lock ./
RUN pip install --upgrade pip
RUN pip install poetry
RUN poetry export -f requirements.txt --output requirements.txt --without-hashes --dev
RUN pip install -r requirements.txt

# add app
COPY . .
