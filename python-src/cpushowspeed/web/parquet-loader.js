import {parquetReadObjects} from './vendor/hyparquet/src/index.js';
import {decompress} from './vendor/fzstd/index.js';
const compressors = {ZSTD: (bytes, size) => decompress(bytes, new Uint8Array(size))};

export function decodeRows(raw, codec) {
  return raw.map(source => {
    const row = {};
    for (const [key, info] of Object.entries(codec)) {
      if (info.presence && !source[info.presence]) continue;
      const value = source[info.column];
      row[key] = info.empty_string && source[info.empty_string] ? '' : info.encoding === 'json' ? JSON.parse(value) : value;
    }
    return row;
  });
}

export async function loadBundle(manifest, readBytes) {
  if (manifest.schema_version !== 'vaxen-web-parquet-v1') throw Error('Unsupported timeline data version');
  async function restore(value) {
    if (!value || typeof value !== 'object') return value;
    if (value.$parquet) {
      const info = manifest.artifacts[value.$parquet];
      if (!info) throw Error('Missing Parquet manifest entry');
      const file = await readBytes(value.$parquet, info);
      if (file.byteLength !== info.bytes) throw Error('Incomplete Parquet file: ' + value.$parquet);
      const rows = decodeRows(await parquetReadObjects({file, compressors}), info.codec);
      if (rows.length !== info.rows) throw Error('Parquet row count mismatch');
      if (value.shape === 'values') return rows.map(r => r.value);
      if (value.shape === 'columns') return Object.fromEntries(Object.keys(info.codec).map(k => [k, rows.map(r => r[k])]));
      return rows;
    }
    // Sequential decode avoids overlapping temporary buffers across large tables.
    if (Array.isArray(value)) {
      const out = []; for (const item of value) out.push(await restore(item)); return out;
    }
    const out = {}; for (const [key, item] of Object.entries(value)) out[key] = await restore(item); return out;
  }
  return {data: await restore(manifest.data), lineage: await restore(manifest.lineage), calibration: await restore(manifest.calibration)};
}
