"""题型分流：不可转换启发式。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

REJECT_TEXT = "该需求不能直接转换为FOFA搜索语句"

_IP_TOKEN_RE = re.compile(
    r"(?:地址或网段为|IP(?:\s*地址)?(?:为|是)?|网段)\s*([0-9.]+(?:/[0-9]+)?)",
    re.I,
)
_PORT_RE = re.compile(r"(?:开放|端口为|端口)\s*([0-9]{1,9})\s*端口?")
_CONTRADICTION_RE = re.compile(
    r"国家代码必须等于\s*([A-Za-z]{2}).{0,40}不等于\s*\1",
    re.I | re.S,
)


@dataclass
class RejectHit:
    reason: str
    text: str = REJECT_TEXT


def _octet_ok(part: str) -> bool:
    if not part.isdigit():
        return False
    n = int(part)
    return 0 <= n <= 255


def _ip_or_cidr_invalid(token: str) -> bool:
    if "/" in token:
        ip, _, mask = token.partition("/")
        if not mask.isdigit() or not (0 <= int(mask) <= 32):
            return True
        token = ip
    parts = token.split(".")
    if len(parts) != 4:
        return True
    return not all(_octet_ok(p) for p in parts)


def check_reject(nl: str) -> Optional[RejectHit]:
    """命中则返回拒绝结果，否则 None。"""
    text = (nl or "").strip()
    if not text:
        return RejectHit("empty")

    # 非法端口
    for m in _PORT_RE.finditer(text):
        port = int(m.group(1))
        if port < 0 or port > 65535:
            return RejectHit(f"invalid_port:{port}")

    # 字面量「开放 N 端口」且 N 过大（无「端口为」时）
    for m in re.finditer(r"开放\s*([0-9]{6,})\s*端口", text):
        return RejectHit(f"invalid_port:{m.group(1)}")

    # 非法 IP / 网段（仅当题干明确给出地址字面量）
    for m in _IP_TOKEN_RE.finditer(text):
        token = m.group(1)
        if _ip_or_cidr_invalid(token):
            return RejectHit(f"invalid_ip:{token}")
    # 五段伪 IP
    if re.search(r"\b\d+(?:\.\d+){4,}\b", text):
        return RejectHit("invalid_ip:too_many_octets")

    if _CONTRADICTION_RE.search(text):
        return RejectHit("contradictory_country")

    if re.search(r"最安全", text):
        return RejectHit("subjective_security")

    if re.search(r"容器内存使用率|容器监控数据|运行时访问权限", text):
        return RejectHit("runtime_monitor")

    return None
