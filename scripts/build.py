#!/usr/bin/env python3
"""Render the CoT roll samples into an interactive static review site.

  python scripts/build.py --samples samples --out site

samples/<export>/<kind>/<NN>/{input.json, output.json?, img_XX.jpg}  -> one record each in the viewer
samples/1113/review.html                                              -> copied through unchanged, linked
The sample data is inlined into index.html so the page also works opened straight from disk.
"""
import argparse
import json
import shutil
from pathlib import Path

KIND_ORDER = ["img1", "imgN", "text", "vshort", "vlong"]
APP = Path(__file__).resolve().parent / "app.html"


def norm_messages(msgs):
    out = []
    for m in msgs or []:
        c, parts = m.get("content"), []
        if isinstance(c, str):
            parts.append({"t": "text", "v": c})
        else:
            for p in c or []:
                if p.get("type") in ("image_url", "video_url"):
                    parts.append({"t": "img", "v": (p.get(p["type"]) or {}).get("url", "")})
                else:
                    parts.append({"t": "text", "v": p.get("text", "")})
        out.append({"role": m.get("role", "?"), "parts": parts})
    return out


def load_sample(export, kind, d):
    inp = json.loads((d / "input.json").read_text())
    outp = json.loads((d / "output.json").read_text()) if (d / "output.json").exists() else None
    meta = dict((outp or {}).get("meta") or inp.get("meta") or {})
    msgs = norm_messages(inp.get("messages"))
    imgs = [p["v"] for m in msgs for p in m["parts"] if p["t"] == "img"]
    rec = {
        "key": f"{kind}-{d.name}", "export": export, "kind": kind, "nn": d.name, "id": inp.get("id"),
        "base": f"samples/{export}/{kind}/{d.name}", "images": imgs, "messages": msgs,
        "gt": meta.get("gt"), "dataset": meta.get("dataset"), "turn": int(meta.get("turn") or 0),
        "n_turns": int(meta.get("n_turns") or 1), "frame_ts": meta.get("frame_ts") or [],
        "duration_s": meta.get("duration_s"), "fps": meta.get("fps"),
        "placement_fallback": bool(meta.get("placement_fallback")),
        "est_prompt_tokens": meta.get("est_prompt_tokens"), "has_output": outp is not None,
    }
    if outp:
        c = (outp.get("choices") or [{}])[0]
        rec.update(reasoning=c.get("reasoning") or "", answer=c.get("content") or "",
                   finish=c.get("finish_reason"), usage=outp.get("usage") or {},
                   latency_s=outp.get("latency_s"), model=outp.get("model"))
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", default="samples")
    ap.add_argument("--out", default="site")
    a = ap.parse_args()
    src, out = Path(a.samples), Path(a.out)
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(src, out / "samples", ignore=shutil.ignore_patterns(".DS_Store"))
    recs = []
    for exp in sorted(p for p in src.iterdir() if p.is_dir()):
        kinds = sorted((p for p in exp.iterdir() if p.is_dir()),
                       key=lambda p: KIND_ORDER.index(p.name) if p.name in KIND_ORDER else 99)
        for kd in kinds:
            for d in sorted(p for p in kd.iterdir() if p.is_dir() and (p / "input.json").exists()):
                recs.append(load_sample(exp.name, kd.name, d))
    extras = []
    if (src / "1113" / "review.html").exists():
        extras.append({"href": "samples/1113/review.html", "label": "11-13 帧率 smoke"})
    data = json.dumps({"samples": recs, "extras": extras}, ensure_ascii=False).replace("</", "<\\/")
    page = APP.read_text().replace("/*__DATA__*/null", data)
    (out / "index.html").write_text(page)
    (out / ".nojekyll").write_text("")
    print(f"wrote {out}/index.html with {len(recs)} samples")


if __name__ == "__main__":
    main()
