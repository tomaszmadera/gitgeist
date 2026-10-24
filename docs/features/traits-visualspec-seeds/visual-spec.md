# VisualSpec schema

`gitgeist.schemas.visual_spec.VisualSpec` is the renderer-neutral scene for
stage 3. Its contract and formulas are in the [approved spec](spec.md).
`gitgeist.visual.build_visual_spec` builds it from features v2, `Traits` and
an `IdentitySeed`. All models use Pydantic v2, are frozen and forbid extra
fields. JSON roundtrips preserve their values. Stage 3 does not write a
`visual-spec.json` CLI artifact or draw these scenes.

## Coordinates and identity

The footprint is a circle of radius 1 at (0, 0). Mass positions, radii and
knot offsets use these units. A renderer scales the composition by
`footprint.coverage`, a fraction of frame diameter. Changing `size` changes
the footprint only.

| Field | Type and range |
|---|---|
| `schema_version` | Literal `"1"` |
| `representation` | `"abstract"` or `"character"` |
| `style` | Resolved registered name: `"orbits"` or `"creature"` |
| `style_requested` | `"auto"` or the requested name |
| `variety` | `"low"`, `"medium"` or `"high"` |
| `seeds.identity_seed` | 64 lowercase hexadecimal characters |
| `seeds.user_seed` | Integer 0 to 2^63 - 1, or `null` |
| `seeds.style_seed`, `seeds.effective_seed` | Unsigned 64-bit integers |
| `traits.scale` | `"absolute"` or `"corpus"` |
| `traits.table_version` | String for corpus mode; `null` for absolute mode |
| `traits.reference_time` | Aware UTC datetime; default is extraction day's midnight UTC |
| `traits.size`, `age`, `alive`, `crowd`, `focus`, `care`, `sprawl`, `prose`, `debt` | Each [0, 1], stored to 6 decimal places |

Style and effective seeds follow the SHA-256 formulas in the spec. The
`layout`, `hue`, `strands` and `cracks` labels give independent random streams.
The knot uses the start angle of the layout stream. Seeds do not change
traits, factual mass shares, order or counts of marks.

## Scene parts

| Part | Fields and ranges |
|---|---|
| `footprint` | `coverage` [0.25, 0.85]; integer `element_count` [40, 600] |
| `masses` | List of 0 to 8 `SpecMass` objects in factual structure order |
| `SpecMass` | `name` string; `is_merged` boolean; `file_share` and `churn_share` [0, 1]; `language` string or `null`; `hue` [0, 360) or `null`; finite `x`, `y`; `radius` [0, 1] |
| `rings` | `first_year` integer or `null`; `thickness` list of 0 to 40 values in [0, 1], oldest first |
| `palette` | `mode` is `"language"`; `saturation` [0.10, 0.85]; `hue_offset` within +/-10, +/-25 or +/-45 degrees for low, medium or high variety |
| `knot` | `null` or one `Knot`: `mass_index` points into `masses`; `path` string; finite `offset_x`, `offset_y`; `radius` [0.15, 0.50] as a share of its mass radius; `flicker` [0, 1] |
| `strands` | Integer `count` [1, 12]; `paths` has exactly `count` entries |
| `StrandPath` | `phase` [0, 1); `curvature` [-1, 1] |
| `cracks` | Integer `count` [0, 60]; `marks` has exactly `count` entries |
| `CrackMark` | `mass_index` points into `masses`; polar radius share `u` [0, 1]; polar angle share `v` [0, 1); `angle` [0, 360) degrees |
| `hatching` | `coverage` [0, 0.60] of mass area |
| `edge` | `blur_px` [0, 6]; `jitter` [0, 0.25] as a share of radius |
| `topology` | Integer `nesting_levels` [0, 3] per mass |
| `motion` | `speed_hz` [0.05, 1.2]; `loop_seconds` is 12.0; `pulse` is a list of monthly values in [0, 1] |

Mass radii start at `sqrt(file_share)`. Packing uses golden-angle rays,
0.01-unit search steps and bounded jitter, then scales the whole composition
to fit the unit circle. A mass without a language has `hue = null` and is
drawn neutral (mass saturation 0). Other masses use the global saturation.

Rings group the monthly timeline by calendar year, including quiet years.
If there are more than 40 years, the oldest years form the first ring, then
all ring thicknesses are normalized by the largest resulting group. Without
history, rings and motion pulse are empty. Without masses, there is no knot
and there are no crack marks. A merged `other` takes precedence over a real
directory named `other` when resolving that hotspot mass name.

## Example

The following scene is copied from the committed
[`single-script-abstract.json`](../../../tests/golden/visual_spec/single-script-abstract.json)
snapshot. Regenerate snapshots only by running the golden test with
`GITGEIST_UPDATE_GOLDEN=1`.

```json
{
  "schema_version": "1",
  "representation": "abstract",
  "style": "orbits",
  "style_requested": "auto",
  "variety": "medium",
  "seeds": {
    "identity_seed": "97fb87284557562049995b5ecebf25733b110ab88f6e077831f1cd9f77de4350",
    "user_seed": null,
    "style_seed": 16453198283450077755,
    "effective_seed": 1522113844098133332
  },
  "traits": {
    "scale": "absolute",
    "table_version": null,
    "reference_time": "2026-04-16T00:00:00Z",
    "size": 0.0,
    "age": 0.023946,
    "alive": 0.704486,
    "crowd": 0.0,
    "focus": 0.0,
    "care": 0.0,
    "sprawl": 0.0,
    "prose": 0.0,
    "debt": 0.0
  },
  "footprint": {
    "coverage": 0.25,
    "element_count": 40
  },
  "masses": [
    {
      "name": ".",
      "is_merged": false,
      "file_share": 1.0,
      "churn_share": 1.0,
      "language": "Shell",
      "hue": 134.0307475288586,
      "x": 0.0257969949740088,
      "y": -0.00859913122641567,
      "radius": 0.9728075376705574
    }
  ],
  "rings": {
    "first_year": 2026,
    "thickness": [
      1.0
    ]
  },
  "palette": {
    "mode": "language",
    "saturation": 0.6283644999999999,
    "hue_offset": 24.030747528858598
  },
  "knot": {
    "mass_index": 0,
    "path": "run.sh",
    "offset_x": -0.3742962627379004,
    "offset_y": -0.31062989881465675,
    "radius": 0.15,
    "flicker": 1.0
  },
  "strands": {
    "count": 1,
    "paths": [
      {
        "phase": 0.07366656923420611,
        "curvature": -0.38679676127857077
      }
    ]
  },
  "cracks": {
    "count": 0,
    "marks": []
  },
  "hatching": {
    "coverage": 0.0
  },
  "edge": {
    "blur_px": 6.0,
    "jitter": 0.25
  },
  "topology": {
    "nesting_levels": 0
  },
  "motion": {
    "speed_hz": 0.8601589,
    "loop_seconds": 12.0,
    "pulse": [
      1.0
    ]
  }
}
```
