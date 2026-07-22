import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests


# --------------------------------------------------
# Settings
# --------------------------------------------------

API_BASE_URL = "https://api.yodelpass.com/api"
VANCOUVER_TZ = ZoneInfo("America/Vancouver")

NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "").strip()

PASSES = {
    "Morning Pass": {
        "catalog_item_id": 11584,
        "place_id": 10672,
        "booking_page": "https://yodelportal.com/Buntzen-Lake/Half-Day-Pass",
    },
    "Afternoon Pass": {
        "catalog_item_id": 12197,
        "place_id": 10672,
        "booking_page": "https://yodelportal.com/Buntzen-Lake/Half-Day-Pass",
    },
    "All-Day Pass": {
        "catalog_item_id": 12196,
        "place_id": 10671,
        "booking_page": "https://yodelportal.com/Buntzen-Lake/All-Day-Pass",
    },
}


# --------------------------------------------------
# Notification
# --------------------------------------------------

def send_notification(
    pass_name: str,
    status: str,
    target_date: str,
    booking_page: str,
) -> None:
    """Send an ntfy notification when a pass may be available."""

    if not NTFY_TOPIC:
        print("Warning: NTFY_TOPIC secret is missing. Notification not sent.")
        return

    message = (
        f"{pass_name} may be available for {target_date}.\n"
        f"Status: {status}\n"
        f"Book immediately before it disappears."
    )

    try:
        response = requests.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=message.encode("utf-8"),
            headers={
                "Title": f"Buntzen pass available: {pass_name}",
                "Priority": "urgent",
                "Tags": "rotating_light,parking",
                "Click": booking_page,
            },
            timeout=20,
        )
        response.raise_for_status()
        print(f"Notification sent for {pass_name}.")

    except requests.RequestException as error:
        print(f"Could not send notification for {pass_name}: {error}")


# --------------------------------------------------
# Availability check
# --------------------------------------------------

def check_pass(
    pass_name: str,
    pass_info: dict,
    target_date: str,
    checked_time: str,
) -> None:
    """Check one Buntzen parking-pass type."""

    catalog_item_id = pass_info["catalog_item_id"]
    place_id = pass_info["place_id"]

    url = f"{API_BASE_URL}/catalog-items/{catalog_item_id}"

    params = {
        "licensePlate": "",
        "licensePlateState": "",
        "extendPassDuration": 0,
        "placeId": place_id,
        "quantity": 1,
        "ltc": target_date,
        "channel": 0,
    }

    headers = {
        "x-api-version": "5.6",
        "Accept": "application/json",
        "User-Agent": "Buntzen-Pass-Monitor/1.0",
    }

    try:
        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        capacity_summary = data.get("capacitySummary") or {}

        status = capacity_summary.get(
            "displayCapacityStatus",
            "Unknown",
        )

        capacity_status = capacity_summary.get("capacityStatus")
        display_capacity = capacity_summary.get("displayCapacity")

        print(
            f"{pass_name}: {status} | "
            f"capacityStatus={capacity_status} | "
            f"capacity={display_capacity} | "
            f"date={target_date} | "
            f"checked={checked_time}"
        )

        normalized_status = str(status).strip().lower()

        sold_out_statuses = {
            "sold out",
            "unavailable",
            "not available",
            "closed",
        }

        is_sold_out = (
            normalized_status in sold_out_statuses
            or capacity_status == 2
        )

        if not is_sold_out:
            send_notification(
                pass_name=pass_name,
                status=status,
                target_date=target_date,
                booking_page=pass_info["booking_page"],
            )

    except requests.RequestException as error:
        print(
            f"{pass_name}: request failed | "
            f"date={target_date} | "
            f"checked={checked_time} | "
            f"error={error}"
        )

    except ValueError as error:
        print(
            f"{pass_name}: invalid API response | "
            f"date={target_date} | "
            f"checked={checked_time} | "
            f"error={error}"
        )
#print
def send_summary(target_date, checked_time, results):
    if not NTFY_TOPIC:
        return

    message = (
        f"Checked: {checked_time}\n"
        f"Target date: {target_date}\n\n"
        + "\n".join(results)
    )

    try:
        requests.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=message.encode("utf-8"),
            headers={
                "Title": "Buntzen Monitor Check",
                "Priority": "default",
                "Tags": "parking",
            },
            timeout=20,
        )
    except Exception as e:
        print(f"Could not send summary: {e}")

# --------------------------------------------------
# Main
# --------------------------------------------------

def main() -> None:
    now_vancouver = datetime.now(VANCOUVER_TZ)

    # Always check tomorrow according to Vancouver's local date,
    # not the GitHub server's UTC date.
    target_date = (now_vancouver + timedelta(days=1)).date().isoformat()

    checked_time = now_vancouver.strftime(
        "%Y-%m-%d %I:%M:%S %p %Z"
    )

    print("=" * 65)
    print(f"Buntzen pass check started: {checked_time}")
    print(f"Target date: {target_date}")
    print("=" * 65)

    for pass_name, pass_info in PASSES.items():
        check_pass(
            pass_name=pass_name,
            pass_info=pass_info,
            target_date=target_date,
            checked_time=checked_time,
        )

    print("=" * 65)
    print("Buntzen pass check finished.")
    print("=" * 65)


if __name__ == "__main__":
    main()
