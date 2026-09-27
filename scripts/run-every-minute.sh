#!/usr/bin/env bash

# Poll after each run finishes so successive LibreLinkUp requests stay spaced
# beyond the API's observed one-request-per-minute limit.
while true; do
    echo "[glucose-alerts] Starting scheduled poll at $(date --iso-8601=seconds)"
    timeout 120s python main.py
    status=$?
    if [ "$status" -ne 0 ]; then
        echo "[glucose-alerts] Poll failed with exit code ${status}; retrying after the delay"
    fi
    sleep 60
done
