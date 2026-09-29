"""Offline calibration lineage presentation sourced from the research registry."""

import hashlib
import json
import os
from pathlib import Path

from cpushowspeed.classic_bridge_data import bridge_rows
from cpushowspeed.research_io import read_csv


def build_lineage(output):
    registry_path = Path("research/model-registry.json")
    registry = json.loads(registry_path.read_text())
    models = {m["id"]: m for m in registry["models"]}
    edge_path = Path("research/data/spec/fitting/integer-rate-edge-intervals.csv")
    bridge_path = Path("research/data/classic/spec89-rate-bridge-summary.csv")
    classic_path = Path("data/derived/classic/network-fit/coefficients.csv")
    mix_path = Path("data/derived/classic/mix-network-fit/coefficients.csv")
    inputs = [registry_path, edge_path, bridge_path, classic_path, mix_path]
    rates = read_csv(edge_path)
    bridge = read_csv(bridge_path)
    nodes = []
    edges = []

    def node(id, title, subtitle, x, y, w=175, h=64, kind="metric", owner=None, details=""):
        nodes.append(dict(id=id, title=title, subtitle=subtitle, x=x, y=y, w=w, h=h, kind=kind, details=details, owner=owner))

    def edge(model, source, target, label, stats=None, kind="fit", details=""):
        m = models[model]
        edges.append(
            dict(
                id=model,
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

    gens = ["2026", "2017", "2006", "2000", "95", "92"]
    for i, g in enumerate(gens):
        node("rate-" + g, "SPEC" + g + " rate", "Integer · Base / Peak", 25 + i * 190, 65)
    node(
        "vaxen",
        "VAXen",
        "VAX-11/780 = 1",
        1195,
        240,
        185,
        88,
        "unit",
        details="VAXen is the plural of VAX. The reference rate score is 604800 / 25500 ≈ 23.717647. SPECint92 speed uses a different scale. SI prefixes are decimal: 1 kVAXen = 1,000 VAXen; 1 MVAXen = 1,000,000 VAXen; 1 mVAX = 0.001 VAX. Calibrated values are estimates, not new SPEC measurements.",
    )
    for new, old in zip(gens, gens[1:]):
        stats = []
        for r in rates:
            if (
                r["new_generation"] == "cpu" + new
                and r["old_generation"] == "cpu" + old
                and r["scenario"] == ("same_os" if old == "92" else "strict")
            ):
                stats.append(
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
                )
        if {r["mode"] for r in stats} != {"base", "peak"}:
            raise ValueError("Missing rate edge metadata: " + new + " to " + old)
        edge(
            f"rate-{new}-to-{old}",
            "rate-" + new,
            "rate-" + old,
            "× k",
            stats,
            details="The same_os chain uses same_os for CPU95→92 and strict pairing on newer edges. CPU2026 has sparse overlap; its estimate remains exploratory. Individual edge CI95 is not full-chain CI95.",
        )
    edge(
        "rate92-unit",
        "rate-92",
        "vaxen",
        "× 25500 / 604800",
        kind="definition",
        details="Defined scale, not a fitted edge. The same factor applies to base and peak.",
    )
    node("int89", "SPECint89", "Recovered integer speed", 30, 240, 215)
    node("int92", "SPECint92", "Integer speed · not rate", 345, 240, 215)
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
                    error=r["model_center_p95_percent"],
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
        420,
        300,
        90,
        details="Six metrics retain version, native/SP/DP precision and original units. Training uses measured rate anchors and optional SPEC89-derived anchors.",
    )
    node("classic-model", "Classical joint model", "Six per-benchmark coefficients", 465, 400, 275, 100, "model")
    node(
        "mixes",
        "Gibson / ADP",
        "CCTA/TSU KIPS · correlated inputs",
        385,
        645,
        300,
        75,
        details="One InstructionMix family. Combined rows use equal log weights over available mixes; a single available score passes through.",
    )
    node("mix-model", "Mix + classical joint model", "Shared model-bootstrap draws", 835, 535, 300, 105, "model")
    for mid, src, dst, label in [
        ("classical-sparse-network", "classical", "classic-model", "Joint log fit"),
        ("instruction-mix-joint-network", "classical", "mix-model", "Classical evidence"),
        ("instruction-mix-joint-network", "mixes", "mix-model", "Candidate links"),
    ]:
        edge(mid, src, dst, label, kind="candidate" if mid.startswith("instruction") else "joint")
        edges[-1]["id"] = mid + ":" + src
    for mid, nid, path in [
        ("classical-sparse-network", "classic-model", classic_path),
        ("instruction-mix-joint-network", "mix-model", mix_path),
    ]:
        stats = []
        for r in read_csv(path):
            if r["scenario"] == "linear_clock" and r["cohort"] == "with_spec89":
                stats.append(
                    dict(
                        metric=r["metric"],
                        factor=float(r["coefficient_vaxen_per_score"]),
                        low=float(r.get("factor_ci95_low") or r["ci95_vaxen_low"]),
                        high=float(r.get("factor_ci95_high") or r["ci95_vaxen_high"]),
                        unit="VAXen / " + r["score_unit"],
                    )
                )
        edge(
            mid,
            nid,
            "vaxen",
            "Weighted geometric estimate",
            stats,
            kind="joint",
            details="linear_clock / with_spec89. Original classical observations and SPEC92 rate anchors are jointly fitted; predicted VAXen is not measured training evidence. CI95 retains shared draws and excludes model discrepancy.",
        )
    # Modern local predictors feed the older rate backbone, not their own rate node.
    for n in nodes:
        if n["y"] >= 240:
            n["y"] += 100
    for i, (new, old) in enumerate(zip(gens, gens[1:])):
        nid = "predictor-" + new
        node(nid, "Speed / joint", "SPEC" + new + " inputs", 25 + i * 190, 180, h=64, kind="predictor")
        edges.append(
            dict(
                id=nid + "-to-rate",
                source=nid,
                target="rate-" + old,
                label="Local predictor",
                kind="fit",
                stats=[],
                formula="older rate = k × speed, or k × sqrt(speed × rate)",
                status="conditional calibration",
                details="Select this predictor to inspect speed-only, matched-cohort rate-only and joint models.",
                owner=os.path.relpath(Path("research/spec-joint-tracks.md").resolve(), output.parent.resolve()),
            )
        )
    for n in nodes:
        touching = [e for e in edges if n["id"] in (e["source"], e["target"])]
        n["edge_ids"] = [e["id"] for e in touching]
    legacy_path = Path("research/data/spec89/v2.0.0/csv/bridges89_92.csv")
    inputs.append(legacy_path)
    legacy = dict(rows=bridge_rows(legacy_path), fit=next(r for r in bridge if r["edge"] == "int89_to_int92"))
    return dict(
        nodes=nodes,
        edges=edges,
        legacy_fit=legacy,
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
<p class="lineage-intro">SPEC calibration is provisional: known fixed-count conflicts are excluded; missing or varying execution counts still require review.</p>
<div class="lineage-toolbar">
<span class="hint">Solid: calibration · dashed: candidate links · teal: fixed conversion</span></div>
<div id="lineage-selection" aria-live="polite">Select a node or arrow to inspect its calibration. Click empty graph space to reset. To trace a plotted result, pin the point and choose View calibration path.</div>
<div class="lineage-layout"><div class="lineage-scroll"><svg id="lineage-graph" viewBox="0 0 1410 860" aria-label="Benchmark calibration pathways"></svg></div>
<aside id="lineage-card" aria-live="polite"><h3>Calibration details</h3><p>Select a node or arrow.</p><p>Joint models share evidence; their intervals are correlated.</p></aside></div>
<div id="predictor-path" aria-live="polite"></div>
<details id="fit-comparison"><summary>Compare generation fits</summary>
<p><label>Generations <select id="fit-generation">
<option value="cpu2000">SPEC2000 → SPEC95</option>
<option value="cpu89">SPEC89 → SPEC92 (speed)</option>
<option value="cpu95">SPEC95 → SPEC92</option>
<option value="cpu2006">SPEC2006 → SPEC2000</option>
<option value="cpu2017">SPEC2017 → SPEC2006</option>
<option value="cpu2026">SPEC2026 → SPEC2017</option>
</select></label>
<label>Matching <select id="fit-policy"><option value="strict">Strict</option><option value="ram-aliases" selected>RAM + aliases</option><option value="cpu-clock">CPU + clock</option></select></label>
<label>Scores <select id="fit-mode"><option value="peak">Peak</option><option value="base">Base</option></select></label>
<label>Inputs <select id="fit-method"><option value="equal_geometric">Speed + rate</option><option value="speed_only">Speed only</option><option value="rate_only">Rate only — matched cohort</option></select></label></p>
<p id="fit-stats"></p><svg id="fit-scatter" viewBox="0 0 700 330" style="max-width:850px" aria-label="Generation calibration scatterplot"></svg>
<p class="hint">Each mark is a source pairing; repeated submissions remain included. Shading is coefficient CI95. Axes show native benchmark scores. Matching applies across generations. CPU + clock matches near-equal clocks; it does not scale scores.</p>
</details></details>
"""
SCRIPT = r"""
const lineage=__LINEAGE_DATA__;
let lineageActive=null,lineageRecord=null;
const lineageNode=id=>lineage.nodes.find(n=>n.id===id);
const lineageNumber=x=>Number(x).toPrecision(5);
function pathway(r){
 if(['speed','joint'].includes(r.estimate_kind)){const old={cpu95:'cpu92',cpu2000:'cpu95',cpu2006:'cpu2000',cpu2017:'cpu2006',cpu2026:'cpu2017'}[r.generation];return old?['predictor-'+r.generation.slice(3),...pathway({...r,estimate_kind:'baseline',generation:old})]:[];}
 if(r.generation&&r.generation.startsWith('cpu')&&r.generation!=='cpu89'){
  const gens=['2026','2017','2006','2000','95','92'],i=gens.indexOf(r.generation.slice(3));
  return i<0?[]:gens.slice(i).map(g=>'rate-'+g).concat('vaxen');
 }
 if(r.route==='SPEC89')return ['int89','int92','vaxen'];
 if(['Gibson mix','ADP mix','Combined mixes'].includes(r.route))return ['mixes','classical','mix-model','vaxen'];
 if(r.route==='classical')return ['classical','classic-model','vaxen'];
 return [];
}
function drawLineage(){
 const svg=document.querySelector('#lineage-graph'), chosen=lineageActive;
 let s='<defs><marker id="lineage-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#648398"/></marker></defs>';
 s+='<text x="25" y="30" fill="#516a7a" font-size="18">SPEC rate generations</text><text x="30" y="305" fill="#516a7a" font-size="18">Recovered speed results</text><text x="30" y="475" fill="#516a7a" font-size="18">Sparse, jointly calibrated historical scores</text>';
 for(const e of lineage.edges){const a=lineageNode(e.source),b=lineageNode(e.target);if(!a||!b)continue;
  const active=!chosen||(chosen.includes(e.source)&&chosen.includes(e.target));
  const x=a.x+a.w,y=a.y+a.h/2,xx=b.x,yy=b.y+b.h/2;
  const d=e.source.startsWith('predictor-')?`M${x} ${y}C${x+25} ${y},${xx-25} ${yy},${xx} ${yy}`:y===yy?`M${x} ${y}L${xx} ${yy}`:`M${x} ${y}C${x+65} ${y},${xx-65} ${yy},${xx} ${yy}`;
  const labelX=(x+xx)/2,labelY=y===yy?y-44:(y+yy)/2-12;
  const c=e.kind==='definition'?'#148c80':e.kind==='candidate'?'#a66c3d':'#497e9d';
  s+=`<g role="button" tabindex="0" data-key="${esc(e.id)}" data-type="edge" aria-label="${esc(e.label+' '+a.title+' to '+b.title)}" opacity="${active?1:.16}"><path d="${d}" fill="none" stroke="transparent" stroke-width="22"/><path d="${d}" fill="none" stroke="${c}" stroke-width="2.5" ${e.kind==='candidate'?'stroke-dasharray="7 5"':''} marker-end="url(#lineage-arrow)"/><text x="${labelX}" y="${labelY}" text-anchor="middle" font-size="11" fill="${c}">${esc(e.source.startsWith('predictor-')?'':e.label)}</text><title>${esc(e.label)}</title></g>`;
 }
 for(const n of lineage.nodes){const active=!chosen||chosen.includes(n.id),c=n.kind==='unit'?'#d9f3ed':['model','predictor'].includes(n.kind)?'#e8e6f7':'#fff';
 s+=`<g role="button" tabindex="0" data-key="${esc(n.id)}" data-type="node" aria-label="${esc(n.title)}" opacity="${active?1:.2}"><rect x="${n.x}" y="${n.y}" width="${n.w}" height="${n.h}" rx="14" fill="${c}" stroke="${active&&chosen?'#1c658e':'#bdccd7'}" stroke-width="${active&&chosen?3:1.5}"/><text x="${n.x+12}" y="${n.y+27}" font-size="17" fill="#213b50">${esc(n.title)}</text><text x="${n.x+12}" y="${n.y+49}" font-size="12" fill="#506676">${esc(n.subtitle)}</text>${n.kind==='model'?`<text x="${n.x+12}" y="${n.y+76}" font-size="11" fill="#60567d">Shared anchors · conditional calibration</text>`:''}</g>`;}
 svg.innerHTML=s;
}
function lineageStats(edges){return edges.map(e=>{
 let stats=e.stats||[];
 const generation=/^rate-(95|2000|2006|2017|2026)-to-/.exec(e.id)?.[1];
 if(generation)stats=(lineage.rate_edges?.[matching]||[]).filter(r=>r.generation==='cpu'+generation);
 if(lineageRecord){const mode=modeOf(lineageRecord);stats=stats.filter(s=>!s.mode||s.mode===mode);}
 return `<h4>${esc(e.label)}</h4><p><code>${esc(e.formula)}</code><br>${esc(generation?'Active matching: '+matching+'. Full rate cohort; shared-model bootstrap. Local edge CI95 is separate from full-chain CI95.':e.details)}</p>`+
 (stats.length?'<table><thead><tr><th>Metric / mode</th><th>k · CI95</th></tr></thead><tbody>'+stats.map(r=>`<tr><td>${esc(r.metric||r.mode)}<br>${esc(r.unit)}</td><td>${lineageNumber(r.factor)}<br>${lineageNumber(r.low)}–${lineageNumber(r.high)}${r.groups!==undefined?`<br>${r.groups} groups · ${r.pairs} pairs`:''}${r.error!==undefined?`<br>${esc(r.error_label)}: ${lineageNumber(r.error)}`:''}</td></tr>`).join('')+'</tbody></table>':'')+
 `<p><a href="${esc(e.owner)}">Research / method notes</a> · ${esc(e.status)}</p>`;
 }).join('');}
function openFit(generation,mode,method){
 document.querySelector('#fit-generation').value=generation;
 if(mode)document.querySelector('#fit-mode').value=mode;
 if(method)document.querySelector('#fit-method').value=method;
 document.querySelector('#fit-comparison').open=true;drawFit();
}
function inspectLineage(type,id){
 const predictor=/^predictor-(95|2000|2006|2017|2026)/.exec(id)?.[1];
 const generation=predictor|| (id==='int89-int92'?'cpu89':/^rate-(95|2000|2006|2017|2026)-to-/.exec(id)?.[1]);
 if(generation)openFit(generation==='cpu89'?generation:'cpu'+generation);
 const edge=lineage.edges.find(e=>e.id===id),node=lineageNode(id);
 const edges=type==='edge'?(edge?[edge]:[]):lineage.edges.filter(e=>(e.source===id||e.target===id)&&(!lineageActive||(lineageActive.includes(e.source)&&lineageActive.includes(e.target))));
 document.querySelector('#lineage-card').innerHTML=`<h3>${esc(type==='edge'?edge?.label:node?.title)}</h3><p>${esc(node?.details||'')}</p>`+lineageStats(edges);
}
function traceLineage(r){
 lineageRecord=r;lineageActive=pathway(r);document.querySelector('#lineage').open=true;drawLineage();
 document.querySelector('#lineage-selection').textContent=`${r.system} · ${r.route} · ${modeOf(r)}`;
 const formula=r.estimate_kind==='joint'?'V = k × sqrt(speed × rate); local model then upstream rate chain':r.estimate_kind==='speed'?'V = k × speed; local throughput predictor then upstream rate chain':r.route==='Combined mixes'?'V = geometric mean(kᵢ × scoreᵢ); aligned joint draws for CI95':r.route==='classical'?'V = family-balanced geometric mean(kᵢ × scoreᵢ)':'V = input score × saved calibration factor(s)';
 document.querySelector('#lineage-card').innerHTML=`<h3>${esc(r.system)}</h3><p class="lineage-badge">${esc(r.route)} · ${esc(modeOf(r))}</p><h4>Actual inputs</h4><div>${scoreDetails(r)}</div><p>${esc(formula)}</p><h4>${fmt(r.vaxen)}</h4><p>Calibration CI95<br>${fmt(r.ci95_low)} – ${fmt(r.ci95_high)}</p><p>${esc(r.variants?matching:(r.calibration_scenario||'Saved route calibration'))}<br>${esc(r.limitation)}</p><p><a href="${esc(r.source_url)}">Original source</a></p><p>Select a highlighted arrow for details. CI95 uses the saved joint or chain calibration.</p>`;
 if(['speed','joint'].includes(r.estimate_kind)){document.querySelector('#lineage-selection').textContent+=' · '+estimateLabel(r)+' → highlighted upstream rate path';openFit(r.generation,modeOf(r),r.estimate_kind==='joint'?'equal_geometric':'speed_only');}
 clearSelection();document.querySelector('#lineage').scrollIntoView?.({behavior:'smooth',block:'start'});
}
for(const event of ['click','keydown'])document.querySelector('#lineage-graph').addEventListener(event,e=>{
 if(event==='keydown'&&!['Enter',' '].includes(e.key))return;
 const target=e.target.closest?.('[data-key]')||e.target;if(!target.dataset?.key){if(event==='click')resetLineage();return;}
 if(event==='keydown')e.preventDefault();inspectLineage(target.dataset.type,target.dataset.key);
});
function resetLineage(){lineageActive=null;lineageRecord=null;drawLineage();document.querySelector('#lineage-selection').textContent='Rate, speed and joint calibration pathways';document.querySelector('#lineage-card').innerHTML='<h3>Calibration details</h3><p>Select a node or arrow.</p><p>Joint models share evidence; their intervals are correlated.</p>';}
document.querySelector('#trace-path').addEventListener('click',()=>{if(candidates.length)traceLineage(candidates[active].r);});

function drawPredictorPath(generation,mode,method,fit){
 const panel=document.querySelector('#predictor-path'),legacy=generation==='cpu89';
 if(legacy){panel.innerHTML='<strong>Historical speed bridge</strong><p>SPECint89 speed → SPECint92 speed → rate-VAXen</p>';return;}
 const old={cpu95:'92',cpu2000:'95',cpu2006:'2000',cpu2017:'2006',cpu2026:'2017'}[generation];
 const speed=method!=='rate_only',rate=method!=='speed_only';
 const formula=method==='equal_geometric'?'sqrt(speed × rate)':speed?'speed':'rate';
 panel.innerHTML='<strong>SPEC'+esc(generation.slice(3))+' local predictor · '+esc(mode)+' · '+esc(matching)+'</strong>'+
 '<div class="predictor-flow"><div class="predictor-inputs"><span class="predictor-box '+(speed?'selected':'')+'">Speed'+(speed?' ✓':' (unused)')+'</span><span class="predictor-box '+(rate?'selected':'')+'">Rate'+(rate?' ✓':' (unused)')+'</span></div><span>→</span><span class="predictor-box">'+esc(formula)+' × k</span><span>→</span><span class="predictor-box">SPEC'+old+' rate</span><span>→ upstream rate chain → VAXen</span></div>'+
 '<p>'+ (fit?'Local k = '+lineageNumber(fit.coefficient_older_rate)+'. Full-route k = '+lineageNumber(fit.coefficient_vaxen)+'.':'No supported coefficient for this selection.')+
 '</p><p class="hint">Use the comparison controls below to select a generation and inputs. Rate-only here uses the joint model’s matched cohort; the top rate backbone uses its full cohort. Shared evidence means correlated uncertainty.</p>';
}
function drawFit(){
 const generation=document.querySelector('#fit-generation').value||'cpu2000',legacy=generation==='cpu89';
 const mode=document.querySelector('#fit-mode').value||'peak',method=document.querySelector('#fit-method').value||'equal_geometric';
 document.querySelector('#fit-mode').disabled=legacy;
 document.querySelector('#fit-method').disabled=legacy;
 document.querySelector('#fit-policy').disabled=legacy;
 const policy=matching,experiment=lineage.experiments?.[policy];
 const rows=legacy?(lineage.legacy_fit?.rows||[]):(experiment?.triples||[]).filter(r=>r.new_generation===generation&&r.mode===mode);
 const saved=lineage.legacy_fit?.fit;
 const fit=legacy&&saved?{models:saved.models,processor_configs:'unknown',tuples:saved.pairs,coefficient_older_rate:saved.factor,local_ci95_low:saved.factor_ci95_low,local_ci95_high:saved.factor_ci95_high,model_center_p95_percent:saved.model_center_p95_percent}:experiment?.fits.find(r=>r.new_generation===generation&&r.mode===mode&&r.method===method);
 const older={cpu95:'92',cpu2000:'95',cpu2006:'2000',cpu2017:'2006',cpu2026:'2017'}[generation];
 const xlabel=legacy?'SPECint89 speed':`SPEC${generation.slice(3)} ${method==='speed_only'?'speed':method==='rate_only'?'rate':'sqrt(speed × rate)'} (${mode})`;
 const ylabel=legacy?'SPECint92 speed':`SPEC${older} rate (${mode})`;
 const svg=document.querySelector('#fit-scatter');
 svg.setAttribute('aria-label',xlabel+' versus measured '+ylabel);
 const cohort=legacy?'Historical source pairs · speed only':policy+' · '+mode;
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
 out+=values.map((v,i)=>`<circle cx="${xx(v[0])}" cy="${yy(v[1])}" r="3" fill="#207ca3" opacity=".55"><title>${rows[i].count||1} calibration tuple(s)</title></circle>`).join('');
 svg.innerHTML=out+`</g><text x="350" y="324" text-anchor="middle">${esc(xlabel)} (log scale)</text><text x="75" y="18">Measured ${esc(ylabel)} (log scale)</text>`;
}
for(const id of ['fit-generation','fit-mode','fit-method'])document.querySelector('#'+id).addEventListener('change',drawFit);
document.querySelector('#fit-policy').addEventListener('change',e=>setMatching(e.target.value));
drawFit();drawLineage();
"""
