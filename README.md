### General setup

### Running the script locally

1. Create a `.env` file in this repo, matching the syntax of `.env.example`
2. Generate a QR code to link your Signal device: `bash ./scripts/generate-signal-qr-code.sh`
3. Run the script: `bash ./scripts/run_main.sh`

### Development

Run tests and type checks: `bash ./scripts/run-tests-and-lint.sh`

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

Nice to have (high priority):
- Daily summary with graph of the day's data
- Graph of last few hours of data

Nice to have (low priority):
- Only store latest 100 values, to avoid taking longer and longer to read and write data file
  - OR: write to multiple files, one per day!
- Only fetch every 5 minutes when latest value is above 20 (return early)
- Pictures of Chips for each level
- Get and store "retry-after" from response on 429
