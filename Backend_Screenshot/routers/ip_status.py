"""
IP status router — live status of the Tor-based IP changer.

GET /ip-status        cheap cached snapshot for the UI (polled every few sec)
GET /ip-status/refresh forces a live exit-IP lookup through Tor (slower)

Read-only. Does not touch the scan pipeline.
"""
import logging

from fastapi import APIRouter

from services import ip_changer

logger = logging.getLogger(__name__)
router = APIRouter(tags=["IP Status"])


@router.get("/ip-status", summary="Live IP-changer status (cached)")
def ip_status():
    """
    Returns:
        enabled     — is IP changing switched on (PROXY_ENABLED)
        tor_up      — is Tor actually reachable right now
        current_ip  — last known Tor exit IP (None until first rotation)
        rotations   — how many times the IP has changed this scan
    """
    return ip_changer.get_status()


@router.get("/ip-status/refresh", summary="Force a live exit-IP lookup")
def ip_status_refresh():
    """Fetches the current exit IP through Tor now (slower), then returns status."""
    ip_changer.get_current_ip()
    return ip_changer.get_status()
