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

# this doesn't use `FROM base AS worker` because that would cause all compilers
# to be reinstalled (which takes forever) any time CMS code changes.
FROM common AS worker

RUN sudo apt update && sudo apt install -y \
    openjdk-19-jdk-headless \
    php8.1-cli rustc mono-mcs haskell-platform \
    golang-go nodejs \
    && sudo rm -rf /var/lib/apt/lists/*

RUN curl https://downloads.python.org/pypy/pypy3.10-v7.3.13-linux64.tar.bz2 -o /tmp/pypy.tar.bz2 && \
    sudo tar -xf /tmp/pypy.tar.bz2 -C /opt && \
    rm /tmp/pypy.tar.bz2 && \
    sudo ln -s /opt/pypy3.10-v7.3.13-linux64 /opt/pypy3

COPY --chown=cmsuser:cmsuser . .
RUN sudo python3.8 prerequisites.py --yes --cmsuser=cmsuser install
RUN venv/bin/python setup.py install
