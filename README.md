### General setup

### Running the script locally

1. Set up the virtual environment: `python3 -m venv .venv`
2. Activate the virtual environment: `source .venv/bin/activate`
3. Ensure that pip is up to date: `python3 -m pip install --upgrade pip`
4. Install all dependencies: `python3 -m pip install -r requirements.txt`
5. Create a `.env` file in this repo, matching the syntax of `.env.example`
6. Run the script: `python3 main.py`

### Development

Saving dependencies: `python3 -m pip freeze > requirements.txt`
Run tests and type checks: `bash ./run-tests-and-lint.sh`

### Details
- This script returns early if it has been run in the last 50 seconds, as a lazy guard against exceeding the API's rate limit, which appears to be around 1 request per minute
- There are four alert levels: Target, Low, Warning, and Emergency.
  - An alert is sent whenever a data point falls below a new threshold, as compared against the last alert
  - A recovery alerts is sent after receiving three consecutive values above the last alert's threshold

### TODO

Required:
- Connect to Whatsapp
- Nicer alert messages
- Send SMS to on-call recipients when entering or existing warning/emergency levels
- Send an email to admins on any unexpected error (especially Whatsapp/Libreview connection errors)
- Send an hourly heartbeat email

Nice to have (high priority):
- (no items at the moment)

Nice to have (low priority):

- Only store latest 100 values, to avoid taking longer and longer to read and write data file
  - OR: write to multiple files, one per day!
- Only fetch every 5 minutes when latest value is above 20 (return early)
- Pictures of Chips for each level
- Graph of last few hours of data
- Get and store "retry-after" from response on 429
