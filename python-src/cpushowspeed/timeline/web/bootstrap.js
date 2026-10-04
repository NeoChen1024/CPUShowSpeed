const status = document.querySelector('#load-status');
async function start() {
  if (location.protocol === 'file:') throw Error('Serve this directory over HTTP, then open vaxen-timeline.html.');
  const bundle = await new Promise((resolve, reject) => {
    const source = JSON.parse(document.querySelector('#parquet-worker-source').textContent);
    const workerURL = URL.createObjectURL(new Blob([source], {type:'text/javascript'}));
    let worker;
    try {worker = new Worker(workerURL);} catch (error) {URL.revokeObjectURL(workerURL); reject(error); return;}
    const cleanup = () => {worker.terminate(); URL.revokeObjectURL(workerURL);};
    worker.onmessage = ({data}) => {
      if (data.progress) status.textContent = data.progress;
      if (data.error) {cleanup(); reject(Error(data.error));}
      if (data.bundle) {cleanup(); resolve(data.bundle);}
    };
    worker.onerror = event => {cleanup(); reject(Error(event.message || 'Parquet worker failed'));};
    worker.postMessage({manifestURL: new URL('./manifest.json', document.baseURI).href});
  });
  document.querySelector('#timeline-app').hidden = false;
  mountTimeline(bundle);
  status.hidden = true;
}
start().catch(error => {status.textContent = 'Unable to load timeline: ' + error.message; status.setAttribute('role', 'alert');});
