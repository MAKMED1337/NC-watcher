mysqldump watcher_dev --single-transaction --quick --lock-tables=false > backup-dev-$(date +%"F-%T").sql