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
| **조명** (Lighting) | Specular gloss, main light azimuth and elevation, AO / SSGI / soft shadow toggles and strengths, petal subdivision |
| **장면** (Scene) | Stem and leaves, auto-rotate, 5 backgrounds |

> To scrub through the bloom by hand, turn off "자동 개화" (auto bloom) in the Create tab and move the "개화 정도" (bloom amount) slider.

## The 8 presets

Each preset follows the structure and opening behaviour of the real flower.

| Preset | Structure | How it opens |
| --- | --- | --- |
| Rose | Several whorls of petals in an overlapping spiral, 5 sepals | Outer petals reflex first while the core stays cupped |
| Daisy | One whorl of 21 narrow ray florets around a disc of disc florets | Spreads flat |
| Sunflower | Pointed ray florets around a large golden-angle spiral disc | From the rim inward |
| Tulip | 6 tepals in two whorls of 3, 6 stamens | Stays cup-shaped and opens only slightly |
| Lily | 6 tepals in two whorls of 3, long stamens and pistil | Spreads wide with the tips reflexed back |
| Lotus | Several whorls of broad petals around a central seed pod ringed by stamens | Whorl by whorl from the outside |
| Cherry blossom | 5 notched petals, many slender stamens | All together, wide open |
| Dahlia | Dense spiral of petals, quilled into tubes | From the outside inward |

## Rendering

- **Two-pass deferred rendering**: pass 1 writes colour, normal and position to a G-buffer (multiple render targets, 4× MSAA); pass 2 composites.
- **PBR lighting**: GGX microfacet specular with Fresnel, hemispheric sky/ground ambient, back-light transmission through thin petals.
- **AO** (ambient occlusion), **SSGI** (one-bounce screen-space global illumination), **soft shadows** (screen-space ray march toward the light).
- **ACES tone mapping**.
- Petals, stamens and florets are drawn with instancing; blooming, cupping and reflexing are computed in the vertex shader.

## Run locally

Download `index.html` and open it in a WebGPU-capable browser. No network connection or extra install is needed.

## Deployment (GitHub Pages)

Every change that lands on `main` makes the `.github/workflows/pages.yml` workflow redeploy the repository root to GitHub Pages.
It usually appears at the address above within 1–2 minutes; browser caching can show the previous version for up to about 10 minutes.

- Manual run: repository **Actions** tab → *Deploy to GitHub Pages* → *Run workflow*
- If a deployment fails: check that **Settings → Pages → Build and deployment → Source** is set to **GitHub Actions**.
- The workflow publishes the **entire repository root**, so any other file added to the repository becomes readable under the same address.
