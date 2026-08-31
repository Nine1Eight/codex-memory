#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path
import zlib
from typing import Dict, List

DEFAULT_VISIBLE = "SIGILAGI_COLLAPSE_TO_TEXTUAL_GLYPH_IMAGE"
DEFAULT_BRAILLE = "⠎⠊⠛⠊⠇⠁⠛⠊⠉⠕⠇⠇⠁⠏⠎⠑"
DEFAULT_HANZI = "一二十"

TEMPLATE = '''#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import zlib
from typing import Dict, Any


class {class_name}:
    VISIBLE = {visible!r}
    BRAILLE = {braille!r}
    HANZI = {hanzi!r}

    IDENTITY_SHA256 = {identity_sha256!r}
    PAYLOAD_SHA256 = {payload_sha256!r}
    ENTRY_MODULE = {entry_module!r}
    ENTRY_CLASS = {entry_class!r}
    ENTRY_METHOD = {entry_method!r}
    METADATA = {metadata_json}
    MANIFEST = {manifest_json}

    ENCODED_PAYLOAD = {encoded_payload!r}

    @classmethod
    def identity_hash(cls) -> str:
        raw = f"{{cls.VISIBLE}}{{cls.BRAILLE}}{{cls.HANZI}}".encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    @classmethod
    def decode_payload(cls) -> Dict[str, str]:
        compressed = base64.b85decode(cls.ENCODED_PAYLOAD.encode("ascii"))
        raw = zlib.decompress(compressed)
        actual = hashlib.sha256(raw).hexdigest()
        if actual != cls.PAYLOAD_SHA256:
            raise RuntimeError(f"payload hash mismatch: {{actual}} != {{cls.PAYLOAD_SHA256}}")
        data = json.loads(raw.decode("utf-8"))
        if not isinstance(data, dict):
            raise TypeError("decoded payload must be a mapping of filename -> source")
        return data

    @classmethod
    def textual_glyph_image(cls) -> str:
        return f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                      SIGILAGI REHYDRATING GLYPH CAPSULE                     ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  α-layer: {{cls.VISIBLE:<64}}║
║  β-layer: {{cls.BRAILLE:<64}}║
║  γ-layer: {{cls.HANZI:<64}}║
║  Identity SHA256: {{cls.IDENTITY_SHA256[:64]}}║
║  Payload  SHA256: {{cls.PAYLOAD_SHA256[:64]}}║
║                                                                              ║
║  MODE: Embedded source archive → verify → write → import → execute          ║
║  FILES: {{len(cls.MANIFEST):<3}} modules                                                             ║
╚══════════════════════════════════════════════════════════════════════════════╝
""".strip()

    @classmethod
    def verify(cls) -> Dict[str, Any]:
        payload = cls.decode_payload()
        payload_canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        identity_ok = cls.identity_hash() == cls.IDENTITY_SHA256
        payload_ok = hashlib.sha256(payload_canonical).hexdigest() == cls.PAYLOAD_SHA256

        files = {{}}
        for name, src in payload.items():
            digest = hashlib.sha256(src.encode("utf-8")).hexdigest()
            expected = cls.MANIFEST[name]["sha256"]
            files[name] = {{
                "ok": digest == expected,
                "sha256": digest,
                "expected": expected,
                "size": len(src.encode("utf-8")),
            }}

        all_files_ok = all(v["ok"] for v in files.values())
        return {{
            "identity_ok": identity_ok,
            "payload_ok": payload_ok,
            "all_files_ok": all_files_ok,
            "file_count": len(files),
            "files": files,
        }}

    @classmethod
    def rehydrate(cls, output_dir: str | os.PathLike[str]) -> Dict[str, Any]:
        out = Path(output_dir).expanduser().resolve()
        out.mkdir(parents=True, exist_ok=True)

        payload = cls.decode_payload()
        written = []

        for name, src in payload.items():
            file_path = out / name
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(src, encoding="utf-8")
            actual = hashlib.sha256(file_path.read_bytes()).hexdigest()
            expected = cls.MANIFEST[name]["sha256"]
            if actual != expected:
                raise RuntimeError(f"file hash mismatch for {{name}}: {{actual}} != {{expected}}")
            written.append({{
                "file": str(file_path),
                "sha256": actual,
                "size": file_path.stat().st_size,
            }})

        return {{
            "output_dir": str(out),
            "written": written,
            "count": len(written),
        }}

    @classmethod
    def boot(cls, output_dir: str | os.PathLike[str]) -> Dict[str, Any]:
        out = Path(output_dir).expanduser().resolve()
        entry_path = out / cls.ENTRY_MODULE
        if not entry_path.exists():
            raise FileNotFoundError(f"missing rehydrated file: {{entry_path}}")

        if str(out) not in sys.path:
            sys.path.insert(0, str(out))

        mod_name = Path(cls.ENTRY_MODULE).stem
        spec = importlib.util.spec_from_file_location(mod_name, entry_path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"unable to load entry module: {{entry_path}}")

        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        target_cls = getattr(mod, cls.ENTRY_CLASS)
        target = target_cls()
        method = getattr(target, cls.ENTRY_METHOD)
        result = method()

        return {{
            "boot_module": str(entry_path),
            "entry_class": cls.ENTRY_CLASS,
            "entry_method": cls.ENTRY_METHOD,
            "demo_result": result,
        }}


def main() -> int:
    parser = argparse.ArgumentParser(description="Generated SigilAGI self-rehydrating glyph capsule")
    parser.add_argument("--out", default="./sigilagi_capsule_out", help="rehydration directory")
    parser.add_argument("--verify-only", action="store_true", help="verify capsule without writing files")
    parser.add_argument("--no-boot", action="store_true", help="rehydrate files but do not import/execute stack")
    args = parser.parse_args()

    print({class_name}.textual_glyph_image())

    report = {class_name}.verify()
    print(json.dumps({{
        "verify": {{
            "identity_ok": report["identity_ok"],
            "payload_ok": report["payload_ok"],
            "all_files_ok": report["all_files_ok"],
            "file_count": report["file_count"],
        }}
    }}, indent=2))

    if not (report["identity_ok"] and report["payload_ok"] and report["all_files_ok"]):
        raise SystemExit(2)

    if args.verify_only:
        return 0

    rehydrated = {class_name}.rehydrate(args.out)
    print(json.dumps({{"rehydrate": rehydrated}}, indent=2))

    if args.no_boot:
        return 0

    booted = {class_name}.boot(args.out)
    print(json.dumps({{"boot": booted}}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_payload(files: Dict[str, str]) -> bytes:
    return json.dumps(files, sort_keys=True, separators=(",", ":")).encode("utf-8")


def build_capsule(source_dir: Path, modules: List[str], entry_module: str, entry_class: str, entry_method: str,
                  output: Path, visible: str, braille: str, hanzi: str, class_name: str,
                  metadata: Dict[str, object]) -> Dict[str, object]:
    files: Dict[str, str] = {}
    manifest: Dict[str, Dict[str, object]] = {}

    for module in modules:
        rel = module.replace("\\", "/")
        path = (source_dir / rel).resolve()
        if not path.exists():
            raise FileNotFoundError(f"missing module: {path}")
        if path.is_dir():
            raise IsADirectoryError(f"module path is a directory, not a file: {path}")
        text = path.read_text(encoding="utf-8")
        data = text.encode("utf-8")
        files[rel] = text
        manifest[rel] = {"sha256": sha256_hex(data), "size": len(data)}

    payload_bytes = canonical_payload(files)
    payload_sha256 = sha256_hex(payload_bytes)
    encoded_payload = base64.b85encode(zlib.compress(payload_bytes, level=9)).decode("ascii")
    identity_sha256 = sha256_hex(f"{visible}{braille}{hanzi}".encode("utf-8"))

    capsule = TEMPLATE.format(
        class_name=class_name,
        visible=visible,
        braille=braille,
        hanzi=hanzi,
        identity_sha256=identity_sha256,
        payload_sha256=payload_sha256,
        entry_module=entry_module,
        entry_class=entry_class,
        entry_method=entry_method,
        metadata_json=repr(metadata),
        manifest_json=repr(manifest),
        encoded_payload=encoded_payload,
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(capsule, encoding="utf-8")

    return {
        "output": str(output.resolve()),
        "identity_sha256": identity_sha256,
        "payload_sha256": payload_sha256,
        "file_count": len(files),
        "entry_module": entry_module,
        "entry_class": entry_class,
        "entry_method": entry_method,
        "manifest": manifest,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Deterministic builder for SigilAGI glyph capsules")
    parser.add_argument("--source-dir", required=True)
    parser.add_argument("--module", action="append", required=True)
    parser.add_argument("--entry-module", required=True)
    parser.add_argument("--entry-class", required=True)
    parser.add_argument("--entry-method", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--visible", default=DEFAULT_VISIBLE)
    parser.add_argument("--braille", default=DEFAULT_BRAILLE)
    parser.add_argument("--hanzi", default=DEFAULT_HANZI)
    parser.add_argument("--class-name", default="SigilGlyphCapsule")
    parser.add_argument("--metadata-json", default="{}")
    args = parser.parse_args()

    metadata = json.loads(args.metadata_json)
    if not isinstance(metadata, dict):
        raise TypeError("--metadata-json must decode to a JSON object")

    result = build_capsule(
        source_dir=Path(args.source_dir).expanduser().resolve(),
        modules=args.module,
        entry_module=args.entry_module,
        entry_class=args.entry_class,
        entry_method=args.entry_method,
        output=Path(args.output).expanduser().resolve(),
        visible=args.visible,
        braille=args.braille,
        hanzi=args.hanzi,
        class_name=args.class_name,
        metadata=metadata,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
