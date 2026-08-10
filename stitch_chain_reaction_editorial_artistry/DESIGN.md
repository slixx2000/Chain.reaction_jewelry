---
name: Obsidian & Gold
colors:
  surface: '#131410'
  surface-dim: '#131410'
  surface-bright: '#3a3935'
  surface-container-lowest: '#0e0e0b'
  surface-container-low: '#1c1c18'
  surface-container: '#20201c'
  surface-container-high: '#2a2a26'
  surface-container-highest: '#353530'
  on-surface: '#e5e2db'
  on-surface-variant: '#c4c7c7'
  inverse-surface: '#e5e2db'
  inverse-on-surface: '#31312c'
  outline: '#8e9192'
  outline-variant: '#444748'
  surface-tint: '#c9c6c5'
  primary: '#c9c6c5'
  on-primary: '#313030'
  primary-container: '#090909'
  on-primary-container: '#7a7978'
  inverse-primary: '#5f5e5e'
  secondary: '#f6be39'
  on-secondary: '#402d00'
  secondary-container: '#c59300'
  on-secondary-container: '#433000'
  tertiary: '#ffb3b3'
  on-tertiary: '#630d19'
  tertiary-container: '#1d0002'
  on-tertiary-container: '#c3565c'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#e5e2e1'
  primary-fixed-dim: '#c9c6c5'
  on-primary-fixed: '#1c1b1b'
  on-primary-fixed-variant: '#474646'
  secondary-fixed: '#ffdf9f'
  secondary-fixed-dim: '#f6be39'
  on-secondary-fixed: '#261a00'
  on-secondary-fixed-variant: '#5c4300'
  tertiary-fixed: '#ffdad9'
  tertiary-fixed-dim: '#ffb3b3'
  on-tertiary-fixed: '#40000a'
  on-tertiary-fixed-variant: '#82252d'
  background: '#131410'
  on-background: '#e5e2db'
  surface-variant: '#353530'
typography:
  display-lg:
    fontFamily: Bodoni Moda
    fontSize: 84px
    fontWeight: '700'
    lineHeight: 90px
    letterSpacing: -0.02em
  display-lg-mobile:
    fontFamily: Bodoni Moda
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 52px
    letterSpacing: -0.01em
  headline-lg:
    fontFamily: Bodoni Moda
    fontSize: 48px
    fontWeight: '400'
    lineHeight: 56px
    letterSpacing: 0.02em
  headline-md:
    fontFamily: Bodoni Moda
    fontSize: 32px
    fontWeight: '400'
    lineHeight: 40px
  body-lg:
    fontFamily: Hanken Grotesk
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Hanken Grotesk
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  label-caps:
    fontFamily: Hanken Grotesk
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.15em
  nav-link:
    fontFamily: Hanken Grotesk
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
    letterSpacing: 0.05em
spacing:
  margin-desktop: 64px
  margin-mobile: 20px
  gutter: 24px
  section-gap: 160px
  stack-sm: 8px
  stack-md: 24px
---

## Brand & Style
The design system embodies a "Contemporary African Luxury" aesthetic—a fusion of Zambian artisanal heritage and high-fashion editorial rebellion. The visual narrative is unapologetically bold, favoring a "Dark Mode" first approach that mirrors the depth of an obsidian stone. 

The style is rooted in **Editorial Minimalism** with **Brutalist leanings**. It rejects the soft, approachable nature of modern SaaS interfaces in favor of sharp edges, thin structural lines, and dramatic asymmetry. The user experience should feel like flipping through a premium physical lookbook: high-contrast, tactile (through grain and texture), and intentionally spacious. The "rebellious" streak is expressed through unconventional grid placements and massive, overlapping typography.

## Colors
The palette is dominated by **Obsidian (#090909)**, providing a deep, infinite canvas that makes jewelry photography "pop." **Warm Ivory (#F1EEE7)** serves as the primary engine for legibility, used for all body text and critical UI labels to maintain high contrast.

**Antique Gold (#D6A21A)** is the "spark." Use it sparingly: for active states, price points, or singular iconic flourishes. It should never be used for large surfaces. **Deep Burgundy (#5C0715)** acts as a whisper of color—ideal for subtle hover states on dark backgrounds or highlighting "Limited Edition" status. **Charcoal (#151515)** provides the necessary tonal shift for subtle section layering without breaking the dark aesthetic.

## Typography
The typography relies on the tension between the high-contrast, romantic **Bodoni Moda** and the surgical precision of **Hanken Grotesk**. 

- **Campaign Headlines:** Use `display-lg` with tight tracking for a high-fashion impact. 
- **Product Names:** Use `headline-lg` to convey craftsmanship.
- **Labels:** Small, uppercase `label-caps` are used for navigation, price tags, and technical specs. These must always have generous letter spacing (0.15em) to maintain an airy, luxury feel.
- **Body Text:** Keep paragraphs concise. Use `body-lg` for descriptions to allow the ivory text to breathe against the obsidian background.

## Layout & Spacing
The layout uses a **12-column asymmetric grid**. Content should not always center-align; intentionally "misalign" elements by shifting them 1-2 columns off-center to create visual tension.

- **Negative Space:** Use massive `section-gap` units between different editorial stories. The white space (or "black space" in this case) is as important as the product imagery.
- **Asymmetry:** On desktop, allow images to bleed off the edge of the screen on one side while maintaining a strict `margin-desktop` on the other.
- **Borders:** Use 1px ivory or charcoal horizontal rules to separate content, evoking the structure of a broadsheet newspaper.

## Elevation & Depth
This design system avoids shadows entirely. Depth is achieved through **Tonal Layering** and **Grain Texture**.

- **Surface Levels:** Use `Obsidian` for the base and `Charcoal` for elevated surfaces like "Quick View" drawers or shopping bags.
- **Thin Outlines:** Distinguish elements using 0.5px or 1px solid borders in `Warm Ivory` at 20-30% opacity. 
- **Texture:** Apply a subtle, global noise/grain overlay (2-3% opacity) to all surfaces to simulate high-quality paper stock and give the digital interface a human, "crafted" feel.

## Shapes
Shapes are strictly **Sharp (0px)**. Every button, input field, and image container must have 90-degree corners. This reinforces the "architectural" and "rebellious" nature of the brand, moving away from the soft consumerism of rounded corners.

## Components
- **Buttons:** Large, rectangular blocks. Primary buttons use an Ivory background with Obsidian text. Secondary buttons are transparent with a 1px Ivory border. All button text uses `label-caps`.
- **Product Cards:** Full-bleed imagery with no visible border. Product names and prices appear below in `label-caps`, separated by a thin horizontal rule.
- **Input Fields:** A single 1px Ivory bottom-border only (minimalist style). Labels sit above the line in `label-caps`.
- **Chips/Filters:** Sharp-edged rectangles with `label-caps` text. Active state uses a `Gold` bottom-border.
- **Lists:** Editorial style; items are separated by full-width 1px lines. Hovering an item may trigger a large image preview in the background (asymmetric).
- **Navigation:** Top-tier links are all caps. The "Bag" or "Cart" count is displayed in small `Gold` numerals without a circle container.