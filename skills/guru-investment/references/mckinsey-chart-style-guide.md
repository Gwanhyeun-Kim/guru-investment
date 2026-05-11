# McKinsey Chart Style Guide for matplotlib Implementation

## 1. Typography
- **Headlines/Titles**: Serif font (Georgia as PPT substitute for proprietary "Bower"). Bold, 24-28pt.
- **Body/Labels**: Sans-serif (Arial or Helvetica). 16-18pt body, 12-14pt chart labels.
- **Action titles**: Full-sentence conclusions, not descriptive labels. E.g., "Revenue grew 3x in target segment" not "Revenue by Segment."

## 2. Color Palette
- **Primary dark**: Deep navy/black `#051C2C` (McKinsey dark blue) for primary text and key data
- **Highlight blue**: Vivid blue `#005EB8` for the single most important data series
- **Gray tones**: `#A2AAAD` (mid-gray), `#D0D0D0` (light gray) for secondary series and gridlines
- **Accent (sparing)**: Gold/amber `#F3C13A` for callout or alert emphasis
- **Background**: White `#FFFFFF`
- **Rule**: One highlight color per chart. If blue = client, gray = benchmark. Never swap mid-deck.

## 3. Layout Principles
- **Title placement**: Top-left, bold, full-sentence "action title" stating the insight
- **Subtitle/source**: Small gray text at bottom-left for source attribution
- **Generous white space**: Margins are wide; chart area does not fill the entire frame
- **Aspect ratio**: ~16:9 or 4:3; avoid too-tall or too-wide charts that distort slopes

## 4. Grid and Axis Styling
- **Gridlines**: Horizontal only, very light gray (`#E0E0E0` or lighter), thin (0.5pt)
- **No vertical gridlines**
- **Y-axis**: Minimal tick marks or none; labels only at key intervals
- **X-axis**: Thin baseline in dark gray; labels in regular-weight sans-serif
- **No chart border/frame**: Remove top and right spines entirely
- **Scale**: Make range explicit; always specify units (M, B, %). Keep consistent across comparison charts.

## 5. Data Point and Line Labeling
- **Direct labeling beats legends**: Label each line at its endpoint (right side) with the series name
- **No legend box** whenever possible
- **Selective data point labels**: Label only start, end, and key inflection points -- not every point
- **Line weight**: Primary series ~2pt, secondary series ~1-1.5pt in gray
- **No markers** on every point; use a small dot only at labeled inflection points

## 6. Distinctive Visual Elements
- **Callout annotations**: Short text boxes ("New pricing introduced here") with a thin line pointing to the relevant data point
- **Shaded regions**: Light fill to highlight a time period or range (e.g., light blue/gray band)
- **Arrows**: Thin arrows for growth indicators (e.g., CAGR annotation between two points)
- **Insight box**: Sometimes a bordered text box near the chart stating the "so what" in 1-2 sentences

## 7. Overall Philosophy
- **Ruthless minimalism**: Every element must serve the message. Remove anything that doesn't actively help comprehension.
- **"A chart is a sentence, not a picture of data"**: Each chart conveys exactly one point.
- **Simplify first, annotate second**: If you need many annotations, the chart design itself is the problem.
- **Functional color, not decorative**: No rainbows, gradients, or heavy fills.

---
*Sources: Umbrex, Slideworks, SlideUplift, Analyst Academy, Visual Sculptors, Stratechi (2024-2026)*
