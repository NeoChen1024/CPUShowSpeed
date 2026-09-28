"""Self-contained offline historical timeline with screen-space point selection."""

import json
from html import escape

from cpushowspeed.timeline_lineage import MARKUP, SCRIPT, STYLE

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


def render_html(rows, output, title=TITLE, lineage=None):
    # Keep rich provenance in JSONL/CSV; share repeated strings in the offline display payload.
    fields = "configuration_id route system cpu clock_mhz os configuration scores year year_low year_high date_method date_notes date_sources vaxen ci95_low ci95_high mode measurement_scope chips cores threads_per_core copies_min copies_max calibration_route uncertainty_scope limitation source_url reported_unit mix_variant evidence_class source_locator generation reported_score benchmark_id calibration_scenario".split()
    strings, indexes, packed = [], {}, []
    for row in rows:
        values = []
        for field in fields:
            value = row.get(field, "")
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)
            if isinstance(value, str):
                if value not in indexes:
                    indexes[value] = len(strings)
                    strings.append(value)
                value = "~" + str(indexes[value])
            values.append(value)
        packed.append(values)
    payload = json.dumps(dict(fields=fields, strings=strings, rows=packed), ensure_ascii=False, separators=(",", ":")).replace(
        "<", "\\u003c"
    )
    output.write_text(
        PAGE.replace("__TITLE__", escape(title))
        .replace("__PAYLOAD__", payload)
        .replace("__LINEAGE_STYLE__", STYLE)
        .replace("__LINEAGE_MARKUP__", MARKUP)
        .replace(
            "__LINEAGE_SCRIPT__",
            SCRIPT.replace(
                "__LINEAGE_DATA__", json.dumps(lineage or {"nodes": [], "edges": []}, ensure_ascii=False).replace("<", "\\u003c")
            ),
        )
        .replace("__BROWSING_TOP__", list_browsing())
        .replace("__BROWSING_BOTTOM__", list_browsing("-bottom"))
    )


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
table{border-collapse:collapse;width:100%}small,.hint{color:#556}.table-tools{margin:20px 0 10px}
#tip{position:fixed;z-index:10;width:340px;max-width:calc(100vw - 36px);max-height:calc(100vh - 24px);
 overflow:auto;background:#fff;border:2px solid #207ca3;border-radius:8px;padding:12px;box-shadow:0 4px 24px #2233;
 pointer-events:none;overflow-wrap:anywhere;font-size:14px;box-sizing:border-box}
#tip.pinned{pointer-events:auto}#tip strong{display:block}#tip p{margin:7px 0}#tip-controls{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}
#tip:not(.pinned) #tip-controls{display:none}[hidden]{display:none!important}#plot{touch-action:pan-y}
__LINEAGE_STYLE__
</style>
<h1>__TITLE__</h1>
__LINEAGE_MARKUP__
<label>Search system, CPU, configuration or benchmark: <input id="q" placeholder="VAX, PDP, LINPACK…"></label>
<fieldset id="scores"><legend>Scores</legend>
<label><input type="checkbox" style="width:auto" data-mode="base" checked> SPEC Base</label>
<label><input type="checkbox" style="width:auto" data-mode="peak" checked> SPEC Peak</label>
<label><input type="checkbox" style="width:auto" data-mode="peak_proxy" checked> Historical estimates</label>
</fieldset>
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
<p class="hint" style="text-align:center">Records per year. Drag the handles to resize the time window; drag its center to move it. Arrow keys adjust focused handles.</p>
<div id="tip" role="region" aria-label="Selected data point" hidden><div id="tip-content"></div>
<div id="tip-controls"><button id="prev" type="button">Previous</button><button id="next" type="button">Next</button>
<button id="close" type="button">Close</button><button id="trace-path" type="button">View calibration path</button></div></div>
__BROWSING_TOP__
<table><thead><tr><th>Year / evidence</th><th>System / configuration</th><th>Route / inputs</th><th>VAXen / CI95</th><th>Sources</th></tr></thead><tbody id="body"></tbody></table>
__BROWSING_BOTTOM__
<script>
const packed=__PAYLOAD__;
const data=packed.rows.map(values=>Object.fromEntries(packed.fields.map((key,i)=>[key,typeof values[i]==='string'?packed.strings[Number(values[i].slice(1))]:values[i]])));
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function fmt(value){const x=Number(value);if(!Number.isFinite(x))return '—';
 const prefixes=['p','n','µ','m','','k','M','G','T','P','E'];
 let e=x===0?0:Math.max(-12,Math.min(18,Math.floor(Math.log10(Math.abs(x))/3)*3));
 let scaled=x/10**e;if(Math.abs(Number(scaled.toFixed(3)))>=1000&&e<18){e+=3;scaled=x/10**e;}
 return `${scaled.toFixed(3)} ${prefixes[(e+12)/3]}VAXen`;}
const plot=document.querySelector('#plot'), tip=document.querySelector('#tip'), overviewPlot=document.querySelector('#overview');
const dated=data.filter(r=>r.year), ymin=Math.floor(Math.log10(Math.min(...data.map(r=>r.ci95_low)))),
 ymax=Math.ceil(Math.log10(Math.max(...data.map(r=>r.ci95_high)))),
 xmin=Math.min(...dated.map(r=>r.year))-1,xmax=Math.max(...dated.map(r=>r.year))+1;
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
function showSelection(){if(!candidates.length){clearSelection();return;}
 const p=candidates[active],r=p.r,c=color(r),m=plot.getScreenCTM(),scale=Math.hypot(m.a,m.b)||1;
 document.querySelector('#highlight').innerHTML=`<path d="${spans(r)}" stroke="${c}" opacity=".75" stroke-width="3" vector-effect="non-scaling-stroke"/>
 <circle cx="${p.x}" cy="${p.y}" r="${10/scale}" fill="white" stroke="${c}" stroke-width="2" vector-effect="non-scaling-stroke"/>
 <circle cx="${p.x}" cy="${p.y}" r="${6/scale}" fill="${c}"/>`;
 tip.hidden=false;tip.classList.toggle('pinned',pinned);tip.style.borderColor=c;
 document.querySelector('#tip-content').innerHTML=`<strong>${esc(r.system)}</strong>
 <p>${esc(r.cpu||'CPU unspecified')} · ${esc(r.route)}</p><p>${esc(configurationDetails(r))}</p>
 <p>${esc(modeOf(r))} · ${esc(r.measurement_scope||'historical proxy')}<br>
 Chips ${esc(r.chips||'?')} · cores ${esc(r.cores||'?')} · threads/core ${esc(r.threads_per_core||'?')} · copies ${esc(r.copies_min||'?')}–${esc(r.copies_max||'?')}</p>
 <p><b>${fmt(r.vaxen)}</b><br>CI95: ${fmt(r.ci95_low)}–${fmt(r.ci95_high)}</p>
 <p>Year: ${esc(r.year)} (${esc(r.year_low)}–${esc(r.year_high)})<br><small>${esc(r.date_method)}</small></p>
 <p><small>${esc(r.scores)}${r.mix_variant?'<br>'+esc(r.mix_variant)+' · '+esc(r.reported_unit):''}<br>${esc(r.calibration_route||r.route)}<br>${esc(r.uncertainty_scope||'conditional calibration CI95')}<br>${esc(r.limitation||'')}<br>${esc(r.date_notes||'')}</small></p><small>${pinned?'Pinned':'Click to pin'} · ${active+1} / ${candidates.length} nearby point${candidates.length===1?'':'s'}</small>`;
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
 <td>${esc(r.route)} · ${esc(modeOf(r))}<br><small>${esc(r.scores)}</small></td><td>${fmt(r.vaxen)}<br><small>${fmt(r.ci95_low)}–${fmt(r.ci95_high)}</small></td>
 <td><a href="${esc(r.source_url)}">Benchmark</a><br>${r.date_sources.split(';').filter(Boolean).map(u=>`<a href="${esc(u)}">Year source</a>`).join(' ')}<br><small>${esc(r.date_notes)}</small></td></tr>`).join('');
}
function draw(){clearSelection();const query=document.querySelector('#q').value.toLowerCase();
 const cohort=data.filter((r,i)=>searchable[i].includes(query)&&enabled.has(r.route)&&enabledModes.has(modeOf(r)));
 filtered=cohort.filter(r=>!r.year||(r.year>=viewMin&&r.year<=viewMax));
 document.querySelector('#count').textContent=`${filtered.length} configurations / source submissions; ${filtered.filter(r=>r.year).length} with estimated years`;
 let s='<defs><clipPath id="plot-region"><rect x="90" y="40" width="1270" height="640"/></clipPath></defs>';for(let y=ymin;y<=ymax;y++){let p=Y(10**y);s+=`<path d="M90 ${p}H1360" stroke="#dde3e8"/><text x="8" y="${p+5}">10^${y} VAXen</text>`;}
 const step=viewMax-viewMin<12?1:5;for(let x=Math.ceil(viewMin/step)*step;x<=viewMax;x+=step)s+=`<path d="M${X(x)} 40V680" stroke="#eee"/><text x="${X(x)-17}" y="710">${x}</text>`;
 points=filtered.filter(r=>r.year).map(r=>({r,x:X(r.year),y:Y(r.vaxen)}));
 // Batch vector geometry per route: all observations retained, without thousands of DOM circles.
 for(const route of routeNames){const ps=points.filter(p=>p.r.route===route);if(!ps.length)continue;const c=color(ps[0].r);
 const intervals=ps.map(p=>spans(p.r)).join(' '),marks=ps.map(p=>`M${p.x-3},${p.y}a3,3 0 1,0 6,0a3,3 0 1,0 -6,0`).join(' ');
 s+=`<g clip-path="url(#plot-region)"><path d="${intervals}" stroke="${c}" fill="none" opacity=".12" stroke-width="2"/><path d="${marks}" fill="${c}" opacity=".45"/></g>`;}
 plot.innerHTML=s+'<g id="highlight" clip-path="url(#plot-region)" pointer-events="none"></g>';indexPoints();renderTable();
 document.querySelector('#range-label').textContent=`${viewMin.toFixed(1)}–${viewMax.toFixed(1)}`;
 const bins=new Map();for(const r of cohort)if(r.year)bins.set(r.year,(bins.get(r.year)||0)+1);
 const maxCount=Math.max(0,...bins.values()),left=overviewX(viewMin),right=overviewX(viewMax);
 let overview=`<text x="90" y="13" font-size="12">Records/year · max ${maxCount} · √ height</text>`;
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
function bindListBrowsing(suffix){
 for(const [id,delta] of [['table-prev',-1],['table-next',1]])document.querySelector('#'+id+suffix).addEventListener('click',()=>{page+=delta;renderTable();});
 document.querySelector('#page-jump'+suffix).addEventListener('submit',e=>{e.preventDefault();const n=Number(document.querySelector('#goto-page'+suffix).value);const max=Math.max(1,Math.ceil(filtered.length/PAGE_SIZE));if(!Number.isInteger(n)||n<1||n>max)return;page=n-1;renderTable();});
 document.querySelector('#sort'+suffix).addEventListener('change',()=>{sortOrder=document.querySelector('#sort'+suffix).value;page=0;renderTable();});
}
browsingSuffixes.forEach(bindListBrowsing);
document.querySelector('#q').addEventListener('input',()=>{page=0;draw();});
__LINEAGE_SCRIPT__
draw();
</script></html>"""
