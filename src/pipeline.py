"""批跑入口：拒绝门 → 规则 → seed → LLM → 校验 →（可选）FOFA 试跑 → 导出。"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from classify import REJECT_TEXT, check_reject  # noqa: E402
from export_answer import build_answer_doc, write_answer, write_report  # noqa: E402
from extract_docx import extract  # noqa: E402
from fofa_client import available as fofa_available  # noqa: E402
from fofa_client import probe  # noqa: E402
from llm_convert import available as llm_available  # noqa: E402
from llm_convert import convert as llm_convert  # noqa: E402
from rules_engine import try_rules  # noqa: E402
from validate import validate_query  # noqa: E402

SEED_PATH = ROOT / "knowledge" / "seed_answers.json"


def _load_seed() -> dict[str, str]:
    if not SEED_PATH.exists():
        return {}
    data = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        return {str(k): str(v) for k, v in data.items()}
    return {}


def convert_one(qid: str, nl: str, seed: dict[str, str]) -> dict:
    row: dict = {
        "题号": qid,
        "自然语言输入": nl,
        "path": "",
        "query": "",
        "confidence": 0.0,
        "needs_review": False,
        "validate_ok": True,
        "errors": [],
        "warnings": [],
        "fofa": None,
    }

    reject = check_reject(nl)
    if reject:
        row.update(
            path="reject",
            query=reject.text,
            confidence=1.0,
            reason=reject.reason,
        )
        return row

    rule = try_rules(nl)
    if rule and rule.confidence >= 0.85:
        row.update(
            path="rule",
            query=rule.query,
            confidence=rule.confidence,
            rule_id=rule.rule_id,
        )
    elif qid in seed:
        row.update(
            path="seed",
            query=seed[qid],
            confidence=0.8,
        )
    else:
        llm = llm_convert(nl) if llm_available() else None
        if llm and llm.reject:
            row.update(path="llm_reject", query=REJECT_TEXT, confidence=0.7)
        elif llm and llm.query:
            row.update(path="llm", query=llm.query, confidence=0.7)
        else:
            row.update(
                path="needs_review",
                query=seed.get(qid, ""),
                confidence=0.0,
                needs_review=True,
            )
            if not row["query"]:
                row["query"] = REJECT_TEXT
                row["errors"].append("no_conversion")

    if row["query"] != REJECT_TEXT:
        vr = validate_query(row["query"])
        row["validate_ok"] = vr.ok
        row["errors"].extend(vr.errors)
        row["warnings"].extend(vr.warnings)
        if not vr.ok:
            row["needs_review"] = True
            # 语法坏且有 seed 时回退 seed
            if qid in seed and seed[qid] != row["query"]:
                row["query"] = seed[qid]
                row["path"] = f"{row['path']}+seed_fallback"
                vr2 = validate_query(row["query"])
                row["validate_ok"] = vr2.ok
                row["errors"] = vr2.errors
                row["warnings"] = vr2.warnings

        if fofa_available() and row["query"] != REJECT_TEXT:
            pr = probe(row["query"])
            row["fofa"] = {
                "skipped": pr.skipped,
                "ok": pr.ok,
                "syntax_error": pr.syntax_error,
                "errmsg": pr.errmsg,
                "size": pr.size,
            }
            if pr.syntax_error:
                row["needs_review"] = True
                row["errors"].append("fofa_syntax_error")

    return row


def run(*, player_name: str = "") -> tuple[Path, Path]:
    questions, template = extract(force=False)
    seed = _load_seed()
    name = player_name or os.environ.get("FOFA_PLAYER_NAME") or ""

    rows = []
    answers_by_id: dict[str, str] = {}
    for q in questions:
        qid = q["题号"]
        nl = q["自然语言输入"]
        row = convert_one(qid, nl, seed)
        rows.append(row)
        answers_by_id[qid] = row["query"]

    doc = build_answer_doc(
        template=template,
        answers_by_id=answers_by_id,
        player_name=name,
    )
    answer_path = write_answer(doc)
    report = {
        "pkg": template.get("参赛包编号"),
        "total": len(rows),
        "by_path": {},
        "needs_review": [r["题号"] for r in rows if r.get("needs_review")],
        "llm_available": llm_available(),
        "fofa_available": fofa_available(),
        "items": rows,
    }
    for r in rows:
        p = r.get("path") or "unknown"
        report["by_path"][p] = report["by_path"].get(p, 0) + 1
    report_path = write_report(report)
    return answer_path, report_path


def main() -> None:
    answer_path, report_path = run()
    print(f"wrote {answer_path}")
    print(f"wrote {report_path}")


if __name__ == "__main__":
    main()
