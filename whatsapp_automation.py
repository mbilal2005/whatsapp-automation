"""
WhatsApp personalized message sender using pywhatkit.

Usage:
    python whatsapp_sender.py --batch 1
    python whatsapp_sender.py --batch 2
    python whatsapp_sender.py --batch 3

Each batch sends to a slice of contacts.csv (default: 10 contacts per batch).
Run each batch at a different time of day (e.g. morning / afternoon / evening)
via Task Scheduler (Windows) or cron (Mac/Linux), or just run manually.
"""

import argparse
import csv
import os
import random
import time
import logging
from datetime import date

import pandas as pd
import pywhatkit as kit

# ---------------------------------------------------------------------------
# CONFIG — edit these
# ---------------------------------------------------------------------------
DEFAULT_COUNTRY_CODE = "+92"  # change to your country code
CONTACTS_FILE = "contacts.csv"
SENT_LOG_FILE = "sent_log.csv"
BATCH_SIZE = 10
MIN_DELAY = 20  # seconds between sends
MAX_DELAY = 45
LONG_PAUSE_CHANCE = 0.15  # ~15% chance of an extra long pause after a send
LONG_PAUSE_RANGE = (60, 90)
SEND_HOUR_START = 9  # don't send before 9 AM
SEND_HOUR_END = 21  # don't send after 9 PM

# A few phrasing variants — {name} gets filled in automatically.
# If your CSV has its own message_template column, that takes priority instead.
DEFAULT_TEMPLATES = [
    "Hi {name}, hope you're doing well! Just a quick reminder about our meeting.",
    "Hey {name}, wanted to send a quick reminder about our upcoming meeting.",
    "Hello {name}, this is a friendly reminder regarding our meeting.",
]

logging.basicConfig(
    filename="whatsapp_log.txt",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def normalize_phone(phone, default_code=DEFAULT_COUNTRY_CODE):
    phone = str(phone).strip().replace(" ", "").replace("-", "")
    if phone.startswith("+"):
        return phone
    if phone.startswith("0"):
        return default_code + phone[1:]
    if phone.startswith(default_code.replace("+", "")):
        return "+" + phone
    return default_code + phone


def load_sent_today():
    """Return a set of phone numbers already messaged today."""
    if not os.path.exists(SENT_LOG_FILE):
        return set()
    today = str(date.today())
    sent = set()
    with open(SENT_LOG_FILE, newline="") as f:
        for row in csv.reader(f):
            if len(row) >= 2 and row[1] == today:
                sent.add(row[0])
    return sent


def log_sent(phone):
    file_exists = os.path.exists(SENT_LOG_FILE)
    with open(SENT_LOG_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([phone, str(date.today())])


def check_sending_hours():
    hour = time.localtime().tm_hour
    if not (SEND_HOUR_START <= hour < SEND_HOUR_END):
        print(
            f"Current time is outside the allowed sending window "
            f"({SEND_HOUR_START}:00-{SEND_HOUR_END}:00). Exiting."
        )
        logging.warning("Run blocked: outside allowed sending hours.")
        exit(0)


def get_batch(df, batch_num, batch_size=BATCH_SIZE):
    start = (batch_num - 1) * batch_size
    end = start + batch_size
    return df.iloc[start:end]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Send a batch of WhatsApp messages.")
    parser.add_argument(
        "--batch", type=int, required=True, help="Batch number (1, 2, 3, ...)"
    )
    parser.add_argument(
        "--batch-size", type=int, default=BATCH_SIZE, help="Contacts per batch"
    )
    parser.add_argument(
        "--skip-hour-check",
        action="store_true",
        help="Ignore the allowed sending-hours window",
    )
    args = parser.parse_args()

    if not args.skip_hour_check:
        check_sending_hours()

    df = pd.read_csv(CONTACTS_FILE)
    batch_df = get_batch(df, args.batch, args.batch_size)

    if batch_df.empty:
        print(f"Batch {args.batch} is empty — no contacts at that range.")
        return

    already_sent = load_sent_today()

    success_count = 0
    skipped = []
    failed = []

    for idx, row in batch_df.iterrows():
        name = row["name"]
        phone = normalize_phone(row["phone"])

        if not phone.startswith("+"):
            logging.error(f"Skipped {name}: invalid phone -> {phone}")
            failed.append((name, phone, "invalid phone format"))
            continue

        if phone in already_sent:
            logging.info(f"Skipped {name} ({phone}): already messaged today.")
            skipped.append((name, phone))
            continue

        # message: use CSV template if present, else rotate default templates
        if "message_template" in row and pd.notna(row["message_template"]):
            template = row["message_template"]
        else:
            template = random.choice(DEFAULT_TEMPLATES)
        message = template.format(name=name)

        try:
            kit.sendwhatmsg_instantly(
                phone_no=phone, message=message, wait_time=15, tab_close=True
            )
            logging.info(f"Message sent to {name} ({phone})")
            log_sent(phone)
            success_count += 1

        except Exception as e:
            logging.error(f"Failed to send to {name} ({phone}): {e}")
            failed.append((name, phone, str(e)))

        # randomized delay, occasionally longer
        if random.random() < LONG_PAUSE_CHANCE:
            delay = random.randint(*LONG_PAUSE_RANGE)
        else:
            delay = random.randint(MIN_DELAY, MAX_DELAY)
        time.sleep(delay)

    print(
        f"\nBatch {args.batch} done. Sent: {success_count}, "
        f"Skipped (already sent today): {len(skipped)}, Failed: {len(failed)}"
    )
    if failed:
        print("Failed sends:")
        for name, phone, reason in failed:
            print(f" - {name} ({phone}): {reason}")


if __name__ == "__main__":
    main()
