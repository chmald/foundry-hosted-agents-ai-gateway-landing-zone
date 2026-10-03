"""Render live-evidence charts from a JSON run summary.

Usage:
    python scripts/render_evidence.py
    python scripts/render_evidence.py --summary docs/assets/evidence/live-run-2026-10-02.json --out-dir docs/assets/evidence

The summary holds only sanitized results (no keys, tokens, tenant/subscription IDs or
unique resource names). Re-run after each live run to refresh the PNGs.
"""
from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

BLUE, GREEN, ORANGE, RED, GREY = "#0078D4", "#107C10", "#CA5010", "#A4262C", "#605E5C"
DPI = 200
STATE_STYLE = {
    "pass": (GREEN, "PASS"),
    "fail": (RED, "FAIL"),
    "blocked": (ORANGE, "BLOCKED"),
    "na": ("#8A8886", "n/a"),
}

plt.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Segoe UI", "Arial", "DejaVu Sans"],
        "axes.edgecolor": "#C8C6C4",
        "axes.labelcolor": GREY,
        "xtick.color": GREY,
        "ytick.color": GREY,
        "axes.spines.top": False,
        "axes.spines.right": False,
    }
)


def _caption(fig, label: str, extra: str = "") -> None:
    import textwrap

    text = textwrap.fill(f"Source: {label}" + (f" - {extra}" if extra else ""), 190)
    fig.text(0.01, 0.01, text, fontsize=8, color=GREY, ha="left", va="bottom")


def render_matrix(data: dict, out: Path) -> None:
    steps = data["matrix"]["steps"]
    cols = data["matrix"]["columns"]
    results = data["matrix"]["results"]
    fig, ax = plt.subplots(figsize=(9.5, 5.2))
    cw, ch = 1.0, 0.8
    for r, step in enumerate(steps):
        for c, state in enumerate(results[step["id"]]):
            color, label = STATE_STYLE[state]
            ax.add_patch(Rectangle((c * cw, -r * ch), cw - 0.04, ch - 0.06, color=color))
            ax.text(c * cw + cw / 2 - 0.02, -r * ch + ch / 2 - 0.03, label, color="white",
                    ha="center", va="center", fontsize=10, fontweight="bold")
        ax.text(-0.08, -r * ch + ch / 2 - 0.03, f"{step['id']}  {step['name']}", ha="right",
                va="center", fontsize=10, color="#201F1E")
    for c, col in enumerate(cols):
        host = data.get("agents", {}).get(col["agent"].lower(), {}).get("host", "")
        ax.text(c * cw + cw / 2 - 0.02, ch + 0.2, col["agent"], ha="center", va="bottom",
                fontsize=10, fontweight="bold", color="#201F1E")
        if host:
            ax.text(c * cw + cw / 2 - 0.02, ch + 0.04, host, ha="center", va="bottom",
                    fontsize=7.5, color=GREY)
    gateways: dict[str, list[int]] = {}
    for c, col in enumerate(cols):
        gateways.setdefault(col["gateway"], []).append(c)
    for name, idx in gateways.items():
        x0, x1 = min(idx) * cw, (max(idx) + 1) * cw - 0.04
        ax.plot([x0, x1], [ch + 0.62, ch + 0.62], color=BLUE, lw=2)
        ax.text((x0 + x1) / 2, ch + 0.7, name, ha="center", va="bottom", fontsize=11, color=BLUE,
                fontweight="bold")
    ax.set_xlim(-2.2, len(cols) * cw)
    ax.set_ylim(-(len(steps) - 1) * ch - 0.2, ch + 1.2)
    ax.axis("off")
    fig.suptitle("Walkthrough pass/fail matrix: agent x gateway x step", fontsize=14,
                 fontweight="bold", x=0.02, ha="left", color="#201F1E")
    _caption(fig, data["run"]["label"], data["matrix"].get("caption", ""))
    fig.tight_layout(rect=(0, 0.04, 1, 0.95))
    fig.savefig(out, dpi=DPI)
    plt.close(fig)


def _fmt_seconds(value: float) -> str:
    if value >= 100:
        return f"{int(value // 60)}m {int(round(value % 60))}s"
    return f"{value:.1f}s"


def render_durations(data: dict, out: Path) -> None:
    prov = data["provisioning"]
    items = sorted(prov["resources"].items(), key=lambda kv: statistics.mean(kv[1]))
    names = [k for k, _ in items]
    means = [statistics.mean(v) for _, v in items]
    lows = [statistics.mean(v) - min(v) for _, v in items]
    highs = [max(v) - statistics.mean(v) for _, v in items]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.8), gridspec_kw={"width_ratios": [1.5, 1]})
    ax1.barh(names, means, xerr=[lows, highs], color=BLUE, ecolor=GREY, capsize=3, height=0.62)
    for y, (m, hi) in enumerate(zip(means, highs)):
        ax1.text(m + hi + 0.5, y, f"{m:.1f}s", va="center", fontsize=9, color="#201F1E")
    ax1.set_xlim(0, max(m + hi for m, hi in zip(means, highs)) * 1.15)
    ax1.set_xlabel("seconds (bar = mean, whisker = min to max)")
    ax1.set_title(f"Per-resource provisioning (azd, {prov['runs']} successful runs)", fontsize=11,
                  loc="left", fontweight="bold")
    phases = list(prov["phases_seconds"].items())
    p_names = [k for k, _ in phases]
    p_vals = [statistics.mean(v) for _, v in phases]
    colors = [RED if "down" in k else BLUE for k in p_names]
    ax2.barh(p_names[::-1], p_vals[::-1], color=colors[::-1], height=0.55)
    for y, v in enumerate(p_vals[::-1]):
        ax2.text(v + 25, y, _fmt_seconds(v), va="center", fontsize=9, color="#201F1E")
    ax2.set_xlim(0, max(p_vals) * 1.2)
    ax2.set_xlabel("seconds (mean per phase)")
    ax2.set_title("End-to-end phases", fontsize=11, loc="left", fontweight="bold")
    fig.suptitle("Provisioning and deployment durations", fontsize=14, fontweight="bold", x=0.02,
                 ha="left", color="#201F1E")
    _caption(fig, data["run"]["label"], prov["note"])
    fig.tight_layout(rect=(0, 0.08, 1, 0.94))
    fig.savefig(out, dpi=DPI)
    plt.close(fig)


def render_audit(data: dict, out: Path) -> None:
    queries = data["audit_queries"]
    color_for = {"ok": GREEN, "fixed": BLUE, "empty": GREY, "unverified": ORANGE}
    legend = {"ok": "Rows returned", "fixed": "Rows returned after live schema fix",
              "empty": "Empty in this run", "unverified": "Rows returned, labels unverified"}
    labels = [f"{q['id']}  {q['name']}" for q in queries][::-1]
    rows = [q["rows"] for q in queries][::-1]
    colors = [color_for[q["status"]] for q in queries][::-1]
    fig, ax = plt.subplots(figsize=(10.5, 6))
    plotted = [max(r, 0.6) for r in rows]
    ax.barh(labels, plotted, color=colors, height=0.62)
    ax.set_xscale("log")
    ax.set_xlim(0.5, max(rows) * 6)
    for y, r in enumerate(rows):
        ax.text(max(r, 0.6) * 1.15, y, f"{r:,}", va="center", fontsize=9, color="#201F1E")
    ax.set_xlabel("rows returned (log scale; zero shown as a stub)")
    seen = []
    handles = []
    for q in queries:
        if q["status"] not in seen:
            seen.append(q["status"])
            handles.append(Rectangle((0, 0), 1, 1, color=color_for[q["status"]]))
    ax.legend(handles, [legend[s] for s in seen], loc="upper right", frameon=False, fontsize=9)
    fig.suptitle("Saved audit queries 01-11: rows returned from the live workspace", fontsize=14,
                 fontweight="bold", x=0.02, ha="left", color="#201F1E")
    _caption(fig, data["run"]["label"], data.get("audit_caption", "query 04 is dominated by application trace noise"))
    fig.tight_layout(rect=(0, 0.04, 1, 0.95))
    fig.savefig(out, dpi=DPI)
    plt.close(fig)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    default_dir = root / "docs" / "assets" / "evidence"
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--summary", type=Path, default=default_dir / "live-run-2026-10-02.json")
    parser.add_argument("--out-dir", type=Path, default=default_dir)
    args = parser.parse_args()

    data = json.loads(args.summary.read_text(encoding="utf-8"))
    args.out_dir.mkdir(parents=True, exist_ok=True)
    render_matrix(data, args.out_dir / "pass-fail-matrix.png")
    render_durations(data, args.out_dir / "provisioning-durations.png")
    render_audit(data, args.out_dir / "audit-query-results.png")
    print(f"Rendered 3 charts to {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
