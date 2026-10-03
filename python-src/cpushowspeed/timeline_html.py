"""Static HTTP timeline with external Parquet data and screen-space point selection."""

import hashlib
import json
import re
from html import escape
from pathlib import Path

from cpushowspeed import timeline_calculator, timeline_theme
from cpushowspeed.timeline_lineage import MARKUP, SCRIPT, STYLE
from cpushowspeed.timeline_storage import WebExport, browser_worker_source

TITLE = "CPUShowSpeed: 70 years of benchmarks measured in VAXen"


def list_browsing(suffix=""):
    """One toolbar template for both ends of the list."""
    return f"""<form id="page-jump{suffix}" class="table-tools" aria-label="List browsing">
<label>Sort <select id="sort{suffix}">
<option value="year-asc">Year: oldest first</option><option value="year-desc">Year: newest first</option>
<option value="vaxen-asc">VAXen: low to high</option><option value="vaxen-desc">VAXen: high to low</option>
<option value="name">System name: A–Z</option></select></label>
<button id="table-prev{suffix}" type="button">Previous</button>
<span id="page-count{suffix}" aria-live="polite"></span>
<button id="table-next{suffix}" type="button">Next</button>
<label>Go to page <input id="goto-page{suffix}" type="number" min="1" step="1" value="1" required style="width:6em"></label>
<button id="goto-submit{suffix}" type="submit">Go</button>
</form>"""


def render_html(rows, output, title=TITLE, lineage=None, calculator=None):
    fields = "record_id quantity resource_warning runtime_resources hardware_context resource_basis reported_cpu_count cores_per_chip input_configurations estimate_kind system_id mix_combination source_record_ids benchmark_sources configuration_id route system cpu clock_mhz os configuration scores year year_low year_high date_method date_notes date_sources vaxen ci95_low ci95_high mode measurement_scope chips cores threads_per_core copies_min copies_max calibration_route uncertainty_scope limitation source_url reported_unit evidence_class source_locator generation reported_score benchmark_id calibration_scenario".split()
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
        .replace("__THEME_STYLE__", timeline_theme.stylesheet())
        .replace("__THEME_INIT__", timeline_theme.INIT_SCRIPT)
        .replace("__THEME_PICKER__", timeline_theme.picker())
        .replace("__THEME_CREDITS__", timeline_theme.credits())
        .replace("__LINEAGE_STYLE__", STYLE)
        .replace("__LINEAGE_MARKUP__", MARKUP)
        .replace("__LINEAGE_SCRIPT__", SCRIPT.replace("const lineage=__LINEAGE_DATA__;", ""))
        .replace("__CALCULATOR_STYLE__", timeline_calculator.STYLE)
        .replace("__CALCULATOR_MARKUP__", timeline_calculator.calculator_markup())
        .replace("__CALCULATOR_SCRIPT__", timeline_calculator.SCRIPT.replace("const calibration=__CALCULATOR_DATA__;", ""))
        .replace("__BROWSING_TOP__", list_browsing())
        .replace("__BROWSING_BOTTOM__", list_browsing("-bottom"))
    )
    start = page.index("<script>")
    end = page.index("</script>", start)
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
__THEME_INIT__
<style>
__THEME_STYLE__
body{font:15px system-ui;margin:24px;color:var(--fg);background:var(--bg)}a{color:var(--link)}input,select,button{font:inherit;padding:7px}
input{width:min(36em,85vw)}button{cursor:pointer}svg{width:100%;background:var(--plot-bg);display:block}svg text{fill:var(--fg)}
.subtitle{margin:-6px 0 14px;color:var(--muted)}
.sr-only{position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%);white-space:nowrap}
.toolbar{display:flex;flex-wrap:wrap;align-items:center;gap:8px 16px;margin:0 0 12px}.toolbar input[type=search]{width:min(20em,85vw)}
#quantities{display:flex;gap:14px;border:none;margin:0;padding:0}.toolbar label,#routes label{display:flex;align-items:center;gap:4px}
#filters{position:relative}#filters>summary{cursor:pointer;padding:6px 10px;border:1px solid var(--panel-border);border-radius:6px}
.filters-panel{position:absolute;z-index:20;top:calc(100% + 6px);left:0;width:min(26em,85vw);padding:12px;background:var(--card);
 border:1px solid var(--card-border);border-radius:8px;box-shadow:0 4px 24px var(--shadow)}
.filters-panel fieldset{margin:0 0 10px}.filters-panel label{margin:4px 0}.filters-panel p{margin:6px 0 0}
.view-tools{display:flex;flex-wrap:wrap;align-items:center;gap:6px}#zoom-in,#zoom-out{min-width:2.4em}#range-label{margin-left:4px}
.chart-row{display:flex;flex-wrap:wrap;justify-content:center;align-items:flex-start;gap:12px 16px}
#routes{flex:0 0 170px;margin:0;font-size:14px}#routes label{margin:4px 0}
@media(max-width:900px){#routes{flex-basis:100%;display:flex;flex-wrap:wrap;gap:0 14px}}
.chart-notes{display:flex;flex-wrap:wrap;justify-content:space-between;gap:4px 16px;margin:6px 0 0;font-size:13px}
menu[role=tablist]{display:flex;flex-wrap:wrap;gap:2px;margin:28px 0 0;padding:0;list-style:none;border-bottom:1px solid var(--panel-border)}
menu[role=tablist]>li>a{display:block;padding:8px 16px;color:var(--fg);text-decoration:none;border-bottom:3px solid transparent}
menu[role=tablist]>li[aria-selected=true]>a{border-bottom-color:var(--accent);font-weight:600}.tab-panel{padding-top:4px}
#tip .tip-value{font-size:17px}#tip details{margin:7px 0}
.timeline-chart{flex:1 1 640px;min-width:0;width:100%;max-width:min(1440px,calc((75vh - 80px)*1.842105));margin:0 auto}
@supports(height:1svh){.timeline-chart{max-width:min(1440px,calc((75svh - 80px)*1.842105))}}
#plot{height:auto;aspect-ratio:1400/760}#overview{height:80px;touch-action:none;user-select:none;cursor:crosshair}
#overview [data-brush="move"]{cursor:grab}#overview [data-brush="left"],#overview [data-brush="right"]{cursor:ew-resize}
#overview [role="slider"]:focus{outline:none;stroke:var(--focus);stroke-width:3}
.chart{overflow:hidden}.plot-stack{position:relative;background:var(--plot-bg)}
#plot-canvas{position:absolute;inset:0;width:100%;height:100%;display:block}#plot{position:relative;background:transparent}td,th{padding:7px;text-align:left;border-bottom:1px solid var(--rule);vertical-align:top}
.score-input{display:block;margin:3px 0;overflow-wrap:anywhere}.score-input strong{font-weight:500;color:var(--fg)}
table{border-collapse:collapse;width:100%}small,.hint{color:var(--muted)}.table-tools{margin:20px 0 10px}
#tip{position:fixed;z-index:10;width:340px;max-width:calc(100vw - 36px);max-height:calc(100vh - 24px);
 overflow:auto;background:var(--card);border:2px solid var(--accent);border-radius:8px;padding:12px;box-shadow:0 4px 24px var(--shadow);
 pointer-events:none;overflow-wrap:anywhere;font-size:14px;box-sizing:border-box}
#tip.pinned{pointer-events:auto}#tip strong{display:block}#tip p{margin:7px 0}#tip-controls{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}
#tip:not(.pinned) #tip-controls{display:none}[hidden]{display:none!important}#plot{touch-action:pan-y}
__LINEAGE_STYLE__
__CALCULATOR_STYLE__
</style>
__THEME_PICKER__
<h1><span>__TITLE__</span></h1>
<p class="subtitle">Each point is one benchmark result converted to VAXen: the VAX-11/780 is 1.</p>
<p id="load-status" role="status">Loading timeline…</p>
<noscript>JavaScript is required to view the timeline.</noscript>
<div id="timeline-app" hidden>
<div class="toolbar">
<input id="q" type="search" placeholder="Search systems, CPUs, benchmarks" aria-label="Search systems, CPUs, configurations and benchmarks">
<fieldset id="quantities"><legend class="sr-only">Quantity</legend>
<label title="Throughput: every copy a system runs at once"><input type="checkbox" style="width:auto" data-quantity="rate" checked> ● Rate-VAXen</label>
<label title="Single job: one copy timed alone"><input type="checkbox" style="width:auto" data-quantity="speed" checked> ▲ Speed-VAXen</label></fieldset>
<details id="filters"><summary>Filters</summary><div class="filters-panel">
<fieldset id="scores"><legend>Scores</legend>
<label><input type="checkbox" style="width:auto" data-mode="base" checked> SPEC base</label>
<label><input type="checkbox" style="width:auto" data-mode="peak" checked> SPEC peak</label>
<label><input type="checkbox" style="width:auto" data-mode="peak_proxy" checked> Historical</label>
</fieldset>
<fieldset id="estimates"><legend>Estimates</legend>
<label><input type="checkbox" style="width:auto" data-estimate="baseline" checked> Reported scores</label>
<label><input type="checkbox" style="width:auto" data-estimate="mix_combined" checked> ■ Mixes, combined</label>
<label><input type="checkbox" style="width:auto" data-estimate="mix"> ■ Mixes, single</label></fieldset>
<p class="hint">Combined merges a source row's Gibson and ADP ratings; single ratings are optional comparisons.</p>
<p id="estimate-status" class="hint"></p></div></details>
<span class="view-tools"><button id="reset" type="button">All years</button>
<button id="early" type="button" title="Up to 1992">Early</button><button id="modern" type="button" title="From 1991">SPEC era</button>
<button id="zoom-out" type="button" aria-label="Zoom out">−</button><button id="zoom-in" type="button" aria-label="Zoom in">+</button>
<span id="range-label"></span></span>
</div>
<div class="chart-row">
<div class="timeline-chart"><div class="chart plot-stack"><canvas id="plot-canvas" aria-hidden="true"></canvas><svg id="plot" viewBox="0 0 1400 760" aria-label="Historical VAXen scatterplot"></svg></div>
<svg id="overview" viewBox="0 0 1400 90" preserveAspectRatio="none" aria-label="Record counts and time-range selection"></svg></div>
<fieldset id="routes"><legend>Routes</legend></fieldset>
</div>
<div class="chart-notes"><span id="count" aria-live="polite"></span><span class="hint">Hover to inspect · click to pin · wheel to zoom · drag to pan</span></div>
<p class="chart-notes hint">One value per system or node, not per core. Year: CPU release, else system availability, else submission date; undated rows appear only in the list.</p>
<div id="tip" role="region" aria-label="Selected data point" hidden><div id="tip-content"></div>
<div id="tip-controls"><button id="prev" type="button">Previous</button><button id="next" type="button">Next</button>
<button id="close" type="button">Close</button><button id="trace-path" type="button">View calibration path</button></div></div>
<menu id="tabs" role="tablist" aria-label="Views">
<li role="tab" id="tab-btn-list" aria-controls="tab-list" aria-selected="true"><a href="#tab-list">List</a></li>
<li role="tab" id="tab-btn-calculator" aria-controls="tab-calculator" aria-selected="false"><a href="#tab-calculator">Calculator</a></li>
<li role="tab" id="tab-btn-method" aria-controls="tab-method" aria-selected="false"><a href="#tab-method">Method</a></li>
</menu>
<section id="tab-list" class="tab-panel" role="tabpanel" aria-labelledby="tab-btn-list">
__BROWSING_TOP__
<table><thead><tr><th>Year / evidence</th><th>System / configuration</th><th>Route / inputs</th><th>VAXen / CI95</th><th>Sources</th></tr></thead><tbody id="body"></tbody></table>
__BROWSING_BOTTOM__
</section>
<section id="tab-calculator" class="tab-panel" role="tabpanel" aria-labelledby="tab-btn-calculator" hidden>
__CALCULATOR_MARKUP__
</section>
<section id="tab-method" class="tab-panel" role="tabpanel" aria-labelledby="tab-btn-method" hidden>
__LINEAGE_MARKUP__
</section>
</div>
__THEME_CREDITS__
<script>
for(const r of data)for(const key of ['source_record_ids','benchmark_sources','runtime_resources','hardware_context','input_configurations']){
 if(typeof r[key]==='string'&&r[key])r[key]=JSON.parse(r[key]);}
const enabledEstimates=new Set(['baseline','mix_combined']),enabledQuantities=new Set(['rate','speed']);
const kind=r=>r.estimate_kind||'baseline';
const quantityOf=r=>r.quantity||'speed';
const quantityLabel=r=>quantityOf(r)==='rate'?'Throughput · rate-VAXen':'Single job · speed-VAXen';
const estimateLabel=r=>({baseline:r.generation&&r.generation.startsWith('cpu')&&r.generation!=='cpu89'?'Reported SPEC':'Historical estimate',mix:'Single mix rating',mix_combined:'Combined mixes'}[kind(r)]||kind(r));
// Rows derived from one source result (base/peak, single↔combined mixes) and rows of one resolved system.
const index=(key,r,map)=>{if(!key)return;const a=map.get(key)||[];a.push(r);map.set(key,a);};
const sourceIndex=new Map(),systemIndex=new Map();
for(const r of data){for(const id of r.source_record_ids||[])index(id,r,sourceIndex);index(r.system_id,r,systemIndex);}
function relatives(r){const found=new Map();for(const id of r.source_record_ids||[])for(const q of sourceIndex.get(id)||[])if(q!==r)found.set(q.record_id,q);return [...found.values()];}
function sameSystem(r){const direct=new Set(relatives(r));return (systemIndex.get(r.system_id)||[]).filter(q=>q!==r&&!direct.has(q));}
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function fmt(value,quantity){const x=Number(value);if(!Number.isFinite(x))return '—';
 const prefixes=['p','n','µ','m','','k','M','G','T','P','E'];
 let e=x===0?0:Math.max(-12,Math.min(18,Math.floor(Math.log10(Math.abs(x))/3)*3));
 let scaled=x/10**e;if(Math.abs(Number(scaled.toFixed(3)))>=1000&&e<18){e+=3;scaled=x/10**e;}
 const prefix=prefixes[(e+12)/3];
 if(quantity!=='rate'&&quantity!=='speed')return `${scaled.toFixed(3)} ${prefix}VAXen`;
 return `${scaled.toFixed(3)} ${prefix?prefix+' ':''}${quantity}-VAXen`;}
const plot=document.querySelector('#plot'), tip=document.querySelector('#tip'), overviewPlot=document.querySelector('#overview'), canvas=document.querySelector('#plot-canvas');
const dated=data.filter(r=>r.year);let ymin=Math.floor(Math.log10(data.reduce((m,r)=>Math.min(m,r.ci95_low),Infinity))),
 ymax=Math.ceil(Math.log10(data.reduce((m,r)=>Math.max(m,r.ci95_high),0))),
 xmin=dated.reduce((m,r)=>Math.min(m,r.year),Infinity)-1,xmax=dated.reduce((m,r)=>Math.max(m,r.year),-Infinity)+1;
const originalBounds={xmin,xmax,ymin,ymax};let userPredictions=[];
let viewMin=xmin,viewMax=xmax,page=0;const PAGE_SIZE=200;
const X=x=>90+(x-viewMin)/(viewMax-viewMin)*1270,Y=y=>680-(Math.log10(y)-ymin)/(ymax-ymin)*640;
const palette=[0,1,2,3,4,5,6,7].map(i=>`var(--route-${i})`);
const routeNames=[...new Set(data.map(r=>r.route))],enabled=new Set(routeNames),routeCode=new Map(routeNames.map((n,i)=>[n,i]));
const color=r=>palette[routeCode.get(r.route)%palette.length];
const modeOf=r=>r.mode||'peak_proxy';
// Saved scopes read conditional_<kind>_CI95_not_machine_prediction_interval.
const scopeLabel=r=>{const m=/^conditional_(.+)_CI95_not_machine_prediction_interval$/.exec(r.uncertainty_scope||'');
 return m?m[1].replace(/_/g,' ')+' CI95, not a prediction interval for one machine':r.uncertainty_scope||'calibration CI95';};
const configurationDetails=r=>[Number(r.clock_mhz)>0?`clock: ${r.clock_mhz} MHz`:'',r.os,r.configuration].filter(Boolean).join('; ');
let sortOrder='year-asc';
const browsingSuffixes=['','-bottom'];
const enabledModes=new Set(['base','peak','peak_proxy']);
const searchable=data.map(r=>[r.system,r.cpu,r.configuration,r.os,r.scores,r.route,modeOf(r)].join(' ').toLowerCase());
// Column arrays: filtering, time windows, counts and drawing read these instead of row objects.
const N=data.length,codes=values=>{const names=[...new Set(values)];const map=new Map(names.map((n,i)=>[n,i]));return [names,Uint8Array.from(values,v=>map.get(v))];};
const [kindNames,rowKind]=codes(data.map(kind)),[modeNames,rowMode]=codes(data.map(modeOf)),[quantityNames,rowQuantity]=codes(data.map(quantityOf));
const rowRoute=Uint16Array.from(data,r=>routeCode.get(r.route)),rowShape=Uint8Array.from(data,r=>kind(r).startsWith('mix')?2:quantityOf(r)==='speed'?1:0);
const column=f=>Float64Array.from(data,f),rowYear=column(r=>r.year?Number(r.year):NaN),rowYearLow=column(r=>Number(r.year_low)),rowYearHigh=column(r=>Number(r.year_high));
const rowLog=column(r=>Math.log10(r.vaxen)),rowLogLow=column(r=>Math.log10(r.ci95_low)),rowLogHigh=column(r=>Math.log10(r.ci95_high));
const byYear=Int32Array.from(data.keys()).filter(i=>!Number.isNaN(rowYear[i])).sort((a,b)=>rowYear[a]-rowYear[b]);
// Distinct source records are counted through interned keys and a stamp per key.
const sourceStart=new Int32Array(N+1),sourceKeys=[],sourceCode=new Map();
data.forEach((r,i)=>{sourceStart[i]=sourceKeys.length;for(const id of r.source_record_ids||[r.configuration_id]){const key=(r.generation||r.route)+':'+id;
 if(!sourceCode.has(key))sourceCode.set(key,sourceCode.size);sourceKeys.push(sourceCode.get(key));}});sourceStart[N]=sourceKeys.length;
const sourceSeen=new Uint32Array(sourceCode.size),rowSeen=new Uint32Array(N);let stamp=0;
const spans=r=>`M${X(r.year)} ${Y(r.ci95_low)}V${Y(r.ci95_high)} M${X(r.year_low)} ${Y(r.vaxen)}H${X(r.year_high)}`;
// Built on first use after each draw: hover lookups and related-row highlights.
let visibleCache=null;const visiblePoint=id=>(visibleCache??=new Map(points.map(p=>[p.r.record_id,p]))).get(id);
let filtered=data,filteredIndex=[],points=[],candidates=[],active=0,pinned=false,grid=null,drag=null,dragged=false;
function clearSelection(){candidates=[];active=0;pinned=false;tip.hidden=true;tip.classList.remove('pinned');
 document.querySelector('#highlight')?.replaceChildren();}
function screenPoint(p){return new DOMPoint(p.x,p.y).matrixTransform(plot.getScreenCTM());}
// The screen-space grid is rebuilt lazily, on the first lookup after a draw or resize.
const cellKey=(gx,gy)=>(gx+32768)*65536+gy+32768;
function indexPoints(){grid=null;}
function buildGrid(){grid=new Map();const m=plot.getScreenCTM();if(!m)return;
 for(const p of points){const sx=m.a*p.x+m.c*p.y,sy=m.b*p.x+m.d*p.y,key=cellKey(Math.floor(sx/12),Math.floor(sy/12));
 const cell=grid.get(key);if(cell)cell.push({p,sx,sy});else grid.set(key,[{p,sx,sy}]);}}
function nearby(x,y){const m=plot.getScreenCTM();if(!m)return [];if(!grid)buildGrid();x-=m.e;y-=m.f;
 const gx=Math.floor(x/12),gy=Math.floor(y/12),hits=[];
 for(let i=-1;i<=1;i++)for(let j=-1;j<=1;j++)for(const h of grid.get(cellKey(gx+i,gy+j))||[]){
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
  'SPECint92':['SPECint92 speed',''],
  'SPECbase_int92':['SPECint92 speed',''],
  'SPECrate_int92':['SPEC92 integer rate',''],
  'SPECrate_base_int92':['SPEC92 integer rate','']
 };
 return Object.entries(scores).map(([key,value])=>{
  let [label,unit]=labels[key]||[key,''];
  const rate=/^CINT(95|2000|2006|2017|2026)rate$/.exec(key);
  const speed=/^CINT(95|2000|2006|2017|2026)$/.exec(key);
  if(rate)label='SPEC'+rate[1]+' integer rate';
  if(speed)label='SPEC'+speed[1]+' integer speed';
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
 if(!r.generation)return 'Historical hardware; runtime concurrency not established';
 return one(r)+(r.hardware_context?'<details><summary>Hardware / software disclosure</summary>'+
 Object.entries(r.hardware_context).filter(([k,v])=>v).map(([k,v])=>'<p><b>'+esc(k)+'</b>: '+esc(v)+'</p>').join('')+'</details>':'');
}
function showSelection(){if(!candidates.length){clearSelection();return;}
 const p=candidates[active],r=p.r,c=color(r),m=plot.getScreenCTM(),scale=Math.hypot(m.a,m.b)||1;
 const related=relatives(r),others=[...sameSystem(r)].sort((a,b)=>(a.route===r.route)-(b.route===r.route)),visible=[r,...related].map(q=>visiblePoint(q.record_id)).filter(Boolean);
 const connections=visible.length>1?`<path d="${visible.map((q,i)=>(i?'L':'M')+q.x+' '+q.y).join(' ')}" style="stroke:${c}" fill="none" opacity=".7"/>`:'';
 document.querySelector('#highlight').innerHTML=connections+visible.map(q=>`<path d="${spans(q.r)}" style="stroke:${c}" opacity=".35"/><path d="${marker(q,5)}" style="fill:${c}"/>`).join('')+`<path d="${spans(r)}" style="stroke:${c}" opacity=".75" stroke-width="3" vector-effect="non-scaling-stroke"/>
 <circle cx="${p.x}" cy="${p.y}" r="${10/scale}" style="fill:var(--halo);stroke:${c}" stroke-width="2" vector-effect="non-scaling-stroke"/>
 <circle cx="${p.x}" cy="${p.y}" r="${6/scale}" style="fill:${c}"/>`;
 tip.hidden=false;tip.classList.toggle('pinned',pinned);tip.style.borderColor=c;
 document.querySelector('#tip-content').innerHTML=`<strong>${esc(r.system)}</strong>
 <p class="tip-value"><b>${fmt(r.vaxen,quantityOf(r))}</b><br><small>CI95 ${fmt(r.ci95_low,quantityOf(r))}–${fmt(r.ci95_high,quantityOf(r))}<br>${esc(scopeLabel(r))}</small></p>
 <p>${esc(r.cpu||'CPU unspecified')} · ${esc(r.year||'undated')} <small>(${esc(r.year_low)}–${esc(r.year_high)})</small><br>${esc(r.route)} · ${esc(estimateLabel(r))} · ${esc(modeOf(r))}<br><small>${esc(quantityLabel(r))}</small></p>
 ${related.length?'<details><summary>From the same source results · '+related.length+'</summary>'+related.slice(0,8).map(q=>`<p>${esc(estimateLabel(q))} · ${esc(q.route)} · ${esc(modeOf(q))}: <b>${fmt(q.vaxen,quantityOf(q))}</b><br><small>${esc(q.system)} · CI95 ${fmt(q.ci95_low,quantityOf(q))}–${fmt(q.ci95_high,quantityOf(q))}</small></p>`).join('')+(related.length>8?`<small>${related.length} related rows; first 8 shown</small>`:'')+'</details>':''}
 ${others.length?'<details><summary>Same resolved system · '+others.length+' other row'+(others.length===1?'':'s')+'</summary>'+others.slice(0,8).map(q=>`<p>${esc(q.route)} · ${esc(quantityOf(q))} · ${esc(estimateLabel(q))} · ${esc(modeOf(q))}: <b>${fmt(q.vaxen,quantityOf(q))}</b><br><small>${esc(q.year||'undated')} · CI95 ${fmt(q.ci95_low,quantityOf(q))}–${fmt(q.ci95_high,quantityOf(q))}</small></p>`).join('')+'</details>':''}
 <details><summary>Details</summary><p>${esc(configurationDetails(r))}</p><p>${esc(r.measurement_scope||'historical proxy')}<br>${resourceDescription(r)}</p>
 <p><small>${scoreDetails(r)}${r.mix_combination?'<br>'+esc(r.mix_combination)+' · '+esc(r.reported_unit):''}<br>${esc(r.calibration_route||r.route)}<br>${esc(r.calibration_scenario||'')}<br>${esc(r.limitation||'')}</small></p>
 <p><small>Year method: ${esc(r.date_method)}<br>${esc(r.date_notes||'')}</small></p></details>
 <p>${(r.benchmark_sources||[r.source_url]).map((u,i)=>`<a href="${esc(u)}">Source ${i+1}</a>`).join(' · ')}</p><small>${pinned?'Pinned':'Click to pin'} · ${active+1} / ${candidates.length} nearby point${candidates.length===1?'':'s'}</small>`;
 document.querySelector('#prev').disabled=document.querySelector('#next').disabled=candidates.length<2;
 positionTip();
}
plot.addEventListener('pointermove',e=>{if(drag){const delta=e.clientX-drag.x;if(!dragged&&Math.abs(delta)<=3)return;dragged=true;const dx=delta/drag.width*(drag.hi-drag.lo);setRange(drag.lo-dx,drag.hi-dx);return;}if(pinned)return;const next=nearby(e.clientX,e.clientY);
 if(next.length===candidates.length&&next.every((p,i)=>p===candidates[i]))return;
 candidates=next;active=0;showSelection();});
plot.addEventListener('pointerleave',()=>{if(!pinned)clearSelection();});
plot.addEventListener('click',e=>{if(dragged){dragged=false;return;}candidates=nearby(e.clientX,e.clientY);active=0;pinned=!!candidates.length;showSelection();});
const filters=document.querySelector('#filters');
document.addEventListener('click',e=>{if(pinned&&!plot.contains(e.target)&&!tip.contains(e.target))clearSelection();
 if(filters.open&&!filters.contains(e.target))filters.open=false;});
document.addEventListener('keydown',e=>{if(e.key==='Escape'){clearSelection();filters.open=false;}});
// Views below the chart; the address fragment names the open one.
const tabNames=['list','calculator','method'];
function showTab(name,focus){for(const n of tabNames){const on=n===name,tab=document.querySelector('#tab-btn-'+n);
 tab.setAttribute('aria-selected',String(on));document.querySelector('#tab-'+n).hidden=!on;if(on&&focus)tab.querySelector?.('a')?.focus();}
 if(typeof history==='object')history.replaceState?.(null,'','#tab-'+name);}
document.querySelector('#tabs').addEventListener('click',e=>{const tab=e.target.closest?.('[role=tab]');if(!tab)return;e.preventDefault();showTab(tab.id.slice(8));});
document.querySelector('#tabs').addEventListener('keydown',e=>{const step={ArrowLeft:-1,ArrowRight:1}[e.key],tab=e.target.closest?.('[role=tab]');if(!step||!tab)return;
 e.preventDefault();showTab(tabNames[(tabNames.indexOf(tab.id.slice(8))+step+tabNames.length)%tabNames.length],true);});
if(typeof location==='object'&&tabNames.includes(location.hash.slice(5)))showTab(location.hash.slice(5));
for(const [id,delta] of [['prev',-1],['next',1]])document.querySelector('#'+id).addEventListener('click',()=>{
 active=(active+delta+candidates.length)%candidates.length;showSelection();});
document.querySelector('#close').addEventListener('click',clearSelection);
window.addEventListener('resize',()=>{indexPoints();paintCanvas();if(pinned)showSelection();else clearSelection();});
window.addEventListener('scroll',()=>{if(pinned)positionTip();else clearSelection();},true);
// Global row orders, sorted once per sort key; a page scans one for rows of the current selection.
const orders={};let nameRank=null;
function sortedRows(order){
 if(!nameRank){const byName=[...data.keys()].sort((a,b)=>data[a].system.localeCompare(data[b].system)||data[a].configuration_id.localeCompare(data[b].configuration_id));
  nameRank=new Int32Array(N);byName.forEach((i,k)=>nameRank[i]=k);}
 if(orders[order])return orders[order];
 const sign=order.endsWith('desc')?-1:1,vaxen=data.map(r=>r.vaxen);
 return orders[order]=Int32Array.from(data.keys()).sort((a,b)=>{let d=0;
  if(order.startsWith('year')){const ua=Number.isNaN(rowYear[a]),ub=Number.isNaN(rowYear[b]);if(ua!==ub)return ua?1:-1;if(!ua)d=(rowYear[a]-rowYear[b])*sign;}
  else if(order.startsWith('vaxen'))d=(vaxen[a]-vaxen[b])*sign;
  return d||nameRank[a]-nameRank[b];});
}
let tableTimer=null;
function renderTable(){if(tableTimer!==null){clearTimeout(tableTimer);tableTimer=null;}
 const total=filteredIndex.length,pages=Math.max(1,Math.ceil(total/PAGE_SIZE));page=Math.max(0,Math.min(page,pages-1));
 for(const suffix of browsingSuffixes){
 document.querySelector('#page-count'+suffix).textContent=`Page ${page+1} / ${pages} · ${total} rows`;
 document.querySelector('#table-prev'+suffix).disabled=page===0;
 document.querySelector('#table-next'+suffix).disabled=page===pages-1;
 document.querySelector('#sort'+suffix).value=sortOrder;
 const goto=document.querySelector('#goto-page'+suffix);goto.max=pages;goto.value=page+1;goto.disabled=total===0;
 document.querySelector('#goto-submit'+suffix).disabled=total===0;
 }
 const rows=[],first=page*PAGE_SIZE;let seen=0;
 if(total)for(const i of sortedRows(sortOrder)){if(rowSeen[i]!==stamp)continue;if(seen++>=first)rows.push(data[i]);if(rows.length===PAGE_SIZE)break;}
 document.querySelector('#body').innerHTML=rows.map(r=>`<tr><td>${esc(r.year||'Unknown')}<br><small>${esc(r.date_method)} ${esc(r.year_low)}–${esc(r.year_high)}</small></td>
 <td>${esc(r.system)}${r.cpu?'<br>'+esc(r.cpu):''}<br><small>${esc(configurationDetails(r))}</small></td>
 <td>${esc(r.route)} · ${esc(modeOf(r))}<br>${esc(quantityLabel(r))} · ${esc(estimateLabel(r))}<br><small>${scoreDetails(r)}</small></td><td>${fmt(r.vaxen,quantityOf(r))}<br><small>${fmt(r.ci95_low,quantityOf(r))}–${fmt(r.ci95_high,quantityOf(r))}</small></td>
 <td>${(r.benchmark_sources||[r.source_url]).map(u=>`<a href="${esc(u)}">Benchmark</a>`).join(' · ')}<br>${r.date_sources.split(';').filter(Boolean).map(u=>`<a href="${esc(u)}">Year source</a>`).join(' ')}<br><small>${esc(r.date_notes)}</small></td></tr>`).join('');
}
function marker(p,size){const x=p.x,y=p.y,s=size;
 if(kind(p.r).startsWith('mix'))return `M${x-s} ${y-s}h${s*2}v${s*2}h${-s*2}z`;
 if(quantityOf(p.r)==='speed')return `M${x} ${y-s}l${s} ${s*2}h${-s*2}z`;
 return `M${x-s},${y}a${s},${s} 0 1,0 ${s*2},0a${s},${s} 0 1,0 ${-s*2},0`;}
// The selection without the time window, cached until a filter or the search changes.
let cohort=null;
function selectCohort(query){
 const key=JSON.stringify([query,...[enabled,enabledModes,enabledEstimates,enabledQuantities].map(set=>[...set].sort())]);
 if(cohort&&cohort.key===key)return cohort;
 const on=(names,set)=>names.map(n=>set.has(n)),route=on(routeNames,enabled),mode=on(modeNames,enabledModes),est=on(kindNames,enabledEstimates),qty=on(quantityNames,enabledQuantities);
 const keep=new Uint8Array(N),undated=[],baseline=kindNames.indexOf('baseline');let estimates=0,total=0;
 for(let i=0;i<N;i++)if(route[rowRoute[i]]&&mode[rowMode[i]]&&est[rowKind[i]]&&qty[rowQuantity[i]]&&(!query||searchable[i].includes(query))){
  keep[i]=1;total++;if(rowKind[i]!==baseline)estimates++;if(Number.isNaN(rowYear[i]))undated.push(i);}
 const dated=byYear.filter(i=>keep[i]),bins=new Map();for(const i of dated)bins.set(rowYear[i],(bins.get(rowYear[i])||0)+1);
 return cohort={key,dated,undated,bins,estimates,total};
}
// First position in year order whose year is not below (or, with `after`, not at or below) the value.
const bound=(rows,value,after)=>{let lo=0,hi=rows.length;while(lo<hi){const mid=(lo+hi)>>1,y=rowYear[rows[mid]];if(y<value||(after&&y===value))lo=mid+1;else hi=mid;}return lo;};
// Time window, points, counts and every drawn layer; the table may be deferred while dragging.
function render(deferTable){const started=typeof performance==='object'?performance.now():0;clearSelection();const query=document.querySelector('#q').value.toLowerCase();
 const c=selectCohort(query);
 document.querySelector('#estimate-status').textContent=`${c.estimates} mix estimates and ${c.total-c.estimates} reported rows selected. Mix estimates are correlated with the classical route, not extra evidence.`;
 const visible=c.dated.subarray(bound(c.dated,viewMin,false),bound(c.dated,viewMax,true));
 filteredIndex=[...c.undated,...visible];filtered=filteredIndex.map(i=>data[i]);
 stamp++;let sources=0,rate=0;const rateCode=quantityNames.indexOf('rate');
 for(const i of filteredIndex){rowSeen[i]=stamp;if(rowQuantity[i]===rateCode)rate++;
  for(let k=sourceStart[i];k<sourceStart[i+1];k++)if(sourceSeen[sourceKeys[k]]!==stamp){sourceSeen[sourceKeys[k]]=stamp;sources++;}}
 document.querySelector('#count').textContent=`${filtered.length} points (${rate} rate, ${filtered.length-rate} speed) from ${sources} source records`;
 points=Array.from(visible,i=>({r:data[i],i,x:X(rowYear[i]),y:Y(data[i].vaxen)}));visibleCache=null;indexPoints();
 paintCanvas();
 let s='<defs><clipPath id="plot-region"><rect x="90" y="40" width="1270" height="640"/></clipPath></defs>';for(let y=ymin;y<=ymax;y++)s+=`<text x="8" y="${Y(10**y)+5}">10^${y} VAXen</text>`;
 for(const x of yearTicks())s+=`<text x="${X(x)-17}" y="710">${x}</text>`;
 plot.innerHTML=s+'<g id="highlight" clip-path="url(#plot-region)" pointer-events="none"></g>'+predictionMarkup();
 if(deferTable&&typeof setTimeout==='function'){if(tableTimer!==null)clearTimeout(tableTimer);tableTimer=setTimeout(renderTable,150);}else renderTable();
 document.querySelector('#range-label').textContent=`${viewMin.toFixed(1)}–${viewMax.toFixed(1)}`;
 const maxCount=Math.max(0,...c.bins.values()),left=overviewX(viewMin),right=overviewX(viewMax);
 let overview=`<text x="90" y="13" font-size="12">Points per year (max ${maxCount}, √ scale) · drag to choose years</text>`;
 for(const [yr,n] of c.bins)overview+=`<path d="M${overviewX(yr)} 65V${65-42*Math.sqrt(n/Math.max(1,maxCount))}" style="stroke:var(--overview-bar)" stroke-width="5" pointer-events="none"/>`;
 overview+=`<rect x="90" y="18" width="${left-90}" height="49" style="fill:var(--overview-mask)" pointer-events="none"/>
 <rect x="${right}" y="18" width="${1360-right}" height="49" style="fill:var(--overview-mask)" pointer-events="none"/>
 <rect data-brush="move" x="${left}" y="18" width="${right-left}" height="49" style="fill:var(--accent-wash);stroke:var(--accent)"/>
 <text x="90" y="84" font-size="13">${xmin}</text><text x="1360" y="84" text-anchor="end" font-size="13">${xmax}</text>`;
 // Keep interactive handles stable across redraws so keyboard focus and pointer capture survive.
 document.querySelector('#overview-content').innerHTML=overview;
 for(const [id,x,value,min,max] of [['brush-left',left,viewMin,xmin,viewMax-1],['brush-right',right,viewMax,viewMin+1,xmax]]){
 const handle=document.querySelector('#'+id);handle.setAttribute('x',x-7);handle.setAttribute('aria-valuenow',value.toFixed(2));
 handle.setAttribute('aria-valuetext',`Year ${value.toFixed(1)}`);handle.setAttribute('aria-valuemin',min);handle.setAttribute('aria-valuemax',max);}
 // Visible in browser performance tools as a User Timing measure.
 if(started)performance.measure?.('timeline render',{start:started});
}
function yearTicks(){const step=viewMax-viewMin<12?1:5,out=[];for(let x=Math.ceil(viewMin/step)*step;x<=viewMax;x+=step)out.push(x);return out;}
function draw(){if(frame!==null){cancelAnimationFrame(frame);frame=null;}render(false);}
// Pointer, wheel and brush changes coalesce into one render per animation frame.
let frame=null;
function requestDraw(){if(typeof requestAnimationFrame!=='function'){render(false);return;}
 if(frame===null)frame=requestAnimationFrame(()=>{frame=null;render(true);});}
// Theme colours for the canvas, reread when the theme or system preference changes.
let themeColors=null;
function colors(){if(themeColors)return themeColors;const style=typeof getComputedStyle==='function'?getComputedStyle(canvas):null;
 const v=(name,fallback)=>style?.getPropertyValue('--'+name).trim()||fallback;
 return themeColors={bg:v('plot-bg','#fafbfd'),grid:v('grid','#dde3e8'),minor:v('grid-minor','#eee'),interval:Number(v('interval-alpha','.12')),
  point:Number(v('point-alpha','.45')),routes:palette.map((_,i)=>v('route-'+i,'#888'))};}
window.addEventListener('themechange',()=>{themeColors=null;paintCanvas();});
// Grid, intervals and markers in viewBox units on a canvas sized to device pixels.
// Each route's intervals and markers are painted opaque on an offscreen layer and composited
// with the theme alpha: overlaps within a route do not darken (as one translucent SVG path),
// while a translucent stroke over tens of thousands of overlapping segments would be very slow.
let layer=null;
function offscreen(w,h){const c=layer?.canvas||document.createElement?.('canvas');if(!c)return null;
 if(c.width!==w)c.width=w;if(c.height!==h)c.height=h;return layer??={canvas:c,ctx:c.getContext('2d')};}
function paintCanvas(){const ctx=canvas.getContext?.('2d');if(!ctx)return;
 const box=canvas.getBoundingClientRect(),ratio=window.devicePixelRatio||1,w=Math.max(1,Math.round(box.width*ratio)),h=Math.max(1,Math.round(box.height*ratio));
 if(canvas.width!==w)canvas.width=w;if(canvas.height!==h)canvas.height=h;
 const theme=colors(),view=[w/1400,0,0,h/760,0,0];ctx.setTransform(...view);ctx.globalAlpha=1;ctx.fillStyle=theme.bg;ctx.fillRect(0,0,1400,760);
 ctx.lineWidth=1;ctx.strokeStyle=theme.grid;ctx.beginPath();for(let y=ymin;y<=ymax;y++){const p=Y(10**y);ctx.moveTo(90,p);ctx.lineTo(1360,p);}ctx.stroke();
 ctx.strokeStyle=theme.minor;ctx.beginPath();for(const x of yearTicks()){ctx.moveTo(X(x),40);ctx.lineTo(X(x),680);}ctx.stroke();
 const off=offscreen(w,h);
 function composite(alpha,paint){
  if(!off){ctx.save();ctx.beginPath();ctx.rect(90,40,1270,640);ctx.clip();ctx.globalAlpha=alpha;paint(ctx);ctx.restore();return;}
  const g=off.ctx;g.setTransform(1,0,0,1,0,0);g.clearRect(0,0,w,h);g.setTransform(...view);g.save();g.beginPath();g.rect(90,40,1270,640);g.clip();paint(g);g.restore();
  ctx.setTransform(1,0,0,1,0,0);ctx.globalAlpha=alpha;ctx.drawImage(off.canvas,0,0);ctx.globalAlpha=1;ctx.setTransform(...view);}
 const groups=routeNames.map(()=>[]);for(const p of points)groups[rowRoute[p.i]].push(p);
 const scaleY=640/(ymax-ymin),yOf=l=>680-(l-ymin)*scaleY,s=3,CHUNK=512;
 groups.forEach((group,route)=>{if(!group.length)return;const color=theme.routes[route%theme.routes.length];
  composite(theme.interval,g=>{g.strokeStyle=color;g.lineWidth=2;
   for(let k=0;k<group.length;k+=CHUNK){g.beginPath();for(let n=k;n<Math.min(k+CHUNK,group.length);n++){const {i,x}=group[n],y=yOf(rowLog[i]);
    g.moveTo(x,yOf(rowLogLow[i]));g.lineTo(x,yOf(rowLogHigh[i]));g.moveTo(X(rowYearLow[i]),y);g.lineTo(X(rowYearHigh[i]),y);}g.stroke();}});
  composite(theme.point,g=>{g.fillStyle=color;
   for(let k=0;k<group.length;k+=CHUNK){g.beginPath();for(let n=k;n<Math.min(k+CHUNK,group.length);n++){const {i,x,y}=group[n],shape=rowShape[i];
    if(shape===0){g.moveTo(x+s,y);g.arc(x,y,s,0,2*Math.PI);}
    else if(shape===1){g.moveTo(x,y-s);g.lineTo(x+s,y+s);g.lineTo(x-s,y+s);g.closePath();}
    else{g.moveTo(x-s,y-s);g.lineTo(x+s,y-s);g.lineTo(x+s,y+s);g.lineTo(x-s,y+s);g.closePath();}}g.fill();}});});
}
function setRange(lo,hi){let width=Math.max(1,Math.min(xmax-xmin,hi-lo));lo=Math.max(xmin,Math.min(lo,xmax-width));viewMin=lo;viewMax=lo+width;page=0;requestDraw();}
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
overviewPlot.innerHTML='<g id="overview-content"></g><rect id="brush-left" data-brush="left" role="slider" aria-label="Start year" tabindex="0" y="17" width="14" height="51" rx="3" style="fill:var(--card);stroke:var(--accent)" fill-opacity=".9"/><rect id="brush-right" data-brush="right" role="slider" aria-label="End year" tabindex="0" y="17" width="14" height="51" rx="3" style="fill:var(--card);stroke:var(--accent)" fill-opacity=".9"/>';
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
document.querySelector('#routes').innerHTML='<legend>Routes</legend>'+routeNames.map((name,i)=>`<label style="color:${palette[i%palette.length]}"><input type="checkbox" style="width:auto" data-route="${esc(name)}" ${enabled.has(name)?'checked':''}> ${esc(name)}</label>`).join('');
document.querySelector('#routes').addEventListener('change',e=>{const name=e.target.dataset.route;if(!name)return;e.target.checked?enabled.add(name):enabled.delete(name);page=0;draw();});
document.querySelector('#scores').addEventListener('change',e=>{const mode=e.target.dataset.mode;if(!mode)return;e.target.checked?enabledModes.add(mode):enabledModes.delete(mode);page=0;draw();});
document.querySelector('#quantities').addEventListener('change',e=>{const q=e.target.dataset.quantity;if(!q)return;e.target.checked?enabledQuantities.add(q):enabledQuantities.delete(q);page=0;draw();});
document.querySelector('#estimates').addEventListener('change',e=>{const k=e.target.dataset.estimate;if(!k)return;e.target.checked?enabledEstimates.add(k):enabledEstimates.delete(k);page=0;draw();});
function bindListBrowsing(suffix){
 for(const [id,delta] of [['table-prev',-1],['table-next',1]])document.querySelector('#'+id+suffix).addEventListener('click',()=>{page+=delta;renderTable();});
 document.querySelector('#page-jump'+suffix).addEventListener('submit',e=>{e.preventDefault();const n=Number(document.querySelector('#goto-page'+suffix).value);const max=Math.max(1,Math.ceil(filtered.length/PAGE_SIZE));if(!Number.isInteger(n)||n<1||n>max)return;page=n-1;renderTable();});
 document.querySelector('#sort'+suffix).addEventListener('change',()=>{sortOrder=document.querySelector('#sort'+suffix).value;page=0;renderTable();});
}
browsingSuffixes.forEach(bindListBrowsing);
// Typing settles for 120 ms before the selection is recomputed.
let searchTimer=null;
document.querySelector('#q').addEventListener('input',()=>{page=0;if(typeof setTimeout!=='function'){draw();return;}
 clearTimeout(searchTimer);searchTimer=setTimeout(draw,120);});
__LINEAGE_SCRIPT__
__CALCULATOR_SCRIPT__
draw();
</script></html>"""
