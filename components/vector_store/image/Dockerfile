FROM public.ecr.aws/docker/library/python:3.10.13-slim-bullseye

RUN apt-get -y update && apt-get install -y --no-install-recommends \
    zip \
    unzip \
    && rm -rf /var/lib/apt/lists/*

RUN addgroup --gid  1001 nonroot && \
    adduser --uid 1001 --gid 1001 --disabled-password --gecos "" nonroot && \
    echo 'nonroot ALL=(ALL) NOPASSWD: ALL' >> /etc/sudoers

USER nonroot 

COPY requirements.txt /tmp/

RUN python -m pip install -U pip

RUN  pip install --force-reinstall --no-cache-dir \
    -r /tmp/requirements.txt

HEALTHCHECK NONE

WORKDIR /opt/ml