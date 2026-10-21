#!/bin/bash
set -euo pipefail

mkdir -p /var/lib/obc /run/sshd
chown obc:obc /var/lib/obc

if [[ ! -f /var/lib/obc/simulator.json ]]; then
  python3 -c "from satellite.persistence import reset_simulator; reset_simulator()"
fi

exec /usr/sbin/sshd -D -e
