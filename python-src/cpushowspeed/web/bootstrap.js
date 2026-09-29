const status = document.querySelector('#load-status');
async function start() {
  if (location.protocol === 'file:') throw Error('Serve this directory over HTTP, then open vaxen-timeline.html.');
  const bundle = await new Promise((resolve, reject) => {
    const worker = new Worker(new URL('./parquet-worker.js', import.meta.url), {type: 'module'});
    worker.onmessage = ({data}) => {
      if (data.progress) status.textContent = data.progress;
      if (data.error) {worker.terminate(); reject(Error(data.error));}
      if (data.bundle) {worker.terminate(); resolve(data.bundle);}
    };
    worker.onerror = event => {worker.terminate(); reject(Error(event.message || 'Parquet worker failed'));};
    worker.postMessage({manifestURL: new URL('../manifest.json', import.meta.url).href});
  });
  const {mountTimeline} = await import('./timeline.js');
  document.querySelector('#timeline-app').hidden = false;
  mountTimeline(bundle);
  status.hidden = true;
}
start().catch(error => {status.textContent = 'Unable to load timeline: ' + error.message; status.setAttribute('role', 'alert');});
