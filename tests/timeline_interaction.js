// Run generated page logic in a minimal DOM model; no browser or network access.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync(process.argv[2],'utf8');
const script=html.match(/<script>([\s\S]*?)<\/script>/)[1];
class Element {
 constructor(){this.value='';this.innerHTML='';this.hidden=false;this.style={};this.events={};this.classes=new Set();
 this.classList={add:x=>this.classes.add(x),remove:x=>this.classes.delete(x),toggle:(x,b)=>b?this.classes.add(x):this.classes.delete(x)};}
 addEventListener(t,f){this.events[t]=f;}
 setAttribute(key,value){this[key]=String(value);}
 replaceChildren(){this.innerHTML='';}
 contains(e){return e===this;}
 getBoundingClientRect(){return {width:340,height:260};}
 getScreenCTM(){return {a:scale,b:0,c:0,d:scale,e:20,f:10,inverse(){return {a:1/scale,b:0,c:0,d:1/scale,e:-20/scale,f:-10/scale};}};}
 setPointerCapture(){}
}
let scale=1;
const elements=Object.fromEntries([...html.matchAll(/id="([^"]+)"/g)].map(m=>m[1]).concat(['highlight']).map(k=>['#'+k,new Element()]));
elements['#sort'].value='year-asc';
const document={events:{},querySelector:s=>elements[s],addEventListener(t,f){this.events[t]=f;}};
const window={events:{},addEventListener(t,f){this.events[t]=f;}};
class DOMPoint{constructor(x,y){this.x=x;this.y=y;}matrixTransform(m){return {x:this.x*m.a+this.y*m.c+m.e,y:this.x*m.b+this.y*m.d+m.f};}}
const context=vm.createContext({document,window,DOMPoint,innerWidth:1500,innerHeight:900,assert,elements,
 reference:process.argv[4]?JSON.parse(fs.readFileSync(process.argv[4],'utf8')):null,setScale:s=>scale=s});
if(process.argv[3]==='full'){
 vm.runInContext(script+`
 assert.equal(data.filter(r=>kind(r)==='baseline').length,61070);
 assert.equal(filtered.length,60710);
 assert.equal((elements['#body'].innerHTML.match(/<tr>/g)||[]).length,200);
 const baselineCount=filtered.length;
 elements['#estimates'].events.change({target:{dataset:{estimate:'speed'},checked:true}});
 assert(filtered.length>baselineCount);
 assert.equal(matching,'ram-aliases');setMatching('strict');
 const missingStrict=data.find(r=>kind(r)==='speed'&&r.generation==='cpu2000');assert(missingStrict&&!variant(missingStrict));
 setMatching('ram-aliases');assert(variant(missingStrict));
 elements['#estimates'].events.change({target:{dataset:{estimate:'joint'},checked:true}});
 const paired=points.find(p=>kind(p.r)==='joint'&&p.r.generation==='cpu2000');assert(paired);
 candidates=[paired];active=0;pinned=true;showSelection();assert(elements['#tip-content'].innerHTML.includes('matched cohort'));
 assert(relatives(paired.r).some(r=>kind(r)==='speed'));assert(relatives(paired.r).some(r=>kind(r)==='baseline'));
 assert(marker(paired,3).endsWith('z'));
 traceLineage(paired.r);assert(lineageActive.includes('predictor-2000'));assert(lineageActive.includes('rate-95'));assert(!lineageActive.includes('rate-2000'));
 assert(elements['#fit-comparison'].open);assert(elements['#fit-stats'].textContent.includes('3 CPU models'));
 assert(resourceDescription(paired.r).includes('speed input'));assert(resourceDescription(paired.r).includes('rate input'));
 const withThreads=data.find(r=>kind(r)==='speed'&&r.runtime_resources?.status==='reported');
 assert(withThreads&&resourceDescription(withThreads).includes('Speed benchmark threads'));
 assert.equal(withThreads.runtime_resources.quantity,'threads');
 const missingDetail=data.find(r=>r.runtime_resources?.status==='not_collected');
 assert(resourceDescription(missingDetail).includes('detail not collected'));
 const legacyCount=data.find(r=>r.generation==='cpu92'&&r.reported_cpu_count);
 assert(resourceDescription(legacyCount).includes('chip equivalence unverified'));
 const disputed=data.find(r=>r.resource_warning);assert(disputed);
 assert(resourceDescription(disputed).includes('topology requires review'));
 const pairIDs=data.filter(r=>kind(r)==='joint').map(r=>r.record_id);assert.equal(new Set(pairIDs).size,pairIDs.length);
 setMatching('cpu-clock');assert(elements['#fit-stats'].textContent.includes('72 tuples'));
 elements['#estimates'].events.change({target:{dataset:{estimate:'speed'},checked:false}});
 elements['#estimates'].events.change({target:{dataset:{estimate:'joint'},checked:false}});
 setMatching('strict');assert.equal(filtered.length,baselineCount);
 for(const generation of ['cpu95','cpu2000','cpu2006','cpu2017','cpu2026']){
  for(const mode of ['base','peak'])for(const method of ['speed_only','rate_only','equal_geometric']){
   openFit(generation,mode,method);
   const expected=lineage.experiments.strict.triples.filter(r=>r.new_generation===generation&&r.mode===mode);
   assert.equal((elements['#fit-scatter'].innerHTML.match(/<circle /g)||[]).length,expected.length);
   assert(!/NaN|Infinity/.test(elements['#fit-scatter'].innerHTML));
   assert(elements['#fit-scatter']['aria-label'].includes('SPEC'+generation.slice(3)));
  }
 }
 inspectLineage('edge','rate-2026-to-2017');assert.equal(elements['#fit-generation'].value,'cpu2026');
 setMatching('cpu-clock');assert(elements['#fit-stats'].textContent.startsWith('cpu-clock'));
 inspectLineage('edge','int89-int92');
 assert.equal(elements['#fit-generation'].value,'cpu89');
 assert(elements['#fit-mode'].disabled&&elements['#fit-method'].disabled);
 assert.equal((elements['#fit-scatter'].innerHTML.match(/<circle /g)||[]).length,17);
 assert(elements['#fit-scatter'].innerHTML.includes('SPECint92 speed'));
 openFit('cpu2000','peak','equal_geometric');assert(!elements['#fit-mode'].disabled);
 setMatching('strict');


 inspectLineage('node','predictor-2017');assert.equal(elements['#fit-generation'].value,'cpu2017');
 assert(elements['#predictor-path'].innerHTML.includes('SPEC2006 rate'));
 assert(elements['#predictor-path'].innerHTML.includes('sqrt(speed'));
 assert.throws(()=>historicalPrediction({}),/at least one/);
 assert.throws(()=>historicalPrediction({'Dhrystone:v1.1_DMIPS':0}),/greater than zero/);
 assert.throws(()=>specPrediction('cpu2000','peak',10,20,'strict'),/No supported/);
 assert.throws(()=>specPrediction('cpu89','peak','',20,'ram-aliases'),/speed only/);
 assert.throws(()=>specPrediction('cpu92','base',1,'','ram-aliases'),/legacy speed/);
 assert.throws(()=>specPrediction('cpu2017','peak','NaN',20,'ram-aliases'),/finite/);
 const defined=specPrediction('cpu92','base','',604800/25500,'ram-aliases')[0];
 for(const v of defined.values)assert(Math.abs(v-1)<1e-12);
 assert.equal(specPrediction('cpu92','peak',1,604800/25500,'ram-aliases').length,2);
 if(reference){
  for(const c of reference.historical){
   const r=historicalPrediction(c.scores);
   r.values.forEach((v,i)=>assert(Math.abs(v/c.values[i]-1)<1e-10));
  }
  for(const c of reference.spec){
   const r=specPrediction(c.generation,c.mode,c.speed,c.rate,c.policy)[0];
   r.values.forEach((v,i)=>assert(Math.abs(v/c.values[i]-1)<1e-10));
  }
 }
 elements['#calc-kind'].value='spec';calculatorView();
 assert(elements['#calc-historical'].hidden&&!elements['#calc-spec'].hidden);
 elements['#calc-generation'].value='cpu92';elements['#calc-rate'].value=604800/25500;runCalculator();
 assert(elements['#calc-result'].innerHTML.includes('1.000 VAX'));

 const sourceLength=data.length,sourceCount=filtered.length;
 elements['#calc-year'].value='1985';runCalculator();
 assert.equal(userPredictions.length,1);assert.equal(userPredictions[0].year,1985);
 assert(elements['#plot'].innerHTML.includes('You are here'));
 assert.equal(data.length,sourceLength);assert.equal(filtered.length,sourceCount);
 clearSelection();assert(elements['#plot'].innerHTML.includes('You are here'));
 setRange(1990,2000);assert.equal(userPredictions.length,1);
 assert(!elements['#plot'].innerHTML.includes('You are here'));
 elements['#reset'].events.click();assert(elements['#plot'].innerHTML.includes('You are here'));
 elements['#calc-form'].events.input();assert.equal(userPredictions.length,0);
 elements['#calc-year'].value=originalBounds.xmax+10;elements['#calc-rate'].value='1e20';runCalculator();
 assert(userPredictions[0].year<=viewMax);assert(ymax>originalBounds.ymax);
 assert(X(userPredictions[0].year)>107&&X(userPredictions[0].year)<1343);
 assert(!/NaN|Infinity/.test(predictionMarkup()));
 elements['#calc-clear'].events.click();assert.equal(userPredictions.length,0);
 assert.equal(elements['#calc-year'].value,'');assert.equal(ymax,originalBounds.ymax);assert.equal(xmax,originalBounds.xmax);
 assert.equal(xmin,originalBounds.xmin);assert.equal(ymin,originalBounds.ymin);
 elements['#calc-rate'].value=604800/25500;
 elements['#calc-year'].value='1985.5';runCalculator();assert.equal(userPredictions.length,0);
 assert(elements['#calc-result'].textContent.includes('whole number'));
 elements['#calc-year'].value='1800';elements['#calc-speed'].value='1';runCalculator();
 assert.equal(userPredictions.length,2);assert(xmin<=1799);
 assert(predictionMarkup().includes('Legacy speed estimate'));
 assert(predictionMarkup().includes('Defined SPEC92 rate scale'));
 setMatching('ram-aliases');assert.equal(elements['#calc-result'].innerHTML,'');
 elements['#calc-clear'].events.click();assert.equal(elements['#calc-rate'].value,'');
 elements['#calc-kind'].value='historical';calculatorView();setMatching('strict');
 for(const mode of ['peak','peak_proxy'])elements['#scores'].events.change({target:{dataset:{mode},checked:false}});assert.equal(filtered.length,32027);
 for(const mode of ['peak','peak_proxy'])elements['#scores'].events.change({target:{dataset:{mode},checked:true}});assert.equal(filtered.length,60710);
 assert.equal(data.filter(r=>r.route==='Gibson mix').length,177);
 assert.equal(data.filter(r=>r.route==='ADP mix').length,183);
 assert.equal(data.filter(r=>r.route==='Combined mixes').length,186);
 enabled.delete('Combined mixes');enabled.delete('Gibson mix');enabled.delete('ADP mix');draw();assert.equal(filtered.length,60524);
 enabled.add('Gibson mix');enabled.add('ADP mix');draw();assert.equal(filtered.length,60884);
 const modern=data.find(r=>r.generation==='cpu2026'&&r.mode==='base');
 traceLineage(modern);assert(lineageActive.includes('rate-2026')&&lineageActive.includes('rate-92'));
 assert(!lineageActive.includes('mix-model'));assert(elements['#lineage'].open);
 inspectLineage('edge','rate-2026-to-2017');assert(elements['#lineage-card'].innerHTML.includes('base'));
 const mixed=data.find(r=>r.route==='Combined mixes');traceLineage(mixed);
 assert(lineageActive.includes('mix-model')&&!lineageActive.includes('classic-model'));
 assert(elements['#lineage-card'].innerHTML.includes('Actual inputs'));
 const classic=data.find(r=>r.route==='classical');traceLineage(classic);assert(lineageActive.includes('classic-model'));
 const s89=data.find(r=>r.route==='SPEC89');traceLineage(s89);assert.deepEqual(pathway(s89),['int89','int92','vaxen']);
 const beforePathReset={count:filtered.length,lo:viewMin,hi:viewMax,page};
 elements['#lineage-graph'].events.click({target:{dataset:{key:'int89',type:'node'}}});assert.notEqual(lineageActive,null);
 elements['#lineage-graph'].events.click({target:elements['#lineage-graph']});assert.equal(lineageActive,null);assert.equal(lineageRecord,null);
 assert.deepEqual({count:filtered.length,lo:viewMin,hi:viewMax,page},beforePathReset);
 const countBefore=filtered.length;elements['#zoom-in'].events.click();assert(filtered.length<countBefore);
 elements['#reset'].events.click();assert.equal(filtered.length,countBefore);
 elements['#sort'].value='vaxen-desc';elements['#sort'].events.change();
 const maximum=filtered.reduce((a,b)=>a.vaxen>b.vaxen?a:b);assert(elements['#body'].innerHTML.includes(esc(maximum.system)));
 elements['#table-next'].events.click();assert.equal(page,1);
 elements['#table-next-bottom'].events.click();assert.equal(page,2);
 elements['#sort-bottom'].value='vaxen-asc';elements['#sort-bottom'].events.change();assert.equal(page,0);
 assert.equal(elements['#sort'].value,'vaxen-asc');
 elements['#goto-page-bottom'].value='3';elements['#page-jump-bottom'].events.submit({preventDefault(){}});assert.equal(page,2);
 assert.equal(elements['#goto-page'].value,3);
 assert.equal(elements['#goto-page'].max,elements['#goto-page-bottom'].max);
 assert.equal(elements['#page-count'].textContent,elements['#page-count-bottom'].textContent);
 elements['#goto-page'].value='5';elements['#page-jump'].events.submit({preventDefault(){}});assert.equal(page,4);
 elements['#goto-page'].value='0';elements['#page-jump'].events.submit({preventDefault(){}});assert.equal(page,4);
 elements['#goto-page'].value=elements['#goto-page'].max;elements['#page-jump'].events.submit({preventDefault(){}});
 assert(elements['#table-next'].disabled&&elements['#table-next-bottom'].disabled);
 for(const mode of ['base','peak','peak_proxy'])elements['#scores'].events.change({target:{dataset:{mode},checked:false}});
 assert.equal(filtered.length,0);assert.equal(page,0);assert(elements['#goto-submit'].disabled);
 for(const mode of ['base','peak','peak_proxy'])elements['#scores'].events.change({target:{dataset:{mode},checked:true}});
 elements['#q'].value='VAX';elements['#q'].events.input();assert.equal(page,0);assert(filtered.length>0&&filtered.length<countBefore);
 `,context);
 console.log('PASS: full generated page; baseline parity, estimate/policy switching, paired comparisons, lineage, pagination, zoom and search');
 process.exit(0);
}
vm.runInContext(script+`
assert.equal(configurationDetails({clock_mhz:'',os:'',configuration:'memory cycle µs: 2'}),'memory cycle µs: 2');
assert.equal(configurationDetails({clock_mhz:16,os:'',configuration:'memory: 512 KB'}),'clock: 16 MHz; memory: 512 KB');
const body=()=>elements['#body'].innerHTML;
const setOrder=value=>{elements['#sort'].value=value;elements['#sort'].events.change();};
setOrder('vaxen-asc');assert(body().indexOf('Low machine')<body().indexOf('High machine'));
setOrder('vaxen-desc');assert(body().indexOf('High machine')<body().indexOf('Low machine'));
for(const order of ['year-asc','year-desc']){setOrder(order);assert(body().indexOf('Unknown machine')>body().indexOf('Low machine'));}
setOrder('name');assert(body().indexOf('High machine')<body().indexOf('Low machine'));
setOrder('vaxen-desc');elements['#q'].value='machine';elements['#q'].events.input();
assert.equal(elements['#sort'].value,'vaxen-desc');assert(body().indexOf('High machine')<body().indexOf('Low machine'));
const center=()=>screenPoint(points.find(p=>p.r.system==='Low machine'));
const move=offset=>{const p=center();plot.events.pointermove({clientX:p.x+offset,clientY:p.y});};
move(8);assert.equal(tip.hidden,false);assert.equal(candidates.length,2);assert(elements['#highlight'].innerHTML.includes('<circle'));
move(13);assert.equal(tip.hidden,true);assert.equal(elements['#highlight'].innerHTML,'');
setScale(.5);window.events.resize();move(11);assert.equal(tip.hidden,false);move(13);assert.equal(tip.hidden,true);
setScale(1);window.events.resize();const p=center();plot.events.click({clientX:p.x+8,clientY:p.y});assert.equal(pinned,true);
const first=candidates[active].r.configuration_id;elements['#next'].events.click();assert.notEqual(candidates[active].r.configuration_id,first);
plot.events.pointerleave();assert.equal(tip.hidden,false);assert.equal(pinned,true);
document.events.keydown({key:'Escape'});assert.equal(tip.hidden,true);
plot.events.click({clientX:p.x,clientY:p.y});document.events.click({target:{}});assert.equal(tip.hidden,true);
plot.events.click({clientX:p.x,clientY:p.y});elements['#q'].value='no such model';elements['#q'].events.input();
assert.equal(tip.hidden,true);assert.equal(points.length,0);assert.equal(body(),'');
elements['#q'].value='';elements['#q'].events.input();
const width=viewMax-viewMin;elements['#zoom-in'].events.click();assert(viewMax-viewMin<width);
elements['#reset'].events.click();assert.equal(viewMax-viewMin,width);
setRange(1979,1981);assert(points.every(p=>p.r.year===1980));assert(body().includes('Unknown machine'));assert(!body().includes('High machine'));
move(8);assert(!tip.hidden);elements['#reset'].events.click();
let prevented=false;const anchor=center();plot.events.wheel({clientX:anchor.x,clientY:anchor.y,deltaY:-100,preventDefault(){prevented=true;}});assert(prevented);assert(viewMax-viewMin<width);
elements['#reset'].events.click();
for(const mode of ['peak','peak_proxy'])elements['#scores'].events.change({target:{dataset:{mode},checked:false}});assert.equal(points.length,0);
elements['#scores'].events.change({target:{dataset:{mode:'peak_proxy'},checked:true}});assert.equal(points.length,3);
elements['#routes'].events.change({target:{dataset:{route:'classical'},checked:false}});assert.equal(points.length,0);
elements['#routes'].events.change({target:{dataset:{route:'classical'},checked:true}});assert.equal(points.length,3);
setRange(1979,1985);const start=viewMin;plot.events.pointerdown({button:0,clientX:500,pointerId:1});
plot.events.pointermove({clientX:450,clientY:300});plot.events.pointerup();assert(viewMin>start);
plot.events.click({clientX:450,clientY:300});assert.equal(pinned,false);
elements['#reset'].events.click();
assert.equal(fmt(1234),'1.234 kVAXen');assert.equal(fmt(.026),'26.000 mVAXen');assert.equal(fmt(2000000),'2.000 MVAXen');
assert.equal(fmt(999999.9),'1.000 MVAXen');assert.equal(fmt(0),'0.000 VAXen');
const brushEvent=(yr,kind)=>({button:0,pointerId:2,clientX:overviewX(yr)+20,clientY:40,target:{dataset:{brush:kind}},preventDefault(){}});
setRange(1980,1988);overviewPlot.events.pointerdown(brushEvent(1980,'left'));overviewPlot.events.pointermove(brushEvent(1982,'left'));overviewPlot.events.pointerup();assert(Math.abs(viewMin-1982)<1e-8);assert.equal(viewMax,1988);
overviewPlot.events.pointerdown(brushEvent(1988,'right'));overviewPlot.events.pointermove(brushEvent(1989,'right'));overviewPlot.events.pointerup();assert.equal(viewMax,1989);
overviewPlot.events.pointerdown(brushEvent(1985,'move'));overviewPlot.events.pointermove(brushEvent(1984,'move'));overviewPlot.events.pointerup();assert(Math.abs(viewMin-1981)<1e-8);assert.equal(viewMax,1988);
overviewPlot.events.pointerdown(brushEvent(1983,undefined));overviewPlot.events.pointermove(brushEvent(1986,undefined));overviewPlot.events.pointerup();assert(Math.abs(viewMin-1983)<1e-8);assert.equal(viewMax,1986);
elements['#brush-left'].events.keydown({key:'ArrowRight',preventDefault(){}});assert(Math.abs(viewMin-1984)<1e-8);
// Handles must not cross and a minimum one-year span must remain.
overviewPlot.events.pointerdown(brushEvent(1984,'left'));overviewPlot.events.pointermove(brushEvent(1990,'left'));overviewPlot.events.pointercancel();assert.equal(viewMax-viewMin,1);



`,context);
console.log('PASS: numeric/year/name sorting, unknown placement, search, 12px snapping at two scales, highlight, overlap cycling, pin and dismissal');
