# CoT roll review

Interactive viewer for exported CoT roll samples: https://yizeezliu.github.io/cot-roll-review/

- `samples/<export>/<kind>/<NN>/` — exported samples (`input.json`, `output.json`, `img_XX.jpg`, `sample.md`)
- `scripts/build.py` + `scripts/app.html` — render everything into `site/` (data inlined, works from disk too)
- `.github/workflows/pages.yml` — every push to `main` rebuilds and deploys to Pages

Add an export: copy it to `samples/<date>/…`, commit, push. Local preview: `python3 scripts/build.py && open site/index.html`.

Keys: `j`/`k` next/prev sample · `/` search · `r` toggle reasoning · `←`/`→` frames · space play.
