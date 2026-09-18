### General setup

### Running the script locally

1. Ensure that pip is up to date: `python3 -m pip install --upgrade pip`
2. Set up the virtual environment: `python3 -m venv .venv`
3. Activate the virtual environment: `source .venv/bin/activate`
4. Install all dependencies: `python3 -m pip install -r requirements.txt`
5. Create a `.env` file in this repo, matching the syntax of `.env.example`
6. Run the script: `python3 main.py`

### Design

Requirements:

- Run every minute
  - Get "retry-after" from response on 429
- Send a Whatsapp message to a group when:
  - Glucose is below soft threshold
    - And the last alert was at least six hours ago
  - Glucose is below hard threshold
    - And the last hard alert was at least one hour ago
  - Glucose recovers from hard threshold
    - And the last recovery message was before the last hard warning
- Send an email to group when:
  - Whatsapp connection fails
  - Libreview connection fails
  - Hourly heartbeat

### Example

https://pylibrelinkup.readthedocs.io/en/latest/usage.html
