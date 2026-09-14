"""Send one WhatsApp template message through the Valcura webhook."""

import argparse
import json
import sys

import requests


# Use this URL while the Django server is running on your local machine.
LOCAL_URL = "http://127.0.0.1:8000/api/macrodroid/webhook/"

# Replace this with the deployed endpoint for your production environment.
PRODUCTION_URL = "https://valcura.onrender.com/api/macrodroid/webhook/"

# Change this one variable when switching between local and production testing.
url = PRODUCTION_URL

# Default values for quick local testing.
DEFAULT_PHONE_NUMBER = "+917978043970"
DEFAULT_TEMPLATE_ID = "UTL-L1-01"
DEFAULT_VARIABLES = {
    "1": "Valcura Dental",
    "2": "Alex",
    "3": "+917978043970",
}


def send_message(phone_number: str, template_id: str, variables: dict, endpoint: str) -> int:
    """Send a template request and print the API response."""
    payload = {
        "phone_number": phone_number,
        "template_id": template_id,
        "variables": variables,
    }

    try:
        response = requests.post(endpoint, json=payload, timeout=30)
    except requests.RequestException as error:
        print(f"Request failed: {error}", file=sys.stderr)
        return 1

    print(f"Status Code: {response.status_code}")
    try:
        print(json.dumps(response.json(), indent=2))
    except ValueError:
        print(response.text)

    return 0 if response.ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Send a WhatsApp message using a configured Meta template."
    )
    parser.add_argument(
        "--mobile",
        default=DEFAULT_PHONE_NUMBER,
        help="Recipient mobile number, including country code.",
    )
    parser.add_argument(
        "--template-id",
        default=DEFAULT_TEMPLATE_ID,
        help="Valcura template ID, for example UTL-L1-01.",
    )
    parser.add_argument(
        "--variables",
        default=json.dumps(DEFAULT_VARIABLES),
        help='Template variables as a JSON object, for example \'{"1":"Valcura Dental","2":"Alex"}\'.',
    )
    parser.add_argument(
        "--url",
        default=url,
        help="Override the endpoint URL; otherwise the URL variable above is used.",
    )
    args = parser.parse_args()

    try:
        variables = json.loads(args.variables)
    except json.JSONDecodeError as error:
        parser.error(f"--variables must be valid JSON: {error}")

    if not isinstance(variables, dict):
        parser.error("--variables must contain a JSON object")

    return send_message(args.mobile, args.template_id, variables, args.url)


if __name__ == "__main__":
    raise SystemExit(main())