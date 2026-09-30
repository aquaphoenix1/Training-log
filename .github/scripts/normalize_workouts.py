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
current_start = next((i for i, v in enumerate(header) if i > 0 and v.strip() == EXERCISE), None)
if current_start is None:
    raise SystemExit("Could not locate current workout section")

def get(row, i):
    return row[i].strip() if i < len(row) else ""

def is_marker(exercise, values):
    text = " ".join([exercise] + [v for v in values if v])
    return "Начало новой схемы" in text or exercise in {"Агенда:", "Изменения"}

def parse_entry(row, source_row, exercise, start, section, explicit=False):
    # Google Sheets has a quirk on rows where the exercise name is explicitly
    # entered: the exercise cell is duplicated in the exported block.
    # Explicit row: exercise | exercise | reps | weight | feeling | felt | note
    # Continued row: blank    | reps     | weight | feeling | felt | note
    value_start = start + 2 if explicit else start + 1
    values = [get(row, value_start + j) for j in range(5)]
    if is_marker(exercise, values):
        return None
    reps, weight, feeling, felt, note = values
    if not any((exercise, reps, weight, feeling, felt, note)):
        return None
    return {
        "source_row": source_row,
        "exercise": exercise,
        "reps": reps,
        "weight": weight,
        "feeling": feeling,
        "felt": felt,
        "note": note,
        "section": section,
        "explicit_exercise": explicit,
    }

sessions = []
for session_number, start in enumerate((1, 6, 11, 16), start=1):
    entries, notes = [], []
    for source_row, row in enumerate(rows[1:], start=2):
        exercise = get(row, 0)
        values = [get(row, start + j) for j in range(6)]
        joined = " ".join([exercise] + [v for v in values if v])
        if "Начало новой схемы" in joined:
            notes.append({"source_row": source_row, "text": joined})
        entry = parse_entry(row, source_row, exercise, start, "old", bool(exercise))
        if entry:
            entries.append(entry)
    sessions.append({"session": session_number, "section": "old", "entries": entries, "notes": notes})

current_starts = [
    i for i, v in enumerate(header[current_start:], start=current_start)
    if v.strip() == EXERCISE and i + 4 < len(header)
]

for start in current_starts:
    entries, notes = [], []
    last_exercise = {}
    for source_row, row in enumerate(rows[1:], start=2):
        raw_exercise = get(row, start)
        if raw_exercise:
            last_exercise[source_row] = raw_exercise
        exercise = last_exercise.get(source_row, "")
        explicit = bool(raw_exercise)
        values = [get(row, start + j) for j in range(6)]
        joined = " ".join([exercise] + [v for v in values if v])
        if "Начало новой схемы" in joined:
            notes.append({"source_row": source_row, "text": joined})
        entry = parse_entry(row, source_row, exercise, start, "current", explicit)
        if entry:
            entries.append(entry)
    sessions.append({"session": len(sessions) + 1, "section": "current", "entries": entries, "notes": notes})

result = {
    "source": "Google Sheets",
    "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    "old_session_count": 4,
    "current_session_count": len(current_starts),
    "session_count": len(sessions),
    "sessions": sessions,
}
with OUTPUT.open("w", encoding="utf-8", newline="\n") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
    f.write("\n")
print(f"Generated {OUTPUT}: {len(sessions)} sessions")
