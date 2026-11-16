"""从参赛包 docx 抽出 JSON 落盘到 data/。"""

from __future__ import annotations

import json
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def _docx_paragraphs(path: Path) -> str:
    with zipfile.ZipFile(path) as zf:
        root = ET.fromstring(zf.read("word/document.xml"))
    lines: list[str] = []
    for para in root.iter(f"{W_NS}p"):
        texts = [t.text or "" for t in para.iter(f"{W_NS}t")]
        line = "".join(texts)
        if line.strip():
            lines.append(line)
    return "\n".join(lines)


def _extract_json_blob(text: str) -> object:
    start_obj = text.find("{")
    start_arr = text.find("[")
    if start_obj < 0 and start_arr < 0:
        raise ValueError("docx 中未找到 JSON")
    if start_arr < 0 or (start_obj >= 0 and start_obj < start_arr):
        start, end_ch = start_obj, "}"
    else:
        start, end_ch = start_arr, "]"
    end = text.rfind(end_ch)
    return json.loads(text[start : end + 1])


def extract(*, force: bool = False) -> tuple[list, dict]:
    DATA.mkdir(parents=True, exist_ok=True)
    q_path = DATA / "题目.json"
    a_path = DATA / "答案模板.json"
    if force or not q_path.exists():
        questions = _extract_json_blob(_docx_paragraphs(ROOT / "题目.docx"))
        q_path.write_text(
            json.dumps(questions, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    else:
        questions = json.loads(q_path.read_text(encoding="utf-8"))

    if force or not a_path.exists():
        template = _extract_json_blob(_docx_paragraphs(ROOT / "答案模板.docx"))
        a_path.write_text(
            json.dumps(template, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    else:
        template = json.loads(a_path.read_text(encoding="utf-8"))

    q_ids = [x["题号"] for x in questions]
    a_ids = [x["题号"] for x in template["答案"]]
    if len(q_ids) != 100 or len(a_ids) != 100:
        raise SystemExit(f"题量异常: questions={len(q_ids)} template={len(a_ids)}")
    if q_ids != a_ids:
        raise SystemExit("题号与答案模板未对齐")
    if len(set(q_ids)) != 100:
        raise SystemExit("题目存在重复题号")
    return questions, template


def main() -> None:
    questions, template = extract(force=True)
    print(f"ok questions={len(questions)} pkg={template.get('参赛包编号')}")


if __name__ == "__main__":
    main()
