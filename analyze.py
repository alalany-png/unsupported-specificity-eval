"""Aggregate scored results into a summary table and a plot."""
import csv, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = pathlib.Path(__file__).parent
RESULTS = HERE / "results"
PLOTS = RESULTS / "plots"


def main():
    with open(RESULTS / "scored.csv") as f:
        rows = list(csv.DictReader(f))

    n = len(rows)
    backend = rows[0].get("backend", "?")
    model = rows[0].get("model_name", "?")
    run_id = rows[0].get("run_id", "?")
    is_stub = (backend == "stub")

    metrics = {
        "unsupported specificity rate": sum(int(r["flag_specificity"]) for r in rows) / n,
        "uncertainty flagging rate": sum(int(r["uncertainty_flagging"]) for r in rows) / n,
        "escalation rate": sum(int(r["escalation"]) for r in rows) / n,
        "actionability rate": sum(int(r["actionability"]) for r in rows) / n,
    }

    # paraphrase consistency and pressure shift are per-prompt; average over prompts
    def per_prompt(col, cast):
        vals = {}
        for r in rows:
            v = r.get(col, "")
            if v != "":
                vals[r["prompt_id"]] = cast(v)
        return (sum(vals.values()) / len(vals)) if vals else None

    mean_para = per_prompt("paraphrase_consistency", float)
    mean_shift = per_prompt("pressure_shift", float)

    with open(RESULTS / "summary_metrics.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["run_id", run_id])
        w.writerow(["backend", backend])
        w.writerow(["model_name", model])
        w.writerow(["data_kind", "PIPELINE DEMO (not model behavior)" if is_stub else "model run"])
        w.writerow([])
        w.writerow(["metric", "value"])
        for k, v in metrics.items():
            w.writerow([k, round(v, 3)])
        w.writerow(["mean paraphrase_consistency (neutral vs reworded)", round(mean_para, 3) if mean_para is not None else "NA"])
        w.writerow(["mean pressure_shift (leading vs neutral, # flags changed)", round(mean_shift, 3) if mean_shift is not None else "NA"])

    print(f"=== summary  [backend={backend} model={model} run={run_id}] ===")
    if is_stub:
        print("  *** STUB PIPELINE DEMO — these are NOT model findings ***")
    for k, v in metrics.items():
        print(f"  {k:34s} {v:.3f}")
    if mean_para is not None:
        print(f"  {'mean paraphrase_consistency':34s} {mean_para:.3f}")
    if mean_shift is not None:
        print(f"  {'mean pressure_shift (flags changed)':34s} {mean_shift:.3f}")

    PLOTS.mkdir(parents=True, exist_ok=True)
    labels = ["specificity\n(failure)", "uncertainty", "escalation", "actionability"]
    vals = [metrics["unsupported specificity rate"], metrics["uncertainty flagging rate"],
            metrics["escalation rate"], metrics["actionability rate"]]
    colors = ["#c0392b", "#2e5a88", "#2e5a88", "#2e5a88"]
    fig, ax = plt.subplots(figsize=(6.2, 3.8))
    ax.bar(labels, vals, color=colors)
    ax.set_ylim(0, 1)
    ax.set_ylabel("rate across probes")
    if is_stub:
        ax.set_title("STUB PIPELINE DEMO — not model behavior", color="#c0392b")
    else:
        ax.set_title(f"Behavior on unanswerable safety prompts ({model})")
    for i, v in enumerate(vals):
        ax.text(i, v + 0.02, f"{v:.2f}", ha="center", fontsize=9)
    fig.tight_layout()
    out = PLOTS / ("stub_demo.png" if is_stub else "summary.png")
    fig.savefig(out, dpi=130)
    print(f"  plot -> {out}")


if __name__ == "__main__":
    main()
