"""Static HTTP timeline with external Parquet data and screen-space point selection."""

import hashlib
import json
import re
from html import escape
from pathlib import Path

from cpushowspeed import timeline_calculator
from cpushowspeed.timeline_lineage import MARKUP, SCRIPT, STYLE
from cpushowspeed.timeline_storage import WebExport, browser_worker_source

TITLE = "CPUShowSpeed: 70 years of benchmarks measured in VAXen"


def list_browsing(suffix=""):
    """One toolbar template for both ends of the list."""
    return f"""<form id="page-jump{suffix}" class="table-tools" aria-label="List browsing">
<label>Sort list: <select id="sort{suffix}">
<option value="year-asc">Year: oldest first</option><option value="year-desc">Year: newest first</option>
<option value="vaxen-asc">VAXen: low to high</option><option value="vaxen-desc">VAXen: high to low</option>
<option value="name">System name: A–Z</option></select></label>
<button id="table-prev{suffix}" type="button">Previous page</button>
<span id="page-count{suffix}" aria-live="polite"></span>
<button id="table-next{suffix}" type="button">Next page</button>
<label>Goto Page <input id="goto-page{suffix}" type="number" min="1" step="1" value="1" required style="width:6em"></label>
<button id="goto-submit{suffix}" type="submit">Go</button>
</form>"""


def render_html(rows, output, title=TITLE, lineage=None, calculator=None):
    fields = "record_id resource_warning runtime_resources hardware_context resource_basis reported_cpu_count cores_per_chip input_configurations estimate_kind variants matched_rate_variants comparison_keys source_record_ids benchmark_sources configuration_id route system cpu clock_mhz os configuration scores year year_low year_high date_method date_notes date_sources vaxen ci95_low ci95_high mode measurement_scope chips cores threads_per_core copies_min copies_max calibration_route uncertainty_scope limitation source_url reported_unit mix_variant evidence_class source_locator generation reported_score benchmark_id calibration_scenario".split()
    output.parent.mkdir(parents=True, exist_ok=True)
    worker = browser_worker_source()
    export = WebExport(output.parent)
    export.table("records", rows)
    display = []
    for row in rows:
        record = {key: row.get(key, "") for key in fields}
        # Preserve existing UI string rendering; structured relation/resource fields
        # are decoded by the same shared page adapter used before this migration.
        display.append({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v for k, v in record.items()})
    data = export.table("timeline", display)
    page = (
        PAGE.replace("__TITLE__", escape(title))
        .replace("__LINEAGE_STYLE__", STYLE)
        .replace("__LINEAGE_MARKUP__", MARKUP)
        .replace("__LINEAGE_SCRIPT__", SCRIPT.replace("const lineage=__LINEAGE_DATA__;", ""))
        .replace("__CALCULATOR_STYLE__", timeline_calculator.STYLE)
        .replace("__CALCULATOR_MARKUP__", timeline_calculator.calculator_markup())
        .replace("__CALCULATOR_SCRIPT__", timeline_calculator.SCRIPT.replace("const calibration=__CALCULATOR_DATA__;", ""))
        .replace("__BROWSING_TOP__", list_browsing())
        .replace("__BROWSING_BOTTOM__", list_browsing("-bottom"))
    )
    start, end = page.index("<script>"), page.index("</script>")
    script = page[start + len("<script>") : end]
    main = "function mountTimeline({data,lineage,calibration}) {\n" + script + "\n}\n"
    main += "// BOOTSTRAP\n" + (Path(__file__).parent / "web/bootstrap.js").read_text()
    # HTML's script terminator is recognized even inside JS strings/comments.
    main = re.sub(r"</script", r"<\\/script", main, flags=re.I)
    encoded_worker = json.dumps(worker, ensure_ascii=False).replace("<", "\\u003c")
    inline = '<script id="parquet-worker-source" type="application/json">' + encoded_worker + "</script>\n"
    inline += '<script id="timeline-code">' + main + "</script>"
    page = page[:start] + inline + page[end + len("</script>") :]
    css = page[page.index("<style>") + len("<style>") : page.index("</style>")]
    export.finish(
        data,
        lineage or {"nodes": [], "edges": []},
        calculator or {"historical_inputs": []},
        inline_sources={
            name: hashlib.sha256(value.encode()).hexdigest() for name, value in {"worker": worker, "main": main, "css": css}.items()
        },
    )
    output.write_text(page)


PAGE = r"""<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__</title>
<style>
body{font:15px system-ui;margin:24px;color:#223} input,select,button{font:inherit;padding:7px}
input{width:min(36em,85vw)}button{cursor:pointer}svg{width:100%;background:#fafbfd;display:block}
.timeline-chart{width:100%;max-width:min(1440px,calc((75vh - 80px)*1.842105));margin:0 auto}
@supports(height:1svh){.timeline-chart{max-width:min(1440px,calc((75svh - 80px)*1.842105))}}
#plot{height:auto;aspect-ratio:1400/760}#overview{height:80px;touch-action:none;user-select:none;cursor:crosshair}
#overview [data-brush="move"]{cursor:grab}#overview [data-brush="left"],#overview [data-brush="right"]{cursor:ew-resize}
#overview [role="slider"]:focus{outline:none;stroke:#e78a19;stroke-width:3}
.chart{overflow:hidden}td,th{padding:7px;text-align:left;border-bottom:1px solid #ddd;vertical-align:top}
.score-input{display:block;margin:3px 0;overflow-wrap:anywhere}.score-input strong{font-weight:500;color:#223}
table{border-collapse:collapse;width:100%}small,.hint{color:#556}.table-tools{margin:20px 0 10px}
#tip{position:fixed;z-index:10;width:340px;max-width:calc(100vw - 36px);max-height:calc(100vh - 24px);
 overflow:auto;background:#fff;border:2px solid #207ca3;border-radius:8px;padding:12px;box-shadow:0 4px 24px #2233;
 pointer-events:none;overflow-wrap:anywhere;font-size:14px;box-sizing:border-box}
#tip.pinned{pointer-events:auto}#tip strong{display:block}#tip p{margin:7px 0}#tip-controls{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}
#tip:not(.pinned) #tip-controls{display:none}[hidden]{display:none!important}#plot{touch-action:pan-y}
__LINEAGE_STYLE__
__CALCULATOR_STYLE__
</style>
<h1>__TITLE__</h1>
<p id="load-status" role="status">Loading timeline…</p>
<noscript>JavaScript is required to view the timeline.</noscript>
<div id="timeline-app" hidden>
__LINEAGE_MARKUP__
<label>Search system, CPU, configuration or benchmark: <input id="q" placeholder="VAX, PDP, LINPACK…"></label>
<fieldset id="scores"><legend>Scores</legend>
<label><input type="checkbox" style="width:auto" data-mode="base" checked> SPEC Base</label>
<label><input type="checkbox" style="width:auto" data-mode="peak" checked> SPEC Peak</label>
<label><input type="checkbox" style="width:auto" data-mode="peak_proxy" checked> Historical estimates</label>
</fieldset>
<fieldset id="estimates"><legend>Estimates</legend>
<label><input type="checkbox" style="width:auto" data-estimate="baseline" checked> ● Rate baseline / historical</label>
<label><input type="checkbox" style="width:auto" data-estimate="speed"> ▲ From speed</label>
<label><input type="checkbox" style="width:auto" data-estimate="joint"> ◆ From speed + rate</label></fieldset>
<fieldset id="matching"><legend>Matching across SPEC generations</legend>
<label><input type="radio" style="width:auto" id="match-strict" name="matching" value="strict"> Strict</label>
<label><input type="radio" style="width:auto" id="match-ram-aliases" name="matching" value="ram-aliases" checked> RAM + aliases</label>
<label><input type="radio" style="width:auto" id="match-cpu-clock" name="matching" value="cpu-clock"> CPU + clock (cross-platform)</label></fieldset>
<p class="hint">All estimates target rate-VAXen. Speed estimates: SPEC95–2026 submissions. Joint estimates: matched overlap pairs. CI95 is calibration uncertainty, not a prediction interval.</p>
<p id="estimate-status" class="hint"></p>
<fieldset id="routes"><legend>Benchmark routes</legend></fieldset>
<p class="hint">Combined mixes merges available Gibson and ADP estimates. Individual mix views are optional comparisons.</p>
<p>System throughput · not per-core performance</p>
<p id="count" aria-live="polite"></p>
<p>Year: CPU release → system availability → eligible submission date. Undated records remain in the list.</p>
<p class="hint">Hover to inspect · click to pin · scroll to zoom · drag to pan</p>
<p><button id="zoom-in">Zoom in</button> <button id="zoom-out">Zoom out</button> <button id="reset">All years</button>
<button id="early">Early hardware</button> <button id="modern">SPEC era</button> <span id="range-label"></span></p>
<div class="timeline-chart"><div class="chart"><svg id="plot" viewBox="0 0 1400 760" aria-label="Historical VAXen scatterplot"></svg></div>
<svg id="overview" viewBox="0 0 1400 90" preserveAspectRatio="none" aria-label="Record counts and time-range selection"></svg></div>
<p class="hint" style="text-align:center">Displayed points per year. Drag the handles to resize the time window; drag its center to move it. Arrow keys adjust focused handles.</p>
<div id="tip" role="region" aria-label="Selected data point" hidden><div id="tip-content"></div>
<div id="tip-controls"><button id="prev" type="button">Previous</button><button id="next" type="button">Next</button>
<button id="close" type="button">Close</button><button id="trace-path" type="button">View calibration path</button></div></div>
__CALCULATOR_MARKUP__
__BROWSING_TOP__
<table><thead><tr><th>Year / evidence</th><th>System / configuration</th><th>Route / inputs</th><th>VAXen / CI95</th><th>Sources</th></tr></thead><tbody id="body"></tbody></table>
__BROWSING_BOTTOM__
</div>
<script>
for(const r of data)for(const key of ['variants','matched_rate_variants','comparison_keys','source_record_ids','benchmark_sources','runtime_resources','hardware_context','input_configurations']){
 if(typeof r[key]==='string'&&r[key])r[key]=JSON.parse(r[key]);}
let matching='ram-aliases';const enabledEstimates=new Set(['baseline']);
const kind=r=>r.estimate_kind||'baseline';
const estimateLabel=r=>({baseline:'Rate baseline / historical',speed:'From speed',joint:'From speed + rate'}[kind(r)]);
function variant(r){const v=r.variants?.[matching];if(r.variants&&Object.keys(r.variants).length&&!v)return null;
 return v?{...r,vaxen:v[0],ci95_low:v[1],ci95_high:v[2],calibration_scenario:matching,uncertainty_scope:kind(r)==='baseline'&&r.generation!=='cpu92'?'conditional whole-CPU-model rate-chain coefficient CI95':r.uncertainty_scope}:r;}
const relationIndex=new Map();for(const r of data)for(const key of r.comparison_keys||[]){const a=relationIndex.get(key)||[];a.push(r);relationIndex.set(key,a);}
function relatives(r){const keys=new Set(r.comparison_keys||[]);for(const k of [...keys])for(const q of relationIndex.get(k)||[])if(kind(q)==='joint')for(const k2 of q.comparison_keys||[])keys.add(k2);
 const found=new Map();for(const k of keys)for(const q of relationIndex.get(k)||[]){const v=variant(q);if(v)found.set(q.record_id,v);}return [...found.values()];}
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function fmt(value){const x=Number(value);if(!Number.isFinite(x))return '—';
 const prefixes=['p','n','µ','m','','k','M','G','T','P','E'];
 let e=x===0?0:Math.max(-12,Math.min(18,Math.floor(Math.log10(Math.abs(x))/3)*3));
 let scaled=x/10**e;if(Math.abs(Number(scaled.toFixed(3)))>=1000&&e<18){e+=3;scaled=x/10**e;}
 return `${scaled.toFixed(3)} ${prefixes[(e+12)/3]}VAXen`;}
const plot=document.querySelector('#plot'), tip=document.querySelector('#tip'), overviewPlot=document.querySelector('#overview');
const dated=data.filter(r=>r.year);let ymin=Math.floor(Math.log10(data.reduce((m,r)=>Math.min(m,r.ci95_low,...Object.values(r.variants||{}).map(v=>v[1])),Infinity))),
 ymax=Math.ceil(Math.log10(data.reduce((m,r)=>Math.max(m,r.ci95_high,...Object.values(r.variants||{}).map(v=>v[2])),0))),
 xmin=dated.reduce((m,r)=>Math.min(m,r.year),Infinity)-1,xmax=dated.reduce((m,r)=>Math.max(m,r.year),-Infinity)+1;
const originalBounds={xmin,xmax,ymin,ymax};let userPredictions=[];
let viewMin=xmin,viewMax=xmax,page=0;const PAGE_SIZE=200;
const X=x=>90+(x-viewMin)/(viewMax-viewMin)*1270,Y=y=>680-(Math.log10(y)-ymin)/(ymax-ymin)*640;
const palette=['#207ca3','#bd5934','#397947','#7c57a2','#ad7130','#ca4779','#4064ac','#537b79'];
const routeNames=[...new Set(data.map(r=>r.route))],enabled=new Set(routeNames.filter(n=>!routeNames.includes('Combined mixes')||!['Gibson mix','ADP mix'].includes(n)));
const color=r=>palette[routeNames.indexOf(r.route)%palette.length];
const modeOf=r=>r.mode||'peak_proxy';
const configurationDetails=r=>[Number(r.clock_mhz)>0?`clock: ${r.clock_mhz} MHz`:'',r.os,r.configuration].filter(Boolean).join('; ');
let sortOrder='year-asc';
const browsingSuffixes=['','-bottom'];
const enabledModes=new Set(['base','peak','peak_proxy']);
const searchable=data.map(r=>[r.system,r.cpu,r.configuration,r.os,r.scores,r.route,modeOf(r)].join(' ').toLowerCase());
const spans=r=>`M${X(r.year)} ${Y(r.ci95_low)}V${Y(r.ci95_high)} M${X(r.year_low)} ${Y(r.vaxen)}H${X(r.year_high)}`;
let visiblePoints=new Map();
let filtered=data,points=[],candidates=[],active=0,pinned=false,grid=new Map(),drag=null,dragged=false;
function clearSelection(){candidates=[];active=0;pinned=false;tip.hidden=true;tip.classList.remove('pinned');
 document.querySelector('#highlight')?.replaceChildren();}
function screenPoint(p){return new DOMPoint(p.x,p.y).matrixTransform(plot.getScreenCTM());}
function indexPoints(){grid=new Map();const m=plot.getScreenCTM();if(!m)return;
 for(const p of points){const sx=m.a*p.x+m.c*p.y,sy=m.b*p.x+m.d*p.y,key=Math.floor(sx/12)+','+Math.floor(sy/12);
 const cell=grid.get(key)||[];cell.push({p,sx,sy});grid.set(key,cell);}}
function nearby(x,y){const m=plot.getScreenCTM();if(!m)return [];x-=m.e;y-=m.f;
 const gx=Math.floor(x/12),gy=Math.floor(y/12),hits=[];
 for(let i=-1;i<=1;i++)for(let j=-1;j<=1;j++)for(const h of grid.get((gx+i)+','+(gy+j))||[]){
 const d=Math.hypot(h.sx-x,h.sy-y);if(d<=12)hits.push({...h,d});}
 hits.sort((a,b)=>a.d-b.d||a.p.r.configuration_id.localeCompare(b.p.r.configuration_id));
 if(!hits.length)return [];
 return hits.filter(h=>Math.hypot(h.sx-hits[0].sx,h.sy-hits[0].sy)<=6).map(h=>h.p);
}
function positionTip(){if(tip.hidden||!candidates.length)return;
 const p=screenPoint(candidates[active]);const box=tip.getBoundingClientRect();
 let left=p.x+18;if(left+box.width>innerWidth-12)left=p.x-box.width-18;
 tip.style.left=Math.max(12,Math.min(left,innerWidth-box.width-12))+'px';
 tip.style.top=Math.max(12,Math.min(p.y+14,innerHeight-box.height-12))+'px';
}

function scoreDetails(r){
 let scores=r.scores;
 if(typeof scores==='string'){try{scores=JSON.parse(scores);}catch{return esc(scores);}}
 if(!scores||typeof scores!=='object')return '';
 const labels={
  'Dhrystone:v1.1_DMIPS':['Dhrystone 1.1','DMIPS'],
  'Dhrystone:v2.1_DMIPS':['Dhrystone 2.1','DMIPS'],
  'Whetstone:MWIPS':['Whetstone Native','MWIPS'],
  'Whetstone:MWIPS_SP':['Whetstone SP','MWIPS'],
  'Whetstone:MWIPS_DP':['Whetstone DP','MWIPS'],
  'LINPACK:n100_MFLOPS':['LINPACK N=100','MFLOPS'],
  'InstructionMix:Gibson_KIPS':['Gibson Mix','KIPS'],
  'InstructionMix:ADP_KIPS':['ADP Mix','KIPS'],
  'SPECint89':['SPECint89',''],
  'SPECrate_int92':['SPEC92 integer rate',''],
  'SPECrate_base_int92':['SPEC92 integer rate','']
 };
 return Object.entries(scores).map(([key,value])=>{
  let [label,unit]=labels[key]||[key,''];
  const rate=/^CINT(95|2000|2006|2017|2026)rate$/.exec(key);
  const speed=/^CPU(95|2000|2006|2017|2026) integer speed (base|peak)$/.exec(key);
  if(rate)label='SPEC'+rate[1]+' integer rate';
  if(speed)label='SPEC'+speed[1]+' integer speed';
  if(key==='speed'||key==='rate')label=(r.generation||r.route||'SPEC').replace(/^cpu/i,'SPEC')+' integer '+key;
  const number=typeof value==='number'&&Number.isFinite(value)?value.toLocaleString('en-US',{maximumSignificantDigits:6}):String(value);
  return '<span class="score-input"><span>'+esc(label)+':</span> <strong>'+esc(number)+(unit?' '+esc(unit):'')+'</strong></span>';
 }).join('');
}

function resourceDescription(r){
 const count=v=>v!==''&&v!==null&&v!==undefined?esc(v):'not reported';
 function one(q){
  let text=q.reported_cpu_count?'Reported CPU count '+count(q.reported_cpu_count)+' (chip equivalence unverified)':
   'Enabled chips '+count(q.chips)+' · enabled cores '+count(q.cores)+' · hardware threads/core '+count(q.threads_per_core);
  if(q.cores_per_chip)text+=' · chip capacity '+count(q.cores_per_chip)+' cores/chip';
  if(q.resource_warning)text+='<br>'+esc(q.resource_warning);
  const run=q.runtime_resources;
  if(run){text+='<br>'+(run.quantity==='copies'?'Rate copies':'Speed benchmark threads')+': ';
   text+=run.status==='reported'?(String(run.minimum)===String(run.maximum)?count(run.minimum):count(run.minimum)+'–'+count(run.maximum)):
    run.status==='not_collected'?'detail not collected':run.unparsed_values?.length?'unparsed source value: '+run.unparsed_values.map(esc).join(', '):'not reported in parsed table';
   if(run.source_url)text+=' · <a href="'+esc(run.source_url)+'">Runtime source</a>';
  }
  return text;
 }
 if(kind(r)==='joint'&&r.input_configurations)return ['speed','rate'].map(role=>'<b>'+role+' input</b><br>'+one(r.input_configurations[role])).join('<br>');
 if(!r.generation)return 'Historical hardware; runtime concurrency not established';
 return one(r)+(r.hardware_context?'<details><summary>Hardware / software disclosure</summary>'+
 Object.entries(r.hardware_context).filter(([k,v])=>v).map(([k,v])=>'<p><b>'+esc(k)+'</b>: '+esc(v)+'</p>').join('')+'</details>':'');
}
function showSelection(){if(!candidates.length){clearSelection();return;}
 const p=candidates[active],r=p.r,c=color(r),m=plot.getScreenCTM(),scale=Math.hypot(m.a,m.b)||1;
 const related=relatives(r),visible=related.map(q=>visiblePoints.get(q.record_id)).filter(Boolean);
 const connections=visible.length>1?`<path d="${visible.map((q,i)=>(i?'L':'M')+q.x+' '+q.y).join(' ')}" stroke="${c}" fill="none" opacity=".7"/>`:'';
 document.querySelector('#highlight').innerHTML=connections+visible.map(q=>`<path d="${spans(q.r)}" stroke="${c}" opacity=".35"/><path d="${marker(q,5)}" fill="${c}"/>`).join('')+`<path d="${spans(r)}" stroke="${c}" opacity=".75" stroke-width="3" vector-effect="non-scaling-stroke"/>
 <circle cx="${p.x}" cy="${p.y}" r="${10/scale}" fill="white" stroke="${c}" stroke-width="2" vector-effect="non-scaling-stroke"/>
 <circle cx="${p.x}" cy="${p.y}" r="${6/scale}" fill="${c}"/>`;
 tip.hidden=false;tip.classList.toggle('pinned',pinned);tip.style.borderColor=c;
 document.querySelector('#tip-content').innerHTML=`<strong>${esc(r.system)}</strong>
 <p>${esc(r.cpu||'CPU unspecified')} · ${esc(r.route)}</p><p>${esc(configurationDetails(r))}</p>
 <p>${esc(modeOf(r))} · ${esc(r.measurement_scope||'historical proxy')}<br>
 ${resourceDescription(r)}</p>
 <p>${esc(estimateLabel(r))} · ${esc(matching)}<br><b>${fmt(r.vaxen)}</b><br>CI95: ${fmt(r.ci95_low)}–${fmt(r.ci95_high)}</p>
 ${related.length?'<details open><summary>Related estimates</summary>'+related.slice(0,8).map(q=>`<p>${esc(estimateLabel(q))}: <b>${fmt(q.vaxen)}</b><br><small>${esc(q.system)} · CI95 ${fmt(q.ci95_low)}–${fmt(q.ci95_high)}</small></p>${q.matched_rate_variants?.[matching]?`<p>Rate-only — matched cohort: ${fmt(q.matched_rate_variants[matching][0])}<br><small>CI95 ${fmt(q.matched_rate_variants[matching][1])}–${fmt(q.matched_rate_variants[matching][2])}</small></p>`:''}`).join('')+(related.length>8?`<small>${related.length} related rows; first 8 shown</small>`:'')+'</details>':''}
 <p>${(r.benchmark_sources||[r.source_url]).map((u,i)=>`<a href="${esc(u)}">Source ${i+1}</a>`).join(' · ')}</p>
 <p>Year: ${esc(r.year)} (${esc(r.year_low)}–${esc(r.year_high)})<br><small>${esc(r.date_method)}</small></p>
 <p><small>${scoreDetails(r)}${r.mix_variant?'<br>'+esc(r.mix_variant)+' · '+esc(r.reported_unit):''}<br>${esc(r.calibration_route||r.route)}<br>${esc(r.uncertainty_scope||'conditional calibration CI95')}<br>${esc(r.limitation||'')}<br>${esc(r.date_notes||'')}</small></p><small>${pinned?'Pinned':'Click to pin'} · ${active+1} / ${candidates.length} nearby point${candidates.length===1?'':'s'}</small>`;
 document.querySelector('#prev').disabled=document.querySelector('#next').disabled=candidates.length<2;
 positionTip();
}
plot.addEventListener('pointermove',e=>{if(drag){const delta=e.clientX-drag.x;if(!dragged&&Math.abs(delta)<=3)return;dragged=true;const dx=delta/drag.width*(drag.hi-drag.lo);setRange(drag.lo-dx,drag.hi-dx);return;}if(pinned)return;const next=nearby(e.clientX,e.clientY);
 if(next.length===candidates.length&&next.every((p,i)=>p===candidates[i]))return;
 candidates=next;active=0;showSelection();});
plot.addEventListener('pointerleave',()=>{if(!pinned)clearSelection();});
plot.addEventListener('click',e=>{if(dragged){dragged=false;return;}candidates=nearby(e.clientX,e.clientY);active=0;pinned=!!candidates.length;showSelection();});
document.addEventListener('click',e=>{if(pinned&&!plot.contains(e.target)&&!tip.contains(e.target))clearSelection();});
document.addEventListener('keydown',e=>{if(e.key==='Escape')clearSelection();});
for(const [id,delta] of [['prev',-1],['next',1]])document.querySelector('#'+id).addEventListener('click',()=>{
 active=(active+delta+candidates.length)%candidates.length;showSelection();});
document.querySelector('#close').addEventListener('click',clearSelection);
window.addEventListener('resize',()=>{indexPoints();if(pinned)showSelection();else clearSelection();});
window.addEventListener('scroll',()=>{if(pinned)positionTip();else clearSelection();},true);
function renderTable(){const order=sortOrder;
 const rows=[...filtered].sort((a,b)=>{let d=0;
 if(order.startsWith('year')){if(!a.year!==!b.year)return a.year?-1:1;d=(Number(a.year)-Number(b.year))*(order.endsWith('desc')?-1:1);}
 else if(order.startsWith('vaxen'))d=(a.vaxen-b.vaxen)*(order.endsWith('desc')?-1:1);
 return d||a.system.localeCompare(b.system)||a.configuration_id.localeCompare(b.configuration_id);});
 const pages=Math.max(1,Math.ceil(rows.length/PAGE_SIZE));page=Math.max(0,Math.min(page,pages-1));
 for(const suffix of browsingSuffixes){
 document.querySelector('#page-count'+suffix).textContent=`Page ${page+1} / ${pages} · ${rows.length} rows`;
 document.querySelector('#table-prev'+suffix).disabled=page===0;
 document.querySelector('#table-next'+suffix).disabled=page===pages-1;
 document.querySelector('#sort'+suffix).value=sortOrder;
 const goto=document.querySelector('#goto-page'+suffix);goto.max=pages;goto.value=page+1;goto.disabled=rows.length===0;
 document.querySelector('#goto-submit'+suffix).disabled=rows.length===0;
 }
 document.querySelector('#body').innerHTML=rows.slice(page*PAGE_SIZE,(page+1)*PAGE_SIZE).map(r=>`<tr><td>${esc(r.year||'Unknown')}<br><small>${esc(r.date_method)} ${esc(r.year_low)}–${esc(r.year_high)}</small></td>
 <td>${esc(r.system)}${r.cpu?'<br>'+esc(r.cpu):''}<br><small>${esc(configurationDetails(r))}</small></td>
 <td>${esc(r.route)} · ${esc(modeOf(r))}<br>${esc(estimateLabel(r))}<br><small>${scoreDetails(r)}</small></td><td>${fmt(r.vaxen)}<br><small>${fmt(r.ci95_low)}–${fmt(r.ci95_high)}</small></td>
 <td>${(r.benchmark_sources||[r.source_url]).map((u,i)=>`<a href="${esc(u)}">${kind(r)==='joint'?(i===0?'Speed':'Rate'):'Benchmark'}</a>`).join(' · ')}<br>${r.date_sources.split(';').filter(Boolean).map(u=>`<a href="${esc(u)}">Year source</a>`).join(' ')}<br><small>${esc(r.date_notes)}</small></td></tr>`).join('');
}
function marker(p,size){const x=p.x,y=p.y,s=size;if(kind(p.r)==='speed')return `M${x} ${y-s}l${s} ${s*2}h${-s*2}z`;
 if(kind(p.r)==='joint')return `M${x} ${y-s}l${s} ${s}l${-s} ${s}l${-s} ${-s}z`;
 return `M${x-s},${y}a${s},${s} 0 1,0 ${s*2},0a${s},${s} 0 1,0 ${-s*2},0`;}
function draw(){clearSelection();const query=document.querySelector('#q').value.toLowerCase();
 const selected=data.filter((r,i)=>searchable[i].includes(query)&&enabled.has(r.route)&&enabledModes.has(modeOf(r))&&enabledEstimates.has(kind(r)));
 const cohort=selected.map(variant).filter(Boolean);
 document.querySelector('#estimate-status').textContent=`${matching}: ${selected.length-cohort.length} estimates unavailable (no fitted coefficient or admitted pair). Historical routes retain their saved calibration.`;
 filtered=cohort.filter(r=>!r.year||(r.year>=viewMin&&r.year<=viewMax));
 const sourceCount=new Set(filtered.flatMap(r=>(r.source_record_ids||[r.configuration_id]).map(id=>(r.generation||r.route)+':'+id))).size;
 document.querySelector('#count').textContent=`${sourceCount} source records · ${filtered.filter(r=>kind(r)==='joint').length} paired estimates · ${filtered.length} displayed points`;
 let s='<defs><clipPath id="plot-region"><rect x="90" y="40" width="1270" height="640"/></clipPath></defs>';for(let y=ymin;y<=ymax;y++){let p=Y(10**y);s+=`<path d="M90 ${p}H1360" stroke="#dde3e8"/><text x="8" y="${p+5}">10^${y} VAXen</text>`;}
 const step=viewMax-viewMin<12?1:5;for(let x=Math.ceil(viewMin/step)*step;x<=viewMax;x+=step)s+=`<path d="M${X(x)} 40V680" stroke="#eee"/><text x="${X(x)-17}" y="710">${x}</text>`;
 points=filtered.filter(r=>r.year).map(r=>({r,x:X(r.year),y:Y(r.vaxen)}));
 visiblePoints=new Map(points.map(p=>[p.r.record_id,p]));
 // Batch vector geometry per route: all observations retained, without thousands of DOM circles.
 for(const route of routeNames){const ps=points.filter(p=>p.r.route===route);if(!ps.length)continue;const c=color(ps[0].r);
 const intervals=ps.map(p=>spans(p.r)).join(' '),marks=ps.map(p=>marker(p,3)).join(' ');
 s+=`<g clip-path="url(#plot-region)"><path d="${intervals}" stroke="${c}" fill="none" opacity=".12" stroke-width="2"/><path d="${marks}" fill="${c}" opacity=".45"/></g>`;}
 plot.innerHTML=s+'<g id="highlight" clip-path="url(#plot-region)" pointer-events="none"></g>'+predictionMarkup();indexPoints();renderTable();
 document.querySelector('#range-label').textContent=`${viewMin.toFixed(1)}–${viewMax.toFixed(1)}`;
 const bins=new Map();for(const r of cohort)if(r.year)bins.set(r.year,(bins.get(r.year)||0)+1);
 const maxCount=Math.max(0,...bins.values()),left=overviewX(viewMin),right=overviewX(viewMax);
 let overview=`<text x="90" y="13" font-size="12">Points/year · max ${maxCount} · √ height</text>`;
 for(const [yr,n] of bins)overview+=`<path d="M${overviewX(yr)} 65V${65-42*Math.sqrt(n/Math.max(1,maxCount))}" stroke="#829bad" stroke-width="5" pointer-events="none"/>`;
 overview+=`<rect x="90" y="18" width="${left-90}" height="49" fill="#ccd3da" opacity=".5" pointer-events="none"/>
 <rect x="${right}" y="18" width="${1360-right}" height="49" fill="#ccd3da" opacity=".5" pointer-events="none"/>
 <rect data-brush="move" x="${left}" y="18" width="${right-left}" height="49" fill="#207ca318" stroke="#207ca3"/>
 <text x="90" y="84" font-size="13">${xmin}</text><text x="1360" y="84" text-anchor="end" font-size="13">${xmax}</text>`;
 // Keep interactive handles stable across redraws so keyboard focus and pointer capture survive.
 document.querySelector('#overview-content').innerHTML=overview;
 for(const [id,x,value,min,max] of [['brush-left',left,viewMin,xmin,viewMax-1],['brush-right',right,viewMax,viewMin+1,xmax]]){
 const handle=document.querySelector('#'+id);handle.setAttribute('x',x-7);handle.setAttribute('aria-valuenow',value.toFixed(2));
 handle.setAttribute('aria-valuetext',`Year ${value.toFixed(1)}`);handle.setAttribute('aria-valuemin',min);handle.setAttribute('aria-valuemax',max);}

}
function setRange(lo,hi){let width=Math.max(1,Math.min(xmax-xmin,hi-lo));lo=Math.max(xmin,Math.min(lo,xmax-width));viewMin=lo;viewMax=lo+width;page=0;draw();}
function zoom(factor,anchor=(viewMin+viewMax)/2){const fraction=(anchor-viewMin)/(viewMax-viewMin),width=Math.max(1,Math.min(xmax-xmin,(viewMax-viewMin)*factor));setRange(anchor-fraction*width,anchor+(1-fraction)*width);}
plot.addEventListener('wheel',e=>{e.preventDefault();const m=plot.getScreenCTM(),local=new DOMPoint(e.clientX,e.clientY).matrixTransform(m.inverse());
 const fraction=Math.max(0,Math.min(1,(local.x-90)/1270));zoom(Math.exp(Math.max(-.5,Math.min(.5,e.deltaY*.002))),viewMin+fraction*(viewMax-viewMin));},{passive:false});
plot.addEventListener('pointerdown',e=>{if(e.button!==0)return;dragged=false;const m=plot.getScreenCTM();drag={x:e.clientX,lo:viewMin,hi:viewMax,width:1270*Math.hypot(m.a,m.b)};plot.setPointerCapture(e.pointerId);});
plot.addEventListener('pointerup',()=>{drag=null;});plot.addEventListener('pointercancel',()=>{drag=null;dragged=false;});
for(const [id,factor] of [['zoom-in',.5],['zoom-out',2]])document.querySelector('#'+id).addEventListener('click',()=>zoom(factor));
document.querySelector('#reset').addEventListener('click',()=>setRange(xmin,xmax));
document.querySelector('#early').addEventListener('click',()=>setRange(xmin,Math.min(1992,xmax)));
document.querySelector('#modern').addEventListener('click',()=>setRange(Math.max(xmin,1991),xmax));
const overviewX=x=>90+(x-xmin)/(xmax-xmin)*1270;
function overviewYear(e){const local=new DOMPoint(e.clientX,e.clientY).matrixTransform(overviewPlot.getScreenCTM().inverse());
 return Math.max(xmin,Math.min(xmax,xmin+(local.x-90)/1270*(xmax-xmin)));}
let brush=null;
overviewPlot.innerHTML='<g id="overview-content"></g><rect id="brush-left" data-brush="left" role="slider" aria-label="Start year" tabindex="0" y="17" width="14" height="51" rx="3" fill="#fff" fill-opacity=".9" stroke="#207ca3"/><rect id="brush-right" data-brush="right" role="slider" aria-label="End year" tabindex="0" y="17" width="14" height="51" rx="3" fill="#fff" fill-opacity=".9" stroke="#207ca3"/>';
overviewPlot.addEventListener('pointerdown',e=>{if(e.button!==0)return;e.preventDefault();const at=overviewYear(e);
 brush={kind:e.target.dataset.brush||'new',at,lo:viewMin,hi:viewMax};overviewPlot.setPointerCapture(e.pointerId);});
overviewPlot.addEventListener('pointermove',e=>{if(!brush)return;const at=overviewYear(e);
 if(brush.kind==='left')setRange(Math.min(at,brush.hi-1),brush.hi);
 else if(brush.kind==='right')setRange(brush.lo,Math.max(at,brush.lo+1));
 else if(brush.kind==='move'){const dx=at-brush.at;setRange(brush.lo+dx,brush.hi+dx);}
 else setRange(Math.min(brush.at,at),Math.max(brush.at,at));});
overviewPlot.addEventListener('pointerup',()=>{brush=null;});overviewPlot.addEventListener('pointercancel',()=>{brush=null;});
for(const [id,side] of [['brush-left','left'],['brush-right','right']])document.querySelector('#'+id).addEventListener('keydown',e=>{
 const delta={ArrowLeft:-1,ArrowDown:-1,ArrowRight:1,ArrowUp:1}[e.key];if(delta===undefined)return;e.preventDefault();
 if(side==='left')setRange(Math.max(xmin,Math.min(viewMax-1,viewMin+delta)),viewMax);
 else setRange(viewMin,Math.min(xmax,Math.max(viewMin+1,viewMax+delta)));});
document.querySelector('#routes').innerHTML='<legend>Benchmark routes</legend>'+routeNames.map((name,i)=>`<label style="margin-right:14px;color:${palette[i%palette.length]}"><input type="checkbox" style="width:auto" data-route="${esc(name)}" ${enabled.has(name)?'checked':''}> ${esc(name)}</label>`).join('');
document.querySelector('#routes').addEventListener('change',e=>{const name=e.target.dataset.route;if(!name)return;e.target.checked?enabled.add(name):enabled.delete(name);page=0;draw();});
document.querySelector('#scores').addEventListener('change',e=>{const mode=e.target.dataset.mode;if(!mode)return;e.target.checked?enabledModes.add(mode):enabledModes.delete(mode);page=0;draw();});
document.querySelector('#estimates').addEventListener('change',e=>{const k=e.target.dataset.estimate;if(!k)return;e.target.checked?enabledEstimates.add(k):enabledEstimates.delete(k);page=0;draw();});
function setMatching(value){matching=value;for(const p of ['strict','ram-aliases','cpu-clock'])document.querySelector('#match-'+p).checked=p===value;document.querySelector('#fit-policy').value=value;page=0;draw();resetLineage();drawFit();calculatorView();}
document.querySelector('#matching').addEventListener('change',e=>setMatching(e.target.value));
function bindListBrowsing(suffix){
 for(const [id,delta] of [['table-prev',-1],['table-next',1]])document.querySelector('#'+id+suffix).addEventListener('click',()=>{page+=delta;renderTable();});
 document.querySelector('#page-jump'+suffix).addEventListener('submit',e=>{e.preventDefault();const n=Number(document.querySelector('#goto-page'+suffix).value);const max=Math.max(1,Math.ceil(filtered.length/PAGE_SIZE));if(!Number.isInteger(n)||n<1||n>max)return;page=n-1;renderTable();});
 document.querySelector('#sort'+suffix).addEventListener('change',()=>{sortOrder=document.querySelector('#sort'+suffix).value;page=0;renderTable();});
}
browsingSuffixes.forEach(bindListBrowsing);
document.querySelector('#q').addEventListener('input',()=>{page=0;draw();});
__LINEAGE_SCRIPT__
__CALCULATOR_SCRIPT__
draw();
</script></html>"""
