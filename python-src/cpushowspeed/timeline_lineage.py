"""Offline calibration lineage presentation sourced from the research registry and saved fits."""

import hashlib
import json
import os
from pathlib import Path

from cpushowspeed.mix_network import MIX_METRICS, TIMELINE_RUN
from cpushowspeed.research_io import read_csv
from cpushowspeed.spec_predictors import DERIVED as PREDICTOR_OUTPUT
from cpushowspeed.spec_predictors import RESEARCH as PREDICTOR_RESEARCH

GENERATIONS = ["2026", "2017", "2006", "2000", "95", "92"]
MIX_LABELS = {"InstructionMix:Gibson_KIPS": "Gibson mix", "InstructionMix:ADP_KIPS": "ADP mix"}


def build_lineage(output):
    registry_path = Path("research/model-registry.json")
    registry = json.loads(registry_path.read_text())
    models = {m["id"]: m for m in registry["models"]}
    edge_path = Path("research/data/spec/fitting/integer-rate-edge-intervals.csv")
    bridge_path = Path("research/data/classic/spec89-rate-bridge-summary.csv")
    evidence_path = Path("research/data/classic/spec89-rate-bridge-evidence.csv")
    classic_path = Path("research/data/classic/network-coefficients.csv")
    mix_path = Path("research/data/classic/mix-network-coefficients.csv")
    summary_path = PREDICTOR_RESEARCH / "summary.csv"
    tuples_path = PREDICTOR_OUTPUT / "tuples.csv"
    inputs = [registry_path, edge_path, bridge_path, evidence_path, classic_path, mix_path, summary_path, tuples_path]
    rates = read_csv(edge_path)
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
    node(
        "vaxen",
        "VAXen",
        "VAX-11/780 = 1",
        1195,
        280,
        185,
        88,
        "unit",
        details="VAXen is the plural of VAX. The reference rate score is 604800 / 25500 ≈ 23.717647. SPECint92 speed uses a different scale. SI prefixes are decimal: 1 kVAXen = 1,000 VAXen; 1 MVAXen = 1,000,000 VAXen; 1 mVAX = 0.001 VAX. Calibrated values are estimates, not new SPEC measurements.",
    )
    for new, old in zip(GENERATIONS, GENERATIONS[1:]):
        scenario = "same_os" if old == "92" else "strict"
        stats = [
            dict(
                mode=r["mode"],
                factor=float(r["factor_old_per_new"]),
                low=float(r["cluster_bootstrap_95_low"]),
                high=float(r["cluster_bootstrap_95_high"]),
                pairs=int(r["fit_pairings"]),
                groups=int(r["processor_configs"]),
                error=100 * float(r["heldout_p95_absolute_pct_error"]),
                unit="older-suite points / newer-suite point",
                error_label="Held-out absolute P95 (%)",
            )
            for r in rates
            if r["new_generation"] == "cpu" + new and r["old_generation"] == "cpu" + old and r["scenario"] == scenario
        ]
        if {r["mode"] for r in stats} != {"base", "peak"}:
            raise ValueError("Missing rate edge metadata: " + new + " to " + old)
        edge(
            f"rate-{new}-to-{old}",
            "rate-" + new,
            "rate-" + old,
            "× k",
            stats,
            details="The timeline chain uses same_os pairing for CPU95→92 and strict pairing on newer edges. CPU2026 has sparse overlap; its estimate remains exploratory. Individual edge CI95 is not full-chain CI95.",
        )
    edge(
        "rate92-unit",
        "rate-92",
        "vaxen",
        "× 25500 / 604800",
        kind="definition",
        details="Defined scale, not a fitted edge. The same factor applies to base and peak.",
    )

    # Speed and paired speed/rate predictors of the older suite's rate, one node per newer suite with a fit.
    fits = [r for r in read_csv(summary_path) if r["status"] == "conditional_fit"]
    model_ids = dict(
        speed_only="spec-predictor-speed-only",
        rate_only="spec-predictor-rate-only",
        equal_geometric="spec-predictor-equal-geometric",
    )
    for new, old in zip(GENERATIONS, GENERATIONS[1:]):
        own = [r for r in fits if r["new_generation"] == "cpu" + new]
        if not own:
            continue
        node(
            "predictor-" + new,
            "SPEC" + new + " speed",
            "Speed · speed + rate",
            column[new],
            170,
            h=56,
            kind="predictor",
            details=f"Hardware-near SPEC{new} speed, rate and SPEC{old} rate results on one resolved system. "
            "Each predictor is fitted on the same tuples; its VAXen use the saved upstream rate chain.",
        )
        stats = [
            dict(
                mode=r["mode"],
                metric={"speed_only": "Speed only", "rate_only": "Rate only", "equal_geometric": "sqrt(speed × rate)"}[r["method"]]
                + " · "
                + r["mode"],
                factor=float(r["coefficient_older_rate"]),
                low=float(r["local_ci95_low"]),
                high=float(r["local_ci95_high"]),
                pairs=int(r["tuples"]),
                groups=int(r["models"]),
                error=float(r["model_center_p95_percent"]),
                unit=f"SPEC{old} rate points / input point",
                error_label="Model-held-out P95 (%)",
            )
            for r in own
        ]
        edge(
            model_ids["equal_geometric"],
            "predictor-" + new,
            "rate-" + old,
            "× k",
            stats,
            details="Speed only, rate only and their geometric mean predict the older suite's rate on identical tuples. "
            "From CPU2006 on, rate counts every core while speed is one task, so speed-only estimates of multi-core machines are weak.",
            id=f"predictor-{new}-to-{old}",
        )

    node("int89", "SPECint89", "Recovered integer speed", 30, 300, 215)
    node("int92", "SPECint92", "Integer speed · not rate", 345, 300, 215)
    for model, source, target, key in [
        ("int89-int92", "int89", "int92", "int89_to_int92"),
        ("int92-rate-vaxen", "int92", "vaxen", "int92_to_rate92"),
    ]:
        r = next(r for r in bridge if r["edge"] == key)
        edge(
            model,
            source,
            target,
            "× k",
            stats=[
                dict(
                    mode="peak_proxy",
                    factor=float(r["factor"]),
                    low=float(r["factor_ci95_low"]),
                    high=float(r["factor_ci95_high"]),
                    pairs=int(r["pairs"]),
                    groups=int(r["models"]),
                    error=float(r["model_center_p95_percent"]),
                    error_label="Model-center P95 (%)",
                    unit="SPECint92 / SPECint89" if source == "int89" else "VAXen / SPECint92",
                )
            ],
            kind="candidate",
            details="Empirical speed bridge. The second edge already includes CPU92 rate normalization; do not apply it again.",
        )

    node(
        "classical",
        "Classical scores",
        "Dhrystone · Whetstone · LINPACK",
        30,
        460,
        300,
        90,
        details="Six metrics retain version, native/SP/DP precision and original units. Training uses measured rate anchors and optional SPEC89-derived anchors.",
    )
    node("classic-model", "Classical joint model", "Six per-benchmark coefficients", 465, 455, 275, 100, "model")
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
            factor=float(r["coefficient_vaxen_per_score"]),
            low=float(r["factor_ci95_low"]),
            high=float(r["factor_ci95_high"]),
            unit="VAXen / " + r["score_unit"],
        )
        for r in read_csv(classic_path)
        if r["scenario"] == "linear_clock" and r["cohort"] == "with_spec89"
    ]
    edge(
        "classical-sparse-network",
        "classic-model",
        "vaxen",
        "Weighted geometric estimate",
        stats,
        kind="joint",
        details="linear_clock / with_spec89. Original classical observations and SPEC92 rate anchors are jointly fitted over resolved systems; predicted VAXen is not measured training evidence. CI95 retains shared draws and excludes model discrepancy.",
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
    node("mix-model", "Classical + mix joint model", "Gibson and ADP share one family", 465, 615, 275, 100, "model")
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
        "vaxen",
        "kᵢ × rating",
        [
            dict(
                metric=MIX_LABELS[r["metric"]],
                factor=float(r["coefficient_vaxen_per_score"]),
                low=float(r["ci95_vaxen_low"]),
                high=float(r["ci95_vaxen_high"]),
                unit="VAXen / KIPS",
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

    pairs = [
        dict(model_key=r["model_key"], system=r["system"], SPECint89=r["x"], SPECint92=r["y_vaxen"], source_url=r["source_url"])
        for r in read_csv(evidence_path)
        if r["edge"] == "int89_to_int92"
    ]
    keep = ("new_generation", "mode", "method", "models", "processor_configs", "tuples", "coefficient_older_rate")
    keep += ("local_ci95_low", "local_ci95_high", "coefficient_vaxen", "model_center_p95_percent")
    tuples = [
        dict(
            new_generation=r["new_generation"],
            mode=r["mode"],
            model_key=r["model_key"],
            system=r["rate_system"],
            target_rate=float(r["target_rate"]),
            speed_score=float(r["speed_score"]),
            rate_score=float(r["rate_score"]),
        )
        for r in read_csv(tuples_path)
    ]
    return dict(
        nodes=nodes,
        edges=edges,
        legacy_fit=dict(rows=pairs, fit=next(r for r in bridge if r["edge"] == "int89_to_int92")),
        predictors=dict(fits=[{k: r[k] for k in keep} for r in fits], tuples=tuples),
        input_sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},
    )


STYLE = r"""
#lineage{max-width:1440px;margin:22px auto;border:1px solid #cedbe5;border-radius:16px;background:#f4f6f8;overflow:hidden}
#lineage summary{cursor:pointer;padding:18px 22px;font-size:19px;font-weight:650}
.lineage-intro{padding:0 22px 8px;max-width:960px;font-size:14px;line-height:1.55}.lineage-intro p{margin:0 0 10px}
.lineage-toolbar{display:flex;flex-wrap:wrap;gap:16px;align-items:center;padding:0 22px 12px}.lineage-toolbar input{width:auto}
.lineage-layout{display:grid;grid-template-columns:minmax(0,1fr) 330px;gap:14px;padding:0 16px 18px}
.lineage-scroll{overflow:auto}#lineage-graph{min-width:850px;width:100%;background:transparent}
#lineage-card{background:#fff;border:1px solid #d8e2e9;border-radius:12px;padding:16px;font-size:13px;overflow-wrap:anywhere;max-height:610px;overflow:auto}
#lineage-card h3{margin:0 0 12px}#lineage-card table{font-size:12px}#lineage-card td{padding:5px}
#lineage-graph [role=button]{cursor:pointer}#lineage-graph [role=button]:focus{outline:none;filter:drop-shadow(0 0 4px #207ca3)}
#lineage-selection{padding:0 22px 12px;font-size:13px} .lineage-badge{display:inline-block;border-radius:12px;background:#e8f1f8;padding:3px 9px;margin:3px}
@media(max-width:1050px){.lineage-layout{grid-template-columns:1fr}#lineage-card{max-height:330px}}
"""
MARKUP = r"""
<details id="lineage"><summary>How scores become VAXen</summary>
<div class="lineage-intro">
<p><strong>1 VAX = the VAX-11/780 reference throughput on the SPEC92 integer-rate scale.</strong><br>
VAXen = SPECrate_int92 × 25500 / 604800. The same formula applies to Base scores.
Other benchmarks are mapped onto this scale using fitted models.</p>
<p class="hint">CI95 describes calibration uncertainty, not the prediction range for an individual machine.</p>
</div>
<p class="lineage-intro">Pairs across SPEC generations require the same resolved system, processor, chip count, clock and memory (hardware-near). CPU92↔CPU95 rate pairs are individually reviewed.</p>
<div class="lineage-toolbar">
<span class="hint">Solid: calibration · dashed: candidate links · teal: fixed conversion</span></div>
<div id="lineage-selection" aria-live="polite">Select a node or arrow to inspect its calibration. Click empty graph space to reset. To trace a plotted result, pin the point and choose View calibration path.</div>
<div class="lineage-layout"><div class="lineage-scroll"><svg id="lineage-graph" viewBox="0 0 1410 740" aria-label="Benchmark calibration pathways"></svg></div>
<aside id="lineage-card" aria-live="polite"><h3>Calibration details</h3><p>Select a node or arrow.</p><p>Joint models share evidence; their intervals are correlated.</p></aside></div>
<div id="predictor-path" aria-live="polite"></div>
<details id="fit-comparison"><summary>Compare predictor fits</summary>
<p><label>Generations <select id="fit-generation">
<option value="cpu95">SPEC95 → SPEC92</option>
<option value="cpu2000">SPEC2000 → SPEC95</option>
<option value="cpu2006">SPEC2006 → SPEC2000</option>
<option value="cpu2017">SPEC2017 → SPEC2006</option>
<option value="cpu2026">SPEC2026 → SPEC2017</option>
<option value="cpu89">SPEC89 → SPEC92 (speed)</option>
</select></label>
<label>Scores <select id="fit-mode"><option value="peak">Peak</option><option value="base">Base</option></select></label>
<label>Inputs <select id="fit-method"><option value="equal_geometric">Speed + rate</option><option value="speed_only">Speed only</option><option value="rate_only">Rate only</option></select></label></p>
<p id="fit-stats"></p><svg id="fit-scatter" viewBox="0 0 700 330" style="max-width:850px" aria-label="Generation calibration scatterplot"></svg>
<p class="hint">Each mark is one hardware-near tuple (older rate, newer speed, newer rate); repeated submissions remain included. Shading is the local coefficient CI95. Axes show native benchmark scores. All three predictors use the same tuples.</p>
</details></details>
"""
SCRIPT = r"""
const lineage=__LINEAGE_DATA__;
let lineageActive=null,lineageRecord=null;
const lineageNode=id=>lineage.nodes.find(n=>n.id===id);
const lineageNumber=x=>Number(x).toPrecision(5);
const olderSuite={cpu95:'92',cpu2000:'95',cpu2006:'2000',cpu2017:'2006',cpu2026:'2017'};
function pathway(r){
 if(['speed','joint'].includes(kind(r))){const old=olderSuite[r.generation];return old?['predictor-'+r.generation.slice(3),...pathway({route:'',estimate_kind:'baseline',generation:'cpu'+old})]:[];}
 if(r.generation&&r.generation.startsWith('cpu')&&r.generation!=='cpu89'){
  const gens=['2026','2017','2006','2000','95','92'],i=gens.indexOf(r.generation.slice(3));
  return i<0?[]:gens.slice(i).map(g=>'rate-'+g).concat('vaxen');
 }
 if(r.route==='SPEC89')return ['int89','int92','vaxen'];
 if(['mix','mix_combined'].includes(kind(r)))return ['mixes','mix-model','vaxen'];
 if(r.route==='classical')return ['classical','classic-model','vaxen'];
 return [];
}
function drawLineage(){
 const svg=document.querySelector('#lineage-graph'), chosen=lineageActive;
 let s='<defs><marker id="lineage-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#648398"/></marker></defs>';
 for(const [y,label] of [[34,'SPEC rate generations'],[160,'SPEC speed predictors of the older rate'],[290,'Recovered speed results'],[448,'Sparse, jointly calibrated historical scores'],[608,'Instruction-mix ratings']])s+=`<text x="25" y="${y}" fill="#516a7a" font-size="16">${label}</text>`;
 for(const e of lineage.edges){const a=lineageNode(e.source),b=lineageNode(e.target);if(!a||!b)continue;
  const active=!chosen||(chosen.includes(e.source)&&chosen.includes(e.target));
  const predictor=e.source.startsWith('predictor-'),down=a.y>b.y+b.h||b.y>a.y+a.h;
  const x=a.x+a.w,y=a.y+a.h/2,xx=b.x,yy=b.y+b.h/2;
  const d=predictor?`M${a.x+a.w-40} ${a.y}C${a.x+a.w-40} ${a.y-30},${xx+40} ${b.y+b.h+30},${xx+40} ${b.y+b.h}`:y===yy?`M${x} ${y}L${xx} ${yy}`:`M${x} ${y}C${x+65} ${y},${xx-65} ${yy},${xx} ${yy}`;
  const labelX=(x+xx)/2,labelY=y===yy?y-12:(y+yy)/2-12;
  const c=e.kind==='definition'?'#148c80':e.kind==='candidate'?'#a66c3d':'#497e9d';
  s+=`<g role="button" tabindex="0" data-key="${esc(e.id)}" data-type="edge" aria-label="${esc(e.label+' '+a.title+' to '+b.title)}" opacity="${active?1:.16}"><path d="${d}" fill="none" stroke="transparent" stroke-width="22"/><path d="${d}" fill="none" stroke="${c}" stroke-width="2.5" ${e.kind==='candidate'?'stroke-dasharray="7 5"':''} marker-end="url(#lineage-arrow)"/><text x="${labelX}" y="${labelY}" text-anchor="middle" font-size="11" fill="${c}">${esc(predictor||down?'':e.label)}</text><title>${esc(e.label)}</title></g>`;
 }
 for(const n of lineage.nodes){const active=!chosen||chosen.includes(n.id),c=n.kind==='unit'?'#d9f3ed':['model','predictor'].includes(n.kind)?'#e8e6f7':'#fff';
 s+=`<g role="button" tabindex="0" data-key="${esc(n.id)}" data-type="node" aria-label="${esc(n.title)}" opacity="${active?1:.2}"><rect x="${n.x}" y="${n.y}" width="${n.w}" height="${n.h}" rx="14" fill="${c}" stroke="${active&&chosen?'#1c658e':'#bdccd7'}" stroke-width="${active&&chosen?3:1.5}"/><text x="${n.x+12}" y="${n.y+25}" font-size="16" fill="#213b50">${esc(n.title)}</text><text x="${n.x+12}" y="${n.y+45}" font-size="12" fill="#506676">${esc(n.subtitle)}</text>${n.kind==='model'?`<text x="${n.x+12}" y="${n.y+76}" font-size="11" fill="#60567d">Shared anchors · conditional calibration</text>`:''}</g>`;}
 svg.innerHTML=s;
}
function lineageStats(edges){return edges.map(e=>{
 let stats=e.stats||[];
 if(lineageRecord){const mode=modeOf(lineageRecord);stats=stats.filter(s=>!s.mode||s.mode===mode||s.mode==='peak_proxy');}
 return `<h4>${esc(e.label)}</h4><p><code>${esc(e.formula)}</code><br>${esc(e.details)}</p>`+
 (stats.length?'<table><thead><tr><th>Metric / mode</th><th>k · CI95</th></tr></thead><tbody>'+stats.map(r=>`<tr><td>${esc(r.metric||r.mode)}<br>${esc(r.unit)}</td><td>${lineageNumber(r.factor)}<br>${lineageNumber(r.low)}–${lineageNumber(r.high)}${r.groups!==undefined?`<br>${r.groups} models/groups · ${r.pairs} pairs`:''}${r.error!==undefined?`<br>${esc(r.error_label)}: ${lineageNumber(r.error)}`:''}</td></tr>`).join('')+'</tbody></table>':'')+
 `<p><a href="${esc(e.owner)}">Research / method notes</a> · ${esc(e.status)}</p>`;
 }).join('');}
function openFit(generation,mode,method){
 document.querySelector('#fit-generation').value=generation;
 if(mode)document.querySelector('#fit-mode').value=mode;
 if(method)document.querySelector('#fit-method').value=method;
 document.querySelector('#fit-comparison').open=true;drawFit();
}
function inspectLineage(type,id){
 const generation=/^predictor-(95|2000|2006|2017|2026)/.exec(id)?.[1];
 if(generation)openFit('cpu'+generation);else if(id==='int89-int92'||id==='int89')openFit('cpu89');
 const edge=lineage.edges.find(e=>e.id===id),node=lineageNode(id);
 const edges=type==='edge'?(edge?[edge]:[]):lineage.edges.filter(e=>(e.source===id||e.target===id)&&(!lineageActive||(lineageActive.includes(e.source)&&lineageActive.includes(e.target))));
 document.querySelector('#lineage-card').innerHTML=`<h3>${esc(type==='edge'?edge?.label:node?.title)}</h3><p>${esc(node?.details||'')}</p>`+lineageStats(edges);
}
function traceFormula(r){
 if(kind(r)==='joint')return 'V = k × sqrt(speed × rate); local predictor, then the upstream rate chain';
 if(kind(r)==='speed')return 'V = k × speed; local predictor, then the upstream rate chain';
 if(kind(r)==='mix_combined')return 'V = geometric mean(kᵢ × ratingᵢ); aligned joint draws for CI95';
 if(kind(r)==='mix')return 'V = k × rating; classical + mix joint model';
 if(r.route==='classical')return 'V = family-balanced geometric mean(kᵢ × scoreᵢ)';
 return 'V = input score × saved calibration factor(s)';
}
function traceLineage(r){
 lineageRecord=r;lineageActive=pathway(r);document.querySelector('#lineage').open=true;drawLineage();
 document.querySelector('#lineage-selection').textContent=`${r.system} · ${r.route} · ${modeOf(r)} · ${estimateLabel(r)}`;
 document.querySelector('#lineage-card').innerHTML=`<h3>${esc(r.system)}</h3><p class="lineage-badge">${esc(r.route)} · ${esc(modeOf(r))}</p><h4>Actual inputs</h4><div>${scoreDetails(r)}</div><p>${esc(traceFormula(r))}</p><h4>${fmt(r.vaxen)}</h4><p>Calibration CI95<br>${fmt(r.ci95_low)} – ${fmt(r.ci95_high)}</p><p>${esc(r.calibration_route||'')}<br>${esc(r.calibration_scenario||'Saved route calibration')}<br>${esc(r.limitation)}</p><p><a href="${esc(r.source_url)}">Original source</a></p><p>Select a highlighted arrow for details. CI95 uses the saved joint or chain calibration.</p>`;
 if(['speed','joint'].includes(kind(r)))openFit(r.generation,modeOf(r),kind(r)==='joint'?'equal_geometric':'speed_only');
 clearSelection();document.querySelector('#lineage').scrollIntoView?.({behavior:'smooth',block:'start'});
}
for(const event of ['click','keydown'])document.querySelector('#lineage-graph').addEventListener(event,e=>{
 if(event==='keydown'&&!['Enter',' '].includes(e.key))return;
 const target=e.target.closest?.('[data-key]')||e.target;if(!target.dataset?.key){if(event==='click')resetLineage();return;}
 if(event==='keydown')e.preventDefault();inspectLineage(target.dataset.type,target.dataset.key);
});
function resetLineage(){lineageActive=null;lineageRecord=null;drawLineage();document.querySelector('#lineage-selection').textContent='Rate, speed, historical and mix calibration pathways';document.querySelector('#lineage-card').innerHTML='<h3>Calibration details</h3><p>Select a node or arrow.</p><p>Joint models share evidence; their intervals are correlated.</p>';}
document.querySelector('#trace-path').addEventListener('click',()=>{if(candidates.length)traceLineage(candidates[active].r);});

function predictorFit(generation,mode,method){return (lineage.predictors?.fits||[]).find(r=>r.new_generation===generation&&r.mode===mode&&r.method===method);}
function drawPredictorPath(generation,mode,method,fit){
 const panel=document.querySelector('#predictor-path');
 if(generation==='cpu89'){panel.innerHTML='<strong>Historical speed bridge</strong><p>SPECint89 speed → SPECint92 speed → rate-VAXen</p>';return;}
 const old=olderSuite[generation],speed=method!=='rate_only',rate=method!=='speed_only';
 const formula=method==='equal_geometric'?'sqrt(speed × rate)':speed?'speed':'rate';
 panel.innerHTML='<strong>SPEC'+esc(generation.slice(3))+' local predictor · '+esc(mode)+' · hardware-near</strong>'+
 '<div class="predictor-flow"><div class="predictor-inputs"><span class="predictor-box '+(speed?'selected':'')+'">Speed'+(speed?' ✓':' (unused)')+'</span><span class="predictor-box '+(rate?'selected':'')+'">Rate'+(rate?' ✓':' (unused)')+'</span></div><span>→</span><span class="predictor-box">'+esc(formula)+' × k</span><span>→</span><span class="predictor-box">SPEC'+old+' rate</span><span>→ upstream rate chain → VAXen</span></div>'+
 '<p>'+(fit?'Local k = '+lineageNumber(fit.coefficient_older_rate)+'. Full-route k = '+lineageNumber(fit.coefficient_vaxen)+' VAXen per input point.':'No supported coefficient: fewer than three processor models.')+
 '</p><p class="hint">The timeline plots speed-only and speed + rate estimates; rate only is shown for comparison and reproduces the full rate chain on these tuples. Shared evidence means correlated uncertainty.</p>';
}
function drawFit(){
 const generation=document.querySelector('#fit-generation').value||'cpu95',legacy=generation==='cpu89';
 const mode=document.querySelector('#fit-mode').value||'peak',method=document.querySelector('#fit-method').value||'equal_geometric';
 document.querySelector('#fit-mode').disabled=legacy;
 document.querySelector('#fit-method').disabled=legacy;
 const rows=legacy?(lineage.legacy_fit?.rows||[]):(lineage.predictors?.tuples||[]).filter(r=>r.new_generation===generation&&r.mode===mode);
 const saved=lineage.legacy_fit?.fit;
 const fit=legacy?(saved&&{models:saved.models,processor_configs:'unknown',tuples:saved.pairs,coefficient_older_rate:saved.factor,local_ci95_low:saved.factor_ci95_low,local_ci95_high:saved.factor_ci95_high,model_center_p95_percent:saved.model_center_p95_percent}):predictorFit(generation,mode,method);
 const older=olderSuite[generation];
 const xlabel=legacy?'SPECint89 speed':`SPEC${generation.slice(3)} ${method==='speed_only'?'speed':method==='rate_only'?'rate':'sqrt(speed × rate)'} (${mode})`;
 const ylabel=legacy?'SPECint92 speed':`SPEC${older} rate (${mode})`;
 const svg=document.querySelector('#fit-scatter');
 svg.setAttribute('aria-label',xlabel+' versus measured '+ylabel);
 const cohort=legacy?'Historical source pairs · speed only':'hardware-near · '+mode;
 document.querySelector('#fit-stats').textContent=fit?`${cohort} · ${fit.models} CPU models · ${fit.processor_configs} configurations · ${fit.tuples} tuples · k ${Number(fit.coefficient_older_rate).toPrecision(5)} · CI95 ${Number(fit.local_ci95_low).toPrecision(5)}–${Number(fit.local_ci95_high).toPrecision(5)} · model-held-out P95 ${Number(fit.model_center_p95_percent).toFixed(2)}%`:`${cohort} · ${new Set(rows.map(r=>r.model_key)).size} CPU models · ${rows.length} tuples · insufficient independent CPU models; no fitted coefficient`;
 drawPredictorPath(generation,mode,method,fit);
 if(!rows.length){svg.innerHTML='';return;}
 const values=rows.map(r=>legacy?[+r.SPECint89,+r.SPECint92]:[method==='speed_only'?+r.speed_score:method==='rate_only'?+r.rate_score:Math.sqrt(r.speed_score*r.rate_score),+r.target_rate]);
 const lo=Math.log10(Math.min(...values.map(r=>r[0])))-.08,hi=Math.log10(Math.max(...values.map(r=>r[0])))+.08;
 const yl=Math.log10(Math.min(...values.map(r=>r[1])))-.08,yh=Math.log10(Math.max(...values.map(r=>r[1])))+.08;
 const xx=v=>75+(Math.log10(v)-lo)/(hi-lo)*580,yy=v=>275-(Math.log10(v)-yl)/(yh-yl)*245;
 let out='';for(let i=0;i<4;i++){const x=10**(lo+(hi-lo)*i/3),y=10**(yl+(yh-yl)*i/3);out+=`<path d="M${xx(x)} 30V275M75 ${yy(y)}H655" stroke="#ddd"/><text x="${xx(x)}" y="295" text-anchor="middle">${x.toPrecision(3)}</text><text x="68" y="${yy(y)}" text-anchor="end">${y.toPrecision(3)}</text>`;}
 out+='<defs><clipPath id="fit-clip"><rect x="75" y="30" width="580" height="245"/></clipPath></defs><g clip-path="url(#fit-clip)">';
 if(fit){const a=10**lo,b=10**hi,k=+fit.coefficient_older_rate,l=+fit.local_ci95_low,h=+fit.local_ci95_high;out+=`<path d="M${xx(a)} ${yy(a*l)}L${xx(b)} ${yy(b*l)}L${xx(b)} ${yy(b*h)}L${xx(a)} ${yy(a*h)}Z" fill="#207ca3" opacity=".15"/><path d="M${xx(a)} ${yy(a*k)}L${xx(b)} ${yy(b*k)}" stroke="#207ca3"/>`;}
 out+=values.map((v,i)=>`<circle cx="${xx(v[0])}" cy="${yy(v[1])}" r="3" fill="#207ca3" opacity=".55"><title>${esc(rows[i].system||rows[i].model_key)}</title></circle>`).join('');
 svg.innerHTML=out+`</g><text x="350" y="324" text-anchor="middle">${esc(xlabel)} (log scale)</text><text x="75" y="18">Measured ${esc(ylabel)} (log scale)</text>`;
}
for(const id of ['fit-generation','fit-mode','fit-method'])document.querySelector('#'+id).addEventListener('change',drawFit);
drawFit();drawLineage();
"""
