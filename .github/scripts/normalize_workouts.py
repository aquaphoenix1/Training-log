#!/usr/bin/env python3
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

INPUT = Path("workouts_raw.csv")
OUTPUT = Path("workouts.json")
EXERCISE = "Тренажер/упражнение"

with INPUT.open("r", encoding="utf-8-sig", newline="") as f:
    rows = list(csv.reader(f))
if not rows:
    raise SystemExit("Google Sheet export is empty")

header = rows[0]

# The actual exported sheet is a horizontal history. Every workout block is
# exactly five columns: exercise, reps, weight, target-muscle feeling, felt.
# Blank separator columns occur between some groups of blocks. There is no
# duplicated exercise cell and no special first-row layout.
block_starts = [
    i for i, value in enumerate(header)
    if value.strip() == EXERCISE
]
if not block_starts:
    raise SystemExit("Could not locate workout blocks")


def get(row, index):
    return row[index].strip() if index < len(row) else ""


def parse_block(start, section, session_number):
    entries = []
    notes = []
    for source_row, row in enumerate(rows[1:], start=2):
        exercise = get(row, start)
        reps = get(row, start + 1)
        weight = get(row, start + 2)
        feeling = get(row, start + 3)
        felt = get(row, start + 4)
        note = get(row, start + 5)

        text = " ".join(v for v in (exercise, reps, weight, feeling, felt, note) if v)
        if "Начало новой схемы" in text:
            notes.append({"source_row": source_row, "text": text})
            continue
        if exercise in {"Агенда:", "Изменения"}:
            continue
        if not any((exercise, reps, weight, feeling, felt, note)):
            continue

        entries.append({
            "source_row": source_row,
            "exercise": exercise,
            "reps": reps,
            "weight": weight,
            "feeling": feeling,
            "felt": felt,
            "note": note,
            "section": section,
            "explicit_exercise": bool(exercise),
        })

    return {
        "session": session_number,
        "section": section,
        "entries": entries,
        "notes": notes,
    }


sessions = []
for session_number, start in enumerate(block_starts, start=1):
    section = "old" if session_number <= 4 else "current"
    sessions.append(parse_block(start, section, session_number))

result = {
    "source": "Google Sheets",
    "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    "old_session_count": sum(s["section"] == "old" for s in sessions),
    "current_session_count": sum(s["section"] == "current" for s in sessions),
    "session_count": len(sessions),
    "sessions": sessions,
}

with OUTPUT.open("w", encoding="utf-8", newline="\n") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
    f.write("\n")

print(f"Generated {OUTPUT}: {len(sessions)} sessions")
