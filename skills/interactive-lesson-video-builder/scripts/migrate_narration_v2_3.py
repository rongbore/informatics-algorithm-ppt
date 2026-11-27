import argparse
import json
import re
from pathlib import Path

DURATION = {"D1": 6, "D2": 8, "D3": 10, "D4": 15, "D5": 20}

RULES = [
    ("D5", [r"综合", r"开放题", r"设计.*方案", r"多条件", r"离堂检测", r"综合分析"]),
    ("D4", [r"代码", r"递归", r"状态转移", r"懒标记", r"区间.*查询", r"模拟", r"推导", r"证明", r"更新路径", r"多个步骤"]),
    ("D3", [r"计算", r"查询", r"更新", r"如何拆分", r"怎样计算", r"过程", r"模拟.*一遍"]),
    ("D2", [r"为什么", r"区别", r"判断", r"理解", r"作用", r"含义"]),
    ("D1", [r"是什么", r"定义", r"说出", r"指出", r"回忆", r"名称"])
]

def classify(text):
    for level, patterns in RULES:
        for pattern in patterns:
            if re.search(pattern, text):
                return level, f"matched rule: {pattern}"
    return "D3", "no strong keyword match; use default single-step reasoning"

def main():
    ap = argparse.ArgumentParser(description="Annotate V2.2 thinking prompts with V2.3 adaptive difficulty")
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--overrides", default="config/thinking_difficulty_overrides.json")
    ap.add_argument("--config", default="config/video_ux_v2_3.json")
    args = ap.parse_args()
    source = json.loads(Path(args.input).read_text(encoding="utf-8-sig"))
    overrides_path = Path(args.overrides)
    overrides = json.loads(overrides_path.read_text(encoding="utf-8-sig")) if overrides_path.exists() else {}
    cfg = json.loads(Path(args.config).read_text(encoding="utf-8-sig"))
    table = cfg["pacing"]["thinking_seconds_by_difficulty"]
    report = []
    for slide in source.get("slides", []):
        slide_id = int(slide["slide"])
        for event in slide.get("events", []):
            if event.get("type") != "thinking_prompt":
                continue
            event_id = event.get("event_id", "")
            override = overrides.get(event_id, overrides.get(f"{slide_id}:{event_id}", overrides.get(str(slide_id))))
            if isinstance(override, str):
                level, reason = override, "teacher override"
            elif isinstance(override, dict):
                level, reason = override.get("difficulty", "D3"), "teacher override"
            elif event.get("difficulty"):
                level, reason = event["difficulty"], "existing explicit difficulty"
            else:
                level, reason = classify(event.get("text", ""))
            if level not in table:
                raise SystemExit(f"Invalid difficulty {level!r} for slide {slide_id} event {event_id}")
            seconds = float(override.get("thinking_seconds")) if isinstance(override, dict) and override.get("thinking_seconds") is not None else float(table[level])
            event["difficulty"] = level
            event["thinking_seconds"] = seconds
            event["difficulty_rationale"] = reason
            report.append({"slide": slide_id, "event_id": event_id, "difficulty": level,
                           "thinking_seconds": seconds, "rationale": reason})
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(source, ensure_ascii=False, indent=2), encoding="utf-8")
    report_path = Path(args.output).with_name("thinking_difficulty_report.json")
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Annotated {len(report)} thinking prompts. Output: {args.output}")
    print(f"Difficulty report: {report_path}")

if __name__ == "__main__":
    main()
