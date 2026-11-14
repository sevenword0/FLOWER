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
| **형태** (Shape) | Petal count, whorls, length, width, widest point, tip roundness, cup, base/mid/tip curvature, opening angle, ruffle, base flare and base curve zone, unfurl direction, sepals and sepal curl, colour |
| **조명** (Lighting) | Specular gloss, main light azimuth and elevation, AO / SSGI / soft shadow toggles and strengths, polygon budget (four triangle-count caps) |
| **장면** (Scene) | Stem and leaves, auto-rotate, 5 backgrounds |

> To scrub through the bloom by hand, move the "개화 정도" (bloom amount) slider in the Create tab; moving it turns auto bloom off.
>
> The readout at the bottom of the screen shows frames per second, the number of parts and the current triangle count.

## The 8 presets

Each preset follows the structure and opening behaviour of the real flower.

| Preset | Structure | How it opens |
| --- | --- | --- |
| Rose | Several whorls of petals in an overlapping spiral, 5 sepals | Outer petals roll back from the tip and margins first while the core stays cupped. The sepals stay attached and arch back |
| Daisy | One whorl of 26 flat, strap-shaped ray florets around a disc of disc florets | Spreads flat, each ray slightly out of step with its neighbours |
| Sunflower | One whorl of 30 ray florets around a large golden-angle spiral disc, with an involucre | Rays standing inside the involucre spread out evenly |
| Tulip | 6 tepals in two whorls of 3, 6 stamens | Opens from a bud with a rounded bowl-shaped bottom into a goblet |
| Lily | 6 tepals in two whorls of 3, long stamens and pistil | Spreads wide from a narrow funnel base, with the tips reflexed back |
| Lotus | Several whorls of broad petals attached in overlap around a small receptacle at the top of the stalk, around a central seed pod ringed by stamens | Whorl by whorl from the outside, out of a pointed egg-shaped bud |
| Cherry blossom | 5 notched petals, many slender stamens; 4 blossoms on one twig | All together, wide open |
| Dahlia | Dense spiral of petals, quilled into tubes | In one continuous sweep from the outside to the centre |

## Attachment and bending

Petals, sepals, bracts and stamens all sit on the surface of the receptacle (the base of the flower).

- **One source of truth**: a single receptacle profile curve is used both for the receptacle that is drawn and for where the parts attach. Each base is sunk slightly into the surface, so no gap opens.
- **Rounded base edge**: the base edge of a petal is not a straight line; it follows the round surface of the receptacle.
- **Curved departure**: a petal leaves in the direction of the receptacle surface and bends into its pose over roughly the first 15–35% of its length. This gives the tulip its round bottom and the lily its narrow funnel.
- **Bending, not rotation**: when a petal opens or is pushed by a neighbour, its base stays fixed and it bends more the farther it is from the base. Sepals and bracts arch back the same way.
- **Unfurl direction**: most flowers open from the base first; the rose rolls back from the tip and margins first.

These can be adjusted in the Shape tab.

| Slider | What it changes |
| --- | --- |
| 밑동 벌어짐 (base flare) | The direction in which a petal leaves the receptacle. Lower values make it leave more sideways, giving a round bowl-shaped bottom |
| 밑동 곡선 구간 (base curve zone) | The length over which the petal bends from that direction into its pose |
| 펴지는 방향 (unfurl direction, base↔tip) | Positive opens from the base first, negative from the tip and margins first |
| 꽃받침 휘어짐 (sepal curl) | How far sepals and bracts arch back |
| 중심↔외곽 높이 (centre↔outer height), 겹침 깊이(층 분리) (layer separation) | Move each petal's attachment along the receptacle surface; bases stay attached |

At the ends of a slider's range, petals can visibly overlap.

## Petal interaction

Petals are aware of each other. Each petal's base-to-tip curve (its spine) is reduced to 8 points and the whole flower is solved together.

- **Holding and release**: closed sepals and outer petals hold the inner petals in, and the layers release one after another from the outside. Stamens spread only once the innermost petals have opened.
- **Layering**: inner and outer petals rest on each other with a gap and push apart instead of passing through one another.
- **Overlap within a whorl**: neighbouring petals of the same whorl sit with one margin over and the other margin under.
- **Springiness**: a released petal overshoots slightly and settles. The same position of the "개화 정도" (bloom amount) slider still always gives the same shape.

Limits: when petals push on each other they deform in one way only, a broad bend from the base to mid-blade. Local dents at the point of contact are not modelled. Some overlap can remain in the bud state of flowers with very many petals and in randomly generated flowers. With "Z 반전" (flip Z) or the petal rotation sliders (X, Y, Z), interaction is switched off and each petal moves independently. Turning petal rotation X or Y close to 90 degrees lifts the base corners off the receptacle. Randomly generated flowers get a receptacle and attachment settings matched to their size, but they are not tuned as carefully as the presets.

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
