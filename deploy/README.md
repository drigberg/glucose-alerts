# Proxmox Docker host deployment

This deploys a tested image from GitHub Container Registry (GHCR). GitHub-hosted
Actions builds the image; the Proxmox Docker host only pulls it, so Chromium and
Python dependencies are not built on the runtime VM. A systemd timer checks for
the `latest` image every five minutes. The timer updates only the glucose app;
Signal registration and app data remain in named Docker volumes.

## One-time GitHub setup

After the first successful `Publish container image` workflow, the repository
owner should make `ghcr.io/drigberg/glucose-alerts` public in the package
settings. This lets the Docker host pull it without storing a GitHub token.
Only successful CI runs on `main` publish or move the `latest` tag.

## One-time Docker host setup

Run these steps on the chosen Docker host. They expect Docker Engine with the
Compose v2 plugin and systemd. Do not put credentials in the repository.

1. Clone this public repository to `/opt/glucose-alerts` so its Compose file,
   Signal linking script, and systemd units are available there.
2. Create `/opt/glucose-alerts/.env` with the required values from
   `.env.example`, then restrict it to the host administrator:
   `chmod 600 /opt/glucose-alerts/.env`.
3. Start Signal API with `docker compose -f deploy/compose.yml up -d signal-api`,
   then link the Signal account with
   `COMPOSE_FILE=deploy/compose.yml bash scripts/generate-signal-qr-code.sh`.
   Keep the QR image private. The Compose volume retains the linked account
   across container replacement.
4. Install the systemd unit and timer from `deploy/systemd/` into
   `/etc/systemd/system/`, run `systemctl daemon-reload`, then enable the timer
   with `systemctl enable --now glucose-alerts-update.timer`.
5. Start the initial project with
   `docker compose -f deploy/compose.yml up -d`.

The update service runs as root because it calls the Docker daemon. Anyone with
root or Docker access on the host can read the environment file, named volumes,
and container logs. The timer writes update results to the systemd journal.

## Logs and troubleshooting

- App and Signal API output: `docker compose -f /opt/glucose-alerts/deploy/compose.yml logs --tail=100`
- Follow app output: `docker compose -f /opt/glucose-alerts/deploy/compose.yml logs --follow glucose-alerts`
- Update attempts: `journalctl -u glucose-alerts-update.service`
- Timer status: `systemctl list-timers glucose-alerts-update.timer`

Docker's `local` log driver keeps a bounded history (up to five 10 MB files per
service). Application logs can include the latest glucose value and timestamp,
raw LibreLinkUp responses on parse errors, and Signal API error bodies. Logs
stay on the Docker host; this setup does not ship them elsewhere. Proxmox
administrators and Docker administrators on this host can read them.

## Rollback

The publishing workflow tags each successful image with its tested commit SHA.
For a rollback, set `image` in `/opt/glucose-alerts/deploy/compose.yml` to
`ghcr.io/drigberg/glucose-alerts:<commit-sha>`, then run `docker compose -f
/opt/glucose-alerts/deploy/compose.yml pull glucose-alerts` and
`docker compose -f /opt/glucose-alerts/deploy/compose.yml up -d --no-build
glucose-alerts`. Restore `:latest` after resolving the issue.
