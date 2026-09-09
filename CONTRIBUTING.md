# Contributing

## Documentation

`docs/guide.md` is the operator guide for this plugin. It is the single place
configuration is documented — the README deliberately stays short — and it is
aggregated into the central ADL documentation site.

**A pull request that touches the connection or station-link models (adding,
removing or renaming a field, changing a default or a validation rule), the
schedule blocks, the variable-mapping or SYNOP-mapping models, or any admin
surface this plugin adds (the connection overview, station detail, office
entry, the SYNOP wizard and archive, the monitoring dashboard, the field app)
must update `docs/guide.md` in the same PR.**

If the change is visible on screen, also update `docs/screenshots.yml` and
regenerate the images with the capture harness in the `adl` repo:

```bash
# from a checkout of wmo-raf/adl, with Docker running
scripts/capture-plugin-docs.sh ../adl-plugins/adl-collector-app-plugin
```

`--only <entry>` re-shoots a single entry, which is what to use for a crop fix:
a full run re-renders every image and the dashboard shots carry live
timestamps, so fixing one crop otherwise lands as a diff in unrelated images.

### The demo data

This plugin's "source" is ADL's own database, so there is nothing to mock —
the demo has to contain observations somebody submitted.
`docs/screenshots/seed.py` runs inside the web container after the fixture is
applied and creates the observer users, attaches them to each station link,
and writes two days of office and field submissions. It deliberately includes
one submission dated before the link's *Collection Start Date*, because the
guide documents the unprocessed-backlog state and an operator meeting it
needs to recognise the screen.

If you change the submission or observer models, change that script in the
same PR, or the capture stops producing the screens the guide describes.

### Two screenshots that document a defect

`collector_synop_preview` and `collector_field_app` deliberately capture the
*form* and the *sign-in screen* rather than the decode preview and the
value-entry screen, because neither of those can be reached in 0.2.1 (issues
[#14](https://github.com/wmo-raf/adl-collector-app-plugin/issues/14) and
[#11](https://github.com/wmo-raf/adl-collector-app-plugin/issues/11)). Each
manifest entry carries the steps to restore once the defect is fixed, and the
guide carries a note to remove. Please do both in the fixing PR.

Images are code: never hand-edit a PNG in `docs/images/`; change the manifest
entry and regenerate. Keep images free of text (only numbered badges), since
the docs are translated.

Messages the plugin shows to operators are listed verbatim-shaped in the
guide's feedback catalogue — add a row when you add or change one.

## Development

See the README for the dev stack. Lint with `make lint` and format with
`make format` inside `plugins/adl_collector_app_plugin/`.

## Releases

Tag releases bare (`0.3.0`, never `v0.3.0`): `plugins.toml` entries pin the tag
verbatim. Use `gh release create 0.3.0`.
