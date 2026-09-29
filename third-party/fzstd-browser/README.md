# fzstd browser distribution

Official fzstd 0.1.1 npm release, MIT licensed. `index.js` is the unchanged
`package/esm/index.mjs` from the published archive, renamed for darkhttpd's
JavaScript MIME support. `provenance.json` records the archive URL, npm SHA-512
integrity, file SHA-256 hashes and exact release gitHead. Source is tracked in
`../fzstd` at that commit. Export verifies the pinned source and release hashes.

The precompiled release is retained here because upstream Git tracks TypeScript,
not the emitted ES module. Exporting the website needs no npm/TypeScript build
and makes no network requests. The loader registers fzstd only for ZSTD pages.
