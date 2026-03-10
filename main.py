import logging
import os
import secrets
from typing import Optional

logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import FileResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles

from checkmk import get_problems

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

app.mount("/static", StaticFiles(directory="static"), name="static")

# --- Basic auth (optional) ---
# Only active when both DASHBOARD_USER and DASHBOARD_PASSWORD are set in .env.

_AUTH_USER     = os.getenv("DASHBOARD_USER", "")
_AUTH_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "")
_auth_enabled  = bool(_AUTH_USER and _AUTH_PASSWORD)

_security = HTTPBasic(auto_error=False)

def _require_auth(credentials: Optional[HTTPBasicCredentials] = Depends(_security)):
    if not _auth_enabled:
        return
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers={"WWW-Authenticate": 'Basic realm="Monitoring Dashboard"'},
        )
    ok_user = secrets.compare_digest(credentials.username.encode(), _AUTH_USER.encode())
    ok_pass = secrets.compare_digest(credentials.password.encode(), _AUTH_PASSWORD.encode())
    if not (ok_user and ok_pass):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers={"WWW-Authenticate": 'Basic realm="Monitoring Dashboard"'},
        )


# --- Routes ---

@app.get("/")
async def root(_: None = Depends(_require_auth)):
    return FileResponse("static/index.html")


@app.get("/api/config")
async def config(_: None = Depends(_require_auth)):
    """Returns non-sensitive config to the frontend."""
    logo_file = os.getenv("DASHBOARD_LOGO", "")
    return {
        "title":         os.getenv("DASHBOARD_TITLE", "Monitoring Dashboard"),
        "site":          os.getenv("CMK_SITE", ""),
        "support_email": os.getenv("SUPPORT_EMAIL", ""),
        "support_phone": os.getenv("SUPPORT_PHONE", ""),
        "logo":          f"/static/{logo_file}" if logo_file else "",
    }


@app.get("/api/problems")
async def problems(_: None = Depends(_require_auth)):
    """
    Fetches non-OK services via the Checkmk REST API.

    Security note: this endpoint does not forward any user input to Checkmk.
    All parameters are hardcoded in checkmk.py.
    The app makes read-only GET requests to Checkmk only.
    """
    try:
        data = await get_problems()
        return data
    except Exception as e:
        logger.exception("Failed to fetch problems from Checkmk: %s", e)
        raise HTTPException(status_code=500, detail="Could not connect to Checkmk.")
