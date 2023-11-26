FROM ubuntu:22.04 AS common

ENV TZ=Europe/Tallinn
RUN apt update && \
    DEBIAN_FRONTEND=noninteractive apt install -y \
    build-essential \
    postgresql-client python3.10 cppreference-doc-en-html \
    cgroup-lite libcap-dev zip \
    python3.10-dev libpq-dev libcups2-dev libyaml-dev \
    libffi-dev python3.10-venv \
    # dependency of python 3.8 but not 3.10 apparently?
    tzdata \
    # for add-apt-repository and sudo
    software-properties-common sudo \
    # for cms unit tests
    wait-for-it \
    && rm -rf /var/lib/apt/lists/*

# we want a newer ubuntu to get newer versions of compilers.
# however, CMS targets ubuntu 20.04, with python 3.8. So pull that in manually
RUN add-apt-repository -y ppa:deadsnakes/ppa && \
    apt update && \
    apt install -y python3.8 python3.8-dev python3.8-venv \
    && rm -rf /var/lib/apt/lists/*


# Create cmsuser user with sudo privileges
RUN useradd -ms /bin/bash cmsuser && \
    usermod -aG sudo cmsuser
# Disable sudo password
RUN echo '%sudo ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers
# HACK to allow the eio user to access the right files in our server setup
RUN groupadd -g 1001 eiogroup && \
    usermod -aG eiogroup cmsuser
# Set cmsuser as default user
USER cmsuser

# needs to be created beforehand to be owned by cmsuser
RUN mkdir -p /home/cmsuser/cms
WORKDIR /home/cmsuser/cms
COPY --chown=cmsuser:cmsuser requirements.txt .
RUN python3.8 -m venv venv && \
    venv/bin/pip install -r requirements.txt

FROM common AS base
COPY --chown=cmsuser:cmsuser . .
RUN sudo python3.8 prerequisites.py --yes --cmsuser=cmsuser install
RUN venv/bin/python setup.py install

# this doesn't use `base` because we don't want to reinstall all the compilers when rebuilding CMS
FROM common AS worker

RUN sudo apt update && sudo apt install -y \
    fp-compiler openjdk-19-jdk-headless \
    php8.1-cli rustc mono-mcs haskell-platform \
    golang-go pypy3 nodejs \
    && sudo rm -rf /var/lib/apt/lists/*

COPY --chown=cmsuser:cmsuser . .
RUN sudo python3.8 prerequisites.py --yes --cmsuser=cmsuser install
RUN venv/bin/python setup.py install
