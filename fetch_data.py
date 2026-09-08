"""
fetch_data.py
=============
Standalone entry point for "pull and cache historical prices for expired
option contracts" (assignment requirement #1) -- run this on its own,
without starting the Reflex app.

    python fetch_data.py

Cache-first: if option_pipeline_data.pkl already exists next to this file,
it does nothing (the app/preview builder both load that file directly).
Delete the pickle to force a re-pull.

Real LSEG pull requires LSEG Workspace/Eikon running and logged in on this
machine, plus `lseg.data` (or legacy `eikon`) installed and configured with
an app key. Without that, this synthesizes a realistic sparse UUUU-like
panel so the rest of the pipeline (parsing, plotting, the two required
stats) can still be built and demoed, and caches THAT to the same pickle
path, clearly flagged with payload["synthetic"] = True, so the app/preview
always load from the pickle rather than silently regenerating on every run.

To force a fresh pull (e.g. a later as-of date), delete
option_pipeline_data.pkl, re-run this file with LSEG Workspace open, then
re-run build_preview.py and re-commit.
"""

from __future__ import annotations

import os
import pickle

from options_surface_app import CACHE_FILE, load_or_fetch_pipeline_data
from option_surface_utils import synthesize_demo_payload


def main():
    if os.path.exists(CACHE_FILE):
        print(f"{CACHE_FILE} already exists -- delete it first to force a re-pull.")
        return

    try:
        import lseg.data as _probe  # noqa: F401

        have_lseg = True
    except Exception:
        have_lseg = False

    if have_lseg:
        payload = load_or_fetch_pipeline_data()  # this branch pickles for us on success
        if os.path.exists(CACHE_FILE):
            print(f"Done (REAL LSEG pull). Cached to {CACHE_FILE}.")
            return
        payload["synthetic"] = True  # real pull failed at runtime; fall through below
    else:
        payload = synthesize_demo_payload()

    with open(CACHE_FILE, "wb") as f:
        pickle.dump(payload, f)
    print(f"Done (SYNTHETIC demo panel -- no LSEG session available). Cached to {CACHE_FILE}.")
    print("Run this again after deleting the pickle once LSEG Workspace is open, to get real data.")


if __name__ == "__main__":
    main()
