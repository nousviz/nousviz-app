# ML Runtime utility

Installs a pinned set of open-source machine learning libraries into the
NousViz Python environment, so analytics plugins can train and score models
on the install's own data.

| Library | Version | Licence | Used for |
|---|---|---|---|
| [LightGBM](https://lightgbm.readthedocs.io) | 4.7.0 | MIT | Gradient-boosted trees: forecasting (incl. quantile), ranking |
| [scikit-learn](https://scikit-learn.org) | 1.9.1 | BSD-3-Clause | Anomaly detection (Isolation Forest), metrics, preprocessing |
| [numpy](https://numpy.org) | 2.5.3 | BSD-3-Clause | Arrays; required by both of the above |
| scipy, joblib, threadpoolctl | 1.18.1, 1.6.0, 3.7.0 | BSD-3-Clause | Dependencies of scikit-learn; joblib also saves models |

Verified together on Python 3.12, 2026-09-26.

## For operators

**Install:** Marketplace → Utilities → ML Runtime → Install. No settings.
The platform pip-installs the libraries (about 270 MB on disk, a minute or two) and
the install hook proves they import.

**Extra work:** none on a standard Linux server. Minimal images without a
C/C++ toolchain may lack the OpenMP runtime LightGBM needs; the install then
fails with the fix spelled out:

```bash
sudo apt-get install -y libgomp1      # Debian/Ubuntu
sudo dnf install -y libgomp           # RHEL/Fedora
```

**Check it:** the utility's health appears in the topbar health menu and at
`/api/health` under `services.ml-runtime`, with the installed versions. It
turns red if a library is missing, and warns if a version differs from the
pin.

**If NousViz's Python environment is rebuilt** (fresh `.venv`, server move,
reinstall), the libraries go with it. Health turns red; reinstall this
utility, or run:

```bash
.venv/bin/python3 -m pip install -r plugins/installed/ml-runtime/requirements.txt
```

**Uninstall** leaves the libraries in place (other code may use numpy or
scipy) and prints the command to remove them. The platform refuses to
uninstall it while a plugin still requires it.

## For plugin authors

Declare the capability, then import the libraries in your **sync script**:

```yaml
# plugin.yaml
requires:
  ml_runtime: true
```

```python
# src/<slug>_ml.py — called from your sync script
import lightgbm as lgb
```

- **Train in the sync job, never in an API route.** Routes run inside the
  API's web workers; a training run there blocks requests. The jobs-worker
  runs sync scripts in their own process with the same Python environment.
- **Do not pin these libraries in your plugin's own requirements.txt.** All
  plugins share one environment, so a second pin would silently up- or
  downgrade numpy for everyone. Rely on this utility's versions and read
  them at runtime (`importlib.metadata.version("lightgbm")`) to record
  which version trained a model.
- **Store models in your plugin's database**, not on disk: LightGBM's
  `model_to_string()` gives text that survives server moves and backups.
- Need another library (e.g. XGBoost, Apache-2.0)? Add it here, verified
  alongside the existing pins, rather than in your plugin.

## Upgrading the libraries

1. Change the pins in `requirements.txt` and bump `version:` in
   `plugin.yaml`.
2. Verify the set together in a scratch venv made from the same Python:
   `python3 -m venv /tmp/v && /tmp/v/bin/pip install -r requirements.txt`,
   then import and fit a small model.
3. Note it in the CHANGELOG. Existing installs pick up the new pins when
   the operator updates the utility, on NousViz versions whose plugin
   update installs `requirements.txt` (branch
   `plugin-update-installs-deps`). On older versions, run the pip command
   above after updating.

## Decision: one shared Python environment

The libraries go into the same environment as the API and the jobs-worker
(both `$NOUSVIZ_DIR/.venv`), rather than a separate one owned by this
utility.

**Why:** plugin sync scripts can `import lightgbm` directly. With a separate
environment, every ML plugin would have to launch a second Python process,
pass its data and credentials to it through files, and handle that
process's failures itself; the SDK's credential broker is not available in
a separately built environment. That is real work and a new class of bugs
in every plugin, to guard against a conflict that does not exist today.

**The risk accepted:** one environment means one version of each package.
Core itself uses none of these libraries (checked 2026-09-26), so there is
no clash now. The guards: this utility is the only place they are pinned,
plugins are told not to pin them, and the health check reports drift.

**When to revisit:** if core or a widely used plugin starts needing a
conflicting numpy or scipy, move this utility to its own environment and
give plugins a small runner helper in the SDK.
