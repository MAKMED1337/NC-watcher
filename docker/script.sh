export host="mysql_host"

systemctl start reporter
systemctl start accounts
systemctl start bot
systemctl start mod_message_watcher
systemctl start watcher

while true; do sleep 1; done;