import httpx
import logging
import os
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()

CMK_URL    = os.getenv("CMK_URL")       # e.g. https://checkmk.example.com/sitename
CMK_USER   = os.getenv("CMK_USER")
CMK_SECRET = os.getenv("CMK_SECRET")    # automation secret
CMK_SITE   = os.getenv("CMK_SITE")      # filter on this site (optional)

TICKET_PATTERN = os.getenv("TICKET_PATTERN", "INC")  # prefix of ticket numbers in acknowledge comments

def _headers():
    return {
        "Authorization": f"Bearer {CMK_USER} {CMK_SECRET}",
        "Accept": "application/json",
    }

def _has_ticket(comment: str) -> bool:
    """Check if the acknowledge comment contains a ticket number."""
    return TICKET_PATTERN.upper() in comment.upper()

async def get_problems() -> dict:
    async with httpx.AsyncClient(verify=False, timeout=10) as client:
        resp = await client.get(
            f"{CMK_URL}/check_mk/api/1.0/domain-types/service/collections/all",
            headers=_headers(),
            params={
                "query": '{"op": ">=", "left": "state", "right": "1"}',
                **({"sites": [CMK_SITE]} if CMK_SITE else {}),
                "columns": [
                    "host_name",
                    "description",
                    "state",
                    "plugin_output",
                    "acknowledged",
                    "comments_with_info",
                    "last_state_change",
                ],
            },
        )
        if not resp.is_success:
            logger.error("Checkmk API error %s: %s", resp.status_code, resp.text)
        resp.raise_for_status()

    services = resp.json().get("value", [])

    critical, warning, acknowledged = [], [], []

    for svc in services:
        ext = svc.get("extensions", {})
        item = {
            "host":        ext.get("host_name", ""),
            "service":     ext.get("description", ""),
            "output":      ext.get("plugin_output", ""),
            "state":       ext.get("state", -1),          # 1=WARN, 2=CRIT, 3=UNKNOWN
            "ack":         bool(ext.get("acknowledged")),
            "ack_comment": " ".join(c[2] for c in ext.get("comments_with_info", []) if len(c) > 2),
            "last_change": ext.get("last_state_change", ""),
        }

        if item["ack"] and _has_ticket(item["ack_comment"]):
            acknowledged.append(item)
        elif item["state"] == 2:
            critical.append(item)
        else:
            warning.append(item)

    return {
        "critical":     critical,
        "warning":      warning,
        "acknowledged": acknowledged,
    }
