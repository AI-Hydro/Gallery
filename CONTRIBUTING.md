# Contributing to AI-Hydro Gallery

Gallery entries are reviewed research map artifacts. They must be safe to load,
traceable, and scientifically citeable.

If you are not ready to prepare a pull request, open the
[new Gallery item template](https://github.com/AI-Hydro/Gallery/issues/new?template=new_gallery_item.md)
with your source, license, citation, and preview. Maintainers can help decide
whether it should become a scene, style preset, dataset connector, case study,
or map plate template.

## Required Manifest Fields

```json
{
  "id": "my-gallery-item",
  "type": "map_scene",
  "title": "Readable title",
  "description": "What this imports and why it is useful.",
  "version": "0.1.0",
  "author": "Name or lab",
  "license": "CC-BY-4.0",
  "trustLevel": "community",
  "tags": ["watershed", "style"],
  "thumbnailUrl": "",
  "githubUrl": "",
  "artifactUrl": "",
  "citation": "Dataset or method citation.",
  "createdAt": "2026-05-28",
  "updatedAt": "2026-05-28",
  "isFeatured": false
}
```

Allowed `type` values:

- `map_scene`
- `style_preset`
- `dataset_connector`
- `case_study`
- `map_plate_template`

Allowed `trustLevel` values:

- `official`
- `reviewed`
- `community`
- `local`

## Review Checklist

- The artifact does not execute code.
- The artifact is loadable through normal AI-Hydro Map import paths.
- License and citation are explicit.
- Large assets are referenced by URL, not committed directly.
- Any limitations or warnings are included in `importWarnings`.
- Dataset source and provenance are described in the item README.

## Static API

The GitHub Action regenerates `api/gallery.json` from `items/**/manifest.json`.
Do not edit `api/gallery.json` by hand unless the workflow is unavailable.
