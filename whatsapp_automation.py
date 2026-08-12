import pywhatkit as kit
import pandas as pd
import time
import logging
import random

logging.basicConfig(
    filename="whatsapp_log.txt",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

DEFAULT_COUNTRY_CODE = "+92"  # change to your country code


def normalize_phone(phone, default_code=DEFAULT_COUNTRY_CODE):
    phone = str(phone).strip().replace(" ", "").replace("-", "")
    if phone.startswith("+"):
        return phone
    if phone.startswith("0"):
        return default_code + phone[1:]
    if phone.startswith(default_code.replace("+", "")):
        return "+" + phone
    return default_code + phone


df = pd.read_csv("contacts.csv")

success_count = 0
failed = []

for idx, row in df.iterrows():
    name = row["name"]
    phone = normalize_phone(row["phone"])

    # basic validation
    if not phone.startswith("+"):
        logging.error(f"Skipped {name}: phone number missing country code -> {phone}")
        failed.append((name, phone, "invalid phone format"))
        continue

    message = row.get("message_template", f"Hi {name}, this is an automated reminder.")
    message = message.format(name=name)

    try:
        kit.sendwhatmsg_instantly(
            phone_no=phone, message=message, wait_time=15, tab_close=True
        )
        logging.info(f"Message sent to {name} ({phone})")
        success_count += 1

    except Exception as e:
        logging.error(f"Failed to send to {name} ({phone}): {e}")
        failed.append((name, phone, str(e)))

    time.sleep(
        random.randint(20, 45)
    )  # instead of time.sleep(20)  # delay between sends

print(f"\nDone. Sent: {success_count}, Failed: {len(failed)}")
if failed:
    print("Failed sends:")
    for name, phone, reason in failed:
        print(f" - {name} ({phone}): {reason}")
