"""Offline predictor UI; export saved coefficients and aligned historical draws."""

import hashlib
import json
from pathlib import Path

import numpy as np
from cpushowspeed.calibration import ANCHOR
from cpushowspeed.classic_predict import OPTIONS, predict_scores
from cpushowspeed.mix_network import OUTPUT as MIX_OUTPUT
from cpushowspeed.mix_network import TIMELINE_RUN
from cpushowspeed.research_io import read_csv
from cpushowspeed.spec_predictors import RESEARCH as PREDICTOR_RESEARCH

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


def _network(draws, metrics, rows, low_key, high_key, name):
    """Coefficients and aligned log draws of one saved network, after checking draws reproduce its intervals."""
    coefficients = {r["metric"]: float(r["coefficient_vaxen_per_score"]) for r in rows}
    if (
        set(metrics) != set(coefficients)
        or (draws.ndim != 2 or draws.shape[1] != len(metrics) or len(draws) < 100)
        or not np.isfinite(draws).all()
    ):
        raise ValueError("inconsistent historical predictor bundle: " + name)
    by_metric = {r["metric"]: r for r in rows}
    for i, metric in enumerate(metrics):
        low, high = np.quantile(np.exp(draws[:, i]), [0.025, 0.975])
        if not np.allclose(
            [low, high], [float(by_metric[metric][low_key]), float(by_metric[metric][high_key])], rtol=1e-12, atol=0
        ):
            raise ValueError(f"{name} draw column / interval mismatch: {metric}")
    return dict(coefficients=coefficients, draws={m: draws[:, i].tolist() for i, m in enumerate(metrics)})


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
        networks["classical"] = _network(
            archive["linear_clock__with_spec89"], run["metrics"], rows, "factor_ci95_low", "factor_ci95_high", "classical"
        )
    mix_paths = [MIX_OUTPUT / "coefficients.csv", MIX_OUTPUT / "coefficient-log-draws.npz", MIX_OUTPUT / "audit.json"]
    mix_run = next(r for r in json.loads(mix_paths[2].read_text())["runs"] if all(r[k] == v for k, v in TIMELINE_RUN.items()))
    mix_rows = [r for r in read_csv(mix_paths[0]) if all(r[k] == v for k, v in TIMELINE_RUN.items())]
    with np.load(mix_paths[1], allow_pickle=False) as archive:
        networks["mixes"] = _network(
            archive[mix_run["draw_key"]], mix_run["metrics"], mix_rows, "ci95_vaxen_low", "ci95_vaxen_high", "mixes"
        )
    bridge_path = Path("research/data/classic/spec89-rate-bridge-summary.csv")
    summary_path = PREDICTOR_RESEARCH / "summary.csv"
    for path in [*paths, *mix_paths, bridge_path, RATE_CHAIN, summary_path]:
        hashes[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
    legacy = {}
    for row in read_csv(bridge_path):
        generation = {"int89_to_rate92_chained": "cpu89", "int92_to_rate92": "cpu92"}.get(row["edge"])
        if generation:
            # These saved factors already target VAXen, despite historical column labels.
            legacy[generation] = [float(row[key]) for key in ("factor", "factor_ci95_low", "factor_ci95_high")]
    rates = [
        dict(
            generation=r["generation"],
            mode=r["mode"],
            values=[float(r[k]) for k in ("vaxen_per_rate_score", "bootstrap_95_low", "bootstrap_95_high")],
        )
        for r in read_csv(RATE_CHAIN)
        if r["scenario"] == RATE_SCENARIO
    ]
    predictors = [
        dict(
            generation=r["new_generation"],
            mode=r["mode"],
            method=r["method"],
            values=[float(r[k]) for k in ("coefficient_vaxen", "vaxen_ci95_low", "vaxen_ci95_high")],
        )
        for r in read_csv(summary_path)
        if r["status"] == "conditional_fit"
    ]
    return (
        dict(
            historical_inputs=HISTORICAL_INPUTS,
            networks=networks,
            anchor=ANCHOR,
            legacy=legacy,
            rates=rates,
            predictors=predictors,
        ),
        hashes,
    )


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
#calc-result:empty{display:none}#predictor-path{margin:12px 22px;padding:14px;background:white;border:1px solid #bdccd7;border-radius:10px}
.predictor-flow{display:flex;align-items:center;flex-wrap:wrap;gap:10px;padding:10px 0}
.predictor-box{border:1px solid #9cb4c7;background:#edf3f7;padding:10px;border-radius:7px}
.predictor-inputs{display:grid;gap:6px}.predictor-box.selected{border:2px solid #207ca3;background:#e3f1f7}
"""

MARKUP = """
<section id="calculator" aria-labelledby="calc-title">
<h2 id="calc-title">Predict VAXen</h2>
<p>Enter scores for the same machine and configuration. Leave unavailable scores blank. No clock scaling.</p>
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
<label>Scores <select id="calc-mode"><option value="peak">Peak / legacy speed</option><option value="base">Base</option></select></label>
<label>Integer speed <input id="calc-speed" type="number" step="any" min="0" placeholder="Not supplied"></label>
<label>Integer rate <input id="calc-rate" type="number" step="any" min="0" placeholder="Not supplied"></label>
</div><p id="calc-policy" class="hint"></p></div>
<p><label>Year (optional) <input id="calc-year" type="number" min="1" max="9999" step="1" placeholder="e.g. 1985" style="max-width:12em"></label>
<small>Add a year to place a “You are here” marker on the timeline.</small></p>
<p class="calc-actions"><button type="submit">Calculate</button> <button type="button" id="calc-clear">Reset</button></p>
</form>
<div id="calc-result" role="status" aria-live="polite"></div>
<p class="hint">CI95 describes shared calibration uncertainty, not the prediction range for an individual machine.
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
  return `<g role="img" aria-label="${esc(label+' · '+r.year+' · '+fmt(r.values[0]))}">
  <path d="M${x} ${Y(r.values[1])}V${Y(r.values[2])}" stroke="${c}" stroke-width="9" opacity=".2"/>
  <circle cx="${x}" cy="${y}" r="17" fill="white" fill-opacity=".85" stroke="${c}" stroke-width="2"/>
  <circle cx="${x}" cy="${y}" r="9" fill="${c}" stroke="white" stroke-width="2"/>
  <path d="M${x+(right?-16:16)} ${y}L${tx} ${ty+5}" stroke="${c}" stroke-width="2"/>
  <text x="${tx}" y="${ty}" text-anchor="${anchor}" fill="${c}" font-size="18" font-weight="700" stroke="white" stroke-width="5" paint-order="stroke">${esc(label)}</text>
  <text x="${tx}" y="${ty+21}" text-anchor="${anchor}" fill="${c}" font-size="15" stroke="white" stroke-width="4" paint-order="stroke">${r.year} · ${fmt(r.values[0])}</text></g>`;
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
 const point=Math.exp(metrics.reduce((z,m)=>z+weights[m]*(Math.log(scores[m])+Math.log(network.coefficients[m])),0));
 const n=network.draws[metrics[0]].length,draws=Array.from({length:n},(_,i)=>Math.exp(metrics.reduce((z,m)=>z+weights[m]*(Math.log(scores[m])+network.draws[m][i]),0)));
 const values=[point,calcQuantile(draws,.025),calcQuantile(draws,.975)];
 if(!values.every(v=>Number.isFinite(v)&&v>0))throw Error('Result exceeds the supported numeric range.');
 return {label:'Historical estimate',values,details:metrics.map(m=>({metric:m,weight:weights[m],vaxen:scores[m]*network.coefficients[m]})),
  path:metrics.some(m=>m.startsWith('InstructionMix:'))?'Mix + classical joint model → VAXen':'Classical joint model → VAXen'};
}
function specPrediction(generation,mode,speed,rate){
 speed=positiveInput(speed,'Speed');rate=positiveInput(rate,'Rate');
 if(speed===null&&rate===null)throw Error('Enter a speed score, a rate score, or both.');
 if(generation==='cpu89'&&(rate!==null||mode!=='peak'))throw Error('SPEC89 supports native integer speed only.');
 const results=[];
 const product=(score,coefficients,label,path)=>({label,values:coefficients.map(k=>score*Number(k)),path});
 if(['cpu89','cpu92'].includes(generation)){
  if(speed!==null){
   if(mode!=='peak')throw Error('The legacy speed bridge is calibrated only for native / peak scores.');
   results.push(product(speed,calibration.legacy[generation],'Legacy speed estimate','SPECint'+generation.slice(3)+' speed → historical bridge → VAXen'));
  }
  if(rate!==null)results.push(product(rate,[calibration.anchor,calibration.anchor,calibration.anchor],'Defined SPEC92 rate scale','SPEC92 rate × 25500 / 604800'));
  if(results.length===2)for(const r of results)r.note='Separate estimates: no joint SPEC92 speed/rate coefficient is calibrated.';
 }else{
  const method=speed!==null&&rate!==null?'equal_geometric':speed!==null?'speed_only':'backbone';
  const fit=method==='backbone'?calibration.rates.find(r=>r.generation===generation&&r.mode===mode):
   calibration.predictors.find(r=>r.generation===generation&&r.mode===mode&&r.method===method);
  if(!fit||fit.values.some(k=>!Number.isFinite(Number(k))||Number(k)<=0))throw Error('No supported coefficient for this selection: too few hardware-near tuples. Enter the rate score alone.');
  const score=method==='equal_geometric'?Math.exp((Math.log(speed)+Math.log(rate))/2):speed??rate;
  results.push(product(score,fit.values,method==='equal_geometric'?'Joint speed + rate estimate':method==='speed_only'?'Speed-derived estimate':'Rate estimate',
   method==='backbone'?'Rate chain → SPEC92 rate → VAXen':(method==='equal_geometric'?'sqrt(speed × rate)':'speed')+' → local predictor → upstream rate chain → VAXen'));
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
 document.querySelector('#calc-policy').textContent='SPEC95–2026: rate alone uses the saved rate chain; speed alone or speed + rate use the hardware-near predictors. Speed-only estimates of multi-core machines are weak.';
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
  out.innerHTML=results.map(r=>'<h3>'+esc(r.label)+': '+fmt(r.values[0])+'</h3><p>Calibration CI95: '+fmt(r.values[1])+' – '+fmt(r.values[2])+
   '</p><p>'+esc(r.path)+'</p>'+(r.note?'<p>'+esc(r.note)+'</p>':'')+(r.details?'<details><summary>Input weights and individual estimates</summary><ul>'+r.details.map(d=>'<li>'+esc(d.metric)+' · weight '+d.weight.toFixed(3)+' · '+fmt(d.vaxen)+'</li>').join('')+'</ul></details>':'')).join('');
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
