# Web Image Sourcing

Use sourced images to make a deck concrete and visually varied without waiting for every
visual to be generated. Search is not permission to reuse: record provenance and check
the asset's own license page before downloading it.

## When sourced images are better than AI generation

- real people, places, artworks, historical objects, products, documents, or events;
- photographic atmosphere where authenticity matters;
- public-domain archives, maps, diagrams, and scientific imagery;
- paper, fabric, architectural, or natural textures that can support a quiet background.

Use AI generation for a bespoke cover language, a fictional scene, or a concept that has
no trustworthy concrete image. Do not use AI to imitate a living artist, a copyrighted
book cover, or a recognizable film poster.

## Source order

1. Official institution, museum, library, government, or project media with an explicit
   reuse statement.
2. Wikimedia Commons file pages. Check the license on the individual file page and keep
   the named author, license, and license URL.
3. Pexels or Unsplash for general photography. Read the current platform license and
   avoid implying endorsement by identifiable people or brands.
4. Other sources only when their asset page states a reusable license clearly.

Never copy a search-result thumbnail, hotlink an image, or infer permission from the
absence of a watermark. Avoid low-resolution assets, screenshots of other presentations,
and decorative images whose license cannot be verified.

## Workflow

1. From the visual plan, write 2–4 concrete search queries in one batch. Include subject,
   visual role, orientation, and a preferred source when useful.
2. Open candidate landing pages. Verify the actual image, creator, reuse terms, and image
   dimensions. For sensitive contexts, also check whether recognizable people, brands,
   or private property create an endorsement or dignity risk.
3. Download the selected original or an appropriately sized derivative to `images/`.
   Keep the extension and never overwrite an existing file silently.
4. Create `media-manifest.json`, then run:

   ```bash
   python scripts/slides.py --json validate media-manifest.json --kind media-manifest
   ```

5. Reference only the local path in `outline.json`. The builder inlines it into the final
   HTML. Put required attribution in speaker notes or a visible source line when the
   license requires it.
6. Pass `--media-manifest media-manifest.json` to the production pipeline so provenance
   is checked with the other inputs.

## Media manifest example

```json
{
  "schema_version": "1.0",
  "deck_id": "urban-gardens",
  "reviewed": true,
  "assets": [
    {
      "asset_id": "community-garden-photo",
      "origin": "web",
      "role": "content",
      "local_path": "images/community-garden.jpg",
      "slide_ids": ["neighbors-grow-together"],
      "alt": "居民在社区花园中整理种植床",
      "fit": "cover",
      "focal_point": "62% 45%",
      "source_url": "https://example.org/photo-page",
      "author": "Photographer Name",
      "license": "CC BY 4.0",
      "license_url": "https://creativecommons.org/licenses/by/4.0/"
    }
  ]
}
```

## Placement and crop safety

- Use `contain` for complete objects, illustrations, diagrams, covers, documents, and
  any image whose edges matter.
- Use `cover` only for a photographic scene where cropping is acceptable. Record a focal
  point such as `62% 45%` and check that the subject remains inside a central 70% safe
  area at 16:9 and narrow browser widths.
- Decorative backgrounds may crop, but keep the text quiet zone empty and reduce contrast
  behind body copy.
- For cover heroes, set `hero_mode` to `float` or `frame`, `hero_fit` to `contain` or
  `cover`, and optionally `hero_position`. The default is `contain`; transparent PNG/WebP
  assets automatically use floating treatment.

This manifest documents reuse decisions but does not replace the license terms or legal
review required for regulated, commercial, or high-risk publishing.
