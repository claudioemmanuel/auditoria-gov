#!/usr/bin/env bash
set -e

# Sync system time at container startup (non-fatal — continues even if NTP fails)
ntpdate-ntpsec -u pool.ntp.org 2>/dev/null || true

exec "$@"
