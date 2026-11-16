# CoT roll review

`samples/` holds the exported CoT roll samples; `scripts/build.py` renders them to `site/`, and the Pages workflow builds and deploys on every push to main.

Add a new export: copy it under `samples/<date>/<kind>/<NN>/` (or extend build.py), commit, push.

Local preview: `python3 scripts/build.py && open site/index.html`
