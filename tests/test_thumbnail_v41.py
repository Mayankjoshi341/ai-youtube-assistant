"""
Standalone thumbnail generation test — V4.1
Tests: 4 subjects + long topic + no-tutor + duration variations
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.thumbnail_template import generate_branded_thumbnail
from services.thumbnail import ThumbnailService

OUTPUT = Path(__file__).resolve().parent.parent / "data" / "outputs"
OUTPUT.mkdir(parents=True, exist_ok=True)

CASES = [
    # class_name, subject, topic, series_label, duration
    ("CLASS IX",  "MATHS",    "LINEAR POLYNOMIALS",                       "NCERT EXERCISE",   "52:49"),
    ("CLASS IX",  "BIOLOGY",  "CELL - PART III",                          "CHAPTER 5",        "38:21"),
    ("CLASS X",   "PHYSICS",  "ELECTRICITY",                              "NCERT EXERCISE 12","01:06:59"),
    ("CLASS XII", "CHEMISTRY","SOLUTIONS AND COLLIGATIVE PROPERTIES",     "PART 2",           "44:10"),
    ("CLASS XI",  "MATHS",    "APPLICATION OF DERIVATIVES AND CONTINUITY — DETAILED WALKTHROUGH", "EXERCISE 6.4", "01:22:33"),
    (None,        None,       "General Knowledge Quiz",                   None,               "15:00"),
    ("CLASS X",   "SCIENCE",  "LIFE PROCESSES",                           None,               ""),
]

print("Running thumbnail generation tests...\n")

for i, (cls, subj, topic, series, dur) in enumerate(CASES, 1):
    out_path = OUTPUT / f"test_thumb_{i:02d}_{(subj or 'GENERAL').lower()}.jpg"
    try:
        result = generate_branded_thumbnail(
            class_name=cls,
            subject=subj,
            topic=topic,
            series_label=series,
            duration=dur,
            tutor_image_path=None,   # no tutor for test
            output_path=out_path,
        )
        size_kb = result.stat().st_size // 1024
        print(f"  [{i}] PASS  {out_path.name}  ({size_kb} KB)")
        w_h = __import__("PIL").Image.open(result).size
        assert w_h == (1280, 720), f"Wrong size: {w_h}"
        print(f"       Dimensions: {w_h[0]}x{w_h[1]}  OK")
    except Exception as e:
        print(f"  [{i}] FAIL  {e}")

# duration formatting tests
print("\nDuration format tests:")
for secs, expected in [(0, ""), (65, "01:05"), (3599, "59:59"), (3600, "01:00:00"), (4019, "01:06:59")]:
    result = ThumbnailService.format_duration(secs)
    status = "PASS" if result == expected else "FAIL"
    print(f"  {status}  {secs}s -> '{result}'  (expected '{expected}')")

print("\nDone.")
