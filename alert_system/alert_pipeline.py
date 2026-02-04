"""This module defines the alert pipeline handler which detects spikes and sends alerts."""

from alert_detect import detect_spikes
from alert_send import send_alerts


def handler(event, context):
    print("=" * 50)
    print("Starting Alert Pipeline")
    print("=" * 50)

    # Detect spikes
    spiking_keywords = detect_spikes()

    if not spiking_keywords:
        print("No spikes detected")
        return {
            "statusCode": 200,
            "body": "No spikes detected"
        }

    # Send alerts
    send_alerts(spiking_keywords)

    print("=" * 50)
    print("Alert Pipeline complete")
    print("=" * 50)

    return {
        "statusCode": 200,
        "body": f"Processed {len(spiking_keywords)} spiking keywords"
    }


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    handler(None, None)
