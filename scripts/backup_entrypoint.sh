#!/bin/sh
set -eu

# Run one backup on container start, then schedule daily at 03:00.
/scripts/backup.sh

echo "0 3 * * * /scripts/backup.sh >> /var/log/backup.log 2>&1" > /etc/crontabs/root

exec crond -f -L /var/log/cron.log
