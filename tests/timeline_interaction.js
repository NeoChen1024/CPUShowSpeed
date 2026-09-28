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
 setScale:s=>scale=s});
if(process.argv[3]==='full'){
 vm.runInContext(script+`
 assert.equal(data.length,61070);
 assert.equal(filtered.length,60710);
 assert.equal((elements['#body'].innerHTML.match(/<tr>/g)||[]).length,200);
 for(const mode of ['peak','peak_proxy'])elements['#scores'].events.change({target:{dataset:{mode},checked:false}});assert.equal(filtered.length,32027);
 for(const mode of ['peak','peak_proxy'])elements['#scores'].events.change({target:{dataset:{mode},checked:true}});assert.equal(filtered.length,60710);
 assert.equal(data.filter(r=>r.route==='Gibson mix').length,177);
 assert.equal(data.filter(r=>r.route==='ADP mix').length,183);
 assert.equal(data.filter(r=>r.route==='Combined mixes').length,186);
 enabled.delete('Combined mixes');enabled.delete('Gibson mix');enabled.delete('ADP mix');draw();assert.equal(filtered.length,60524);
 enabled.add('Gibson mix');enabled.add('ADP mix');draw();assert.equal(filtered.length,60884);
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
 console.log('PASS: complete 61070-row page, 200-row pagination, modes, zoom, reset, numeric sort and search');
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
