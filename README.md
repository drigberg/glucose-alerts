## General setup

### Running the script locally

1. Create a `.env` file in this repo, matching the syntax of `.env.example`
2. Start Signal API with `docker compose up -d signal-api`, then generate a QR
   code to link your Signal device: `bash ./scripts/generate-signal-qr-code.sh`
3. Run one poll: `bash ./scripts/run-main.sh`

## Proxmox deployment

The production Compose setup runs the monitor continuously, polling after each
run with a 60-second delay and terminating any poll that runs longer than two
minutes. The monitor and Signal API use restart policies, application
data and Signal registration live in named Docker volumes, and Docker rotates
each service's logs. The Signal API is reachable only on the private Compose
network; it does not publish its control port on the host.

GitHub Actions runs the existing unit tests and type checks for pull requests
and pushes to `main`. A successful push to `main` publishes a container image
to GitHub Container Registry. On the Docker host, install the files under
`deploy/systemd/` and enable the included timer to pull and start the latest
published image every five minutes. See [the deployment guide](deploy/README.md)
for the one-time host setup.

The image package must be public for the host to pull it without a GitHub
credential. The repository owner may need to change the package visibility
after the first image is published.

Logs can contain service errors and timing information. The monitor avoids
writing glucose values or raw LibreLinkUp responses to logs. Docker retains a
bounded local log history; anyone with Docker or Proxmox administrator access
can still read those logs.

Missing-data alerts are still listed as a TODO in this project. Keep the
official CGM alert path active; this service cannot report that polling itself
has stopped.

### Development

Run tests and type checks: `bash ./scripts/test-and-lint.sh`

### Details
- This script returns early if it has been run in the last 50 seconds, as a lazy guard against exceeding the API's rate limit, which appears to be around 1 request per minute
- There are four alert levels: Good, Target, Warning, and Emergency.
  - An alert is sent whenever a data point falls below a new threshold, as compared against the last alert
  - A recovery alerts is sent after receiving three consecutive values above the last alert's threshold
- Sends alerts to one email address and one Signal group
- Setting `FORCE_SEND_TEST=true` in `.env` overrides the alert level to `TEST` and sends alerts with the latest reading (still requires a new data point)

### TODO

Required:
- Two groups: one for all alerts, and one for only emergency/warning alerts
- Send an email to admins on any unexpected error (especially Whatsapp/Libreview connection errors)
- Send an hourly heartbeat email
- Missing-data alerts

Nice to have (high priority):
- Daily summary with graph of the day's data
- Graph of last few hours of data

Nice to have (low priority):
- Only store latest 100 values, to avoid taking longer and longer to read and write data file
  - OR: write to multiple files, one per day!
- Only fetch every 5 minutes when latest value is above 20 (return early)
- Pictures of Chips for each level
- Get and store "retry-after" from response on 429
