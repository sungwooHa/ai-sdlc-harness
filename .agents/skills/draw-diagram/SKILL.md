---
name: svg-diagram
description: Use this skill when the user asks to create SVG diagrams including sequence diagrams, flowcharts, structural/architecture diagrams, or illustrative diagrams. Triggers include any mention of 'SVG', 'diagram', 'sequence diagram', 'flowchart', 'architecture diagram', or requests to visualize system flows, processes, or structures. Also use when the user wants to modify or iterate on an existing SVG diagram. Do NOT use for charts/graphs, ERDs (use mermaid), or image generation.
---

# SVG Diagram Skill

Create clean, professional SVG diagram files. Covers sequence diagrams, flowcharts, structural diagrams, and illustrative diagrams.

## Environment Detection & Output

### CLI Agent
- `visualize:show_widget` is NOT available
- Write standalone `.svg` files to disk
- Must include `xmlns="http://www.w3.org/2000/svg"` on root element
- Embed all styles in `<defs><style>` block — no external CSS variables
- Use hardcoded hex colors from the palette below

### Web Chat Agent
- If `visualize:show_widget` is available, call `visualize:read_me` with `modules: ["diagram"]` first
- The widget provides CSS variables and `c-blue` style classes — use those instead of hardcoded colors

## Standalone SVG Template (CLI)

```xml
<svg xmlns="http://www.w3.org/2000/svg" width="680" viewBox="0 0 680 {H}">
  <defs>
    <style>
      text { font-family: -apple-system, "Segoe UI", Helvetica, Arial, sans-serif; }
      .th { font-size: 14px; font-weight: 500; fill: #2C2C2A; }
      .ts { font-size: 12px; font-weight: 400; fill: #5F5E5A; }
      .t  { font-size: 14px; font-weight: 400; fill: #2C2C2A; }
      .arr { stroke: #888780; stroke-width: 1.5; }
      .leader { stroke: #B4B2A9; stroke-width: 0.5; stroke-dasharray: 3 3; }
    </style>
    <marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5"
      markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="context-stroke"
        stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
    </marker>
  </defs>
  <!-- content here -->
</svg>
```

Replace `{H}` with content bottom + 40px.

## Color Palette (hardcoded hex)

| Name | Fill | Stroke | Title text | Subtitle text |
|------|------|--------|------------|---------------|
| Blue | #E6F1FB | #185FA5 | #0C447C | #185FA5 |
| Teal | #E1F5EE | #0F6E56 | #085041 | #0F6E56 |
| Purple | #EEEDFE | #534AB7 | #3C3489 | #534AB7 |
| Coral | #FAECE7 | #993C1D | #712B13 | #993C1D |
| Amber | #FAEEDA | #854F0B | #633806 | #854F0B |
| Green | #EAF3DE | #3B6D11 | #27500A | #3B6D11 |
| Gray | #F1EFE8 | #5F5E5A | #444441 | #5F5E5A |
| Red | #FCEBEB | #A32D2D | #791F1F | #A32D2D |
| Pink | #FBEAF0 | #993556 | #72243E | #993556 |

Usage:
```xml
<rect fill="#E6F1FB" stroke="#185FA5" stroke-width="0.5" rx="8" .../>
<text fill="#0C447C" class="th" text-anchor="middle" dominant-baseline="central" ...>Label</text>
```

Rules: max 2-3 ramps per diagram. Color encodes meaning, not sequence.

## Typography

| Class | Size | Weight | Purpose |
|-------|------|--------|---------|
| th | 14px | 500 | Titles, node labels |
| ts | 12px | 400 | Subtitles, arrow labels |
| t | 14px | 400 | Body text |

Width estimation: 14px ~ 8px/char, 12px ~ 7px/char.
Box width = max(title_chars x 8, subtitle_chars x 7) + 24px padding.

SVG text never auto-wraps. If subtitle needs wrapping, shorten it.

## Node Patterns

### Single-line (44px)
```xml
<g>
  <rect x="100" y="20" width="180" height="44" rx="8"
    fill="#E6F1FB" stroke="#185FA5" stroke-width="0.5"/>
  <text class="th" x="190" y="42" text-anchor="middle"
    dominant-baseline="central" fill="#0C447C">Label</text>
</g>
```

### Two-line (56px)
```xml
<g>
  <rect x="100" y="20" width="200" height="56" rx="8"
    fill="#E1F5EE" stroke="#0F6E56" stroke-width="0.5"/>
  <text class="th" x="200" y="38" text-anchor="middle"
    dominant-baseline="central" fill="#085041">Title</text>
  <text class="ts" x="200" y="56" text-anchor="middle"
    dominant-baseline="central" fill="#0F6E56">Subtitle</text>
</g>
```

### Connectors
- Solid (request): stroke-width="1" marker-end="url(#arrow)"
- Dashed (response): add stroke-dasharray="4 3"
- L-bend (avoid crossing): <path d="M x1 y1 L x1 ymid L x2 ymid L x2 y2" fill="none" .../>

## Diagram Types

| Intent | Type |
|--------|------|
| "process/steps/flow" | Flowchart |
| "architecture/structure" | Structural |
| "how does X work" | Illustrative |
| "API call sequence" | Sequence |
| "DB schema / ERD" | mermaid (not this skill) |

### Sequence Diagram
- Actor boxes at top (44px), evenly spaced
- Dashed vertical lifelines below each actor
- Activation bars: 12px wide rects on lifelines
- Solid arrows = request, dashed arrows = response
- 30-40px vertical spacing between messages
- Actor spacing: 2 actors (170,510), 3 actors (130,340,550), 4 actors (100,250,430,580)

### Flowchart
- Max 4-5 nodes; split complex flows across multiple diagrams
- Single direction preferred (top-down or left-right)
- 60px min spacing between boxes
- Check every arrow for box-crossing — route around with L-bend if needed
- Tier width: N x box_width + (N-1) x gap must be <= 600

### Structural
- Outer container: rx=20, lightest fill, 0.5px stroke
- Inner regions: rx=12, different color ramp from parent
- 20px padding inside containers, max 2-3 nesting levels

### Illustrative
- Draw the mechanism itself, not boxes about it
- Freeform shapes: path, ellipse, circle, polygon
- Color = intensity (warm=active, cool=dormant)
- Labels outside the object with leader lines
- One linearGradient allowed for continuous physical properties

## Layout Checklist

1. ViewBox height = bottom-most element + 40px
2. Content within x=0..680
3. Text fits boxes (chars x px + padding < width)
4. No arrows cross unrelated boxes
5. Every text element has class + explicit fill
6. Every connector path has fill="none"
7. Borders: stroke-width 0.5px
8. Rounding: rx=4 default, rx=8 emphasis
9. xmlns on root svg for standalone files
10. No CSS variables in standalone SVG — hardcode all colors