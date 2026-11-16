"""结构化 LLM 转换（OpenAI 兼容接口；无 Key 时跳过）。"""

from __future__ import annotations

import json
import os
import re
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
FIELDS_DOC = ROOT / "knowledge" / "fofa_fields.md"
FEWSHOT = ROOT / "knowledge" / "few_shot.json"
REJECT_TEXT = "该需求不能直接转换为FOFA搜索语句"

SYSTEM = """你是 FOFA 查询语句专家。把用户的自然语言资产搜索需求转成一条可执行的 FOFA Query。
硬约束：
1. 只输出 JSON：{"query":"..."} 或 {"reject":true}
2. 能转换时 query 必须是单行最终语句，不要解释、不要 Markdown、不要候选列表。
3. 不能转换时输出 {"reject":true}（非法端口/IP、逻辑矛盾、无观测特征的主观需求等）。
4. 运算符仅用 = == != *= && || ()；字段参考速查文档。
5. 国家用 ISO 代码；中国大陆排除港澳台时用 country="CN" 并排除 region。
"""


@dataclass
class LlmHit:
    query: Optional[str]
    reject: bool
    raw: str = ""


def available() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY") or os.environ.get("LLM_API_KEY"))


def _endpoint() -> tuple[str, str, str]:
    key = (
        os.environ.get("LLM_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
        or ""
    ).strip()
    base = (
        os.environ.get("LLM_BASE_URL")
        or os.environ.get("OPENAI_BASE_URL")
        or "https://api.openai.com/v1"
    ).rstrip("/")
    model = os.environ.get("LLM_MODEL") or os.environ.get("OPENAI_MODEL") or "gpt-4o-mini"
    return key, base, model


def _few_shot_block() -> str:
    if not FEWSHOT.exists():
        return ""
    try:
        items = json.loads(FEWSHOT.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return ""
    lines = ["示例："]
    for it in items[:12]:
        lines.append(f"- NL: {it.get('nl')}")
        lines.append(f"  OUT: {json.dumps(it.get('out'), ensure_ascii=False)}")
    return "\n".join(lines)


def _parse_json_obj(text: str) -> Optional[dict]:
    raw = (text or "").strip()
    if not raw:
        return None
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw, re.I)
    if fenced:
        raw = fenced.group(1).strip()
    try:
        obj = json.loads(raw)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{[\s\S]*\}", raw)
    if m:
        try:
            obj = json.loads(m.group(0))
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            return None
    return None


def convert(nl: str, *, timeout: float = 60.0) -> Optional[LlmHit]:
    if not available():
        return None
    key, base, model = _endpoint()
    fields = ""
    if FIELDS_DOC.exists():
        fields = FIELDS_DOC.read_text(encoding="utf-8")[:6000]
    user = (
        f"{_few_shot_block()}\n\n字段速查：\n{fields}\n\n"
        f"自然语言：{nl}\n请输出 JSON。"
    )
    payload = {
        "model": model,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user},
        ],
    }
    req = urllib.request.Request(
        f"{base}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        content = data["choices"][0]["message"]["content"]
    except Exception as e:  # noqa: BLE001
        return LlmHit(query=None, reject=False, raw=f"error:{e}")

    obj = _parse_json_obj(content)
    if not obj:
        return LlmHit(query=None, reject=False, raw=content)
    if obj.get("reject") is True:
        return LlmHit(query=REJECT_TEXT, reject=True, raw=content)
    q = (obj.get("query") or "").strip()
    if not q:
        return LlmHit(query=None, reject=False, raw=content)
    return LlmHit(query=q, reject=False, raw=content)
