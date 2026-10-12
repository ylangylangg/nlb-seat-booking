# NLB Seat-Booking Automation

A personal Python project that automates library seat booking on the NLB website using Playwright and GitHub Actions. It supports configurable booking dates (today or tomorrow), start times, durations and seat preferences, with timestamped Telegram notifications at execution checkpoints.

The project explores browser automation, scheduling, configuration and monitoring of unattended runs.

## Features

- Choose to book for today or tomorrow.
- For tomorrow's booking, wait until noon SGT if the script starts early.
- Select a preferred seat, then a backup seat, then `Any available seat` if neither is visible.
- Verify the `Booking successful!` message before reporting success.
- Send Telegram notifications when the script starts, login is confirmed, the page refresh completes if applicable, and booking is confirmed.
- Run locally or through a scheduled GitHub Actions workflow.

Telegram commands for immediate bookings and skipping an upcoming booking are planned; they are not part of the current command interface.

## Booking flow

1. Start the script and open Chromium.
2. Log in to NLB and open the booking page.
3. If booking tomorrow before noon, wait until 12:00 pm Singapore time.
4. Refresh or navigate to the booking page after the wait.
5. Select the booking date, start time and duration.
6. Check availability and select a seat using the preference order.
7. Submit the booking and verify the success message.
8. Send the confirmation notification and close the browser.

When `book_seat()` starts with `page.goto()`, that navigation loads the page after the wait. A separate refresh immediately before it is unnecessary.

## Configuration

Adjust the settings in `main.py`:

| Setting | Example | Purpose |
| --- | --- | --- |
| `BOOK_FOR` | `"tomorrow"` | Choose `"today"` or `"tomorrow"` |
| `SEAT_OPTION_1` | `9` | Preferred seat; the selector adds `S` |
| `SEAT_OPTION_2` | `5` | Backup seat |
| `TIME_OPTION` | `"1:00 pm"` | Start time matching the website label |
| `DURATION_OPTION` | `"4:00"` | Duration matching the website label |
| `BOOKING_URL` | NLB seat-booking URL | Library location and booking page |

Dates and execution timestamps use Singapore time, UTC+8. Tomorrow's bookings become available from noon on the preceding day. Today's booking skips the noon wait, but the selected time must still be available and valid.

The fallback value `Any available seat` describes the selected option; it does not identify the seat ultimately assigned.

## Local setup

Install Python, then create a virtual environment. On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install playwright requests
python -m playwright install chromium
```

If the repository includes `requirements.txt`

Provide the NLB credentials and Telegram configuration through the environment variables read by `main.py`. Use the exact names in the script; do not hardcode credentials.

Run the script from the project directory:

```powershell
python main.py
```

For local inspection, use headed mode if supported by the script. Set `HEADLESS=1` for GitHub Actions. Running the script submits a real booking when a suitable slot is available.

## GitHub Actions

The workflow belongs in `.github/workflows/nlb-booking.yml`. It should check out the repository, set up Python, install dependencies and Chromium, and run `main.py` with the required environment variables.

Add NLB credentials and the Telegram bot token under **Settings → Secrets and variables → Actions**. Match the secret references in the workflow to the environment variable names in the script.

An example daily schedule for 11:50 am Singapore time:

```yaml
on:
  schedule:
    - cron: "50 3 * * *" # 03:50 UTC = 11:50 Singapore
  workflow_dispatch:
```

Starting early allows time for setup and login before the script waits for noon. GitHub scheduled runs can be delayed, so neither the job start nor the booking time is guaranteed. See [GitHub's scheduled workflow documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).

## Notifications and timing

Checkpoint timestamps show when Python observes each milestone. The script-start timestamp is recorded after GitHub's setup steps; the Actions run page provides job timing.

A refresh timestamp records when `DOMContentLoaded` completes. A booking timestamp records when the success message is visible, rather than the server's internal booking time.

Sending a Telegram message before submitting the booking adds network delay. For time-sensitive runs, record the refresh timestamp immediately and send that notification after the booking attempt.

## Limitations

- Website layout or label changes may require selector updates.
- A visible seat option does not guarantee that it remains available at submission.
- A missing success message causes verification to fail; check the actual booking status before retrying.
- Public repositories should exclude credentials, session data and personal booking logs.

## Planned Telegram commands

| Command | Intended behavior |
| --- | --- |
| `/book_now 15:00 2` | Trigger a same-day booking at 3 pm for two hours |
| `/skip_tomorrow` | Skip the scheduled booking for one specific date |

These require a command handler that receives messages promptly, verifies the sender and triggers GitHub Actions or saves the dated skip instruction. Checking messages only during the daily booking run would not provide immediate booking.

## Technology

Python · Playwright · GitHub Actions · Telegram Bot API

Personal learning project; not affiliated with NLB.
