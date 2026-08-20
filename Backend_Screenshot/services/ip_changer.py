"""
ip_changer.py — Tor-based IP rotation for the Creative Scanner Pro scan engine.

Purpose
-------
Route the scan browser through the Tor network and get a fresh exit IP per
site, WITHOUT changing the host machine's system IP and WITHOUT needing root
or systemctl (unlike the original shell script). Also exposes a live status
(enabled / Tor reachable / current IP / rotation count) for the UI.

How it works
------------
Tor exposes a SOCKS5 proxy (default 127.0.0.1:9050). Playwright sends all
browser traffic through it. To change the IP, we ask Tor for a NEW circuit by
sending the NEWNYM signal over Tor's control port (default 127.0.0.1:9051).

Requirements (must be running wherever the scanner runs)
--------------------------------------------------------
Tor installed and running with a torrc containing:

    SocksPort 9050
    ControlPort 9051
    # Authentication — pick ONE:
    HashedControlPassword 16:XXXX...     # make one: tor --hash-password "yourpass"
    # or
    CookieAuthentication 1

Optional Python dependency (for reading the exit IP):
    requests[socks]      # pip install "requests[socks]"

Configuration (environment / .env)
----------------------------------
    PROXY_ENABLED         true|false   master on/off switch (default: false)
    TOR_SOCKS_HOST        127.0.0.1
    TOR_SOCKS_PORT        9050
    TOR_CONTROL_HOST      127.0.0.1
    TOR_CONTROL_PORT      9051
    TOR_CONTROL_PASSWORD  control password (blank = try null/cookie auth)
    TOR_NEWNYM_WAIT       5            seconds to wait after asking for a new IP

Public API
----------
    is_enabled()        -> bool                is IP changing turned on?
    is_tor_reachable()  -> bool                can we actually reach Tor now?
    get_proxy()         -> dict | None         Playwright proxy config, or None
    renew_ip()          -> bool                request a fresh Tor exit IP
    get_current_ip()    -> str | None          fetch current exit IP (live)
    renew_and_report()  -> tuple[str|None,int] rotate, fetch IP, bump counter
    get_status()        -> dict                cached snapshot for the UI
    reset_counters()    -> None                zero the rotation count (scan start)

SAFETY: when PROXY_ENABLED is false — or Tor can't be reached — every function
degrades gracefully so the scanner keeps working normally without IP changing.
It never crashes a scan.
"""
from __future__ import annotations

import logging
import os
import socket
import time
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# ── Live state (cached so the /ip-status endpoint is fast) ────────────────────
_rotation_count: int = 0
_current_ip: Optional[str] = None


# ── Small env helpers ─────────────────────────────────────────────────────────

def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _env_int(name: str, default: int) -> int:
    try:
        return int(_env(name, str(default)))
    except ValueError:
        return default


def is_enabled() -> bool:
    """Master on/off switch. Set PROXY_ENABLED=true in .env to turn IP changing on."""
    return _env("PROXY_ENABLED", "false").lower() in ("1", "true", "yes", "on")


def _socks_host() -> str:
    return _env("TOR_SOCKS_HOST", "127.0.0.1")


def _socks_port() -> int:
    return _env_int("TOR_SOCKS_PORT", 9050)


# ── Proxy config for Playwright ───────────────────────────────────────────────

def get_proxy() -> Optional[dict]:
    """
    Return a Playwright-style proxy config pointing at Tor's SOCKS5 port,
    or None when IP changing is disabled.
    """
    if not is_enabled():
        return None
    return {"server": f"socks5://{_socks_host()}:{_socks_port()}"}


# ── Reachability ──────────────────────────────────────────────────────────────

def is_tor_reachable(timeout: float = 3.0) -> bool:
    """
    Quick check that Tor's SOCKS port is actually accepting connections.
    Used before enabling the proxy so a dead Tor never breaks a scan.
    """
    if not is_enabled():
        return False
    try:
        with socket.create_connection((_socks_host(), _socks_port()), timeout=timeout):
            return True
    except OSError:
        return False


# ── Tor control port (used to rotate the IP) ──────────────────────────────────

def _control_send(commands: list[str], timeout: float = 10.0) -> bool:
    """
    Connect to the Tor control port, authenticate, and run the given commands.
    Returns True only if Tor answered '250' (OK) to all of them.
    """
    host = _env("TOR_CONTROL_HOST", "127.0.0.1")
    port = _env_int("TOR_CONTROL_PORT", 9051)
    password = _env("TOR_CONTROL_PASSWORD", "")

    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            sock.settimeout(timeout)

            def _cmd(line: str) -> str:
                sock.sendall((line + "\r\n").encode("utf-8"))
                return sock.recv(1024).decode("utf-8", "ignore")

            auth_line = f'AUTHENTICATE "{password}"' if password else "AUTHENTICATE"
            resp = _cmd(auth_line)
            if not resp.startswith("250"):
                logger.warning("[TOR] Control-port auth failed: %s", resp.strip())
                return False

            for c in commands:
                resp = _cmd(c)
                if not resp.startswith("250"):
                    logger.warning("[TOR] Command '%s' failed: %s", c, resp.strip())
                    return False
            return True
    except OSError as e:
        logger.warning("[TOR] Cannot reach control port %s:%s — %s", host, port, e)
        return False


def renew_ip() -> bool:
    """
    Ask Tor for a brand-new circuit (fresh exit IP). Waits TOR_NEWNYM_WAIT
    seconds afterwards so Tor can build the new circuit before traffic flows.
    Returns True if Tor accepted the request.
    """
    if not is_enabled():
        return False
    if not _control_send(["SIGNAL NEWNYM"]):
        return False
    time.sleep(max(0.0, float(_env_int("TOR_NEWNYM_WAIT", 5))))
    logger.info("[TOR] Requested new circuit (NEWNYM)")
    return True


# ── Exit-IP lookup ────────────────────────────────────────────────────────────

def get_current_ip() -> Optional[str]:
    """
    Return the current Tor exit IP by calling an echo-IP service THROUGH Tor.
    Needs 'requests[socks]'. Returns None if unavailable. Updates the cache.
    """
    global _current_ip
    if not is_enabled():
        return None
    proxy_url = f"socks5h://{_socks_host()}:{_socks_port()}"
    try:
        import requests  # local import so the engine never hard-depends on it
        resp = requests.get(
            "https://checkip.amazonaws.com",
            proxies={"http": proxy_url, "https": proxy_url},
            timeout=15,
        )
        ip = resp.text.strip() or None
        if ip:
            _current_ip = ip
        return ip
    except Exception as e:  # noqa: BLE001 — verification must never break a scan
        logger.debug("[TOR] get_current_ip failed: %s", e)
        return None


# ── Combined rotate + report (used by the scan engine, one call per site) ─────

def renew_and_report() -> Tuple[Optional[str], int]:
    """
    Rotate to a fresh Tor circuit, read the new exit IP, bump the rotation
    counter, and return (ip, rotation_count). Safe to call even if Tor is
    momentarily unavailable (returns the last known values).
    """
    global _rotation_count
    if renew_ip():
        _rotation_count += 1
        get_current_ip()  # refreshes the cached _current_ip
    return _current_ip, _rotation_count


# ── Status snapshot for the UI (fast — uses cached values) ────────────────────

def get_status() -> dict:
    """Cheap status snapshot for the /ip-status endpoint (no live network call)."""
    return {
        "enabled": is_enabled(),
        "tor_up": is_tor_reachable(),
        "current_ip": _current_ip,
        "rotations": _rotation_count,
    }


def reset_counters() -> None:
    """Zero the rotation count and cached IP — call at the start of each scan."""
    global _rotation_count, _current_ip
    _rotation_count = 0
    _current_ip = None


# ── Manual test: run `python ip_changer.py` to check your Tor setup ──────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    os.environ.setdefault("PROXY_ENABLED", "true")

    print("Enabled       :", is_enabled())
    print("Tor reachable :", is_tor_reachable())
    print("Proxy config  :", get_proxy())
    print("Current IP    :", get_current_ip())
    ip, count = renew_and_report()
    print(f"After rotate  : ip={ip} rotations={count}")
    print("Status        :", get_status())
