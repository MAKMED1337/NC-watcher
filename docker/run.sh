HOSTIP=`ip -4 addr show scope global dev eth0 | grep inet | awk '{print $2}' | cut -d / -f 1 | sed -n 1p`

docker run -v /mirror/reports_dev:/watcher/reporter/reports \
--add-host=mysql_host:${HOSTIP} -e host=mysql_host \
--restart=always -d watcher_dev