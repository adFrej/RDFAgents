FROM ejabberd/ecs:latest

USER root
RUN apk add --no-cache --update python3=3.9.18-r0 --repository=https://dl-cdn.alpinelinux.org/alpine/v3.15/main
RUN python3 -m ensurepip
RUN pip3 install --no-cache --upgrade pip setuptools

RUN mkdir /app
RUN chown ejabberd /app

# Setup runtime environment
USER ejabberd
VOLUME ["$HOME/database","$HOME/conf","$HOME/logs","$HOME/upload"]
EXPOSE 1883 4369-4399 5222 5269 5280 5443

COPY . /app

RUN mkdir /app/logs
VOLUME /app/logs
EXPOSE 10000

RUN pip install --no-cache -r /app/requirements.txt

ENV ADDRESS=admin@localhost
ENV PASSWORD=password

ENTRYPOINT /app/ejabberd_entrypoint.sh
