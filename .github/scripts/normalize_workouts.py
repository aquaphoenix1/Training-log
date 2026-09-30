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


def parse_entry(row, source_row, exercise, start, section, explicit):
    # The exported sheet has two row layouts.
    # Explicit exercise row:
    # exercise | weight | feeling | felt | duplicate-exercise | reps | note
    # Continuation row:
    # blank    | reps   | weight  | feeling | felt | note
    if explicit:
        weight = get(row, start + 1)
        feeling = get(row, start + 2)
        felt = get(row, start + 3)
        note = get(row, start + 4)
        reps = get(row, start + 5)
        if note == exercise:
            note = ""
    else:
        reps = get(row, start + 1)
        weight = get(row, start + 2)
        feeling = get(row, start + 3)
        felt = get(row, start + 4)
        note = get(row, start + 5)

    values = [reps, weight, feeling, felt, note]
    if is_marker(exercise, values):
        return None
    if not any([exercise] + values):
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

# Historical blocks. They use the same explicit/continuation layout.
for session_number, start in enumerate((1, 6, 11, 16), start=1):
    entries, notes = [], []
    current_exercise = ""
    for source_row, row in enumerate(rows[1:], start=2):
        raw_exercise = get(row, start)
        if raw_exercise:
            current_exercise = raw_exercise
        values = [get(row, start + j) for j in range(7)]
        joined = " ".join([current_exercise] + [v for v in values if v])
        if "Начало новой схемы" in joined:
            notes.append({"source_row": source_row, "text": joined})
        entry = parse_entry(row, source_row, current_exercise, start, "old", bool(raw_exercise))
        if entry:
            entries.append(entry)
    sessions.append({"session": session_number, "section": "old", "entries": entries, "notes": notes})

current_starts = [
    i for i, v in enumerate(header[current_start:], start=current_start)
    if v.strip() == EXERCISE and i + 4 < len(header)
]

for start in current_starts:
    entries, notes = [], []
    current_exercise = ""
    for source_row, row in enumerate(rows[1:], start=2):
        raw_exercise = get(row, start)
        if raw_exercise:
            current_exercise = raw_exercise
        explicit = bool(raw_exercise)
        values = [get(row, start + j) for j in range(7)]
        joined = " ".join([current_exercise] + [v for v in values if v])
        if "Начало новой схемы" in joined:
            notes.append({"source_row": source_row, "text": joined})
        entry = parse_entry(row, source_row, current_exercise, start, "current", explicit)
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
