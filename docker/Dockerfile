# Minimal Alpine host with SSH, simulating a lab machine (Raspberry Pi / Linux PC).
FROM alpine:3.20

RUN apk add --no-cache openssh openrc \
    && ssh-keygen -A \
    && adduser -D -s /bin/sh pi \
    && passwd -u pi \
    && mkdir -p /home/pi/.ssh \
    && chmod 700 /home/pi/.ssh \
    && chown pi:pi /home/pi/.ssh

# Enable the ssh service status check used by get_resource_status.
RUN mkdir -p /run/openrc && touch /run/openrc/softlevel

COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

EXPOSE 22
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
