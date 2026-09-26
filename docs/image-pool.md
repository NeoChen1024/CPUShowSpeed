# Image Pool and captioning (selected design)

The Image Pool stores crops from visual regions found during OCR. BLAKE3
identifies the bytes of each stored crop; it is not a way to match similar
pictures across PDFs. Different pixel crops of the same printed figure will
normally have different hashes. The original PDF remains the source of
record. OCR-stage crop storage is implemented; the captioning command is not.

## Storing images

Crop valid visual blocks from the same page image submitted to Chandra.
Consider `Image`, `Figure`, `Diagram`, `Chart`, and other confirmed visual
labels. Chandra's built-in extraction currently crops only `Image` and
`Figure`; do not rely on it as the complete visual-region list. Keep one
DocIR block for each source chunk, with its bbox and `image_blake3` pointing
to the pool. If a crop fails, keep the block and mark that failure.

Use a fixed lossless encoding for pool images so small technical labels
remain legible. Choose PNG or lossless WebP after a small size/quality check.
Hash the encoded bytes and store them under a sharded path such as
`images/ab/cd/<digest>.<extension>`. Publish each asset atomically and
verify an existing file with the same digest. Ingest only references from
the current completed OCR result; a CLI output directory may contain
unreferenced files from earlier runs.

The pool stores image files; a small SQLite catalog records digest, path,
media type, and dimensions. DocIR owns the source PDF/page/block reference.
Image bytes are not copied into DocIR. Successful captions are copied from
SQLite into DocIR by a later, repeatable backfill stage.

## Choosing what to caption

Caption every valid `Image` or `Figure` crop, including those with a
Chandra-generated `alt` description. Skip the second caption for a
`Diagram` or `Chart` only when Chandra supplied useful structured content,
such as Mermaid graph code or parsed table cells; caption unparsed crops.
Structured OCR and captions remain unverified. Important relationship
diagrams and numeric charts still need visual checks; a valid-looking
graph can have wrong edges. A source figure can also be omitted from OCR
entirely, which captioning emitted images cannot repair. The
[time-sharing sample review](../research/chandra-timesharing-sample.md)
shows both cases.

## SQLite and batch processing

Keep the live SQLite catalog on local storage, such as
`data/derived/image-pool/catalog.sqlite` on this host's XFS, rather than on
the NFS bitsavers mount. The OCR stage currently creates `images` for image BLAKE3, filename,
media type, and dimensions. The captioning stage will add a `captions`
table with image BLAKE3, caption text, model name, completion time, and
last error.

The command selects the eligible referenced images whose SQLite caption
is absent. It sends requests with bounded concurrency and has one writer
save each completed caption. An interrupted run simply selects the remaining
images next time. Failed images retain an error and may be retried. If the
user deliberately changes the model or prompt, an explicit `--force` run
replaces existing captions; previous caption versions are not maintained.

The initial request describes the visible crop alone: legible labels and
text, axes, connections, components, and uncertainty. Captions are useful
for finding images but are not source-checked numerical data. If a future
workflow needs surrounding page context, decide that separately; the first
version has no contextual caption machinery.

An `<img>` inside a table cell currently causes an explicit table-conversion
failure rather than a guessed crop. The raw OCR and original PDF page remain
available until that case is tested on real output.
