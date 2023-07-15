HOSTIP=`ip -4 addr show scope global dev eth0 | grep inet | awk '{print $2}' | cut -d / -f 1 | sed -n 1p`

docker run -v /mirror/reports_stable:/watcher/reporter/reports \
-v /mirror/NearCrowd_payment_bot.session:/watcher/NearCrowd_payment_bot.session \
-v /mirror/NearCrowd_reporter_bot.session:/watcher/NearCrowd_reporter_bot.session \
--env-file /etc/systemd/system/tg_api.env \
--env-file /etc/systemd/system/database.env \
--add-host=mysql_host:${HOSTIP} -e host=mysql_host -e db_name=watcher \
--restart=always -d watcher_stable