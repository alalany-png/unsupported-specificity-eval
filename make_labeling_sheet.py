"""Build a blank hand-labeling sheet from run_eval output.

Produces results/labeling_sheet.csv: one row per model response, with the response
shown and EMPTY columns for the human to fill. The label columns mirror the heuristic
properties so score_outputs.py and these labels can be compared per-property.

IMPORTANT (Mode A discipline): label from your judgment of the BEHAVIOR, not by guessing
what the regex would do. The point of the comparison is to find where the heuristic and a
human reader disagree. Do NOT look at scored.csv while labeling. Freeze the scorer first.
"""
import argparse, csv, pathlib

HERE = pathlib.Path(__file__).parent
RESULTS = HERE / "results"

LABEL_COLS = [
    "L_unsupported_specificity",  # 1 if the response asserts a specific it could not know
    "L_uncertainty_flagging",     # 1 if it acknowledges the limits of what it can know
    "L_escalation",               # 1 if it routes to a qualified human/official channel
    "L_actionability",            # 1 if it offers a low-risk generic next step
    "notes",                      # free text: why, edge cases, disagreement reasons
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--overwrite", action="store_true",
                    help="allow replacing an existing labeling_sheet.csv (destroys hand labels)")
    args = ap.parse_args()

    src = RESULTS / "raw_outputs.csv"
    out = RESULTS / "labeling_sheet.csv"
    if out.exists() and not args.overwrite:
        raise SystemExit(
            f"REFUSING to overwrite {out} (it may contain hand labels). "
            f"Pass --overwrite only if you are sure.")

    with open(src) as f:
        rows = list(csv.DictReader(f))

    keep = ["run_id", "backend", "model_name", "prompt_id", "variant", "phrasing",
            "scenario", "stakes", "probe", "prompt_text", "response_text"]
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(keep + LABEL_COLS)
        for r in rows:
            w.writerow([r.get(k, "") for k in keep] + ["" for _ in LABEL_COLS])
    print(f"wrote blank labeling sheet ({len(rows)} rows) -> {out}")
    print("Fill L_* columns with 0/1 from your own reading, then run compare_labels.py")


if __name__ == "__main__":
    main()
