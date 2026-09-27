#!/usr/bin/env python3
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

INPUT = Path("workouts_raw.csv")
OUTPUT = Path("workouts.json")

with INPUT.open("r", encoding="utf-8-sig", newline="") as f:
    rows = list(csv.reader(f))

if not rows:
    raise SystemExit("Google Sheet export is empty")

header = rows[0]

# Detect workout blocks in the wide Google Sheet export. Older blocks are
# separated by an empty column; newer blocks are adjacent and repeat the
# "Тренажер/упражнение" header.
starts = [0]
for i, value in enumerate(header[1:], start=1):
    if value == "":
        if i + 1 < len(header) and header[i + 1] != "":
            starts.append(i + 1)
    elif value == "Тренажер/упражнение":
        starts.append(i)

starts = sorted(set(starts))
blocks = []
for n, start in enumerate(starts):
    end = starts[n + 1] if n + 1 < len(starts) else len(header)
    while start < end and header[start] == "":
        start += 1
    while end > start and header[end - 1] == "":
        end -= 1
    if start < end:
        blocks.append((start, end))

sessions = []
for session_index, (start, end) in enumerate(blocks, start=1):
    fields = header[start:end]
    entries = []
    notes = []

    for source_row, row in enumerate(rows[1:], start=2):
        values = row[start:end]
        values += [""] * max(0, end - start - len(values))
        data = dict(zip(fields, values))

        exercise = data.get("Тренажер/упражнение", "").strip()
        reps = data.get("Повторения", "").strip()
        weight = data.get("Вес", "").strip()
        feeling = data.get("Ощущение целевой мышцы (0–5)", "").strip()
        felt = data.get("Что чувствовал", "").strip()

        # In the oldest blocks the exercise name exists only in column 0.
        if not exercise and start != 0 and row:
            exercise = row[0].strip()

        joined = " ".join(v.strip() for v in values if v.strip())
        if "Начало новой схемы" in joined:
            notes.append({"source_row": source_row, "text": joined})

        if not any((exercise, reps, weight, feeling, felt)):
            continue

        # Keep pure scheme markers as notes, not as exercises.
        if exercise and "Начало новой схемы" in exercise and not any((reps, weight, feeling, felt)):
            continue

        entries.append({
            "source_row": source_row,
            "exercise": exercise,
            "reps": reps,
            "weight": weight,
            "target_feel": feeling,
            "felt": felt,
        })

    sessions.append({
        "session": session_index,
        "entries": entries,
        "notes": notes,
    })

result = {
    "source": "Google Sheets",
    "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    "session_count": len(sessions),
    "sessions": sessions,
}

with OUTPUT.open("w", encoding="utf-8", newline="\n") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
    f.write("\n")

print(f"Generated {OUTPUT} with {len(sessions)} workout blocks")
