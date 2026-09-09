# ADL Collector App Plugin

Brings **manually observed** data into an [ADL](https://github.com/wmo-raf/adl)
instance. Nothing is fetched from a source: observations are typed into ADL —
by office staff on a **Direct Data Entry** form or by pasting a **SYNOP
FM-12** message, and by field observers in a small **progressive web app** on
a phone, which queues submissions while offline. A scheduled sweep turns the
stored submissions into observation records.

One connection groups the manned stations; one station link per station holds
its parameter mappings, its observers and its reporting schedule (fixed
synoptic slots, or a window with a cut-off).

**Operator guide:** [docs/guide.md](docs/guide.md) — prerequisites, every
connection and station-link field, the schedule blocks, office entry, the
SYNOP wizard and archive, the field app, the monitoring dashboard,
diagnostics and troubleshooting. The guide is also published on the central
ADL documentation site.

## Known defects in 0.2.1

Both are documented in the guide and are worth knowing before deploying:

- **SYNOP decoding does not work** — `pymetdecoder` is declared in
  `requirements/base.in`, but the compiled `base.txt` the package installs
  from was built empty ([#14](https://github.com/wmo-raf/adl-collector-app-plugin/issues/14)).
- **Field observers cannot submit** — the app sends its token with the
  `Token` scheme, which ADL core does not accept
  ([#11](https://github.com/wmo-raf/adl-collector-app-plugin/issues/11)).

Office direct entry is unaffected by both.

## Development setup

The plugin runs inside the ADL core image. Build the `adl:latest` image from
the [ADL core repository](https://github.com/wmo-raf/adl) first, then:

```bash
git clone https://github.com/wmo-raf/adl-collector-app-plugin.git
cd adl-collector-app-plugin
cp .env.sample .env        # set PLUGIN_BUILD_UID=$(id -u), PLUGIN_BUILD_GID=$(id -g), ADL_DB_PASSWORD
docker compose build
docker compose up
docker compose exec adl adl createsuperuser
```

The admin is served on `PORT` (default 8080). The plugin source is
bind-mounted, so code changes reload the dev server. The field app is a Vue
build under `src/adl_collector_app_plugin/vue-pwa/`; its compiled bundle is
committed, so a change there needs a rebuild to take effect. If the image
build fails with `pull access denied` for `adl:latest`, prefix it with
`DOCKER_BUILDKIT=0`.

Tests are Django-runner tests under
`plugins/adl_collector_app_plugin/src/adl_collector_app_plugin/tests/`. Lint
and format from `plugins/adl_collector_app_plugin/` with `make lint` and
`make format`. See [CONTRIBUTING.md](CONTRIBUTING.md) — a change to any
connection or station-link field must update the guide in the same PR.
