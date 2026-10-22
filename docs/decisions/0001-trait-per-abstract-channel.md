# 0001: One trait per abstract visual channel

Status: accepted

Date: 2026-10-22

Decided by: Tomasz Madera, stage 0 of `docs/features/visual-diversity/plan.md`

## Context

The product document rejects "arbitrary assignment of one trait to one prop" (`docs/product/emotional-repository-portrait-system.md:418-421`, section 10) and lists meme mappings such as "many tests -> glasses" and "many TODO -> scars" as anti-examples (`:84-91`, section 3).

`docs/features/visual-diversity/analysis.md` shows that portraits of different repositories look alike. The owner asked for the main conclusions about a repository to be readable at a glance. That needs a stable mapping a viewer can learn, which the product wording forbids if it is read as covering every visual property.

## Decision

1. Each trait may own one abstract perceptual channel. The channels are the ones in `docs/features/visual-diversity/design.md` "Visual grammar": footprint, growth rings or strata, saturation and motion speed, strands, focal knot, edge quality, topology of masses, hatching texture, and cracks.
2. The cracks channel is allowed: TODO and debt density drive a density of crack and erosion marks. Cracks are a mark density that every style draws its own way, not a fixed prop.
3. A channel is an abstract visual property, never an object or symbol. Styles change how a channel is drawn, never which trait drives it.
4. The ban on "one trait -> one prop" stays for props and character items. No trait maps to a fixed object, accessory, mascot or symbol (glasses, a scar as an item, monster versus robot). Character styles show traits only through the same abstract channels on the body plan and surface.

## Consequences

- This decision amends sections 3 and 10 of the product document for abstract channels only. The product document keeps its wording and points here.
- Adding a channel or reassigning a trait to another channel needs an update to this record.
- The prompt negative constraints against literal programmer symbols, text and mascots stay.
- Rejected alternatives: keeping the ban for channels too, which would leave the at-a-glance reading only to the caption and `summary.md`; and the channel rule without the cracks channel, which would leave debt without a visual reading.
