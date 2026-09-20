"""Send a WhatsApp template directly through the Meta Cloud API."""

import argparse
import json
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env")


def build_payload(
    recipient: str,
    template_name: str,
    language: str,
    body_variables: list[str],
) -> dict:
    """Build the positional body-variable payload expected by Meta."""
    template = {
        "name": template_name,
        "language": {"code": language},
    }

    if body_variables:
        template["components"] = [
            {
                "type": "body",
                "parameters": [
                    {"type": "text", "text": value}
                    for value in body_variables
                ],
            }
        ]

    return {
        "messaging_product": "whatsapp",
        "to": recipient,
        "type": "template",
        "template": template,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Send an approved WhatsApp template directly through Meta."
    )
    parser.add_argument("--to", required=True, help="Recipient number with country code")
    parser.add_argument("--template-name", required=True, help="Approved Meta template name")
    parser.add_argument("--language", default="en_US", help="Meta template language code")
    parser.add_argument(
        "--body-vars",
        default="[]",
        help='JSON array of body values in order, for example ["Ram", "ABC Dental"]',
    )
    parser.add_argument("--dry-run", action="store_true", help="Print the request without sending it")
    args = parser.parse_args()

    try:
        body_variables = json.loads(args.body_vars)
    except json.JSONDecodeError as error:
        parser.error(f"--body-vars must be valid JSON: {error}")

    if not isinstance(body_variables, list) or not all(
        isinstance(value, (str, int, float)) for value in body_variables
    ):
        parser.error("--body-vars must be a JSON array of text or numeric values")

    phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
    access_token = os.getenv("WHATSAPP_ACCESS_TOKEN")
    api_version = os.getenv("WHATSAPP_API_VERSION", "v18.0")

    if not phone_number_id or not access_token:
        print(
            "Missing WHATSAPP_PHONE_NUMBER_ID or WHATSAPP_ACCESS_TOKEN in .env",
            file=sys.stderr,
        )
        return 1

    payload = build_payload(
        args.to,
        args.template_name,
        args.language,
        [str(value) for value in body_variables],
    )
    url = f"https://graph.facebook.com/{api_version}/{phone_number_id}/messages"

    if args.dry_run:
        print(json.dumps({"url": url, "payload": payload}, indent=2))
        return 0

    try:
        response = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=30,
        )
    except requests.RequestException as error:
        print(f"Request failed: {error}", file=sys.stderr)
        return 1

    print(f"Status Code: {response.status_code}")
    try:
        print(json.dumps(response.json(), indent=2))
    except ValueError:
        print(response.text)

    return 0 if response.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())