import os
import requests
from datetime import datetime, timedelta
from urllib.parse import urlencode


API_ROOT = "https://api.yodelpass.com"
NTFY_TOPIC = os.environ["NTFY_TOPIC"]

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

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://yodelportal.com",
    "x-api-version": "5.6",
}


def check_pass(name, info, target_date):
    params = {
        "licensePlate": "",
        "licensePlateState": "",
        "extendPassDuration": 0,
        "placeId": info["place_id"],
        "quantity": 1,
        "ltc": target_date.isoformat(),
        "channel": 0,
    }

    url = (
        f"{API_ROOT}/api/catalog-items/"
        f"{info['catalog_item_id']}?{urlencode(params)}"
    )

    headers = HEADERS.copy()
    headers["Referer"] = info["booking_page"]

    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()

    data = response.json()
    capacity = data.get("capacitySummary") or {}

    status_code = capacity.get("capacityStatus")
    status_text = capacity.get("displayCapacityStatus")

    sold_out = (
        status_code == 2
        or "sold out" in str(status_text or "").lower()
    )

    print(
        f"{name}: {status_text} "
        f"(status={status_code})"
    )

    return not sold_out


def notify(name, target_date, booking_page):
    message = (
        f"{name} may be AVAILABLE for {target_date}.\n\n"
        "Open this notification and book immediately."
    )

    response = requests.post(
        f"https://ntfy.sh/{NTFY_TOPIC}",
        data=message.encode("utf-8"),
        headers={
            "Title": "Buntzen pass available!",
            "Priority": "urgent",
            "Tags": "rotating_light,car",
            "Click": booking_page,
        },
        timeout=20,
    )

    response.raise_for_status()
    print("Notification sent for", name)


def main():
    target_date = datetime.now().date() + timedelta(days=1)

    print("Checking Buntzen passes for", target_date)

    for name, info in PASSES.items():
        try:
            available = check_pass(name, info, target_date)

            if available:
                notify(
                    name,
                    target_date,
                    info["booking_page"],
                )

        except Exception as error:
            print(f"{name} check failed: {error}")


if __name__ == "__main__":
    main()
