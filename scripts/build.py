#!/usr/bin/env python3
"""Render the CoT roll samples into a static site.

  python scripts/build.py --samples samples --out site

samples/1115/<kind>/<NN>/{input.json, output.json?, img_XX.jpg}  -> one page section per sample
samples/1113/review.html                                          -> copied through unchanged
"""
import argparse
import html
import json
import shutil
from pathlib import Path

KIND_ORDER = ["img1", "imgN", "text", "vshort", "vlong"]
KIND_NAME = {"img1": "单图", "imgN": "多图", "text": "纯文本", "vshort": "短视频", "vlong": "长视频"}

CSS = """
:root{--bg:#fafaf8;--fg:#1d1d1b;--mut:#6b6b66;--card:#fff;--line:#e4e2dc;--acc:#2f6fb2;--warn:#b5532a;--ok:#2e7d4f;--code:#f3f2ee}
@media (prefers-color-scheme:dark){:root{--bg:#161615;--fg:#e8e6e0;--mut:#9a988f;--card:#1f1f1d;--line:#34332f;--acc:#7fb0e6;--warn:#e08a63;--ok:#6cc08f;--code:#262624}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.6 -apple-system,BlinkMacSystemFont,"PingFang SC","Segoe UI",sans-serif}
header{padding:20px 24px;border-bottom:1px solid var(--line)}h1{margin:0;font-size:20px}header p{margin:4px 0 0;color:var(--mut)}
.wrap{display:flex;gap:0;max-width:1400px;margin:0 auto}
nav{position:sticky;top:0;align-self:flex-start;width:240px;max-height:100vh;overflow:auto;padding:16px;border-right:1px solid var(--line)}
nav h3{margin:14px 0 4px;font-size:13px;color:var(--mut);text-transform:uppercase;letter-spacing:.04em}
nav a{display:block;padding:2px 6px;border-radius:4px;color:var(--fg);text-decoration:none;font-size:13px}nav a:hover{background:var(--code)}
main{flex:1;min-width:0;padding:16px 24px 80px}
.s{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:16px 18px;margin:0 0 22px}
.s h2{margin:0 0 4px;font-size:16px}.id{font:12px ui-monospace,Menlo,monospace;color:var(--mut);word-break:break-all}
.tags{margin:8px 0}.tag{display:inline-block;font-size:12px;padding:1px 8px;border-radius:10px;background:var(--code);margin:0 4px 4px 0}
.tag.bad{background:none;border:1px solid var(--warn);color:var(--warn)}.tag.good{background:none;border:1px solid var(--ok);color:var(--ok)}
.msg{border-left:3px solid var(--line);padding:4px 12px;margin:10px 0}.msg.user{border-color:var(--acc)}
.role{font-size:12px;font-weight:600;color:var(--mut);text-transform:uppercase}
.txt{white-space:pre-wrap;word-break:break-word}
.imgs{display:flex;flex-wrap:wrap;gap:6px;margin:6px 0}.imgs a{position:relative;display:block}
.imgs img{display:block;max-height:220px;max-width:100%;border:1px solid var(--line);border-radius:4px}
.imgs.frames img{height:90px}.imgs .n{position:absolute;left:3px;top:2px;font-size:11px;background:#000a;color:#fff;padding:0 4px;border-radius:3px}
.blk{margin:12px 0}.blk>.lab{font-size:12px;font-weight:600;color:var(--mut);text-transform:uppercase;margin-bottom:2px}
.box{background:var(--code);border-radius:6px;padding:10px 12px}
details>summary{cursor:pointer;font-size:13px;color:var(--acc)}details .box{margin-top:6px;max-height:600px;overflow:auto}
.extra{display:block;margin-top:12px;font-size:13px}
@media (max-width:800px){nav{display:none}main{padding:12px 16px}}
"""


def esc(s):
    return html.escape(str(s if s is not None else ""))


def render_content(content, base):
    """content is a string or a list of OpenAI-style parts."""
    if isinstance(content, str):
        return f"<div class='txt'>{esc(content)}</div>"
    out, imgs = [], []

    def flush():
        if imgs:
            cls = "imgs frames" if len(imgs) > 8 else "imgs"
            out.append(f"<div class='{cls}'>" + "".join(
                f"<a href='{base}/{esc(u)}' target='_blank'><img loading='lazy' src='{base}/{esc(u)}'>"
                f"<span class='n'>{k + 1}</span></a>" for k, u in enumerate(imgs)) + "</div>")
            imgs.clear()

    for p in content or []:
        t = p.get("type")
        if t == "image_url":
            imgs.append((p.get("image_url") or {}).get("url", ""))
        elif t == "video_url":
            imgs.append((p.get("video_url") or {}).get("url", ""))
        else:
            flush()
            out.append(f"<div class='txt'>{esc(p.get('text', ''))}</div>")
    flush()
    return "".join(out)


def sample_html(kind, nn, d, rel):
    inp = json.loads((d / "input.json").read_text())
    outp = json.loads((d / "output.json").read_text()) if (d / "output.json").exists() else None
    meta = (outp or {}).get("meta") or inp.get("meta") or {}
    sid = f"{kind}-{nn}"
    tags = [f"n_images={meta.get('n_images', 0)}", f"turn {int(meta.get('turn') or 0) + 1}/{meta.get('n_turns', 1)}"]
    if meta.get("placement_fallback"):
        tags.append("placement_fallback")
    h = [f"<section class='s' id='{sid}'><h2>{KIND_NAME.get(kind, kind)} · #{nn}</h2>",
         f"<div class='id'>{esc(inp.get('id'))}</div>",
         f"<div class='id'>dataset: {esc(meta.get('dataset'))}</div>"]
    t = "".join(f"<span class='tag'>{esc(x)}</span>" for x in tags)
    if outp:
        c = (outp.get("choices") or [{}])[0]
        fin = c.get("finish_reason")
        t += f"<span class='tag {'good' if fin == 'stop' else 'bad'}'>finish={esc(fin)}</span>"
        u = outp.get("usage") or {}
        if u:
            t += f"<span class='tag'>tokens in {u.get('prompt_tokens', '?')} / out {u.get('completion_tokens', '?')}</span>"
        if outp.get("latency_s") is not None:
            t += f"<span class='tag'>{float(outp['latency_s']):.0f} s</span>"
    else:
        t += "<span class='tag bad'>仅输入（导出时还没有输出）</span>"
    h.append(f"<div class='tags'>{t}</div>")
    for m in inp.get("messages") or []:
        role = m.get("role", "?")
        h.append(f"<div class='msg {esc(role)}'><div class='role'>{esc(role)}</div>{render_content(m.get('content'), rel)}</div>")
    if meta.get("gt") is not None:
        h.append(f"<div class='blk'><div class='lab'>Ground truth（训练数据原答案，未给模型看）</div>"
                 f"<div class='box txt'>{esc(meta.get('gt'))}</div></div>")
    if outp:
        c = (outp.get("choices") or [{}])[0]
        rsn, ans = c.get("reasoning") or "", c.get("content") or ""
        h.append(f"<div class='blk'><details><summary>Teacher reasoning（{len(rsn):,} 字符，点开）</summary>"
                 f"<div class='box txt'>{esc(rsn)}</div></details></div>")
        h.append(f"<div class='blk'><div class='lab'>Teacher answer</div>"
                 f"<div class='box txt'>{esc(ans) if ans else '<i>（空：推理达到长度上限被截断）</i>'}</div></div>")
    h.append(f"<a class='extra' href='{rel}/sample.md'>sample.md</a></section>")
    return sid, "".join(h)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", default="samples")
    ap.add_argument("--out", default="site")
    a = ap.parse_args()
    src, out = Path(a.samples), Path(a.out)
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(src, out / "samples", ignore=shutil.ignore_patterns(".DS_Store"))
    root = src / "1115"
    nav, body, n = [], [], 0
    kinds = sorted([p.name for p in root.iterdir() if p.is_dir()],
                   key=lambda k: KIND_ORDER.index(k) if k in KIND_ORDER else 99)
    for kind in kinds:
        nav.append(f"<h3>{KIND_NAME.get(kind, kind)} ({kind})</h3>")
        for d in sorted(p for p in (root / kind).iterdir() if p.is_dir()):
            sid, sec = sample_html(kind, d.name, d, f"samples/1115/{kind}/{d.name}")
            nav.append(f"<a href='#{sid}'>#{d.name}</a>")
            body.append(sec)
            n += 1
    extra = ""
    if (src / "1113" / "review.html").exists():
        nav.append("<h3>其他</h3><a href='samples/1113/review.html'>11-13 帧率 smoke（review.html）</a>")
        extra = " · <a href='samples/1113/review.html'>11-13 帧率 smoke</a>"
    page = (f"<!doctype html><html lang='zh'><head><meta charset='utf-8'>"
            f"<meta name='viewport' content='width=device-width,initial-scale=1'><title>CoT Roll Samples</title>"
            f"<style>{CSS}</style></head><body><header><h1>CoT roll 样例（DSV4.1-Flash，11-15 导出）</h1>"
            f"<p>{n} 条 · 每条含实际发送的图像/帧、全部轮次、GT、完整推理与答案{extra}</p></header>"
            f"<div class='wrap'><nav>{''.join(nav)}</nav><main>{''.join(body)}</main></div></body></html>")
    (out / "index.html").write_text(page)
    (out / ".nojekyll").write_text("")
    print(f"wrote {out}/index.html with {n} samples")


if __name__ == "__main__":
    main()
