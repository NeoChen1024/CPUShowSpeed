"""Lossless Zstd level 3 Parquet export for the static timeline, without an npm build."""

import hashlib
import json
import math
import re
import subprocess
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

FORMAT = "vaxen-web-parquet-v1"
ZSTD_COMMIT = "807a854cac2c5766ef030832cc5b66482dc7ca8a"
VENDOR_COMMIT = "460fb574870606a67eccaf59f7d7c08b46ec551e"
ROOT = Path(__file__).resolve().parents[2]


def compact(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))


def write_table(path, rows):
    """Preserve numbers, strings, null, empty strings and missing keys distinctly.

    Scalars are native Parquet columns. Heterogeneous/nested evidence uses explicitly
    tagged JSON cells, never a whole-dataset JSON blob. Presence columns preserve
    absent keys separately from null. The codec is also stored in Parquet metadata.
    """
    keys = list(dict.fromkeys(k for row in rows for k in row))
    arrays, codec = {}, {}
    for i, key in enumerate(keys):
        name = key if re.fullmatch(r"[A-Za-z_]\w*", key) else f"__column_{i}"
        values = [r.get(key) for r in rows]
        nonnull = [v for v in values if v is not None]
        types = {type(v) for v in nonnull}
        if any(type(v) is int and abs(v) > 2**53 - 1 for v in nonnull):
            raise ValueError(f"{key}: integer cannot be represented exactly in browser")
        if any(type(v) is float and not math.isfinite(v) for v in nonnull):
            raise ValueError(f"{key}: non-finite number")
        info = {"column": name, "name": key, "encoding": "native"}
        if types <= {int, float}:
            typ = pa.float64()
        elif types <= {str}:
            typ = pa.string()
        elif types <= {bool}:
            typ = pa.bool_()
        elif types <= {int, float, str} and all(not isinstance(v, str) or v == "" for v in nonnull):
            info["empty_string"] = name + "_empty"
            arrays[info["empty_string"]] = pa.array([v == "" for v in values])
            values = [None if v == "" else v for v in values]
            typ = pa.float64()
        else:
            info["encoding"] = "json"
            values = [compact(v) for v in values]
            typ = pa.string()
        arrays[name] = pa.array(values, type=typ)
        if any(key not in row for row in rows):
            info["presence"] = name + "_present"
            arrays[info["presence"]] = pa.array([key in row for row in rows])
        codec[key] = info
    table = pa.table(arrays).replace_schema_metadata(
        {b"cpushowspeed.codec": compact(codec).encode(), b"schema_version": FORMAT.encode()}
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".parquet.partial")
    pq.write_table(table, tmp, compression="zstd", compression_level=3, row_group_size=8192, use_dictionary=True, version="1.0")
    tmp.replace(path)
    return dict(rows=len(rows), bytes=path.stat().st_size, sha256=hashlib.sha256(path.read_bytes()).hexdigest(), codec=codec)


def read_table(path):
    """Reference reader for scientific export/parity checks."""
    table = pq.read_table(path)
    codec = json.loads(table.schema.metadata[b"cpushowspeed.codec"])
    result = []
    for raw in table.to_pylist():
        row = {}
        for key, info in codec.items():
            if info.get("presence") and not raw[info["presence"]]:
                continue
            value = raw[info["column"]]
            row[key] = (
                ""
                if info.get("empty_string") and raw[info["empty_string"]]
                else json.loads(value) if info["encoding"] == "json" else value
            )
        result.append(row)
    return result


class WebExport:
    def __init__(self, output):
        self.output = output
        self.artifacts = {}
        previous = output / "manifest.json"
        previous_manifest = json.loads(previous.read_text()) if previous.exists() else {}
        self.previous = previous_manifest.get("artifacts", {})
        self.previous_assets = previous_manifest.get("assets_sha256", {})

    def table(self, name, rows, shape="rows"):
        relative = "data/" + name + ".parquet"
        info = write_table(self.output / relative, rows)
        self.artifacts[relative] = info
        return {"$parquet": relative, "shape": shape}

    def tree(self, value, path):
        """Externalize large arrays; retain small configuration objects as JSON."""
        if isinstance(value, list) and value and len(compact(value)) > 8192:
            if all(isinstance(r, dict) for r in value):
                return self.table(path, value)
            return self.table(path, [{"value": v} for v in value], "values")
        if isinstance(value, dict):
            return {k: self.tree(v, path + "-" + re.sub(r"[^A-Za-z0-9_-]", "_", k)) for k, v in value.items()}
        if isinstance(value, list):
            return [self.tree(v, path + "-" + str(i)) for i, v in enumerate(value)]
        return value

    def finish(self, data, lineage, calculator, inline_sources=None):
        # Every draw index remains aligned across metric columns within its model.
        calculator = dict(calculator, networks={k: dict(v) for k, v in calculator.get("networks", {}).items()})
        for name, network in calculator["networks"].items():
            draws = network["draws"]
            lengths = {len(v) for v in draws.values()}
            if len(lengths) != 1:
                raise ValueError("unaligned calibration draws")
            network["draws"] = self.table("draws-" + name, [dict(zip(draws, values)) for values in zip(*draws.values())], "columns")
        manifest = dict(
            schema_version=FORMAT,
            vendor=dict(name="hyparquet", version="1.31.2", commit=VENDOR_COMMIT, license="MIT"),
            compression=dict(codec="zstd", level=3),
            zstd_decoder=dict(name="fzstd", version="0.1.1", commit=ZSTD_COMMIT, license="MIT"),
            data=data,
            lineage=self.tree(lineage, "lineage"),
            calibration=self.tree(calculator, "calibration"),
            records={"$parquet": "data/records.parquet", "shape": "rows"} if "data/records.parquet" in self.artifacts else None,
            artifacts=self.artifacts,
            inline_sources_sha256=inline_sources or {},
        )
        (self.output / "manifest.json").write_text(compact(manifest) + "\n")
        for name in self.previous.keys() - self.artifacts.keys():
            candidate = self.output / name
            if candidate.parent == self.output / "data" and candidate.suffix == ".parquet":
                candidate.unlink(missing_ok=True)
        # Remove only unchanged assets owned by the preceding exporter.
        assets = (self.output / "assets").resolve()
        for name, digest in self.previous_assets.items():
            candidate = (self.output / name).resolve()
            if (
                candidate.is_relative_to(assets)
                and candidate.is_file()
                and hashlib.sha256(candidate.read_bytes()).hexdigest() == digest
            ):
                candidate.unlink()
        if assets.is_dir():
            for directory in sorted([p for p in assets.rglob("*") if p.is_dir()], key=lambda p: len(p.parts), reverse=True) + [
                assets
            ]:
                try:
                    directory.rmdir()
                except OSError:
                    pass
        return manifest


def browser_worker_source():
    vendor = ROOT / "third-party/hyparquet"
    if not (vendor / "src/index.js").is_file():
        raise ValueError("Initialize the decoder: git submodule update --init third-party/hyparquet")
    revision = subprocess.check_output(["git", "-C", str(vendor), "rev-parse", "HEAD"], text=True).strip()
    if revision != VENDOR_COMMIT:
        raise ValueError("hyparquet revision differs from the tested export revision")
    if subprocess.check_output(["git", "-C", str(vendor), "status", "--porcelain"], text=True).strip():
        raise ValueError("hyparquet submodule has local modifications")
    zstd_source = ROOT / "third-party/fzstd"
    if not (zstd_source / "src/index.ts").exists():
        raise ValueError("Initialize the decoder: git submodule update --init third-party/fzstd")
    revision = subprocess.check_output(["git", "-C", str(zstd_source), "rev-parse", "HEAD"], text=True).strip()
    if (
        revision != ZSTD_COMMIT
        or subprocess.check_output(["git", "-C", str(zstd_source), "status", "--porcelain"], text=True).strip()
    ):
        raise ValueError("fzstd source must match the clean, pinned release commit")
    distribution = ROOT / "third-party/fzstd-browser"
    provenance = json.loads((distribution / "provenance.json").read_text())
    if provenance["source_commit"] != ZSTD_COMMIT:
        raise ValueError("fzstd release/source mismatch")
    for name, digest in provenance["files_sha256"].items():
        source = distribution / name
        if hashlib.sha256(source.read_bytes()).hexdigest() != digest:
            raise ValueError("fzstd release checksum mismatch: " + name)
    bundle_dir = ROOT / "third-party/timeline-decoder"
    info = json.loads((bundle_dir / "provenance.json").read_text())
    for name, digest in info["source_sha256"].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest:
            raise ValueError("Decoder bundle source changed; rebuild the pinned bundle: " + name)
    decoder = (bundle_dir / "decoder.js").read_bytes()
    if hashlib.sha256(decoder).hexdigest() != info["bundle_sha256"]:
        raise ValueError("Decoder bundle checksum mismatch")
    web = Path(__file__).parent / "web"
    loader = (web / "parquet-loader.js").read_text()
    for statement in (
        "import {parquetReadObjects} from './vendor/hyparquet/src/index.js';",
        "import {decompress} from './vendor/fzstd/index.js';",
    ):
        if statement not in loader:
            raise ValueError("Unexpected loader import; update inline assembly")
        loader = loader.replace(statement, "")
    loader = loader.replace("export function ", "function ").replace("export async function ", "async function ")
    worker = (web / "parquet-worker.js").read_text().replace("import {loadBundle} from './parquet-loader.js';", "")
    return decoder.decode() + "\nconst {parquetReadObjects,decompress}=ParquetDecoder;\n" + loader + "\n" + worker
