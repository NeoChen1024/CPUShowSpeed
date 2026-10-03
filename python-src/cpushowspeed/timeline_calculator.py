"""Offline predictor UI; export saved coefficients and aligned historical draws.

Historical inputs and SPEC speed give speed-VAXen; SPEC rate gives rate-VAXen.
Speed and rate are separate results and are never combined.
"""

import hashlib
import json
import math
from pathlib import Path

import numpy as np
from cpushowspeed.classic_predict import OPTIONS, predict_scores
from cpushowspeed.mix_network import OUTPUT as MIX_OUTPUT
from cpushowspeed.mix_network import TIMELINE_RUN
from cpushowspeed.research_io import read_csv
from cpushowspeed.spec_speed_chain import INTERVALS as SPEED_CHAIN

CLASSICAL_LABELS = {
    "dhrystone_1_1": "Dhrystone 1.1",
    "dhrystone_2_1": "Dhrystone 2.1",
    "whetstone_sp": "Whetstone SP",
    "whetstone_dp": "Whetstone DP",
    "whetstone_native": "Whetstone Native",
    "linpack_100": "LINPACK N=100",
}
HISTORICAL_INPUTS = [(key, metric, CLASSICAL_LABELS[key], unit) for key, (metric, unit) in OPTIONS.items()] + [
    ("gibson", "InstructionMix:Gibson_KIPS", "Gibson mix", "KIPS"),
    ("adp", "InstructionMix:ADP_KIPS", "ADP mix", "KIPS"),
]
RATE_CHAIN = Path("research/data/spec/fitting/integer-rate-chain-intervals.csv")
RATE_SCENARIO = "same_os"
SPEC89_AUDIT = Path("research/data/classic/spec89-audit.json")


def _network(archive, key, metrics, rows, name):
    """Power-law calibrations and aligned (intercept, exponent) draws of one saved network, after checking the draws
    reproduce its intervals."""
    intercepts, exponents = archive[key + "__intercept"], archive[key + "__exponent"]
    coefficients = {r["metric"]: [math.log(float(r["vaxen_at_unit_score"])), float(r["exponent"])] for r in rows}
    if (
        set(metrics) != set(coefficients)
        or any(d.shape != intercepts.shape or d.ndim != 2 or d.shape[1] != len(metrics) for d in (intercepts, exponents))
        or len(intercepts) < 100
        or not (np.isfinite(intercepts).all() and np.isfinite(exponents).all())
    ):
        raise ValueError("inconsistent historical predictor bundle: " + name)
    by_metric = {r["metric"]: r for r in rows}
    for i, metric in enumerate(metrics):
        saved = [float(by_metric[metric][k]) for k in ("unit_score_ci95_low", "unit_score_ci95_high")]
        saved += [float(by_metric[metric][k]) for k in ("exponent_ci95_low", "exponent_ci95_high")]
        drawn = [*np.exp(np.quantile(intercepts[:, i], [0.025, 0.975])), *np.quantile(exponents[:, i], [0.025, 0.975])]
        if not np.allclose(drawn, saved, rtol=1e-12, atol=0):
            raise ValueError(f"{name} draw column / interval mismatch: {metric}")
    return dict(
        coefficients=coefficients,
        draws={m: [intercepts[:, i].tolist(), exponents[:, i].tolist()] for i, m in enumerate(metrics)},
    )


def calculator_payload():
    """Keep exact draw alignment. Never combine marginal interval endpoints."""
    networks, hashes = {}, {}
    root = Path("data/derived/classic/network-fit")
    paths = [root / "coefficients.csv", root / "coefficient-log-draws.npz", root / "prediction-calibration.json"]
    run = next(
        r for r in json.loads(paths[2].read_text())["runs"] if r["scenario"] == "linear_clock" and r["cohort"] == "with_spec89"
    )
    # Validate the existing CLI bundle contract before embedding its bytes.
    predict_scores({run["metrics"][0]: 1}, root)
    rows = [r for r in read_csv(paths[0]) if r["scenario"] == "linear_clock" and r["cohort"] == "with_spec89"]
    with np.load(paths[1], allow_pickle=False) as archive:
        networks["classical"] = _network(archive, run["draw_key"], run["metrics"], rows, "classical")
    mix_paths = [MIX_OUTPUT / "coefficients.csv", MIX_OUTPUT / "coefficient-log-draws.npz", MIX_OUTPUT / "audit.json"]
    mix_run = next(r for r in json.loads(mix_paths[2].read_text())["runs"] if all(r[k] == v for k, v in TIMELINE_RUN.items()))
    mix_rows = [r for r in read_csv(mix_paths[0]) if all(r[k] == v for k, v in TIMELINE_RUN.items())]
    with np.load(mix_paths[1], allow_pickle=False) as archive:
        networks["mixes"] = _network(archive, mix_run["draw_key"], mix_run["metrics"], mix_rows, "mixes")
    for path in [*paths, *mix_paths, SPEC89_AUDIT, RATE_CHAIN, SPEED_CHAIN]:
        hashes[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
    # The timeline's SPEC89 rows use the bridge's joint-bootstrap interval, so the calculator does too.
    bridge = json.loads(SPEC89_AUDIT.read_text())
    spec89 = [bridge["bridge_factor"], *bridge["bridge_factor_ci95"]]
    rates = [
        dict(
            generation=r["generation"],
            mode=r["mode"],
            values=[float(r[k]) for k in ("vaxen_per_rate_score", "bootstrap_95_low", "bootstrap_95_high")],
        )
        for r in read_csv(RATE_CHAIN)
        if r["scenario"] == RATE_SCENARIO
    ]
    speeds = [
        dict(
            generation=r["generation"],
            mode=r["mode"],
            values=[float(r[k]) for k in ("speed_vaxen_per_score", "bootstrap_95_low", "bootstrap_95_high")],
        )
        for r in read_csv(SPEED_CHAIN)
    ]
    return dict(historical_inputs=HISTORICAL_INPUTS, networks=networks, spec89=spec89, rates=rates, speeds=speeds), hashes


def calculator_markup():
    fields = "".join(
        f'<label>{label} ({unit}) <input id="calc-{key}" type="number" step="any" min="0" placeholder="Not supplied"></label>'
        for key, metric, label, unit in HISTORICAL_INPUTS
    )
    return MARKUP.replace("__HISTORICAL_FIELDS__", fields)


STYLE = """
#calculator{margin:24px 0;padding:20px;border:1px solid #bdccd7;border-radius:12px;background:#f4f6f8;container-type:inline-size}
#calculator h2{margin-top:0}#calc-form{max-width:64rem}
.calc-fields{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px 24px;align-items:start}
#calculator label{display:grid;gap:6px;min-width:0}
#calculator input,#calculator select{display:block;width:100%;min-width:0;max-width:100%;box-sizing:border-box}
#calc-kind{display:flex;flex-wrap:wrap;gap:12px 24px;margin:16px 0;padding:12px;border:1px solid #bdccd7;border-radius:8px}
#calc-kind label{display:flex;align-items:center;gap:8px;cursor:pointer}
#calc-kind input[type="radio"]{width:auto;flex:none;margin:0;accent-color:#207ca3}
#calculator small{display:block;margin-top:6px}
.calc-actions{display:flex;flex-wrap:wrap;gap:10px}
@container (max-width:36rem){.calc-fields{grid-template-columns:minmax(0,1fr)}}
@supports not (container-type:inline-size){@media(max-width:660px){.calc-fields{grid-template-columns:minmax(0,1fr)}}}
#calc-result{margin-top:16px;padding:12px;background:white;border:1px solid #bdccd7}
#calc-result:empty{display:none}
"""

MARKUP = """
<section id="calculator" aria-labelledby="calc-title">
<h2 id="calc-title">Predict VAXen</h2>
<p>Enter scores for the same machine and configuration. Leave unavailable scores blank. No clock scaling.
Historical scores and SPEC speed give speed-VAXen (one job); SPEC rate gives rate-VAXen (throughput).</p>
<form id="calc-form">
<fieldset id="calc-kind"><legend>Inputs</legend>
<label><input type="radio" id="calc-kind-historical" name="calc-kind" value="historical" checked> Classical / Mixes</label>
<label><input type="radio" id="calc-kind-spec" name="calc-kind" value="spec"> SPEC speed / rate</label>
</fieldset>
<div id="calc-historical">
<div class="calc-fields">__HISTORICAL_FIELDS__</div>
<p class="hint">Dhrystone 1.1 / 2.1 use DMIPS; divide Dhrystones/s by 1757 first. Whetstone Native is distinct from SP and DP.
Gibson and ADP mix ratings use CCTA KIPS; adding them selects the classical + mix joint model.</p></div>
<div id="calc-spec" hidden>
<div class="calc-fields">
<label>Generation <select id="calc-generation">
<option value="cpu92">SPEC92</option><option value="cpu89">SPEC89</option><option value="cpu95">SPEC95</option>
<option value="cpu2000">SPEC2000</option><option value="cpu2006">SPEC2006</option>
<option value="cpu2017">SPEC2017</option><option value="cpu2026">SPEC2026</option></select></label>
<label>Scores <select id="calc-mode"><option value="peak">Peak</option><option value="base">Base</option></select></label>
<label>Integer speed <input id="calc-speed" type="number" step="any" min="0" placeholder="Not supplied"></label>
<label>Integer rate <input id="calc-rate" type="number" step="any" min="0" placeholder="Not supplied"></label>
</div><p id="calc-policy" class="hint"></p></div>
<p><label>Year (optional) <input id="calc-year" type="number" min="1" max="9999" step="1" placeholder="e.g. 1985" style="max-width:12em"></label>
<small>Add a year to place a “You are here” marker on the timeline.</small></p>
<p class="calc-actions"><button type="submit">Calculate</button> <button type="button" id="calc-clear">Reset</button></p>
</form>
<div id="calc-result" role="status" aria-live="polite"></div>
<p class="hint">CI95 describes shared calibration uncertainty, not the prediction range for an individual machine.
Speed-VAXen and rate-VAXen both set the VAX-11/780 to 1 but measure different things: one job versus all copies.
Historical inputs use equal family weights, then equal weights within each family. Gibson and ADP share one family.</p>
</section>
"""

SCRIPT = r"""
const calibration=__CALCULATOR_DATA__;

function predictionYear(value){
 if(value===''||value===undefined||value===null)return null;
 const year=Number(value);
 if(!Number.isInteger(year)||year<1||year>9999)throw Error('Year must be a whole number from 1 to 9999.');
 return year;
}
function updatePredictionMarkers(results=[],year=null){
 userPredictions=year===null?[]:results.map(r=>({...r,year}));
 ({xmin,xmax,ymin,ymax}=originalBounds);
 for(const r of userPredictions){
  xmin=Math.min(xmin,r.year-1);xmax=Math.max(xmax,r.year+1);
  ymin=Math.min(ymin,Math.floor(Math.log10(Math.min(...r.values)))-1);
  ymax=Math.max(ymax,Math.ceil(Math.log10(Math.max(...r.values)))+1);
 }
 if(userPredictions.length){
  const pad=Math.max(1,(xmax-xmin)*.025);
  xmin=Math.min(xmin,year-pad);xmax=Math.max(xmax,year+pad);
  viewMin=Math.min(viewMin,year-pad);viewMax=Math.max(viewMax,year+pad);
 }
 const width=Math.min(xmax-xmin,Math.max(1,viewMax-viewMin));
 viewMin=Math.max(xmin,Math.min(viewMin,xmax-width));viewMax=viewMin+width;
 draw();
}
function clearPredictionMarkers(){
 if(userPredictions.length)updatePredictionMarkers();
}
function predictionMarkup(){
 return '<g id="prediction-markers" clip-path="url(#plot-region)" pointer-events="none">'+userPredictions.map((r,i)=>{
  if(r.year<viewMin||r.year>viewMax)return '';
  const x=X(r.year),y=Y(r.values[0]),right=x>725,tx=x+(right?-25:25);
  const ty=Math.max(62,Math.min(651,y-25+i*48)),anchor=right?'end':'start',c='#b34400';
  const label='You are here'+(userPredictions.length>1?' · '+r.label:'');
  return `<g role="img" aria-label="${esc(label+' · '+r.year+' · '+fmt(r.values[0],r.quantity))}">
  <path d="M${x} ${Y(r.values[1])}V${Y(r.values[2])}" stroke="${c}" stroke-width="9" opacity=".2"/>
  <circle cx="${x}" cy="${y}" r="17" fill="white" fill-opacity=".85" stroke="${c}" stroke-width="2"/>
  <circle cx="${x}" cy="${y}" r="9" fill="${c}" stroke="white" stroke-width="2"/>
  <path d="M${x+(right?-16:16)} ${y}L${tx} ${ty+5}" stroke="${c}" stroke-width="2"/>
  <text x="${tx}" y="${ty}" text-anchor="${anchor}" fill="${c}" font-size="18" font-weight="700" stroke="white" stroke-width="5" paint-order="stroke">${esc(label)}</text>
  <text x="${tx}" y="${ty+21}" text-anchor="${anchor}" fill="${c}" font-size="15" stroke="white" stroke-width="4" paint-order="stroke">${r.year} · ${fmt(r.values[0],r.quantity)}</text></g>`;
 }).join('')+'</g>';
}
function calcQuantile(values,p){
 const a=values.slice().sort((a,b)=>a-b),i=(a.length-1)*p,j=Math.floor(i);
 return a[j]+(a[Math.min(j+1,a.length-1)]-a[j])*(i-j);
}
function positiveInput(value,label){
 if(value===''||value===null||value===undefined)return null;
 const n=Number(value);if(!Number.isFinite(n)||n<=0)throw Error(label+' must be finite and greater than zero.');
 return n;
}
function historicalPrediction(scores){
 const metrics=Object.keys(scores);if(!metrics.length)throw Error('Enter at least one benchmark score.');
 for(const m of metrics)positiveInput(scores[m],m);
 const network=calibration.networks[metrics.some(m=>m.startsWith('InstructionMix:'))?'mixes':'classical'];
 const families={};for(const m of metrics){if(!(m in network.coefficients))throw Error('Unsupported benchmark: '+m);const f=m.split(':')[0];families[f]=(families[f]||0)+1;}
 const count=Object.keys(families).length,weights=Object.fromEntries(metrics.map(m=>[m,1/count/families[m.split(':')[0]]]));
 const point=Math.exp(metrics.reduce((z,m)=>z+weights[m]*(network.coefficients[m][0]+network.coefficients[m][1]*Math.log(scores[m])),0));
 const n=network.draws[metrics[0]][0].length,draws=Array.from({length:n},(_,i)=>Math.exp(metrics.reduce((z,m)=>z+weights[m]*(network.draws[m][0][i]+network.draws[m][1][i]*Math.log(scores[m])),0)));
 const values=[point,calcQuantile(draws,.025),calcQuantile(draws,.975)];
 if(!values.every(v=>Number.isFinite(v)&&v>0))throw Error('Result exceeds the supported numeric range.');
 return {label:'Historical estimate',values,details:metrics.map(m=>({metric:m,weight:weights[m],vaxen:Math.exp(network.coefficients[m][0]+network.coefficients[m][1]*Math.log(scores[m]))})),
  quantity:'speed',path:metrics.some(m=>m.startsWith('InstructionMix:'))?'Mix + classical joint model → speed-VAXen':'Classical joint model → speed-VAXen'};
}
function specPrediction(generation,mode,speed,rate){
 speed=positiveInput(speed,'Speed');rate=positiveInput(rate,'Rate');
 if(speed===null&&rate===null)throw Error('Enter a speed score, a rate score, or both.');
 const suite='SPEC'+generation.slice(3),results=[];
 const product=(score,coefficients,label,quantity,path)=>({label,quantity,values:coefficients.map(k=>score*Number(k)),path});
 if(generation==='cpu89'){
  if(rate!==null||mode!=='peak')throw Error('SPEC89 supports native integer speed (SPECint89) only.');
  results.push(product(speed,calibration.spec89,'Speed estimate','speed','SPECint89 → SPECint92 bridge → speed-VAXen'));
 }else{
  const chain=(list,quantity)=>{const fit=list.find(r=>r.generation===generation&&r.mode===mode);
   if(!fit||fit.values.some(k=>!Number.isFinite(Number(k))||Number(k)<=0))throw Error('No supported '+quantity+' coefficient for this selection.');return fit.values;};
  if(speed!==null)results.push(product(speed,chain(calibration.speeds,'speed'),'Speed','speed',
   generation==='cpu92'?'SPECint92 speed = speed-VAXen (VAX-11/780 = 1)':suite+' speed → integer-speed chain → SPECint92 speed'));
  if(rate!==null)results.push(product(rate,chain(calibration.rates,'rate'),'Rate','rate',
   generation==='cpu92'?'SPEC92 rate × 25500 / 604800':suite+' rate → integer-rate chain → SPEC92 rate → rate-VAXen'));
  if(results.length===2)results[1].note='Rate ÷ speed = '+(results[1].values[0]/results[0].values[0]).toPrecision(3)+
   ': a rough diagnostic of effective parallelism, not a combined estimate.';
 }
 if(results.some(r=>!r.values.every(v=>Number.isFinite(v)&&v>0)))throw Error('Result exceeds the supported numeric range.');
 return results;
}
function calculatorView(){
 clearPredictionMarkers();
 const spec=document.querySelector('#calc-kind-spec').checked;
 for(const [key] of calibration.historical_inputs)document.querySelector('#calc-'+key).disabled=spec;
 for(const id of ['calc-speed','calc-rate'])document.querySelector('#'+id).disabled=!spec;
 document.querySelector('#calc-spec').hidden=!spec;document.querySelector('#calc-historical').hidden=spec;
 document.querySelector('#calc-policy').textContent='Speed uses the integer-speed chain (speed-VAXen); rate uses the integer-rate chain (rate-VAXen). Entering both gives two separate results.';
 document.querySelector('#calc-result').innerHTML='';
}
function runCalculator(){
 const out=document.querySelector('#calc-result');clearPredictionMarkers();try{
  const year=predictionYear(document.querySelector('#calc-year').value);
  let results;
  if(document.querySelector('#calc-kind-spec').checked){
   results=specPrediction(document.querySelector('#calc-generation').value||'cpu92',document.querySelector('#calc-mode').value||'peak',
    document.querySelector('#calc-speed').value,document.querySelector('#calc-rate').value);
  }else{
   const scores={};for(const [key,metric,label] of calibration.historical_inputs){const score=positiveInput(document.querySelector('#calc-'+key).value,label);if(score!==null)scores[metric]=score;}
   results=[historicalPrediction(scores)];
  }
  out.innerHTML=results.map(r=>'<h3>'+esc(r.label)+': '+fmt(r.values[0],r.quantity)+'</h3><p>Calibration CI95: '+fmt(r.values[1],r.quantity)+' – '+fmt(r.values[2],r.quantity)+
   '</p><p>'+esc(r.path)+'</p>'+(r.note?'<p>'+esc(r.note)+'</p>':'')+(r.details?'<details><summary>Input weights and individual estimates</summary><ul>'+r.details.map(d=>'<li>'+esc(d.metric)+' · weight '+d.weight.toFixed(3)+' · '+fmt(d.vaxen,r.quantity)+'</li>').join('')+'</ul></details>':'')).join('');
  if(year!==null){updatePredictionMarkers(results,year);plot.scrollIntoView?.({behavior:'smooth',block:'center'});}
 }catch(error){out.textContent=error.message;}
}
document.querySelector('#calc-form').addEventListener('submit',e=>{e.preventDefault();runCalculator();});
for(const id of ['calc-kind','calc-generation','calc-mode'])document.querySelector('#'+id).addEventListener('change',calculatorView);
document.querySelector('#calc-form').addEventListener('input',()=>{document.querySelector('#calc-result').innerHTML='';clearPredictionMarkers();});
document.querySelector('#calc-clear').addEventListener('click',()=>{
 for(const [key] of calibration.historical_inputs)document.querySelector('#calc-'+key).value='';
 for(const id of ['calc-speed','calc-rate','calc-year'])document.querySelector('#'+id).value='';
 calculatorView();
});
calculatorView();
"""
