FROM python:3.11

RUN wget https://raw.githubusercontent.com/gdraheim/docker-systemctl-replacement/master/files/docker/systemctl3.py -O /usr/local/bin/systemctl
RUN chmod +x /usr/local/bin/systemctl

WORKDIR /watcher

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY docker/*.service /etc/systemd/system/
RUN systemctl enable reporter
RUN systemctl enable accounts
RUN systemctl enable bot
RUN systemctl enable watcher
RUN systemctl enable mod_message_watcher

COPY *.session .
COPY env/*.env /etc/systemd/system/

COPY . .

CMD sh docker/script.sh