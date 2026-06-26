#!/bin/sh
# Installs the mounted demo public key for user `pi`, then runs sshd in the
# foreground. The key is mounted read-only at /authorized_key.pub.
set -e

if [ -f /authorized_key.pub ]; then
    cp /authorized_key.pub /home/pi/.ssh/authorized_keys
    chmod 600 /home/pi/.ssh/authorized_keys
    chown pi:pi /home/pi/.ssh/authorized_keys
else
    echo "WARNING: /authorized_key.pub not mounted; SSH login will fail." >&2
fi

# `systemctl is-active ssh` is Linux-systemd specific; provide a shim so the
# diagnostics tool reports a sensible value on Alpine too.
cat > /usr/local/bin/systemctl <<'EOF'
#!/bin/sh
if [ "$1" = "is-active" ]; then echo "active"; exit 0; fi
exit 0
EOF
chmod +x /usr/local/bin/systemctl

exec /usr/sbin/sshd -D -e
