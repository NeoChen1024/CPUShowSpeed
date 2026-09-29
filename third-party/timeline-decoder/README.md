# Pinned browser decoder bundle

`decoder.js` contains only the runtime import closure needed by `entry.js`:
hyparquet's `parquetReadObjects` and fzstd's `decompress`. Unused exports are
removed by esbuild. It is an IIFE exposing `ParquetDecoder`, suitable for an
inline Blob Worker. Both upstream MIT license texts are included in the bundle.

The source repositories and official fzstd browser distribution remain separately
tracked. `provenance.json` records hashes of every build input, the resulting
bundle, and the exact esbuild distribution used. Export verifies these hashes
and the pinned source commits; it never downloads or builds JavaScript.

## Updating

From the repository root, with esbuild **0.25.12** available:

```sh
esbuild third-party/timeline-decoder/entry.js \
  --bundle --format=iife --global-name=ParquetDecoder --minify \
  --target=es2020 --legal-comments=inline \
  --outfile=third-party/timeline-decoder/decoder.js \
  --metafile=/tmp/decoder-metafile.json
```

Prepend a `/*! ... */` comment containing `hyparquet 1.31.2`, its complete
LICENSE text, then `fzstd 0.1.1` and its complete LICENSE text, separated by
blank lines. Recompute SHA-256 for the metafile's input files, the two LICENSE
files, and the final bundle in `provenance.json`. When changing dependencies,
update their pinned versions/commits and provenance together. Run the generated
page interaction tests and verify loading in a real browser before publishing.

The build tool can be obtained as the official platform-specific esbuild npm
archive; verify its registry integrity before use. npm is not needed to extract
or run that binary, and neither esbuild nor npm is required for daily exports.
