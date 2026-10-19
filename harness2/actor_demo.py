"""CPU-only actor proposals through Harness2's real recursion loop.

The proposer and solver are scripted. Scene facts and the oracle stay on the host;
the editable harness supplies only declarative policy values.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from .core import tree
from .core.proposer import Proposer, Reply
from .core.schedule import run_domain
from .core.spec import BenchPrompts, BenchSpec, ChannelSpec
from .substrate.opencode import OpencodeSubstrate

BASE_GUIDANCE = """Plan a target-relative actor approach from the scene snapshot.
coordinate_policy: round_to_tenth
clearance_policy: default_gap
Return a JSON proposal; the host computes geometry and validates it.
"""
FIXED_GUIDANCE = """Plan a target-relative actor approach from the scene snapshot.
coordinate_policy: preserve_snapshot
clearance_policy: preserve_requested_gap
Return a JSON proposal; the host computes geometry and validates it.
"""

# Frozen fixture data is copied only to source/, never to an editable harness tree.
FIXTURES = {
    "left-mirror": {
        "actor": {"id": "aya", "x": 0.8, "y": 0.5, "radius": 0.05},
        "target": {"id": "ren", "x": 0.2, "y": 0.5, "radius": 0.05},
        "context": "guide", "intensity": "subtle", "facing": "toward_camera", "stop_gap": 0.12,
    },
    "right-mirror": {
        "actor": {"id": "ren", "x": 0.2, "y": 0.5, "radius": 0.05},
        "target": {"id": "aya", "x": 0.8, "y": 0.5, "radius": 0.05},
        "context": "guide", "intensity": "subtle", "facing": "away_from_camera", "stop_gap": 0.12,
    },
    "heldout-diagonal": {
        "actor": {"id": "mira", "x": 0.82, "y": 0.28, "radius": 0.04},
        "target": {"id": "sora", "x": 0.23, "y": 0.67, "radius": 0.06},
        "context": "greeting", "intensity": "normal", "facing": "toward_camera", "stop_gap": 0.14,
    },
}


def _unique_pairs(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def _bad_constant(value):
    raise ValueError(f"nonfinite JSON number: {value}")


def _number(value, lo, hi, name, *, open_lo=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name}: expected finite number")
    try:
        finite = math.isfinite(value)
    except OverflowError:
        finite = False
    if not finite:
        raise ValueError(f"{name}: expected finite number")
    if (value <= lo if open_lo else value < lo) or value > hi:
        raise ValueError(f"{name}: out of range")


def check_proposal(raw: str, fixture: dict) -> dict:
    """Independent host oracle: strict shape, scene fidelity, and planner geometry."""
    if len(raw) > 8192:
        raise ValueError("proposal too large")
    try:
        p = json.loads(raw, object_pairs_hook=_unique_pairs, parse_constant=_bad_constant)
    except RecursionError as exc:
        raise ValueError("proposal nesting too deep") from exc
    if not isinstance(p, dict) or set(p) != set(fixture):
        raise ValueError("proposal fields differ from task contract")
    for role in ("actor", "target"):
        actor = p[role]
        if not isinstance(actor, dict) or set(actor) != {"id", "x", "y", "radius"}:
            raise ValueError(f"{role}: wrong fields")
        if not isinstance(actor["id"], str) or not actor["id"]:
            raise ValueError(f"{role}.id: invalid")
        for name in ("x", "y"):
            _number(actor[name], 0, 1, f"{role}.{name}")
        _number(actor["radius"], 0, 0.5, f"{role}.radius", open_lo=True)
        if any((actor[c] - actor["radius"] < 0 or actor[c] + actor["radius"] > 1)
               for c in ("x", "y")):
            raise ValueError(f"{role}: footprint outside frame")
    _number(p["stop_gap"], 0, 1, "stop_gap")
    if p["actor"]["id"] == p["target"]["id"]:
        raise ValueError("actor and target IDs must differ")
    if not isinstance(p["context"], str) or p["context"] not in {"guide", "greeting", "dramatic"}:
        raise ValueError("unsupported context")
    if not isinstance(p["intensity"], str) or p["intensity"] not in {"subtle", "normal", "strong"}:
        raise ValueError("unsupported intensity")
    if not isinstance(p["facing"], str) or p["facing"] not in {"toward_camera", "away_from_camera"}:
        raise ValueError("unsupported facing")
    for name, expected in fixture.items():
        if p[name] != expected:
            raise ValueError(f"{name}: scene or requested action changed")
    a, t = p["actor"], p["target"]
    dx, dy = t["x"] - a["x"], t["y"] - a["y"]
    distance = math.hypot(dx, dy)
    required = a["radius"] + t["radius"] + p["stop_gap"]
    if distance < required - 1e-12:
        raise ValueError("actor already inside requested stop gap")
    travel = max(0.0, distance - required)
    final_x, final_y = a["x"] + dx * travel / distance, a["y"] + dy * travel / distance
    edge_gap = math.hypot(t["x"] - final_x, t["y"] - final_y) - a["radius"] - t["radius"]
    if edge_gap < p["stop_gap"] - 1e-9:
        raise ValueError("clearance violated")
    gaze = "screen_left" if dx < -1e-12 else "screen_right" if dx > 1e-12 else "center"
    # Mirrors Hermes's flat-adapter limitation: screen-left gaze has no supported control.
    control = "look_right" if gaze == "screen_right" and abs(dy) <= 1e-12 else (
        "neutral" if gaze == "center" and abs(dy) <= 1e-12 else None
    )
    return {"valid": True, "edge_gap_final": edge_gap, "travel_distance": travel,
            "gaze": gaze, "adapter_control": control, "final_position": {"x": final_x, "y": final_y}}


class ActorAdapter:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.substrate = OpencodeSubstrate()
        channel = ChannelSpec("opencode", "local/scripted")
        self.spec = BenchSpec(
            name="actor_demo", runs_root=self.root / "runs", install_mode="workspace_config",
            prompts=BenchPrompts(work="plan a target-relative actor approach using exact scene facts",
                                 domain_word="actor planning"),
            channels={"proposer": channel, "selector": channel},
            leak_globs=("oracle.json", "heldout.json"),
        )
        self.execution_count = 0
        base = {name: "" for name in self.substrate.surface().always_on}
        base["systemprompt.md"] = BASE_GUIDANCE
        tree.write_tree(self.substrate.surface(), base, self.base_harness(), stubs=False)
        for task_id in self.tasks("all"):
            source = self.task_files(task_id)
            source.mkdir(parents=True, exist_ok=True)
            (source / "scene.json").write_text(json.dumps(FIXTURES[task_id], indent=2) + "\n")

    def tasks(self, split="train"):
        if split == "train":
            return ["left-mirror", "right-mirror"]
        if split == "heldout":
            return ["heldout-diagonal"]
        if split == "all":
            return ["left-mirror", "right-mirror", "heldout-diagonal"]
        raise ValueError(f"unknown split: {split}")

    def domain_of(self, task_id):
        return "actor-planning"

    def task_prompt(self, task_id):
        return "Propose exact actor/target scene fields and requested stop_gap from scene.json."

    def task_files(self, task_id):
        return self.root / "sources" / task_id

    def base_harness(self):
        return self.root / "base"

    def validate_tree(self, harness):
        guidance = harness.get("systemprompt.md", "")
        if guidance.count("coordinate_policy:") != 1 or guidance.count("clearance_policy:") != 1:
            raise ValueError("one declarative coordinate and clearance policy required")
        if not any(f"coordinate_policy: {v}" in guidance for v in ("round_to_tenth", "preserve_snapshot")):
            raise ValueError("unknown coordinate policy")
        if not any(f"clearance_policy: {v}" in guidance for v in ("default_gap", "preserve_requested_gap")):
            raise ValueError("unknown clearance policy")

    def execute(self, task_id, harness_dir, run_id, *, timeout=None):
        del timeout
        if task_id not in FIXTURES:
            raise ValueError("unknown task")
        self.execution_count += 1
        guidance = ((harness_dir or self.base_harness()) / "systemprompt.md").read_text()
        fixture = FIXTURES[task_id]
        proposal = json.loads(json.dumps(fixture))
        if "coordinate_policy: round_to_tenth" in guidance:
            for role in ("actor", "target"):
                for axis in ("x", "y"):
                    proposal[role][axis] = round(proposal[role][axis], 1)
        if "clearance_policy: default_gap" in guidance:
            proposal["stop_gap"] = 0.08
        raw = json.dumps(proposal, sort_keys=True)
        try:
            verdict = check_proposal(raw, fixture)
        except ValueError as exc:
            verdict = {"valid": False, "reason": str(exc)}
        run_dir = self.root / "executions" / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "proposal.json").write_text(raw + "\n")
        (run_dir / "verdict.json").write_text(json.dumps(verdict, indent=2) + "\n")
        (run_dir / "trajectory.md").write_text(
            "[ACTION] Scripted policy proposed actor move\n[OBSERVATION] " + raw + "\n"
            + ("[HOST] valid\n" if verdict["valid"] else "[HOST] rejected: " + verdict["reason"] + "\n")
        )
        return run_dir

    def delivered(self, run_dir):
        return (run_dir / "proposal.json").is_file()

    def trajectory(self, run_dir, *, obs_trunc):
        return (run_dir / "trajectory.md").read_text()[:obs_trunc]

    def deliverable_text(self, run_dir):
        return (run_dir / "proposal.json").read_text()

    def deliverable_files(self, run_dir):
        return {"proposal.json": self.deliverable_text(run_dir)}


class ActorProposer(Proposer):
    """Deterministic harness editor; no model API or untrusted code execution."""

    def call(self, mission, context_dir, label, **kwargs):
        del mission, kwargs
        context = Path(context_dir)
        workspace = None
        if label.startswith("experience."):
            text = "NO_ENTRY"
        elif label.startswith("select."):
            candidates = sorted((context / "candidates").glob("*.md"))
            chosen = candidates[0].stem
            text = f"<why>Scripted selection of final deliverable.</why>\n```choice\n{chosen}\n```"
        else:
            workspace = context / "harness"
            prompt = workspace / "systemprompt.md"
            prompt.write_text(FIXED_GUIDANCE)
            text = "<notes>Preserve scene coordinates and requested clearance.</notes>"
        reply = Reply(label=label, text=text, ok=True, attempts=1, workspace=workspace)
        self._calls.append(reply)
        return reply


def run_actor_demo(root: Path) -> dict:
    adapter = ActorAdapter(root)
    proposer = ActorProposer(adapter.spec.channels["proposer"])
    result = run_domain("actor-planning", adapter.tasks("train"), 1, adapter=adapter,
                        prop=proposer, runs_root=adapter.spec.runs_root,
                        library_root=root / "library", modes=("seq",))
    rows = []
    for task_id in adapter.tasks("train"):
        summary = json.loads((adapter.spec.runs_root / "actor_demo-oc-agg1" / task_id / "summary.json").read_text())
        base = Path(summary["base"][0]["run_dir"])
        chosen = Path(summary["selections"]["seq"]["chosen_run_dir"])
        rows.append({"task": task_id,
                     "base": {"proposal": json.loads((base / "proposal.json").read_text()),
                              "host_verdict": json.loads((base / "verdict.json").read_text())},
                     "adapted": {"proposal": json.loads((chosen / "proposal.json").read_text()),
                                 "host_verdict": json.loads((chosen / "verdict.json").read_text())},
                     "recursion": {"stages": summary["modes"]["seq"]["stages"],
                                   "ledger": summary["modes"]["seq"]["ledger"],
                                   "selection": {"chosen_label": summary["selections"]["seq"]["chosen_label"],
                                                 "ok": summary["selections"]["seq"]["ok"]}}})
    final_harness = adapter.spec.runs_root / "actor_demo-oc-seq1" / adapter.tasks("train")[-1] / "harnesses" / "c1"
    heldout_base = adapter.execute("heldout-diagonal", None, "heldout-base")
    heldout_adapted = adapter.execute("heldout-diagonal", final_harness, "heldout-adapted")
    evidence = {"scope": "CPU-only scripted policy and deterministic editor; no model learning or renderer",
                "harness2_run_domain": result, "train": rows,
                "heldout": {"task": "heldout-diagonal", "adaptation_used_this_task": False,
                            "base": {"proposal": json.loads((heldout_base / "proposal.json").read_text()),
                                     "host_verdict": json.loads((heldout_base / "verdict.json").read_text())},
                            "adapted": {"proposal": json.loads((heldout_adapted / "proposal.json").read_text()),
                                        "host_verdict": json.loads((heldout_adapted / "verdict.json").read_text())}},
                "execution_count": adapter.execution_count, "editor_calls": len(proposer._calls)}
    (root / "actor-demo.json").write_text(json.dumps(evidence, indent=2) + "\n")
    return evidence


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    evidence = run_actor_demo(args.output.expanduser().resolve())
    print(json.dumps({"done": evidence["harness2_run_domain"]["done"],
                      "failed": evidence["harness2_run_domain"]["failed"],
                      "report": str(args.output / "actor-demo.json")}))
    return int(evidence["harness2_run_domain"]["failed"] > 0)


if __name__ == "__main__":
    raise SystemExit(main())
