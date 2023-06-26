FROM python:3.11

RUN wget https://raw.githubusercontent.com/gdraheim/docker-systemctl-replacement/master/files/docker/systemctl3.py -O /usr/local/bin/systemctl
RUN chmod +x /usr/local/bin/systemctl

ARG github_token
RUN git clone https://$github_token@github.com/MAKMED1337/NC-watcher.git /watcher
WORKDIR /watcher

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY *.session .
COPY docker/*.env /etc/systemd/system/

COPY docker/*.service /etc/systemd/system/
RUN systemctl enable reporter
RUN systemctl enable accounts
RUN systemctl enable bot
RUN systemctl enable watcher
RUN systemctl enable mod_message_watcher

CMD sh docker/script.sh