"""Send one WhatsApp template message through the Meta Cloud API."""

import argparse
import json
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env")

# Default values for the approved Meta onboarding template.
DEFAULT_PHONE_NUMBER = "+917978043970"
DEFAULT_TEMPLATE_NAME = "3p_direct_integration_test_template"
DEFAULT_LANGUAGE = "en_US"
DEFAULT_BODY_VARIABLES: list[str] = []


def build_payload(
    phone_number: str,
    template_name: str,
    language: str,
    body_variables: list[str],
) -> dict:
    """Build the template payload expected by Meta's Cloud API."""
    template = {
        "name": template_name,
        "language": {"code": language},
    }

    if body_variables:
        template["components"] = [{
            "type": "body",
            "parameters": [
                {"type": "text", "text": value}
                for value in body_variables
            ],
        }]

    return {
        "messaging_product": "whatsapp",
        "to": phone_number,
        "type": "template",
        "template": template,
    }


def send_message(
    phone_number: str,
    template_name: str,
    language: str,
    body_variables: list[str],
) -> int:
    """Send a template request and print the API response."""
    phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
    access_token = os.getenv("WHATSAPP_ACCESS_TOKEN")
    api_version = os.getenv("WHATSAPP_API_VERSION", "v18.0")

    if not phone_number_id or not access_token:
        print(
            "Missing WHATSAPP_PHONE_NUMBER_ID or WHATSAPP_ACCESS_TOKEN in .env",
            file=sys.stderr,
        )
        return 1

    payload = build_payload(phone_number, template_name, language, body_variables)
    endpoint = f"https://graph.facebook.com/{api_version}/{phone_number_id}/messages"

    try:
        response = requests.post(
            endpoint,
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
        "--template-name",
        default=DEFAULT_TEMPLATE_NAME,
        help="Exact approved Meta template name from WhatsApp Manager.",
    )
    parser.add_argument(
        "--language",
        default=DEFAULT_LANGUAGE,
        help="Meta template language code.",
    )
    parser.add_argument(
        "--body-vars",
        default=json.dumps(DEFAULT_BODY_VARIABLES),
        help='JSON array of body values, for example ["Ram", "ABC Dental"]. Leave empty for template messages with no variables.',
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the generated payload without sending it.",
    )
    args = parser.parse_args()

    try:
        body_variables = json.loads(args.body_vars)
    except json.JSONDecodeError as error:
        parser.error(f"--body-vars must be valid JSON: {error}")

    if not isinstance(body_variables, list) or not all(
        isinstance(value, (str, int, float)) for value in body_variables
    ):
        parser.error("--body-vars must be a JSON array of text or numeric values")

    if args.dry_run:
        print(json.dumps(
            build_payload(
                args.mobile,
                args.template_name,
                args.language,
                [str(value) for value in body_variables],
            ),
            indent=2,
        ))
        return 0

    return send_message(
        args.mobile,
        args.template_name,
        args.language,
        [str(value) for value in body_variables],
    )


if __name__ == "__main__":
    raise SystemExit(main())

