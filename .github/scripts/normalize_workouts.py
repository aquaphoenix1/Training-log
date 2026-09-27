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

def parse_entry(row, source_row, exercise, start, section, explicit=False):
    # Block layout: exercise | weight(s) | feeling score | felt | note.
    weight = get(row, start + 1)
    feeling = get(row, start + 2)
    felt = get(row, start + 3)
    note = get(row, start + 4)
    if not any((exercise, weight, feeling, felt, note)):
        return None
    if exercise.startswith("Агенда:") or exercise == "Изменения":
        return None
    return {
        "source_row": source_row,
        "exercise": exercise,
        "weight": weight,
        "feeling": feeling,
        "felt": felt,
        "note": note,
        "section": section,
        "explicit_exercise": explicit,
    }

sessions = []

# Historical section: four blocks, B/G/L/Q.
for session_number, start in enumerate((1, 6, 11, 16), start=1):
    entries, notes = [], []
    for source_row, row in enumerate(rows[1:], start=2):
        exercise = get(row, 0)
        joined = " ".join(get(row, start + j) for j in range(5))
        if "Начало новой схемы" in joined:
            notes.append({"source_row": source_row, "text": joined})
        entry = parse_entry(row, source_row, exercise, start, "old", True)
        if entry:
            entries.append(entry)
    sessions.append({"session": session_number, "section": "old", "entries": entries, "notes": notes})

# Current section: every repeated exercise header starts a workout block.
current_starts = [
    i for i, v in enumerate(header[current_start:], start=current_start)
    if v.strip() == EXERCISE and i + 3 < len(header)
]
last_exercise = {}
for start in current_starts:
    entries, notes = [], []
    for source_row, row in enumerate(rows[1:], start=2):
        raw_exercise = get(row, start)
        if raw_exercise:
            last_exercise[source_row] = raw_exercise
        exercise = last_exercise.get(source_row, "")
        values = [get(row, start + j) for j in range(5)]
        joined = " ".join(v for v in values if v)
        if "Начало новой схемы" in joined:
            notes.append({"source_row": source_row, "text": joined})
        entry = parse_entry(row, source_row, exercise, start, "current", bool(raw_exercise))
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
