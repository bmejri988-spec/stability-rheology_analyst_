import json
import sys
import time
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv

from config import FIRECRAWL_API_KEY, FIRECRAWL_MODEL, FIRECRAWL_TIMEOUT_SECONDS, FIRECRAWL_URL


STATIC_PROMPT = (
    "From the provided pages, return one short summary sentence and up to three bullets about key points."
)

STATIC_URLS = [
    "https://docs.firecrawl.dev/introduction",
    "https://firecrawl.dev",
]

STATIC_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "risk_signals": {"type": "array", "items": {"type": "string"}},
        "uncertainties": {"type": "array", "items": {"type": "string"}},
        "alternatives": {"type": "array", "items": {"type": "string"}},
    },
}


def _status_url(job_id: str) -> str:
    base = (FIRECRAWL_URL or "https://api.firecrawl.dev/v2/agent").rstrip("/")
    if base.endswith("/v2/agent"):
        return f"{base}/{job_id}"
    parsed = urlparse(base)
    root = f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme and parsed.netloc else "https://api.firecrawl.dev"
    return f"{root}/v2/agent/{job_id}"


def main() -> int:
    load_dotenv()

    if not FIRECRAWL_API_KEY:
        print("ERROR: FIRECRAWL_API_KEY/firecrawl_api_key is missing.")
        return 1

    payload = {
        "prompt": STATIC_PROMPT,
        "urls": STATIC_URLS,
        "schema": STATIC_SCHEMA,
        "maxCredits": 120,
        "strictConstrainToURLs": True,
        "model": FIRECRAWL_MODEL or "spark-1-mini",
    }

    print("Posting to Firecrawl agent endpoint...")
    try:
        res = requests.post(
            FIRECRAWL_URL,
            headers={
                "Authorization": f"Bearer {FIRECRAWL_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=max(20, FIRECRAWL_TIMEOUT_SECONDS),
        )
    except Exception as exc:
        print(f"ERROR: POST failed: {exc}")
        return 1

    print(f"POST status: {res.status_code}")
    try:
        post_body = res.json()
    except Exception:
        print("ERROR: Non-JSON POST response")
        print(res.text[:1200])
        return 1

    print("POST body:")
    print(json.dumps(post_body, indent=2, ensure_ascii=True)[:2000])

    if res.status_code >= 400:
        return 1

    if isinstance(post_body.get("data"), dict):
        print("Completed immediately with data.")
        print(json.dumps(post_body.get("data"), indent=2, ensure_ascii=True)[:4000])
        return 0

    job_id = str(post_body.get("id") or "").strip()
    if not job_id:
        print("ERROR: No job id returned.")
        return 1

    status_url = _status_url(job_id)
    print(f"Polling job status: {status_url}")

    deadline = time.time() + 90
    while time.time() < deadline:
        try:
            poll = requests.get(
                status_url,
                headers={"Authorization": f"Bearer {FIRECRAWL_API_KEY}"},
                timeout=20,
            )
        except Exception as exc:
            print(f"WARN: poll failed: {exc}")
            time.sleep(2)
            continue

        try:
            body = poll.json()
        except Exception:
            print("WARN: non-JSON poll response")
            time.sleep(2)
            continue

        status = str(body.get("status") or "unknown").lower()
        print(f"poll status={poll.status_code}, state={status}")

        if status == "completed":
            data = body.get("data", {})
            print("Completed data:")
            print(json.dumps(data, indent=2, ensure_ascii=True)[:4000])
            return 0

        if status in {"failed", "cancelled", "canceled"}:
            print("ERROR: job failed/cancelled")
            print(json.dumps(body, indent=2, ensure_ascii=True)[:4000])
            return 1

        time.sleep(2)

    print("ERROR: timed out waiting for completion")
    return 1


if __name__ == "__main__":
    sys.exit(main())
