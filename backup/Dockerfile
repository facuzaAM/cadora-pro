FROM postgres:16-alpine

RUN apk add --no-cache bash

COPY backup.sh /app/backup.sh
RUN chmod +x /app/backup.sh

CMD ["/bin/sh", "-c", "echo '0 3 * * * /app/backup.sh >> /var/log/backup.log 2>&1' | crontab - && crond -f -l 2"]
