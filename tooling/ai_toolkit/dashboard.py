"""Render a scan result card as a self-contained HTML dashboard.

The page is a single file with inline CSS and a few lines of inline JavaScript
(filtering and search). It loads nothing from the network, so it can be opened
from disk, attached to a CI run, or published as a Pages artifact. Every value
from the card is HTML-escaped; the dashboard only displays statuses, it never
recomputes them.
"""

from __future__ import annotations

import html
from typing import Any, Callable

from . import VERSION
from .report import group_controls, next_action

READINESS_ORDER = ("RED", "ORANGE", "GREEN", "GRAY")
READINESS_LABEL = {"GREEN": "Passed", "ORANGE": "Advisory gap", "RED": "Blocked", "GRAY": "Inactive"}
GROUP_LABEL = {"failed": "Failed", "unverified": "Unverified", "passed": "Passed", "not_activated": "Not activated"}


def _e(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def _percent(block: Any) -> str:
    if not isinstance(block, dict) or block.get("percent") is None:
        return "—"
    return f"{block['percent']:g}%"


def _meter(block: Any) -> str:
    if not isinstance(block, dict) or not block.get("total"):
        return '<div class="meter"><span style="width:0%"></span></div>'
    width = max(0.0, min(100.0, 100.0 * float(block.get("passed", 0)) / float(block["total"])))
    return f'<div class="meter" role="img" aria-label="{width:.0f}% passed"><span style="width:{width:.1f}%"></span></div>'


def _group_of(row: dict[str, Any], groups: dict[str, list[dict[str, Any]]]) -> str:
    for name, rows in groups.items():
        if any(item is row for item in rows):
            return name
    return "unverified"


def render_html(card: dict[str, Any], *, generated_at: str = "", action: Callable[[dict[str, Any]], str] = next_action) -> str:
    groups = group_controls(card)
    status = str(card.get("status", "UNKNOWN")).upper()
    subject = card.get("subject") if isinstance(card.get("subject"), dict) else {}
    readiness = card.get("readiness") if isinstance(card.get("readiness"), dict) else {}
    controls = [row for row in card.get("controls", []) if isinstance(row, dict)]
    rank = {name: index for index, name in enumerate(("failed", "unverified", "passed", "not_activated"))}
    controls.sort(key=lambda row: (rank.get(_group_of(row, groups), 9), str(row.get("id", ""))))

    total = sum(int(readiness.get(key, 0) or 0) for key in READINESS_ORDER)
    segments = "".join(
        f'<span class="seg r-{key.lower()}" style="flex:{int(readiness.get(key, 0) or 0)}" title="{_e(READINESS_LABEL[key])}: {int(readiness.get(key, 0) or 0)}"></span>'
        for key in READINESS_ORDER if int(readiness.get(key, 0) or 0) > 0
    ) if total else '<span class="seg r-gray" style="flex:1"></span>'
    legend = "".join(
        f'<li><span class="dot r-{key.lower()}"></span>{_e(READINESS_LABEL[key])} <b>{int(readiness.get(key, 0) or 0)}</b></li>'
        for key in READINESS_ORDER
    )
    chips = [f'<button class="chip on" data-filter="all">All <b>{len(controls)}</b></button>']
    chips += [f'<button class="chip" data-filter="{name}">{_e(label)} <b>{len(groups[name])}</b></button>'
              for name, label in GROUP_LABEL.items() if groups[name]]

    cards = []
    for row in controls:
        group = _group_of(row, groups)
        result = row.get("authoritative_result") if isinstance(row.get("authoritative_result"), dict) else {}
        provider = (row.get("authoritative_provider") or {}).get("display_name", "—") if isinstance(row.get("authoritative_provider"), dict) else "—"
        evidence_status = str(row.get("authoritative_evidence_status", "missing"))
        row_readiness = str(row.get("readiness", "GRAY")).upper()
        reason = result.get("reason") or ""
        step = "" if group in {"passed", "not_activated"} else action(row)
        cards.append(
            f'<article class="control g-{group}" data-group="{group}" data-text="{_e((str(row.get("id", "")) + " " + str(row.get("name", "")) + " " + provider).lower())}">'
            f'<header><span class="pill r-{_e(row_readiness.lower())}">{_e(READINESS_LABEL.get(row_readiness, row_readiness))}</span>'
            f'<h3>{_e(row.get("name") or row.get("id"))}</h3><code>{_e(row.get("id"))}</code></header>'
            f'<dl><dt>Provider</dt><dd>{_e(provider)}</dd><dt>Mode</dt><dd>{_e(row.get("effective_mode", "—"))}</dd>'
            f'<dt>Evidence</dt><dd>{_e(evidence_status)}</dd></dl>'
            + (f'<p class="reason">{_e(reason)}</p>' if reason and reason not in step else "")
            + (f'<p class="next"><b>Next:</b> {_e(step)}</p>' if step else "")
            + "</article>"
        )
    findings = [finding for finding in card.get("findings", []) if isinstance(finding, dict) and finding.get("kind") == "subject_mismatch"]
    mismatch = "".join(f'<div class="alert">Subject mismatch: {_e(finding.get("message"))}</div>' for finding in findings)
    artifacts = card.get("artifacts") if isinstance(card.get("artifacts"), dict) else {}
    artifact_rows = "".join(f"<li><span>{_e(name.title())}</span><code>{_e(path)}</code></li>" for name, path in sorted(artifacts.items()) if path)

    return TEMPLATE.format(
        status=_e(status), status_class=_e(status.lower()), decision=_e(card.get("decision", "unknown")),
        policy=_e(card.get("policy", "?")), operation=_e(card.get("operation", "?")),
        subject_type=_e(subject.get("type", "?")), revision=_e(str(subject.get("revision", "?"))[:12]),
        revision_full=_e(subject.get("revision", "?")),
        advisory=_percent(card.get("advisory")), advisory_meter=_meter(card.get("advisory")),
        advisory_detail=_e(f"{(card.get('advisory') or {}).get('passed', 0)} of {(card.get('advisory') or {}).get('total', 0)}"),
        enforced=_percent(card.get("enforced")), enforced_meter=_meter(card.get("enforced")),
        enforced_detail=_e(f"{(card.get('enforced') or {}).get('passed', 0)} of {(card.get('enforced') or {}).get('total', 0)}"),
        segments=segments, legend=legend, chips="".join(chips), cards="".join(cards) or '<p class="empty">No controls in this card.</p>',
        mismatch=mismatch, artifacts=(f'<section class="artifacts"><h2>Artifacts</h2><ul>{artifact_rows}</ul></section>' if artifact_rows else ""),
        generated=_e(generated_at), version=_e(VERSION),
    )


TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Guardrails Scorecard — {status}</title>
<style>
:root {{
  --bg:#f6f7f9; --panel:#fff; --ink:#1b1f24; --muted:#5b6470; --line:#e3e6ea;
  --green:#1f883d; --orange:#b35900; --red:#cf222e; --gray:#8c959f; --accent:#0969da;
  --green-bg:#dafbe1; --orange-bg:#fff1e0; --red-bg:#ffebe9; --gray-bg:#eef0f2;
}}
@media (prefers-color-scheme: dark) {{
  :root {{ --bg:#0d1117; --panel:#161b22; --ink:#e6edf3; --muted:#9198a1; --line:#30363d;
    --green:#3fb950; --orange:#e3963e; --red:#f85149; --gray:#8b949e; --accent:#4493f8;
    --green-bg:#12261e; --orange-bg:#2d2112; --red-bg:#2d1517; --gray-bg:#21262d; }}
}}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--ink); font:15px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif; }}
main {{ max-width:1100px; margin:0 auto; padding:28px 16px 48px; }}
code {{ font:12.5px ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; color:var(--muted); word-break:break-all; }}
.top {{ display:flex; flex-wrap:wrap; gap:16px; align-items:center; justify-content:space-between; }}
.top h1 {{ margin:0; font-size:22px; }}
.top p {{ margin:2px 0 0; color:var(--muted); }}
.badge {{ font-weight:700; letter-spacing:.04em; padding:8px 16px; border-radius:999px; font-size:15px; }}
.badge.green {{ background:var(--green-bg); color:var(--green); }} .badge.orange {{ background:var(--orange-bg); color:var(--orange); }}
.badge.red {{ background:var(--red-bg); color:var(--red); }} .badge.gray, .badge.unknown {{ background:var(--gray-bg); color:var(--gray); }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(min(220px,100%),1fr)); gap:12px; margin:20px 0; }}
.card {{ background:var(--panel); border:1px solid var(--line); border-radius:12px; padding:14px 16px; }}
.card h2 {{ margin:0 0 4px; font-size:12px; text-transform:uppercase; letter-spacing:.06em; color:var(--muted); font-weight:600; }}
.big {{ font-size:26px; font-weight:700; }}
.meter {{ height:6px; background:var(--gray-bg); border-radius:99px; overflow:hidden; margin-top:8px; }}
.meter span {{ display:block; height:100%; background:var(--green); }}
.stack {{ display:flex; height:10px; border-radius:99px; overflow:hidden; gap:2px; margin:10px 0 8px; }}
.seg.r-green, .dot.r-green {{ background:var(--green); }} .seg.r-orange, .dot.r-orange {{ background:var(--orange); }}
.seg.r-red, .dot.r-red {{ background:var(--red); }} .seg.r-gray, .dot.r-gray {{ background:var(--gray); }}
.legend {{ list-style:none; margin:0; padding:0; display:flex; flex-wrap:wrap; gap:4px 14px; color:var(--muted); font-size:13px; }}
.dot {{ display:inline-block; width:9px; height:9px; border-radius:50%; margin-right:6px; }}
.toolbar {{ display:flex; flex-wrap:wrap; gap:8px; align-items:center; margin:24px 0 12px; }}
.chip {{ border:1px solid var(--line); background:var(--panel); color:var(--ink); border-radius:999px; padding:5px 12px; cursor:pointer; font:inherit; font-size:13px; }}
.chip.on {{ border-color:var(--accent); color:var(--accent); }}
.chip b {{ margin-left:4px; }}
input[type=search] {{ margin-left:auto; min-width:200px; flex:1 1 200px; max-width:320px; padding:7px 12px; border-radius:8px; border:1px solid var(--line); background:var(--panel); color:var(--ink); font:inherit; }}
.controls {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(min(320px,100%),1fr)); gap:12px; align-items:start; }}
.control {{ min-width:0; overflow-wrap:anywhere; background:var(--panel); border:1px solid var(--line); border-left:4px solid var(--gray); border-radius:10px; padding:12px 14px; }}
.control.g-passed {{ border-left-color:var(--green); }} .control.g-failed {{ border-left-color:var(--red); }}
.control.g-unverified {{ border-left-color:var(--orange); }}
.control header {{ display:flex; flex-wrap:wrap; align-items:baseline; gap:4px 10px; }}
.control h3 {{ margin:0; font-size:15px; }}
.control header code {{ flex-basis:100%; }}
.pill {{ font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:.05em; padding:2px 8px; border-radius:99px; }}
.pill.r-green {{ background:var(--green-bg); color:var(--green); }} .pill.r-orange {{ background:var(--orange-bg); color:var(--orange); }}
.pill.r-red {{ background:var(--red-bg); color:var(--red); }} .pill.r-gray {{ background:var(--gray-bg); color:var(--gray); }}
dl {{ display:grid; grid-template-columns:auto 1fr; gap:2px 12px; margin:10px 0 0; font-size:13px; }}
dt {{ color:var(--muted); }} dd {{ margin:0; }}
.reason {{ margin:8px 0 0; font-size:13px; color:var(--muted); }}
.next {{ margin:8px 0 0; font-size:13px; background:var(--bg); border-radius:6px; padding:6px 8px; }}
.alert {{ background:var(--red-bg); color:var(--red); border-radius:8px; padding:10px 12px; margin:12px 0; }}
.artifacts ul {{ list-style:none; padding:0; margin:0; }} .artifacts li {{ display:flex; flex-wrap:wrap; gap:0 10px; padding:4px 0; min-width:0; }}
.artifacts li span {{ min-width:80px; color:var(--muted); }}
.artifacts h2 {{ font-size:15px; margin:28px 0 8px; }}
.empty {{ color:var(--muted); }}
footer {{ margin-top:32px; color:var(--muted); font-size:12px; }}
[hidden] {{ display:none !important; }}
</style>
</head>
<body>
<main>
  <div class="top">
    <div>
      <h1>Guardrails Scorecard</h1>
      <p>Policy <b>{policy}</b> · operation <b>{operation}</b> · {subject_type} <code title="{revision_full}">{revision}</code></p>
    </div>
    <span class="badge {status_class}">{status} · {decision}</span>
  </div>
  {mismatch}
  <div class="grid">
    <section class="card"><h2>Readiness</h2>
      <div class="stack">{segments}</div>
      <ul class="legend">{legend}</ul>
    </section>
    <section class="card"><h2>Advisory controls passed</h2><div class="big">{advisory}</div><code>{advisory_detail}</code>{advisory_meter}</section>
    <section class="card"><h2>Enforced controls passed</h2><div class="big">{enforced}</div><code>{enforced_detail}</code>{enforced_meter}</section>
  </div>
  <div class="toolbar" role="toolbar" aria-label="Filter controls">
    {chips}
    <input type="search" id="q" placeholder="Search controls or providers" aria-label="Search controls">
  </div>
  <section class="controls" id="controls">{cards}</section>
  {artifacts}
  <footer>Generated {generated} by ai-toolkit {version}. A missing result is never counted as a pass.</footer>
</main>
<script>
(function () {{
  var filter = "all", q = document.getElementById("q");
  var chips = document.querySelectorAll(".chip"), items = document.querySelectorAll(".control");
  function apply() {{
    var text = (q.value || "").toLowerCase().trim();
    items.forEach(function (el) {{
      var show = (filter === "all" || el.dataset.group === filter) && (!text || el.dataset.text.indexOf(text) !== -1);
      el.hidden = !show;
    }});
  }}
  chips.forEach(function (chip) {{
    chip.addEventListener("click", function () {{
      chips.forEach(function (c) {{ c.classList.remove("on"); }});
      chip.classList.add("on"); filter = chip.dataset.filter; apply();
    }});
  }});
  q.addEventListener("input", apply);
}})();
</script>
</body>
</html>
"""
