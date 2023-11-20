FROM ubuntu:22.04

RUN apt update
ENV TZ=Europe/Tallinn
RUN DEBIAN_FRONTEND=noninteractive apt install -y \
    build-essential openjdk-19-jdk-headless fp-compiler \
    postgresql-client python3.10 cppreference-doc-en-html \
    cgroup-lite libcap-dev zip \
    python3.10-dev libpq-dev libcups2-dev libyaml-dev \
    libffi-dev python3.10-venv \
    php8.1-cli rustc mono-mcs haskell-platform \
    golang-go pypy3 nodejs \
    pypy python2.7 \
    # for add-apt-repository and sudo
    software-properties-common sudo \
    # for cms unit tests
    wait-for-it

# we want a newer ubuntu to get newer versions of compilers.
# however, CMS targets ubuntu 20.04, with python 3.8. So pull that in manually
RUN add-apt-repository -y ppa:deadsnakes/ppa
RUN apt update
RUN apt install -y python3.8 python3.8-dev python3.8-venv

# Create cmsuser user with sudo privileges
RUN useradd -ms /bin/bash cmsuser && \
    usermod -aG sudo cmsuser
# Disable sudo password
RUN echo '%sudo ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers
# Set cmsuser as default user
USER cmsuser

# needs to be created beforehand to be owned by cmsuser
RUN mkdir -p /home/cmsuser/cms
WORKDIR /home/cmsuser/cms
COPY --chown=cmsuser:cmsuser requirements.txt .
RUN python3.8 -m venv venv
RUN venv/bin/pip install -r requirements.txt
COPY --chown=cmsuser:cmsuser . .
RUN sudo python3.8 prerequisites.py --yes --cmsuser=cmsuser install
RUN venv/bin/python setup.py install
