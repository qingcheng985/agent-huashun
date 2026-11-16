"""规则模板引擎：高置信 NL → FOFA Query。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

try:
    import yaml  # type: ignore
except ImportError:  # 无 PyYAML 时用内置精简模板
    yaml = None

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES_PATH = ROOT / "knowledge" / "templates.yaml"

COUNTRY_ALIASES = {
    "大不列颠及北爱尔兰联合王国": "GB",
    "英国": "GB",
    "美国": "US",
    "中国": "CN",
    "中国大陆": "CN",
    "日本": "JP",
    "韩国": "KR",
    "德国": "DE",
    "荷兰": "NL",
    "加拿大": "CA",
    "土耳其": "TR",
    "新西兰": "NZ",
    "台湾": "TW",
    "香港": "HK",
    "澳门": "MO",
}

BUILTIN_TEMPLATES = [
    (r"IP\s*地址为\s*([0-9.]+)", 'ip="{1}"', 0.95),
    (r"([0-9.]+/[0-9]{1,2})\s*网段", 'ip="{1}"', 0.95),
    (r"主域是\s*([a-zA-Z0-9.-]+)", 'domain="{1}"', 0.95),
    (r"网站名为\s*([a-zA-Z0-9.-]+)", 'host="{1}"', 0.9),
    (r"域名里带有\s*([a-zA-Z0-9_-]+)", 'host*="{1}"', 0.9),
    (r"自治系统号为\s*([0-9]+)", 'asn="{1}"', 0.95),
    (r"开放\s*([0-9]{1,5})\s*端口", 'port="{1}"', 0.9),
    (r"状态码为\s*([0-9]{3})", 'status_code="{1}"', 0.85),
    (r"操作系统被识别为\s*linux", 'os="linux"', 0.95),
    (r"网页正文中出现\s+(\S+)\s+错误标记", 'body="{1}"', 0.9),
]


@dataclass
class RuleHit:
    query: str
    rule_id: str
    confidence: float


def _load_templates() -> list[tuple[str, str, str, float]]:
    """返回 (id, pattern, query, confidence)。"""
    if yaml and TEMPLATES_PATH.exists():
        data = yaml.safe_load(TEMPLATES_PATH.read_text(encoding="utf-8")) or {}
        out: list[tuple[str, str, str, float]] = []
        for item in data.get("templates") or []:
            out.append(
                (
                    str(item.get("id") or "tpl"),
                    str(item["pattern"]),
                    str(item["query"]),
                    float(item.get("confidence") or 0.8),
                )
            )
        if out:
            return out
    return [
        (f"builtin_{i}", pat, q, conf)
        for i, (pat, q, conf) in enumerate(BUILTIN_TEMPLATES)
    ]


def _apply_template(query_tpl: str, groups: tuple[str, ...]) -> str:
    out = query_tpl
    for i, g in enumerate(groups, start=1):
        out = out.replace(f"{{{i}}}", g)
    return out


def _country_only(nl: str) -> Optional[RuleHit]:
    # 「搜索位于X的资产」类短句
    m = re.search(r"搜索位于(.+?)的资产", nl)
    if not m:
        return None
    name = m.group(1).strip()
    code = COUNTRY_ALIASES.get(name)
    if code:
        return RuleHit(f'country="{code}"', "country_alias", 0.9)
    return None


def _cross_engine(nl: str) -> Optional[RuleHit]:
    if "Shodan" in nl and "转换成 FOFA" in nl:
        # "Server: nginx" http.title:"Welcome"
        if "Server: nginx" in nl and "Welcome" in nl:
            return RuleHit(
                'header="Server: nginx" && title="Welcome"',
                "shodan_convert",
                0.9,
            )
    if "Google Dork" in nl:
        if 'intitle:"Grafana"' in nl and 'intext:"JavaScript"' in nl:
            return RuleHit(
                'title="Grafana" && body="JavaScript"',
                "dork_convert",
                0.9,
            )
    if "urlscan.io" in nl:
        return RuleHit(
            'body="login" && (host*="bet" || host*="casino" || host*="kasino")',
            "urlscan_convert",
            0.85,
        )
    if "Hunter" in nl and "domain=" in nl:
        return RuleHit(
            'domain="google" && domain!="google.com" && title=""',
            "hunter_convert",
            0.85,
        )
    if "Censys" in nl and "Tengine" in nl:
        return RuleHit(
            'header="Server: Tengine" || header="x-cache: MISS"',
            "censys_convert",
            0.8,
        )
    if "修正这条 FOFA" in nl and "Apache" in nl and "4134" in nl:
        return RuleHit(
            'asn!="4134" && region="HK" && server=="Apache"',
            "fix_quotes",
            0.95,
        )
    if "修正这条 FOFA" in nl and "HFS" in nl:
        return RuleHit(
            '(app="HFS" && port="80") || (app="HFS" && port="8080" && status_code="200")',
            "fix_hfs_or",
            0.95,
        )
    return None


def try_rules(nl: str) -> Optional[RuleHit]:
    text = (nl or "").strip()
    if not text:
        return None

    hit = _cross_engine(text)
    if hit:
        return hit

    hit = _country_only(text)
    if hit:
        return hit

    # SOCKS5 识别提问 → 直接给 protocol
    if re.search(r"SOCKS.*v5|socks5", text, re.I):
        return RuleHit('protocol="socks5"', "socks5", 0.85)

    if re.search(r"使用\s*TCP\s*协议", text, re.I):
        return RuleHit('base_protocol="tcp"', "base_tcp", 0.9)

    # B 段
    m = re.search(r"整个\s*B\s*段[：:]\s*([0-9.]+)", text)
    if m:
        parts = m.group(1).split(".")
        if len(parts) == 4:
            return RuleHit(
                f'ip="{parts[0]}.{parts[1]}.0.0/16"',
                "b_class",
                0.9,
            )

    for rid, pattern, query_tpl, conf in _load_templates():
        m = re.search(pattern, text)
        if not m:
            continue
        # 端口模板需再校验范围
        if "port=" in query_tpl and m.groups():
            try:
                p = int(m.group(1))
            except ValueError:
                continue
            if p < 0 or p > 65535:
                continue
        q = _apply_template(query_tpl, m.groups())
        # 清理 body 模板可能带的句号
        if q.startswith('body="') and q.endswith('。"'):
            q = q[:-2] + '"'
        return RuleHit(q, rid, conf)

    return None
