# pull official base image
FROM centos:8

RUN yum -y install which vim wget curl git tree

# set work directory
WORKDIR /usr/src/app


# install conda
RUN wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh && \
    sh Miniconda3-latest-Linux-x86_64.sh -b -p ./py_conda_env

# Choose Python version
RUN ./py_conda_env/bin/conda install python=3.8.2

# Prevent Python from writing pyc files to disc (equivalent to python -B)
ENV PYTHONDONTWRITEBYTECODE 1
# Prevents Python from buffering stdout and stderr (equivalent to python -u)
ENV PYTHONUNBUFFERED 1

# set locale for python
ENV LANG en_US.UTF-8
ENV LC_ALL en_US.UTF-8

# Copy spacy models that will be later installed via pip
COPY en_core_web* /usr/src/app/spacy_models/

# install dependencies
COPY ./requirements.txt /usr/src/app/requirements.txt
RUN ./py_conda_env/bin/pip install -r requirements.txt


# copy project -> No, better volume-mount to get up-to-date
# COPY . /usr/src/app/

# Add some useful aliases. Need to source manually when using 'docker-compose exec web sh'
RUN echo 'alias ll="ls -Glat"' >> ~/.bashrc

# python modules that belong to webbu should also be mounted as a volume to get updated code