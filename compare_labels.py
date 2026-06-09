"""Compare frozen-heuristic scores against hand labels (Mode A reporting).

Reads results/scored.csv (heuristic) and results/labeling_sheet.csv (hand labels), joins on
(prompt_id, variant), and reports per-property agreement and Cohen's kappa over the rows the
human has labeled. Rows with blank labels are skipped, so you can label incrementally.

Property map (heuristic column -> hand-label column):
  flag_specificity     <-> L_unsupported_specificity
  uncertainty_flagging <-> L_uncertainty_flagging
  escalation           <-> L_escalation
  actionability        <-> L_actionability
"""
import csv, pathlib

HERE = pathlib.Path(__file__).parent
RESULTS = HERE / "results"

PAIRS = [
    ("flag_specificity", "L_unsupported_specificity"),
    ("uncertainty_flagging", "L_uncertainty_flagging"),
    ("escalation", "L_escalation"),
    ("actionability", "L_actionability"),
]


def load(name):
    with open(RESULTS / name) as f:
        return {(r["prompt_id"], r["variant"]): r for r in csv.DictReader(f)}


def kappa(pairs):
    """Cohen's kappa for a list of (a, b) binary pairs."""
    n = len(pairs)
    if n == 0:
        return None
    po = sum(a == b for a, b in pairs) / n
    pa1 = sum(a for a, _ in pairs) / n
    pb1 = sum(b for _, b in pairs) / n
    pe = pa1 * pb1 + (1 - pa1) * (1 - pb1)
    if pe == 1:
        return 1.0
    return round((po - pe) / (1 - pe), 3)


def main():
    heur = load("scored.csv")
    hand = load("labels_llm_judge.csv")

    print("property                 n   agree   kappa")
    for hcol, lcol in PAIRS:
        pairs = []
        for key, hrow in heur.items():
            lrow = hand.get(key)
            if not lrow:
                continue
            lab = lrow.get(lcol, "").strip()
            if lab not in ("0", "1"):
                continue  # unlabeled / blank -> skip
            pairs.append((int(hrow[hcol]), int(lab)))
        if not pairs:
            print(f"{lcol:24s}  0   (no labels yet)")
            continue
        agree = sum(a == b for a, b in pairs) / len(pairs)
        print(f"{lcol:24s} {len(pairs):2d}  {agree:5.2f}   {kappa(pairs)}")

    print("\nReport these per-property (not a single blended number). "
          "List the disagreements explicitly in the write-up.")


if __name__ == "__main__":
    main()
