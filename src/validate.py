"""本地 FOFA Query 语法校验。"""

from __future__ import annotations

import re
from dataclasses import dataclass

KNOWN_FIELDS = {
    "ip",
    "port",
    "protocol",
    "base_protocol",
    "host",
    "domain",
    "title",
    "body",
    "header",
    "banner",
    "server",
    "status_code",
    "country",
    "region",
    "city",
    "asn",
    "org",
    "os",
    "app",
    "product",
    "product.version",
    "product_category",
    "cloud_name",
    "is_cloud",
    "cert",
    "cert.subject",
    "cert.subject.cn",
    "cert.subject.org",
    "cert.issuer",
    "cert.issuer.cn",
    "cert.issuer.org",
    "cert.sn",
    "cert.domain",
    "cert.is_valid",
    "cert.is_match",
    "cert.is_equal",
    "cert.after",
    "cert.before",
    "tls.version",
    "tls.ja3s",
    "jarm",
    "icon_hash",
    "fid",
    "header_hash",
    "body_hash",
    "banner_hash",
    "banner_fid",
    "is_domain",
    "is_ipv6",
    "is_honeypot",
    "is_fraud",
    "cname",
    "cname_domain",
    "after",
    "before",
    "type",
    "icp",
    "icp.number",
}

_FIELD_RE = re.compile(
    r"\b([a-zA-Z_][a-zA-Z0-9_.]*)\s*(?:==|=|!=|\*=)",
)


@dataclass
class ValidationResult:
    ok: bool
    errors: list[str]
    warnings: list[str]


def _balanced(s: str, left: str, right: str) -> bool:
    n = 0
    for ch in s:
        if ch == left:
            n += 1
        elif ch == right:
            n -= 1
            if n < 0:
                return False
    return n == 0


def _quotes_ok(s: str) -> bool:
    # 简单：双引号成对（忽略转义复杂度的粗检）
    in_q = False
    i = 0
    while i < len(s):
        ch = s[i]
        if ch == "\\" and in_q:
            i += 2
            continue
        if ch == '"':
            in_q = not in_q
        i += 1
    return not in_q


def validate_query(query: str) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []
    q = (query or "").strip()
    if not q:
        return ValidationResult(False, ["empty_query"], [])

    if "```" in q or q.startswith("#"):
        errors.append("markdown_or_comment")

    if not _balanced(q, "(", ")"):
        errors.append("unbalanced_parens")
    if not _quotes_ok(q):
        errors.append("unbalanced_quotes")

    # 非法端口字面量
    for m in re.finditer(r'port\s*(?:==|=|!=)\s*"([0-9]+)"', q):
        p = int(m.group(1))
        if p < 0 or p > 65535:
            errors.append(f"invalid_port_literal:{p}")

    # 未知字段（警告，不直接失败——FOFA 字段会演进）
    for m in _FIELD_RE.finditer(q):
        field = m.group(1)
        if field not in KNOWN_FIELDS:
            warnings.append(f"unknown_field:{field}")

    return ValidationResult(ok=not errors, errors=errors, warnings=warnings)
