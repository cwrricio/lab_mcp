#!/usr/bin/env bash
# Generates the demo SSH key pair used to log into the demo containers.
# The private key stays local and is git-ignored. Run once before `docker compose up`.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KEY="$SCRIPT_DIR/keys/sentinel_demo"

if [ -f "$KEY" ]; then
    echo "Demo key already exists at $KEY — nothing to do."
    exit 0
fi

ssh-keygen -t ed25519 -N "" -f "$KEY" -C "lab-sentinel-demo"
echo "Generated demo key pair:"
echo "  private: $KEY"
echo "  public:  $KEY.pub"
echo
echo "Next:"
echo "  1. docker compose up -d --build"
echo "  2. Append docker/ssh_config.example to your ~/.ssh/config"
echo "     (adjust the IdentityFile path to: $KEY)"
echo "  3. cp docker/.sentinel.yaml.example .sentinel.yaml"
