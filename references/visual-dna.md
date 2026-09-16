# Visual DNA — Apple iOS 26 Liquid Glass (CSS)

This is the deck-level style-lock. Keep these constants identical across every slide; vary only the central content. The look is translated from Apple's native Liquid Glass design language (see the ECC `liquid-glass-design` skill, which targets SwiftUI/UIKit/WidgetKit) into pure CSS.

## The cardinal rule
Glass must sit over a vivid, blurred, colorful backdrop. Flat or opaque backgrounds destroy the refraction. Build a colorful mesh + floating blurred blobs behind everything, then float frosted panels on top.

## Background
- A light, premium mesh: soft pastel plus one or two vivid accent blobs (iOS blue, a warm magenta, a mint) at low opacity.
- 2–3 blurred circles drifting slowly (subtle, ~20–30s loop) for life.
- Keep overall light; do not go dark unless the user asks.

## Glass panel (apply to every card / nav chrome)
- `background: rgba(255,255,255,0.55);`
- `backdrop-filter: blur(30px) saturate(200%);` plus the `-webkit-` prefix.
- `border-radius: 26–30px;` (large, organic).
- Top specular highlight: `box-shadow: inset 0 1px 1px rgba(255,255,255,0.85), 0 10px 40px rgba(0,0,0,0.10);`

## Edge light (chromatic rim)
Use a gradient border via a masked pseudo-element so the rim catches light:
```
.glass::before{
  content:""; position:absolute; inset:0; border-radius:inherit; padding:1px;
  background:linear-gradient(135deg, rgba(255,255,255,.9), rgba(255,255,255,.1) 40%, rgba(120,180,255,.25) 72%, rgba(255,255,255,.6));
  -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
  -webkit-mask-composite: xor; mask-composite: exclude;
  pointer-events:none;
}
```

## Light-reactive depth
- On hover / active, lift the panel slightly (`translateY(-4px)`) and strengthen the highlight + shadow — mimics glass responding to touch/pointer (the native `.interactive()` idea).
- Keep motion subtle (200–300ms).

## Typography
- Font stack: `-apple-system, "SF Pro Display", "PingFang SC", "Helvetica Neue", "Microsoft YaHei", sans-serif`
- Headings: weight 600–700, letter-spacing -0.02em, line-height ~1.1, near-black `#1D1D1F`.
- Body: weight 400, line-height 1.6, secondary `#515158`.
- Use `clamp()` for all sizes.

## Accent
- Default vivid iOS blue `#0A84FF`; allow a single brand tint. Keep one accent across the whole deck.

## Avoid
- Flat / opaque backgrounds behind glass.
- Over-applying glass (reserve for floating panels, nav, captions).
- Purple-on-white startup templates.
- Long bullet walls; tiny type; scrollbars inside a slide.
- Baking required text into images.
