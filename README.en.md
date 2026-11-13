# FLOWER — WebGPU Procedural Flower Bloom Simulator

[한국어](README.md) | English

A **single-file HTML app** that renders flowers opening from bud to full bloom in real time with WebGPU.
Petals, stamens, sepals and leaves are all generated procedurally. There are no external libraries and nothing to install.

## Live demo

**https://sevenword0.github.io/FLOWER/**

Open the address and it runs. No install, sign-in or download.

### Supported browsers

| Browser | WebGPU on by default since |
| --- | --- |
| Chrome / Edge (Windows, macOS, ChromeOS) | 113 |
| Chrome (Android) | 121 |
| Safari (macOS, iOS, iPadOS) | 26 |
| Firefox (Windows) | 141 |

In a browser without WebGPU the page shows a "WebGPU unavailable" notice instead of the flower.
Open it in a current version of one of the browsers above.

## How to use

1. Open the address above. A rose starts blooming on its own.
2. **Drag** to orbit the flower. Use the **mouse wheel** (pinch on touch screens) to zoom.
3. Use the four tabs in the left panel to change the flower and the scene. The panel labels are in Korean; the table gives the label for each tab.

| Tab | What it controls |
| --- | --- |
| **생성** (Create) | Flower type (8 presets), random flower, replay, auto showcase, copy current settings. Bloom amount, speed, centre↔outer deviation, easing |
| **형태** (Shape) | Petal count, whorls, length, width, widest point, tip roundness, cup, base/mid/tip curvature, opening angle, ruffle, sepals, colour |
| **조명** (Lighting) | Specular gloss, main light azimuth and elevation, AO / SSGI / soft shadow toggles and strengths, polygon budget (four triangle-count caps) |
| **장면** (Scene) | Stem and leaves, auto-rotate, 5 backgrounds |

> To scrub through the bloom by hand, move the "개화 정도" (bloom amount) slider in the Create tab; moving it turns auto bloom off.
>
> The readout at the bottom of the screen shows frames per second, the number of parts and the current triangle count.

## The 8 presets

Each preset follows the structure and opening behaviour of the real flower.

| Preset | Structure | How it opens |
| --- | --- | --- |
| Rose | Several whorls of petals in an overlapping spiral, 5 sepals | Outer petals reflex first while the core stays cupped |
| Daisy | One whorl of 26 narrow ray florets around a disc of disc florets | Spreads flat, each ray slightly out of step with its neighbours |
| Sunflower | One whorl of 30 ray florets around a large golden-angle spiral disc, with an involucre | Rays folded over the disc stand up and spread |
| Tulip | 6 tepals in two whorls of 3, 6 stamens | Opens from an overlapping wrapped bud into a goblet |
| Lily | 6 tepals in two whorls of 3, long stamens and pistil | Spreads wide with the tips reflexed back |
| Lotus | Several whorls of broad petals around a central seed pod ringed by stamens | Whorl by whorl from the outside |
| Cherry blossom | 5 notched petals, many slender stamens; 4 blossoms on one twig | All together, wide open |
| Dahlia | Dense spiral of petals, quilled into tubes | Row by row from the outside inward |

## Petal interaction

Petals are aware of each other. Each petal's base-to-tip curve (its spine) is reduced to 8 points and the whole flower is solved together.

- **Holding and release**: closed sepals and outer petals hold the inner petals in, and the layers release one after another from the outside. Stamens spread only once the innermost petals have opened.
- **Layering**: inner and outer petals rest on each other with a gap and push apart instead of passing through one another.
- **Overlap within a whorl**: neighbouring petals of the same whorl sit with one margin over and the other margin under.
- **Springiness**: a released petal overshoots slightly and settles. The same position of the "개화 정도" (bloom amount) slider still always gives the same shape.

Limits: this is a reduced model in which each petal hinges as a whole about its base. Local dents at the point of contact are not modelled. Some overlap can remain in the bud state of flowers with very many petals and in randomly generated flowers. With "Z 반전" (flip Z) or the petal rotation sliders (X, Y, Z), interaction is switched off and each petal moves independently.

## Polygon budget

The whole flower has a triangle cap, and the detail of each part is divided automatically within it.

| Level | Triangle cap |
| --- | --- |
| 낮음 (Low) | about 40,000 |
| 보통 (Medium, default) | about 100,000 |
| 높음 (High) | about 200,000 |
| 최고 (Ultra) | about 400,000 |

- Flowers with few petals (rose, tulip, lily) get a dense mesh per petal; flowers with many petals (dahlia) get a coarse one.
- Fine detail such as veins, spots and grooves is drawn by surface shading, not triangles.
- When the page runs slowly (average frame time above 33 ms) it first lowers the internal resolution and then, if still slow, the polygon budget one level at a time. Quality that has been lowered is not raised again automatically.

## Rendering

- **Deferred rendering**: shadow map → G-buffer (direct light, normal, position, ambient; multiple render targets, 4× MSAA) → half-resolution AO / SSGI → blur → glow → composite.
- **PBR lighting**: GGX microfacet specular with Fresnel, per-part materials (gloss, velvet sheen, back-light transmission through thin petals), key light, hemispheric ambient and rim light.
- **Soft shadows**: a shadow map from the light's point of view (2048², penumbra widening with distance).
- **AO** (ambient occlusion) and **SSGI** (one-bounce screen-space global illumination) are applied to ambient light.
- **ACES tone mapping**, glow and dithering.
- **Procedural surfaces**: petal colour gradients, venation and species marks (lily spots, tulip basal blotch and so on) and leaf veins are computed in the shader.
- Petals, stamens and florets are drawn with instancing. Petal poses are solved on the CPU, and the vertex shader deforms each surface from the result.
- The internal render resolution is capped at about 2.3 megapixels (to protect memory on high-resolution phones).

## Environments not verified

Automated checks ran only on a software renderer (Chromium) on a server without a graphics card. Appearance and speed on a real graphics card, in Safari, in Firefox and on a real phone have not been verified.

## Run locally

Download `index.html` and open it in a WebGPU-capable browser. No network connection or extra install is needed.

## Deployment (GitHub Pages)

Every change that lands on `main` makes the `.github/workflows/pages.yml` workflow redeploy the repository root to GitHub Pages.
It usually appears at the address above within 1–2 minutes; browser caching can show the previous version for up to about 10 minutes.

- Manual run: repository **Actions** tab → *Deploy to GitHub Pages* → *Run workflow*
- If a deployment fails: check that **Settings → Pages → Build and deployment → Source** is set to **GitHub Actions**.
- The workflow publishes the **entire repository root**, so any other file added to the repository becomes readable under the same address.
