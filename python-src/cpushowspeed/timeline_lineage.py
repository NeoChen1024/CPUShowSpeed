"""Offline calibration lineage presentation sourced from the research registry and saved fits.

Two parallel chains end in two units: SPEC rate generations in rate-VAXen, and SPEC
speed generations, SPECint89, classical scores and instruction mixes in speed-VAXen.
"""

import hashlib
import json
import os
from pathlib import Path

from cpushowspeed.mix_network import MIX_METRICS, TIMELINE_RUN
from cpushowspeed.research_io import read_csv
from cpushowspeed.spec_speed_chain import DERIVED as SPEED_DERIVED
from cpushowspeed.spec_speed_chain import FACTORS as SPEED_FACTORS

GENERATIONS = ["2026", "2017", "2006", "2000", "95", "92"]
MIX_LABELS = {"InstructionMix:Gibson_KIPS": "Gibson mix", "InstructionMix:ADP_KIPS": "ADP mix"}


def _edge_stats(rows, new, old, unit):
    """Base and peak statistics of one adjacent-suite edge from a factor table."""
    stats = [
        dict(
            mode=r["mode"],
            factor=float(r["factor_old_per_new"]),
            low=float(r["cluster_bootstrap_95_low"]),
            high=float(r["cluster_bootstrap_95_high"]),
            pairs=int(r["fit_pairings"]),
            groups=int(r["processor_configs"]),
            error=100 * float(r["heldout_p95_absolute_pct_error"]),
            unit=unit,
            error_label="Held-out absolute P95 (%)",
        )
        for r in rows
        if r["new_generation"] == "cpu" + new and r["old_generation"] == "cpu" + old
    ]
    if {r["mode"] for r in stats} != {"base", "peak"}:
        raise ValueError(f"Missing edge metadata: {new} to {old}")
    return stats


def build_lineage(output):
    registry_path = Path("research/model-registry.json")
    registry = json.loads(registry_path.read_text())
    models = {m["id"]: m for m in registry["models"]}
    edge_path = Path("research/data/spec/fitting/integer-rate-edge-intervals.csv")
    bridge_path = Path("research/data/classic/spec89-bridge-summary.csv")
    evidence_path = Path("research/data/classic/spec89-bridge-evidence.csv")
    classic_path = Path("research/data/classic/network-coefficients.csv")
    mix_path = Path("research/data/classic/mix-network-coefficients.csv")
    pairs_path = SPEED_DERIVED / "integer-speed-generation-pairs.csv"
    inputs = [registry_path, edge_path, SPEED_FACTORS, pairs_path, bridge_path, evidence_path, classic_path, mix_path]
    rates = [r for r in read_csv(edge_path)]
    speeds = read_csv(SPEED_FACTORS)
    bridge = read_csv(bridge_path)
    nodes = []
    edges = []

    def node(id, title, subtitle, x, y, w=175, h=64, kind="metric", details=""):
        nodes.append(dict(id=id, title=title, subtitle=subtitle, x=x, y=y, w=w, h=h, kind=kind, details=details))

    def edge(model, source, target, label, stats=None, kind="fit", details="", id=None):
        m = models[model]
        edges.append(
            dict(
                id=id or model,
                source=source,
                target=target,
                label=label,
                kind=kind,
                formula=m["formula"],
                status=m["status"],
                details=details or m["shared_evidence"],
                owner=os.path.relpath(Path(m["owner"]).resolve(), output.parent.resolve()),
                stats=stats or [],
            )
        )

    column = {g: 25 + i * 190 for i, g in enumerate(GENERATIONS)}
    for g in GENERATIONS:
        node("rate-" + g, "SPEC" + g + " rate", "Integer · Base / Peak", column[g], 50)
        node("speed-" + g, "SPECint92 speed" if g == "92" else "SPEC" + g + " speed", "Integer · Base / Peak", column[g], 180)
    unit_note = (
        "VAXen is the plural of VAX. SI prefixes are decimal: 1 kVAXen = 1,000 VAXen. "
        "Rate-VAXen and speed-VAXen both set the VAX-11/780 to 1 but measure different things and are never combined. "
        "Calibrated values are estimates, not new SPEC measurements."
    )
    node(
        "rate-vaxen",
        "rate-VAXen",
        "Throughput · VAX-11/780 = 1",
        1195,
        40,
        185,
        84,
        "unit",
        details="Every copy a system runs. The reference rate score is 604800 / 25500 ≈ 23.717647. " + unit_note,
    )
    node(
        "speed-vaxen",
        "speed-VAXen",
        "One job · VAX-11/780 = 1",
        1195,
        300,
        185,
        84,
        "unit",
        details="One job. VAX-11/780 is the SPEC92 reference machine, so one SPECint92 point is one speed-VAXen. " + unit_note,
    )
    for new, old in zip(GENERATIONS, GENERATIONS[1:]):
        scenario = "same_os" if old == "92" else "strict"
        edge(
            f"rate-{new}-to-{old}",
            "rate-" + new,
            "rate-" + old,
            "× k",
            _edge_stats([r for r in rates if r["scenario"] == scenario], new, old, "older-suite points / newer-suite point"),
            details="The timeline chain uses same_os pairing for CPU95→92 and strict pairing on newer edges. CPU2026 has sparse overlap; its estimate remains exploratory. Individual edge CI95 is not full-chain CI95.",
        )
        edge(
            f"speed-{new}-to-{old}",
            "speed-" + new,
            "speed-" + old,
            "× k",
            _edge_stats(speeds, new, old, "older-suite speed points / newer-suite point"),
            details="Automatic hardware_near speed pairs: same system, processor, chips, clock (1%), memory, cores and threads. "
            "Edges share no configuration and are bootstrapped independently. CPU2017 speed may run several threads.",
        )
    edge(
        "rate92-unit",
        "rate-92",
        "rate-vaxen",
        "× 25500 / 604800",
        kind="definition",
        details="Defined scale, not a fitted edge. The same factor applies to base and peak.",
    )
    edge(
        "int92-speed-vaxen",
        "speed-92",
        "speed-vaxen",
        "= 1 × SPECint92",
        kind="definition",
        details="Defined: VAX-11/780 is the SPEC92 reference machine. Base and peak share the scale.",
    )

    def bridge_stats(key, unit):
        r = next(r for r in bridge if r["edge"] == key)
        return [
            dict(
                mode="peak_proxy",
                factor=float(r["factor"]),
                low=float(r["factor_ci95_low"]),
                high=float(r["factor_ci95_high"]),
                pairs=int(r["pairs"]),
                groups=int(r["models"]),
                error=float(r["model_center_p95_percent"]),
                error_label="Model-center P95 (%)",
                unit=unit,
            )
        ]

    node("int89", "SPECint89", "Recovered integer speed", column["92"], 300, 175)
    edge(
        "int89-int92",
        "int89",
        "speed-92",
        "× k",
        bridge_stats("int89_to_int92", "SPECint92 / SPECint89"),
        kind="candidate",
        details="Empirical speed bridge from paired SPECint89/SPECint92 source rows; peak only.",
    )
    edge(
        "int92-rate-vaxen",
        "speed-92",
        "rate-92",
        "diagnostic",
        bridge_stats("int92_to_rate92", "rate-VAXen / SPECint92"),
        kind="diagnostic",
        details="Same DEC report column, one processor: rate-VAXen ≈ speed-VAXen. A diagnostic of the two quantities; never chained.",
    )

    node(
        "classical",
        "Classical scores",
        "Dhrystone · Whetstone · LINPACK",
        30,
        460,
        300,
        90,
        details="Six metrics retain version, native/SP/DP precision and original units. Training uses observed SPECint92 anchors and optional SPEC89-derived anchors.",
    )
    node("classic-model", "Classical joint model", "Power laws through the VAX-11/780", 465, 455, 275, 100, "model")
    edge(
        "classical-sparse-network",
        "classical",
        "classic-model",
        "Joint log fit",
        kind="joint",
        id="classical-sparse-network:classical",
    )
    stats = [
        dict(
            metric=r["metric"],
            factor=float(r["exponent"]),
            low=float(r["exponent_ci95_low"]),
            high=float(r["exponent_ci95_high"]),
            unit=f"exponent ({r['exponent_group']}); 1 speed-VAXen at the VAX-11/780's {float(r['vax780_anchor_score']):.4g} {r['score_unit']}",
        )
        for r in read_csv(classic_path)
        if r["scenario"] == "linear_clock" and r["cohort"] == "with_spec89"
    ]
    edge(
        "classical-sparse-network",
        "classic-model",
        "speed-vaxen",
        "Weighted geometric estimate",
        stats,
        kind="joint",
        details="linear_clock / with_spec89. log speed-VAXen = b × (log score − log VAX-11/780 score); Dhrystone versions share b, each Whetstone precision has its own. Original classical observations and SPECint92 anchors are jointly fitted over resolved systems; predicted speed-VAXen is not measured training evidence. CI95 retains shared draws, including the 780 anchor's run-sample error, and excludes model discrepancy and era drift.",
    )

    node(
        "mixes",
        "Gibson / ADP ratings",
        "CCTA instruction mixes · KIPS",
        30,
        620,
        300,
        90,
        details="Ratings attach to every network node of their resolved system; plus_pending_links also attaches links still under review. No attached system has a SPEC target, so the mix coefficients rest on classical scores.",
    )
    node("mix-model", "Classical + mix joint model", "Gibson and ADP share one family exponent", 465, 615, 275, 100, "model")
    run = " / ".join(TIMELINE_RUN[k] for k in ("links", "scenario", "cohort"))
    mix_rows = [r for r in read_csv(mix_path) if all(r[k] == v for k, v in TIMELINE_RUN.items())]
    edge(
        "instruction-mix-joint-network",
        "mixes",
        "mix-model",
        "Joint log fit",
        kind="joint",
        id="instruction-mix-joint-network:mixes",
    )
    edge(
        "instruction-mix-joint-network",
        "classical",
        "mix-model",
        "Shared classical anchors",
        kind="joint",
        id="instruction-mix-joint-network:classical",
    )
    edge(
        "instruction-mix-joint-network",
        "mix-model",
        "speed-vaxen",
        "aᵢ × rating^b",
        [
            dict(
                metric=MIX_LABELS[r["metric"]],
                factor=float(r["exponent"]),
                low=float(r["exponent_ci95_low"]),
                high=float(r["exponent_ci95_high"]),
                unit=f"family exponent; {float(r['vaxen_at_unit_score']):.4g} speed-VAXen at 1 KIPS (free intercept)",
            )
            for r in mix_rows
            if r["metric"] in MIX_METRICS
        ],
        kind="joint",
        details=run
        + ". Combined mixes are the equal-log-weight mean of a source row's available ratings, with CI95 from aligned draws. "
        "Mix estimates are correlated with the classical route; agreement between them is not independent validation.",
    )
    for n in nodes:
        n["edge_ids"] = [e["id"] for e in edges if n["id"] in (e["source"], e["target"])]

    # Scatter data of the fitted speed edges and the SPEC89 bridge: x = input suite, y = target suite.
    fits = [
        dict(
            edge=f"{r['new_generation']}-{r['old_generation']}",
            mode=r["mode"],
            models=int(r["processor_models"]),
            configurations=int(r["processor_configs"]),
            pairs=int(r["fit_pairings"]),
            factor=float(r["factor_old_per_new"]),
            low=float(r["cluster_bootstrap_95_low"]),
            high=float(r["cluster_bootstrap_95_high"]),
            p95=100 * float(r["heldout_p95_absolute_pct_error"]),
        )
        for r in speeds
    ]
    points = [
        dict(
            edge=f"{r['new_generation']}-{r['old_generation']}",
            mode=mode,
            system=r["new_system"],
            x=float(r[f"new_{mode}"]),
            y=float(r[f"old_{mode}"]),
        )
        for r in read_csv(pairs_path)
        if r["match_tier"] == "hardware_near"
        for mode in ("base", "peak")
        if r[f"{mode}_ratio"] != ""
    ]
    b = next(r for r in bridge if r["edge"] == "int89_to_int92")
    fits.append(
        dict(
            edge="cpu89-cpu92",
            mode="peak",
            models=int(b["models"]),
            configurations="",
            pairs=int(b["pairs"]),
            factor=float(b["factor"]),
            low=float(b["factor_ci95_low"]),
            high=float(b["factor_ci95_high"]),
            p95=float(b["model_center_p95_percent"]),
        )
    )
    points += [
        dict(edge="cpu89-cpu92", mode="peak", system=r["system"], x=float(r["x"]), y=float(r["y_vaxen"]))
        for r in read_csv(evidence_path)
        if r["edge"] == "int89_to_int92"
    ]
    return dict(
        nodes=nodes,
        edges=edges,
        speed_fits=dict(fits=fits, points=points),
        input_sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},
    )


STYLE = r"""
#lineage{max-width:1440px;margin:22px auto;border:1px solid var(--panel-border);border-radius:16px;background:var(--panel);overflow:hidden}
#lineage summary{cursor:pointer;padding:18px 22px;font-size:19px;font-weight:650}
.lineage-intro{padding:0 22px 8px;max-width:960px;font-size:14px;line-height:1.55}.lineage-intro p{margin:0 0 10px}
.lineage-toolbar{display:flex;flex-wrap:wrap;gap:16px;align-items:center;padding:0 22px 12px}.lineage-toolbar input{width:auto}
.lineage-layout{display:grid;grid-template-columns:minmax(0,1fr) 330px;gap:14px;padding:0 16px 18px}
.lineage-scroll{overflow:auto}#lineage-graph{min-width:850px;width:100%;background:transparent}
#lineage-card{background:var(--card);border:1px solid var(--card-border);border-radius:12px;padding:16px;font-size:13px;overflow-wrap:anywhere;max-height:610px;overflow:auto}
#lineage-card h3{margin:0 0 12px}#lineage-card table{font-size:12px}#lineage-card td{padding:5px}
#lineage-graph [role=button]{cursor:pointer}#lineage-graph [role=button]:focus{outline:none;filter:drop-shadow(0 0 4px var(--accent))}
#lineage-selection{padding:0 22px 12px;font-size:13px} .lineage-badge{display:inline-block;border-radius:12px;background:var(--badge);padding:3px 9px;margin:3px}
@media(max-width:1050px){.lineage-layout{grid-template-columns:1fr}#lineage-card{max-height:330px}}
"""
MARKUP = r"""
<details id="lineage"><summary>How scores become VAXen</summary>
<div class="lineage-intro">
<p><strong>1 VAX = the VAX-11/780, in two parallel quantities.</strong><br>
<b>Rate-VAXen</b> (throughput, every copy) = SPECrate_int92 × 25500 / 604800.
<b>Speed-VAXen</b> (one job) = SPECint92 speed: the VAX-11/780 is the SPEC92 reference machine.
Each later SPEC suite is chained to its own quantity; SPEC89, classical and instruction-mix scores are fitted to speed-VAXen.
The two quantities are never converted into each other.</p>
<p class="hint">CI95 describes calibration uncertainty, not the prediction range for an individual machine.</p>
</div>
<p class="lineage-intro">Pairs across SPEC generations require the same resolved system, processor, chip count, clock and memory (hardware-near). CPU92↔CPU95 rate pairs are individually reviewed; speed pairs are automatic.</p>
<div class="lineage-toolbar">
<span class="hint">Solid: calibration · dashed: bridge · dotted grey: diagnostic only · teal: fixed definition</span></div>
<div id="lineage-selection" aria-live="polite">Select a node or arrow to inspect its calibration. Click empty graph space to reset. To trace a plotted result, pin the point and choose View calibration path.</div>
<div class="lineage-layout"><div class="lineage-scroll"><svg id="lineage-graph" viewBox="0 0 1410 740" aria-label="Benchmark calibration pathways"></svg></div>
<aside id="lineage-card" aria-live="polite"><h3>Calibration details</h3><p>Select a node or arrow.</p><p>Joint models share evidence; their intervals are correlated.</p></aside></div>
<details id="fit-comparison"><summary>Speed chain and SPEC89 bridge fits</summary>
<p><label>Edge <select id="fit-edge">
<option value="cpu95-cpu92">SPEC95 → SPECint92 speed</option>
<option value="cpu2000-cpu95">SPEC2000 → SPEC95 speed</option>
<option value="cpu2006-cpu2000">SPEC2006 → SPEC2000 speed</option>
<option value="cpu2017-cpu2006">SPEC2017 → SPEC2006 speed</option>
<option value="cpu2026-cpu2017">SPEC2026 → SPEC2017 speed</option>
<option value="cpu89-cpu92">SPECint89 → SPECint92</option>
</select></label>
<label>Scores <select id="fit-mode"><option value="peak">Peak</option><option value="base">Base</option></select></label></p>
<p id="fit-stats"></p><svg id="fit-scatter" viewBox="0 0 700 330" style="max-width:850px" aria-label="Generation calibration scatterplot"></svg>
<p class="hint">Each mark is one hardware-near pair (or one SPEC89/92 source row); repeated submissions remain included. The line is the fitted factor, shading its CI95; the factor is a mean of processor-configuration medians, not a regression line. Axes show native benchmark scores.</p>
</details></details>
"""
SCRIPT = r"""
const lineage=__LINEAGE_DATA__;
let lineageActive=null,lineageRecord=null;
const lineageNode=id=>lineage.nodes.find(n=>n.id===id);
const lineageNumber=x=>Number(x).toPrecision(5);
const suites=['2026','2017','2006','2000','95','92'];
function pathway(r){
 if(['mix','mix_combined'].includes(kind(r)))return ['mixes','mix-model','speed-vaxen'];
 if(r.route==='classical')return ['classical','classic-model','speed-vaxen'];
 if(r.route==='SPEC89')return ['int89','speed-92','speed-vaxen'];
 if(r.generation&&r.generation.startsWith('cpu')){
  const q=quantityOf(r),i=suites.indexOf(r.generation.slice(3));
  return i<0?[]:suites.slice(i).map(g=>q+'-'+g).concat(q+'-vaxen');
 }
 return [];
}
function drawLineage(){
 const svg=document.querySelector('#lineage-graph'), chosen=lineageActive;
 let s='<defs><marker id="lineage-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" style="fill:var(--lineage-arrow)"/></marker></defs>';
 for(const [y,label] of [[34,'SPEC rate chain → rate-VAXen'],[164,'SPEC speed chain → speed-VAXen'],[290,'Recovered speed results'],[448,'Sparse, jointly calibrated historical scores'],[608,'Instruction-mix ratings']])s+=`<text x="25" y="${y}" style="fill:var(--lineage-lane)" font-size="16">${label}</text>`;
 for(const e of lineage.edges){const a=lineageNode(e.source),b=lineageNode(e.target);if(!a||!b)continue;
  const active=!chosen||(chosen.includes(e.source)&&chosen.includes(e.target));
  // Nodes stacked in one column connect top to bottom; others connect side to side.
  const stacked=Math.abs((a.x+a.w/2)-(b.x+b.w/2))<a.w/2&&(a.y>b.y+b.h||b.y>a.y+a.h);
  let d,labelX,labelY;
  if(stacked){const x=a.x+a.w/2,up=a.y>b.y,y=up?a.y:a.y+a.h,yy=up?b.y+b.h:b.y;d=`M${x} ${y}L${x} ${yy}`;labelX=x+8;labelY=(y+yy)/2+4;}
  else{const x=a.x+a.w,y=a.y+a.h/2,xx=b.x,yy=b.y+b.h/2;d=y===yy?`M${x} ${y}L${xx} ${yy}`:`M${x} ${y}C${x+65} ${y},${xx-65} ${yy},${xx} ${yy}`;labelX=(x+xx)/2;labelY=y===yy?y-12:(y+yy)/2-12;
   // A label longer than its gap would hide under the nodes; lift it above them.
   if(y===yy&&xx-x<6*e.label.length&&e.label.length>4)labelY=Math.min(a.y,b.y)-6;}
  const c=`var(--edge-${['definition','candidate','diagnostic'].includes(e.kind)?e.kind:'fit'})`;
  const dash=e.kind==='candidate'?'stroke-dasharray="7 5"':e.kind==='diagnostic'?'stroke-dasharray="2 5"':'';
  s+=`<g role="button" tabindex="0" data-key="${esc(e.id)}" data-type="edge" aria-label="${esc(e.label+' '+a.title+' to '+b.title)}" opacity="${active?1:.16}"><path d="${d}" fill="none" stroke="transparent" stroke-width="22"/><path d="${d}" fill="none" style="stroke:${c}" stroke-width="2.5" ${dash} marker-end="url(#lineage-arrow)"/><text x="${labelX}" y="${labelY}" text-anchor="${stacked?'start':'middle'}" font-size="11" style="fill:${c}">${esc(e.label)}</text><title>${esc(e.label)}</title></g>`;
 }
 for(const n of lineage.nodes){const active=!chosen||chosen.includes(n.id),c=`var(--lineage-${n.kind==='unit'?'unit':n.kind==='model'?'model':'node'})`;
 s+=`<g role="button" tabindex="0" data-key="${esc(n.id)}" data-type="node" aria-label="${esc(n.title)}" opacity="${active?1:.2}"><rect x="${n.x}" y="${n.y}" width="${n.w}" height="${n.h}" rx="14" style="fill:${c};stroke:var(--${active&&chosen?'lineage-active':'panel-border'})" stroke-width="${active&&chosen?3:1.5}"/><text x="${n.x+12}" y="${n.y+25}" font-size="16" style="fill:var(--lineage-title)">${esc(n.title)}</text><text x="${n.x+12}" y="${n.y+45}" font-size="12" style="fill:var(--lineage-subtitle)">${esc(n.subtitle)}</text>${n.kind==='model'?`<text x="${n.x+12}" y="${n.y+76}" font-size="11" style="fill:var(--lineage-model-text)">Shared anchors · conditional calibration</text>`:''}</g>`;}
 svg.innerHTML=s;
}
function lineageStats(edges){return edges.map(e=>{
 let stats=e.stats||[];
 if(lineageRecord){const mode=modeOf(lineageRecord);stats=stats.filter(s=>!s.mode||s.mode===mode||s.mode==='peak_proxy');}
 return `<h4>${esc(e.label)}</h4><p><code>${esc(e.formula)}</code><br>${esc(e.details)}</p>`+
 (stats.length?'<table><thead><tr><th>Metric / mode</th><th>Value · CI95</th></tr></thead><tbody>'+stats.map(r=>`<tr><td>${esc(r.metric||r.mode)}<br>${esc(r.unit)}</td><td>${lineageNumber(r.factor)}<br>${lineageNumber(r.low)}–${lineageNumber(r.high)}${r.groups!==undefined?`<br>${r.groups} models/groups · ${r.pairs} pairs`:''}${r.error!==undefined?`<br>${esc(r.error_label)}: ${lineageNumber(r.error)}`:''}</td></tr>`).join('')+'</tbody></table>':'')+
 `<p><a href="${esc(e.owner)}">Research / method notes</a> · ${esc(e.status)}</p>`;
 }).join('');}
function openFit(edge,mode){
 document.querySelector('#fit-edge').value=edge;
 if(mode)document.querySelector('#fit-mode').value=mode;
 document.querySelector('#fit-comparison').open=true;drawFit();
}
function inspectLineage(type,id){
 const speed=/^speed-(95|2000|2006|2017|2026)-to-(92|95|2000|2006|2017)$/.exec(id);
 if(speed)openFit('cpu'+speed[1]+'-cpu'+speed[2]);else if(id==='int89-int92'||id==='int89')openFit('cpu89-cpu92','peak');
 const edge=lineage.edges.find(e=>e.id===id),node=lineageNode(id);
 const edges=type==='edge'?(edge?[edge]:[]):lineage.edges.filter(e=>(e.source===id||e.target===id)&&(!lineageActive||(lineageActive.includes(e.source)&&lineageActive.includes(e.target))));
 document.querySelector('#lineage-card').innerHTML=`<h3>${esc(type==='edge'?edge?.label:node?.title)}</h3><p>${esc(node?.details||'')}</p>`+lineageStats(edges);
}
function traceFormula(r){
 if(kind(r)==='mix_combined')return 'V = geometric mean(kᵢ × ratingᵢ); aligned joint draws for CI95';
 if(kind(r)==='mix')return 'V = k × rating; classical + mix joint model';
 if(r.route==='classical')return 'V = family-balanced geometric mean(Aᵢ × scoreᵢ^bᵢ)';
 return 'V = input score × saved calibration factor(s)';
}
function traceLineage(r){
 lineageRecord=r;lineageActive=pathway(r);document.querySelector('#lineage').open=true;drawLineage();
 const q=quantityOf(r);
 document.querySelector('#lineage-selection').textContent=`${r.system} · ${r.route} · ${modeOf(r)} · ${quantityLabel(r)} · ${estimateLabel(r)}`;
 document.querySelector('#lineage-card').innerHTML=`<h3>${esc(r.system)}</h3><p class="lineage-badge">${esc(r.route)} · ${esc(modeOf(r))} · ${esc(quantityLabel(r))}</p><h4>Actual inputs</h4><div>${scoreDetails(r)}</div><p>${esc(traceFormula(r))}</p><h4>${fmt(r.vaxen,q)}</h4><p>Calibration CI95<br>${fmt(r.ci95_low,q)} – ${fmt(r.ci95_high,q)}</p><p>${esc(r.calibration_route||'')}<br>${esc(r.calibration_scenario||'Saved route calibration')}<br>${esc(r.limitation)}</p><p><a href="${esc(r.source_url)}">Original source</a></p><p>Select a highlighted arrow for details. CI95 uses the saved joint or chain calibration.</p>`;
 const i=suites.indexOf((r.generation||'').slice(3));
 if(q==='speed'&&r.generation?.startsWith('cpu')&&i>=0&&i<suites.length-1)openFit(r.generation+'-cpu'+suites[i+1],modeOf(r));
 else if(r.route==='SPEC89')openFit('cpu89-cpu92','peak');
 clearSelection();document.querySelector('#lineage').scrollIntoView?.({behavior:'smooth',block:'start'});
}
for(const event of ['click','keydown'])document.querySelector('#lineage-graph').addEventListener(event,e=>{
 if(event==='keydown'&&!['Enter',' '].includes(e.key))return;
 const target=e.target.closest?.('[data-key]')||e.target;if(!target.dataset?.key){if(event==='click')resetLineage();return;}
 if(event==='keydown')e.preventDefault();inspectLineage(target.dataset.type,target.dataset.key);
});
function resetLineage(){lineageActive=null;lineageRecord=null;drawLineage();document.querySelector('#lineage-selection').textContent='Rate, speed, historical and mix calibration pathways';document.querySelector('#lineage-card').innerHTML='<h3>Calibration details</h3><p>Select a node or arrow.</p><p>Joint models share evidence; their intervals are correlated.</p>';}
document.querySelector('#trace-path').addEventListener('click',()=>{if(candidates.length)traceLineage(candidates[active].r);});

function drawFit(){
 const edge=document.querySelector('#fit-edge').value||'cpu95-cpu92',legacy=edge==='cpu89-cpu92';
 const modeSelect=document.querySelector('#fit-mode');if(legacy)modeSelect.value='peak';modeSelect.disabled=legacy;
 const mode=modeSelect.value||'peak',[input,target]=edge.split('-');
 const fit=(lineage.speed_fits?.fits||[]).find(f=>f.edge===edge&&f.mode===mode);
 const rows=(lineage.speed_fits?.points||[]).filter(r=>r.edge===edge&&r.mode===mode);
 const suite=g=>g==='cpu92'?'SPECint92':g==='cpu89'?'SPECint89':'SPEC'+g.slice(3);
 const xlabel=`${suite(input)} speed (${mode})`,ylabel=`${suite(target)} speed (${mode})`;
 const svg=document.querySelector('#fit-scatter');
 svg.setAttribute('aria-label',xlabel+' versus '+ylabel);
 document.querySelector('#fit-stats').textContent=fit?`${legacy?'Historical source pairs':'hardware-near · '+mode} · ${fit.models} CPU models${fit.configurations!==''?' · '+fit.configurations+' configurations':''} · ${fit.pairs} pairs · k ${lineageNumber(fit.factor)} · CI95 ${lineageNumber(fit.low)}–${lineageNumber(fit.high)} · held-out P95 ${Number(fit.p95).toFixed(2)}%`:'No fitted coefficient for this selection';
 if(!rows.length){svg.innerHTML='';return;}
 const values=rows.map(r=>[r.x,r.y]);
 const lo=Math.log10(Math.min(...values.map(r=>r[0])))-.08,hi=Math.log10(Math.max(...values.map(r=>r[0])))+.08;
 const yl=Math.log10(Math.min(...values.map(r=>r[1])))-.08,yh=Math.log10(Math.max(...values.map(r=>r[1])))+.08;
 const xx=v=>75+(Math.log10(v)-lo)/(hi-lo)*580,yy=v=>275-(Math.log10(v)-yl)/(yh-yl)*245;
 let out='';for(let i=0;i<4;i++){const x=10**(lo+(hi-lo)*i/3),y=10**(yl+(yh-yl)*i/3);out+=`<path d="M${xx(x)} 30V275M75 ${yy(y)}H655" style="stroke:var(--grid)"/><text x="${xx(x)}" y="295" text-anchor="middle">${x.toPrecision(3)}</text><text x="68" y="${yy(y)}" text-anchor="end">${y.toPrecision(3)}</text>`;}
 out+='<defs><clipPath id="fit-clip"><rect x="75" y="30" width="580" height="245"/></clipPath></defs><g clip-path="url(#fit-clip)">';
 if(fit){const a=10**lo,b=10**hi,k=fit.factor,l=fit.low,h=fit.high;out+=`<path d="M${xx(a)} ${yy(a*l)}L${xx(b)} ${yy(b*l)}L${xx(b)} ${yy(b*h)}L${xx(a)} ${yy(a*h)}Z" style="fill:var(--accent)" opacity=".15"/><path d="M${xx(a)} ${yy(a*k)}L${xx(b)} ${yy(b*k)}" style="stroke:var(--accent)"/>`;}
 out+=values.map((v,i)=>`<circle cx="${xx(v[0])}" cy="${yy(v[1])}" r="3" style="fill:var(--accent)" opacity=".55"><title>${esc(rows[i].system)}</title></circle>`).join('');
 svg.innerHTML=out+`</g><text x="350" y="324" text-anchor="middle">${esc(xlabel)} (log scale)</text><text x="75" y="18">${esc(ylabel)} (log scale)</text>`;
}
for(const id of ['fit-edge','fit-mode'])document.querySelector('#'+id).addEventListener('change',drawFit);
drawFit();drawLineage();
"""
