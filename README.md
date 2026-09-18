### General setup

### Running the script locally

1. Ensure that pip is up to date: `python3 -m pip install --upgrade pip`
2. Set up the virtual environment: `python3 -m venv .venv`
3. Activate the virtual environment: `source .venv/bin/activate`
4. Install all dependencies: `python3 -m pip install -r requirements.txt`
5. Create a `.env` file in this repo, matching the syntax of `.env.example`
6. Run the script: `python3 main.py`

### Development

Saving depencies: `python3 -m pip freeze > requirements.txt`
Run tests and type checks: `bash ./run-tests-and-lint.sh`

### Design

Requirements:

- Doesn't allow running twice within a minute
- Send a Whatsapp message to the group when:
  - Entering or exiting a stage
- Send an SMS to on-call folks when:
  - Entering or exiting warning or emergency stages
- Send an email to group when:
  - Whatsapp connection fails
  - Libreview connection fails
  - Hourly heartbeat

Nice to have:

- Get "retry-after" from response on 429

### Example

https://pylibrelinkup.readthedocs.io/en/latest/usage.html
