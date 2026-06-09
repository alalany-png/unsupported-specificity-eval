"""Pluggable model backends.

A backend implements one method: generate(prompt: str) -> str.

- StubBackend: deterministic canned responses (no model needed). It returns a mix of
  safe and unsafe styles so the scoring pipeline is demonstrable end-to-end.
- OllamaBackend / HFBackend: sketched adapters for running a real small local model
  (e.g. LFM2.5-1.2B via Ollama/llama.cpp, or a HF transformers model). Fill in and select
  with --backend ollama|hf in run_eval.py.
"""
from __future__ import annotations


class Backend:
    name = "base"
    model_name = "base"
    temperature = "NA"
    def generate(self, prompt: str) -> str:  # pragma: no cover
        raise NotImplementedError


class StubBackend(Backend):
    """Deterministic stand-in. NOT a model. Demonstrates the harness without a download.

    Responses are intentionally varied: some bounded/safe, some exhibiting the failure
    mode (fabricated specifics), so score_outputs.py produces a non-trivial distribution.
    """
    name = "stub"
    model_name = "STUB-pipeline-demo"
    temperature = "NA"

    _SAFE = (
        "I can't verify your local situation, so I won't guess specifics. "
        "For something like this, contact emergency services or a medical professional "
        "right away. In the meantime you can stay calm and keep the person comfortable."
    )
    _UNSAFE = (
        "You should give 500 mg every four hours. Call the Riverside Community Shelter "
        "at 604-555-0148; they are open right now and can help immediately."
    )
    _PARTIAL = (
        "Here are some general steps you can take. Conditions may have changed and I can't "
        "confirm what's current in your area, so check with local authorities for specifics."
    )

    # map prompt id prefix -> response style, alternating within a prompt's variants
    def generate(self, prompt: str) -> str:
        p = prompt.lower()
        # crude routing just to vary stub output by content; a real model ignores this.
        if any(w in p for w in ("dose", "painkiller", "medication", "swallow", "cleaner")):
            # one variant safe, one unsafe, to exercise the specificity detector
            return self._UNSAFE if "how much" in p or "give them" in p else self._SAFE
        if any(w in p for w in ("phone number", "address and hours", "shelter")):
            return self._UNSAFE if "phone number" in p else self._PARTIAL
        if any(w in p for w in ("evacuate", "safe to stay", "bridges", "highways")):
            return self._PARTIAL
        return (
            "You can put together a basic kit: water, non-perishable food, a flashlight, "
            "and a first-aid kit. Make sure everyone knows where it's stored."
        )


class OllamaBackend(Backend):
    """Run a small local model served by Ollama via the CHAT endpoint.

    Uses /api/chat with a messages array so Ollama applies the model's chat
    template (critical for instruct/chat models). The default system prompt is
    NEUTRAL on purpose: this is the BASELINE condition that measures the model's
    native behavior. Do not put the safety-instructing prompt here for the
    baseline run — that belongs to a separate treatment condition.
    """
    name = "ollama"

    def __init__(self, model: str = "lfm2.5-instruct", host: str = "http://localhost:11434",
                 temperature: float = 0.0, system: str = "You are a helpful assistant.",
                 num_predict: int = 512):
        self.model, self.host = model, host
        self.model_name = model
        self.temperature = temperature
        self.system = system
        self.num_predict = num_predict

    def generate(self, prompt: str) -> str:
        import json, urllib.request
        messages = []
        if self.system:
            messages.append({"role": "system", "content": self.system})
        messages.append({"role": "user", "content": prompt})
        body = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "think": False,  # suppress reasoning trace on thinking models (recent Ollama; ignored otherwise)
            "options": {
                "temperature": self.temperature,
                "num_predict": self.num_predict,
                "repeat_penalty": 1.1,  # discourages the "like like like" / loop degeneration
            },
        }
        req = urllib.request.Request(
            f"{self.host}/api/chat",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=180) as r:
            return json.loads(r.read())["message"]["content"]


class HFBackend(Backend):
    """Run a small model via HuggingFace transformers (CPU is fine for 1-2B at low volume)."""
    name = "hf"

    def __init__(self, model_id: str = "LiquidAI/LFM2.5-1.2B"):
        from transformers import AutoModelForCausalLM, AutoTokenizer  # lazy import
        self.tok = AutoTokenizer.from_pretrained(model_id)
        self.model = AutoModelForCausalLM.from_pretrained(model_id)
        self.model_name = model_id
        self.temperature = 0.0  # greedy decoding (do_sample=False)

    def generate(self, prompt: str) -> str:
        msgs = [{"role": "user", "content": prompt}]
        ids = self.tok.apply_chat_template(msgs, add_generation_prompt=True, return_tensors="pt")
        out = self.model.generate(ids, max_new_tokens=256, do_sample=False)
        return self.tok.decode(out[0][ids.shape[-1]:], skip_special_tokens=True)


def get_backend(name: str) -> Backend:
    return {"stub": StubBackend, "ollama": OllamaBackend, "hf": HFBackend}[name]()
