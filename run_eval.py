"""Run the probe set through a backend and record raw outputs."""
import argparse, csv, json, pathlib, datetime, uuid
from backends import get_backend

HERE = pathlib.Path(__file__).parent
RESULTS = HERE / "results"


def load_prompts():
    rows = []
    with open(HERE / "prompts.jsonl") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", default="stub", choices=["stub", "ollama", "hf"])
    args = ap.parse_args()

    backend = get_backend(args.backend)
    RESULTS.mkdir(exist_ok=True)
    out_path = RESULTS / "raw_outputs.csv"

    run_id = datetime.datetime.now().strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:6]
    timestamp = datetime.datetime.now().isoformat(timespec="seconds")
    meta = [run_id, backend.name, getattr(backend, "model_name", backend.name),
            str(getattr(backend, "temperature", "NA")), timestamp]
    meta_cols = ["run_id", "backend", "model_name", "temperature", "timestamp"]

    if backend.name == "stub":
        print("  NOTE: stub backend — these outputs are a PIPELINE DEMO, not model behavior.")

    n = 0
    with open(out_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(meta_cols + ["prompt_id", "variant", "phrasing", "scenario", "stakes", "probe", "prompt_text", "response_text"])
        for p in load_prompts():
            for i, v in enumerate(p["variants"]):
                # variants may be plain strings (legacy) or {"text","phrasing"} objects
                text = v["text"] if isinstance(v, dict) else v
                phrasing = v.get("phrasing", "") if isinstance(v, dict) else ""
                resp = backend.generate(text)
                w.writerow(meta + [p["id"], i, phrasing, p["scenario"], p["stakes"], p["probe"], text, resp])
                n += 1
    print(f"[{backend.name}] wrote {n} responses (run_id={run_id}) -> {out_path}")


if __name__ == "__main__":
    main()
