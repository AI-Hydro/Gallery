# AI-Hydro Gallery

Community catalog for reusable **AI-Hydro Research Gallery** map artifacts.

The Gallery is for research map scenes, style presets, dataset connectors, case
studies, and map plate templates that can be inspected, cited, imported, and
reused inside the AI-Hydro Map. It is not a code execution marketplace and it is
not a replacement for AI-Hydro Modules, Skills, or MCP tools.

## Browse in AI-Hydro

Open **AI-Hydro Map** and click the **Research Gallery** ribbon button. The
extension reads the static catalog from:

```text
https://ai-hydro.github.io/Gallery/api/gallery.json
```

## Repository Structure

```text
items/
  <gallery-item-id>/
    manifest.json
    README.md
    thumbnail.png
    artifact files or source references
api/
  gallery.json
.github/workflows/
  build-api.yml
```

## Artifact Types

- `map_scene` — AI-Hydro map scene JSON with layer stack, styles, extent, and provenance references.
- `style_preset` — reusable vector/raster symbology preset or a small style fixture.
- `dataset_connector` — a loadable GeoJSON, CSV, GeoTIFF, STAC, GEE, HydroShare, or lab-mirror pointer.
- `case_study` — basin/region scene with notes, validation metrics, citations, and provenance.
- `map_plate_template` — Research Plate Composer preset.

## Contribute

1. Fork this repository.
2. Create `items/<your-item-id>/manifest.json`.
3. Add small local artifacts only when they are safe to host in Git. Otherwise, use stable `artifactUrl` references.
4. Include license, citation, author, version, tags, and trust proposal.
5. Open a pull request.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the manifest checklist.

## License

Repository infrastructure is MIT. Individual Gallery items carry their own
licenses and citations in their manifests.
