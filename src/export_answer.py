"""写出答案.json。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REJECT_TEXT = "该需求不能直接转换为FOFA搜索语句"


def build_answer_doc(
    *,
    template: dict[str, Any],
    answers_by_id: dict[str, str],
    player_name: str = "",
) -> dict[str, Any]:
    out = {
        "选手名称": player_name or template.get("选手名称") or "",
        "参赛包编号": template.get("参赛包编号") or "",
        "答案": [],
    }
    for item in template["答案"]:
        qid = item["题号"]
        q = answers_by_id.get(qid, "")
        if not q:
            raise ValueError(f"缺题: {qid}")
        out["答案"].append({"题号": qid, "查询语句": q})
    ids = [x["题号"] for x in out["答案"]]
    expected = [x["题号"] for x in template["答案"]]
    if ids != expected:
        raise ValueError("题号顺序/集合与模板不一致")
    if len(set(ids)) != len(ids):
        raise ValueError("重复题号")
    return out


def write_answer(doc: dict[str, Any], path: Path | None = None) -> Path:
    path = path or (ROOT / "答案.json")
    path.write_text(
        json.dumps(doc, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def write_report(report: dict[str, Any], path: Path | None = None) -> Path:
    path = path or (ROOT / "run_report.json")
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path
