"""可选 FOFA API 试跑（需环境变量 FOFA_KEY）。"""

from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Optional

DEFAULT_BASE = "https://fofa.info"


@dataclass
class FofaProbeResult:
    ok: bool
    syntax_error: bool
    errmsg: str = ""
    size: int = 0
    skipped: bool = False


def _key() -> str:
    return (os.environ.get("FOFA_KEY") or "").strip()


def available() -> bool:
    return bool(_key())


def probe(query: str, *, size: int = 1, timeout: float = 20.0) -> FofaProbeResult:
    """size=1 试跑；无 Key 时 skipped=True。"""
    key = _key()
    if not key:
        return FofaProbeResult(ok=True, syntax_error=False, skipped=True)

    qbase64 = base64.b64encode(query.encode("utf-8")).decode("ascii")
    params = urllib.parse.urlencode(
        {
            "key": key,
            "qbase64": qbase64,
            "size": str(size),
            "page": "1",
            "fields": "host,ip,port",
        }
    )
    url = f"{DEFAULT_BASE}/api/v1/search/all?{params}"
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return FofaProbeResult(
            ok=False,
            syntax_error="Syntax" in body or "语法" in body,
            errmsg=body[:500],
        )
    except Exception as e:  # noqa: BLE001
        return FofaProbeResult(ok=False, syntax_error=False, errmsg=str(e))

    if data.get("error"):
        errmsg = str(data.get("errmsg") or data.get("message") or "error")
        syntax = "Syntax" in errmsg or "语法" in errmsg or "Incorrect" in errmsg
        return FofaProbeResult(ok=False, syntax_error=syntax, errmsg=errmsg)

    return FofaProbeResult(
        ok=True,
        syntax_error=False,
        size=int(data.get("size") or 0),
        errmsg="",
    )


def account_info(timeout: float = 15.0) -> Optional[dict]:
    key = _key()
    if not key:
        return None
    url = f"{DEFAULT_BASE}/api/v1/info/my?key={urllib.parse.quote(key)}"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:  # noqa: BLE001
        return None
