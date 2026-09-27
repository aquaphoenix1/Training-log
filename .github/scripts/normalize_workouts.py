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

# The sheet contains two layouts.
# Old layout: exercise names are stored once in column A and each workout is
# a five-column block: reps, weight, feeling, felt, separator. There are four
# such historical workouts.
# Current layout: each workout repeats a five-column block beginning with
# "Тренажер/упражнение". A blank exercise cell means the exercise is unchanged
# from the previous workout; a non-empty cell is an explicit replacement.
#
# The previous parser tried to infer blocks from blank columns and consequently
# merged the four old workouts into one session. Keep the layout rules explicit.

current_start = next(
    (i for i, value in enumerate(header) if i > 0 and value.strip() == EXERCISE),
    None,
)
if current_start is None:
    raise SystemExit("Could not locate current workout section")


def cell(row, index):
    return row[index].strip() if index < len(row) else ""


def make_entry(row, source_row, exercise, start, section):
    reps = cell(row, start + 1)
    weight = cell(row, start + 2)
    feeling = cell(row, start + 3)
    felt = cell(row, start + 4)

    if not any((exercise, reps, weight, feeling, felt)):
        return None
    if exercise.startswith("Агенда:") or exercise == "Изменения":
        return None

    return {
        "source_row": source_row,
        "exercise": exercise,
        "reps": reps,
        "weight": weight,
        "target_feel": feeling,
        "felt": felt,
        "section": section,
    }


sessions = []

# Four historical workouts. Column A contains the exercise name for all of
# them; each workout starts at B, G, L and Q respectively.
old_starts = [1, 6, 11, 16]
for session_number, start in enumerate(old_starts, start=1):
    entries = []
    notes = []
    for source_row, row in enumerate(rows[1:], start=2):
        exercise = cell(row, 0)
        joined = " ".join(cell(row, i) for i in range(start, min(start + 5, len(row))))
        if "Начало новой схемы" in joined:
            notes.append({"source_row": source_row, "text": joined})
        entry = make_entry(row, source_row, exercise, start, "old")
        if entry:
            entries.append(entry)

    sessions.append({
        "session": session_number,
        "section": "old",
        "entries": entries,
        "notes": notes,
    })

# Current workouts: every repeated exercise header marks a new workout block.
current_starts = [
    i for i, value in enumerate(header[current_start:], start=current_start)
    if value.strip() == EXERCISE and i + 4 < len(header)
]

# Exercise names persist by source row. This is important because the Google
# Sheet intentionally leaves the name blank when the same exercise continues.
last_exercise_by_row = {}

for start in current_starts:
    session_number = len(sessions) + 1
    entries = []
    notes = []

    for source_row, row in enumerate(rows[1:], start=2):
        raw_exercise = cell(row, start)
        if raw_exercise:
            last_exercise_by_row[source_row] = raw_exercise
        exercise = last_exercise_by_row.get(source_row, "")

        values = [cell(row, start + j) for j in range(5)]
        joined = " ".join(v for v in values if v)
        if "Начало новой схемы" in joined:
            notes.append({"source_row": source_row, "text": joined})

        entry = make_entry(row, source_row, exercise, start, "current")
        if entry:
            entry["explicit_exercise"] = bool(raw_exercise)
            entries.append(entry)

    sessions.append({
        "session": session_number,
        "section": "current",
        "entries": entries,
        "notes": notes,
    })

result = {
    "source": "Google Sheets",
    "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    "old_session_count": len(old_starts),
    "current_session_count": len(current_starts),
    "session_count": len(sessions),
    "sessions": sessions,
}

with OUTPUT.open("w", encoding="utf-8", newline="\n") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
    f.write("\n")

print(
    f"Generated {OUTPUT}: {len(sessions)} sessions "
    f"({len(old_starts)} old + {len(current_starts)} current)"
)
