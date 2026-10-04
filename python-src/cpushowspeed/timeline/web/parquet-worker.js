import {loadBundle} from './parquet-loader.js';
self.onmessage = async ({data: {manifestURL}}) => {
  try {
    const response = await fetch(manifestURL);
    if (!response.ok) throw Error('Cannot load manifest: HTTP ' + response.status);
    const manifest = await response.json();
    const bundle = await loadBundle(manifest, async (path, info) => {
      self.postMessage({progress: 'Loading ' + path});
      const response = await fetch(new URL(path, manifestURL));
      if (!response.ok) throw Error('Cannot load ' + path + ': HTTP ' + response.status);
      const bytes = await response.arrayBuffer();
      if (globalThis.crypto?.subtle) {
        const hash = await crypto.subtle.digest('SHA-256', bytes);
        const hex = Array.from(new Uint8Array(hash), x => x.toString(16).padStart(2, '0')).join('');
        if (hex !== info.sha256) throw Error('Data checksum mismatch: ' + path);
      }
      return bytes;
    });
    self.postMessage({bundle});
  } catch (error) {self.postMessage({error: error.message});}
};
