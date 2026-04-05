# Effect Preset Reference Images

Canonical reference works and direct image URLs for each of the 10 preset categories
defined in `hapax-logos/src/components/graph/presetData.ts`.

For each work: the image URL, the defining characteristic it demonstrates,
and the specific visual feature to look for when calibrating effect parameters.

---

## 1. Minimal / Transparent

**Presets:** `ambient`, `clean`

### Andy Warhol -- Screen Tests (1964-66)

**Image:**
- https://www.warhol.org/wp-content/uploads/2017/10/1997-4-113-141_pub_01-Web-Ready-475px-longest-edge-Check-Copyright-Before-Using-on-Web.jpg
  (Jane Holzer Screen Test, 1964 -- The Andy Warhol Museum)

**Characteristic:** Stillness and presence
**Look for:** High-contrast B&W, single unmoving subject, dreamlike grain from 16mm projected at 16fps.
The "ambient" preset should achieve this sense of perceptual slowness -- the image is
barely touched, yet the viewer's attention is completely held.

### Bill Viola -- The Reflecting Pool (1977-79)

**Image:**
- https://d1hhug17qm51in.cloudfront.net/www-media/2022/05/02111358/91.227_01_g03-Large-TIFF_4000-pixels-long.jpg
  (SFMOMA collection, 2560x1862)
- https://www.eai.org/user_files/images/title/_xl/viola_reflectingpool_xl.jpg
  (Electronic Arts Intermix)

**Characteristic:** Radical clarity of the unprocessed frame
**Look for:** A man frozen mid-leap over a pool, suspended in time. The rest of the scene
continues naturally -- water ripples, light changes. The "clean" preset should preserve
this level of optical clarity while allowing subtle temporal interventions.

---

## 2. Temporal Persistence / Feedback

**Presets:** `ghost`, `trails`, `feedback_preset`, `echo`, `reverie_vocabulary`

### Nam June Paik -- TV Buddha (1974)

**Images:**
- https://upload.wikimedia.org/wikipedia/commons/5/53/TV_Buddha.jpg
  (Wikimedia Commons -- full resolution)
- https://publicdelivery.org/wp-content/uploads/2019/02/Nam-June-Paik-TV-Buddha-19742002.jpeg
- https://publicdelivery.org/wp-content/uploads/2019/02/Nam-June-Paik-TV-Buddha-1976-television-monitor-video-camera-painted-wooden-Buddha-tripod-plinth-monitor-32-x-32-x-32cm-Buddha-75-x-36-x-36-cm-John-Kaldor-Family-Gallery-Art-Gallery-NSW.jpg
- https://publicdelivery.org/wp-content/uploads/2019/02/Nam-June-Paik-TV-Buddha-1992-Buddha-monitor-CCTV-camera-134.6-x-210.8-%C3%97-55.9-cm-53.0-x-83.0-%C3%97-22.0-in-.jpg

**Characteristic:** Closed-loop video feedback
**Look for:** Buddha statue watching its own live image on a CRT monitor via closed-circuit camera.
The feedback loop IS the art. The `feedback_preset` should create this
self-referential quality where the output feeds back into the input.

### Steina & Woody Vasulka -- Noisefields (1974)

**Images (vasulka.org archive):**
- https://www.vasulka.org/Videomasters/pages_stills/thumbnails/Noisefields_01.jpg
- https://www.vasulka.org/Videomasters/pages_stills/thumbnails/Noisefields_02.jpg
- https://www.vasulka.org/Videomasters/pages_stills/thumbnails/Noisefields_03.jpg
- https://www.vasulka.org/Videomasters/pages_stills/thumbnails/Noisefields_04.jpg
- https://www.vasulka.org/Videomasters/pages_stills/thumbnails/Noisefields_05.jpg

**Characteristic:** Electronic signal as visual material
**Look for:** Colorized video noise keyed through a circle, producing rich static modulated
by energy content. Created on the Rutt/Etra Video Synthesizer. The `echo` and `trails` presets
should capture this quality of electronic artifacts as expressive medium, not defect.

### Zbigniew Rybczynski -- Tango (1980)

**Characteristic:** Temporal layering / multiple time streams in one frame
**Look for:** 36 characters performing repetitive loops in one room simultaneously,
each occupying their own temporal layer. Created via ~16,000 cell mattes on an optical printer.
The `ghost` preset should achieve this sense of multiple temporal presences coexisting.

*No direct still image URL found in accessible archives. View on Internet Archive:*
https://archive.org/details/tango_20170601

---

## 3. Analog Degradation

**Presets:** `vhs_preset`, `dither_retro`, `nightvision`

### Pipilotti Rist -- I'm Not The Girl Who Misses Much (1986)

**Images:**
- https://media.tate.org.uk/art/images/work/T/T07/T07972_7.jpg
  (Tate collection)
- https://d1hhug17qm51in.cloudfront.net/www-media/2018/08/25225117/2009.171_02-Large-TIFF_4000-pixels-long-scaled.jpg
  (SFMOMA collection)

**Characteristic:** Deliberate VHS degradation as ritual
**Look for:** Blurred figure with false colors, horizontal tracking lines, zigzag distortions,
vertical/horizontal freeze frames. Rist deliberately manipulated VHS scan lines and color channels.
The `vhs_preset` should reproduce these specific artifacts: scan line displacement,
chroma bleed, horizontal tear, and color channel separation.

### Rosa Menkman -- A Vernacular of File Formats (2010)

**Images:**
- https://images.squarespace-cdn.com/content/v1/65e7176a61627736e02f6c4a/9d1f4eab-9dff-4919-a898-9aa9dd1e1f61/JPEG%2BFROM%2BA%2BVERNACULAR%2BOF%2BFILE%2BFORMATS%2C%2B%282009%2B-%2B2010%29%2C%2B2023%2BREVISITATION%2BWITH%2BHIDDEN%2BMESSAGE%2BIN%2BDCT.%2Bby%2BRosa%2BMenkman+%286%29.jpeg
  (Lumen Prize 2023 still image award winner)

**Characteristic:** Systematic codec failure aesthetics
**Look for:** Same self-portrait glitched through BMP, JPEG, GIF, TIFF, etc. Each format
produces distinct visual artifacts when the same error is introduced. JPEG produces blocky
DCT artifacts; GIF produces color banding; BMP produces raw pixel displacement.
The `dither_retro` preset should reference the posterization and color-banding qualities.

### Zero Dark Thirty -- Raid Scene (2012)

**Characteristic:** Night vision device aesthetic (green phosphor)
**Look for:** Yellow-green monochrome, high gain noise, IR illumination bloom, CCD-style
artifacts. DP Greig Fraser bolted actual Gen3 night vision optics onto ARRI Alexa sensors
and used IR lights for illumination. The `nightvision` preset should reproduce:
green phosphor coloring, high-gain amplification noise, IR bloom on reflective surfaces.

*Film stills behind paywall. For reference characteristics, see:*
https://www.fxguide.com/fxfeatured/lights-out-making-zero-dark-thirty/

### JODI -- %20Wrong (1999-2011)

**Characteristic:** Digital degradation as native vocabulary
**Look for:** Browser interface subverted into abstract visual noise. HTML source code
rendered as visual pattern. Desktop GUI elements decontextualized into non-functional art.
**Live work (still accessible):** https://wrongbrowser.jodi.org/

---

## 4. Databending / Glitch

**Presets:** `datamosh`, `datamosh_heavy`, `glitch_blocks_preset`, `pixsort_preset`

### Takeshi Murata -- Monster Movie (2005)

**Images (Smithsonian American Art Museum):**
- https://ids.si.edu/ids/deliveryService?id=SAAM-2013.71_1&max=960
- https://ids.si.edu/ids/deliveryService?id=SAAM-2013.71_2&max=960
- https://ids.si.edu/ids/deliveryService?id=SAAM-2013.71_3&max=960
- https://ids.si.edu/ids/deliveryService?id=SAAM-2013.71_4&max=960
- https://ids.si.edu/ids/deliveryService?id=SAAM-2013.71_5&max=960
- https://ids.si.edu/ids/deliveryService?id=SAAM-2013.71_6&max=960
- https://ids.si.edu/ids/deliveryService?id=SAAM-2013.71_7&max=960
- https://ids.si.edu/ids/deliveryService?id=SAAM-2013.71_8&max=960

**Characteristic:** Datamoshing as controlled decomposition
**Look for:** B-movie footage (from 1981's Caveman) dissolving into seething color morass.
Frame-by-frame manipulation of I-frames and P-frames creates liquid pixel flow where
motion vectors apply to wrong reference frames. The `datamosh` preset should achieve
this quality of recognizable forms melting into abstract color fields.

### Kanye West / Nabil -- Welcome to Heartbreak (2009)

**Characteristic:** Datamoshing as emotional expression
**Look for:** Kanye's face and figure fragmenting, melting between shots. P-frame motion
vectors from one shot applied to keyframes of another, creating pixel-flow transitions.
The `datamosh_heavy` preset should capture the more aggressive form where subjects
become unrecognizable pools of motion-compensated color.

*Music video on YouTube. Representative stills at:*
https://knowyourmeme.com/videos/9018-datamoshing

### Kim Asendorf -- Mountain Tour (2010)

**Images:**
- https://surfaceandsurface.wordpress.com/wp-content/uploads/2012/09/mountain-tour-kim-asendorf-surface-and-surface-1.jpg
- https://surfaceandsurface.wordpress.com/wp-content/uploads/2012/09/mountain-tour-kim-asendorf-surface-and-surface-2.jpg
- https://surfaceandsurface.wordpress.com/wp-content/uploads/2012/09/mountain-tour-kim-asendorf-surface-and-surface-3.jpg
- https://surfaceandsurface.wordpress.com/wp-content/uploads/2012/09/mountain-tour-kim-asendorf-surface-and-surface-4.jpg
- https://surfaceandsurface.wordpress.com/wp-content/uploads/2012/09/mountain-tour-kim-asendorf-surface-and-surface-5.jpg
- https://surfaceandsurface.wordpress.com/wp-content/uploads/2012/09/mountain-tour-kim-asendorf-surface-and-surface-6.jpg
- https://surfaceandsurface.wordpress.com/wp-content/uploads/2012/09/mountain-tour-kim-asendorf-surface-and-surface-7.jpg
- https://surfaceandsurface.wordpress.com/wp-content/uploads/2012/09/mountain-tour-kim-asendorf-surface-and-surface-8.jpg

**Characteristic:** Pixel sorting -- algorithmic reordering by luminosity
**Look for:** Mountain landscapes where each scan line has pixels sorted by brightness,
creating vertical streaks that stretch from dark regions to bright sky. The original
algorithm scans each row and sorts pixels between brightness thresholds, producing
a signature "dripping paint" effect. The `pixsort_preset` should reproduce this
scan-line sorting with adjustable threshold sensitivity.

---

## 5. Houston Syrup / Hip Hop Temporal

**Presets:** `screwed`, `trap`

### A$AP Rocky / Dexter Navy -- L$D (2015)

**Characteristic:** Liquefied temporal smearing through neon environments
**Look for:** Tokyo neon signs and vending machines dissolving into liquid color
under psychedelic temporal distortion. Long exposures, frame blending, and
color-shifted double exposures. The `screwed` preset should achieve temporal
smearing where motion trails persist and colors bleed across frames.

*Stills from the music video widely available. Video influenced by Gaspar Noe's Enter the Void.*

### Travis Scott / Dave Meyers -- SICKO MODE (2018)

**Characteristic:** Frame stutter and datamosh transitions
**Look for:** MOD VFX produced 200+ shots including datamosh transitions between song
sections, mosaic face splintering, and colorfully-stylized Houston street renderings.
The `trap` preset should capture the frame-stutter aesthetic where temporal
discontinuity creates a hard, percussive visual rhythm.

### Gaspar Noe -- Enter the Void (2009)

**Images (Art of the Title -- title sequence stills):**
- https://www.artofthetitle.com/assets/resized/sm/upload/wj/xz/8h/hq/enter_the_void_contact-0-1080-0-0.jpg?k=bf12e308f9
- https://www.artofthetitle.com/assets/sm/upload/dr/io/fy/31/etv_type_styles_01.jpg?k=8b54804914
- https://www.artofthetitle.com/assets/sm/upload/wc/gx/vj/o6/etv_type_styles_02.jpg?k=aabebdff52
- https://www.artofthetitle.com/assets/sm/upload/2c/vq/8s/br/etv_type_styles_03.jpg?k=61d2a543cc
- https://www.artofthetitle.com/assets/sm/upload/as/wh/yj/0w/etv_type_styles_04.jpg?k=9141a5487e
- https://www.artofthetitle.com/assets/sm/upload/of/mn/7d/ak/etv_type_styles_05.jpg?k=36472c0ec6
- https://www.artofthetitle.com/assets/sm/upload/e9/ad/du/4m/etv_type_styles_06.jpg?k=1ad4149be7
- https://www.artofthetitle.com/assets/resized/sm/upload/00/q3/ov/re/etv_film_still-0-1080-0-0.jpg?k=1e2338895c
- https://www.artofthetitle.com/assets/resized/sm/upload/93/tl/2r/9r/etv_full_title-0-1080-0-0.jpg?k=440e297160

**Characteristic:** Neon spectrum strobing typography / foundational cinematic psychedelia
**Look for:** Rapid-fire neon typography cycling through dozens of typefaces, electrophotographic
distortion by Thorsten Fleisch, Tokyo red-light district neon sign aesthetic. Both the
syrup temporal distortion (film body) and spectral neon (title sequence) are reference points.

---

## 6. False Color / Spectral

**Presets:** `neon`, `thermal_preset`

### Richard Mosse -- The Enclave (2013)

**Images (publicdelivery.org -- extensive gallery):**

Landscapes (infrared pink):
- https://publicdelivery.org/wp-content/uploads/2016/11/Richard-Mosse-Vintage-violence-2011-Courtesy-of-the-artist-and-Jack-Shainman-Gallery-New-York.jpg
- https://publicdelivery.org/wp-content/uploads/2016/11/Richard-Mosse-Of-Lillies-and-Remains-North-Kivu-eastern-Congo-2012-digital-C-print-72-x-90-inches.-Courtesy-of-the-artist-and-Jack-Shainman-Gallery.jpg
- https://publicdelivery.org/wp-content/uploads/2016/11/Richard-Mosse-Safe-From-Harm-North-Kivu-eastern-Congo-2012-Digital-C-print-48-x-60-inches-Courtesy-of-the-artist-and-Jack-Shainman-Gallery.jpg
- https://publicdelivery.org/wp-content/uploads/2016/11/Richard-Mosse-The-Crystal-World-2011.jpg
- https://publicdelivery.org/wp-content/uploads/2016/11/Richard-Mosse-Lac-Vert-2012-from-The-Enclave-Aperture-2013-.jpg

Portraits (infrared false color on skin):
- https://publicdelivery.org/wp-content/uploads/2016/11/Richard-Mosse-Madonna-and-Child-North-Kivu-Eastern-Congo-2012-Digital-C-print-35-x-28-inches.-Courtesy-of-Jack-Shainman-Gallery.jpg
- https://publicdelivery.org/wp-content/uploads/2016/11/Richard-Mosse-She-Brings-the-Rain-2011.jpg

Film stills (16mm infrared):
- https://publicdelivery.org/wp-content/uploads/2016/11/Richard-Mosse-2013-16mm-stills-Six-screen-film-installation-Courtesy-the-artist-and-Jack-Shainman-Gallery-2.jpg
- https://publicdelivery.org/wp-content/uploads/2016/11/Richard-Mosse-2013-16mm-stills-Six-screen-film-installation-Courtesy-the-artist-and-Jack-Shainman-Gallery-3.jpg
- https://publicdelivery.org/wp-content/uploads/2016/11/Richard-Mosse-2013-16mm-stills-Six-screen-film-installation-Courtesy-the-artist-and-Jack-Shainman-Gallery-4.jpg

**Characteristic:** Infrared false-color remapping (Kodak Aerochrome)
**Look for:** Living vegetation rendered in vivid magenta/pink/crimson. Chlorophyll reflects
infrared, which the discontinued military reconnaissance film renders as pink. Skin tones
shift. The `thermal_preset` should achieve dramatic false-color remapping where the
color channels are reassigned based on luminance or frequency bands.

### Richard Mosse -- Incoming (2014-17)

**Image:**
- https://www.designboom.com/wp-content/uploads/2017/02/richard-mosse-heat-maps-designboom-01.jpg

**Characteristic:** Military-grade thermal imaging as art
**Look for:** Monochromatic thermal imagery where human bodies appear as bright heat
signatures against cool backgrounds. Shot with a camera that detects thermal radiation
from 18 miles away. The `thermal_preset` at lower saturation should approximate this
grayscale thermal look.

### Dan Flavin -- untitled (Marfa project) (1996)

**Images (Chinati Foundation):**
- https://chinati.org/wp-content/uploads/2019/06/9330_Chinati_IN_166_flavin.jpg
- https://chinati.org/wp-content/uploads/2019/06/9330_Chinati_IN_172_Flavin2-768x511.jpg
- https://chinati.org/wp-content/uploads/2019/06/9330_Chinati_IN_169_flavin-e1575557310997-768x1152.jpg
- https://chinati.org/wp-content/uploads/2019/06/Flavin-Bldg.-3-Int-scaled-344x454.jpg
- https://chinati.org/wp-content/uploads/2020/01/Flavin-untitled-green-D-Tuck_small-344x229.jpg

**Additional (Wikimedia Commons):**
- https://upload.wikimedia.org/wikipedia/commons/7/77/%2214_-_ITALY_-_Dan_Flavin_in_Milan_-_Chiesa_di_Santa_Maria_Annunciata_in_Chiesa_Rossa_church_-_LED_lightning_-_color_emotion_-_colorful.jpg
- https://upload.wikimedia.org/wikipedia/commons/c/c2/Dan_flavin_%2814032927389%29.jpg
- https://upload.wikimedia.org/wikipedia/commons/2/22/Dan_flavin_%288572894998%29.jpg

**Characteristic:** Fluorescent light as spectral saturation
**Look for:** Corridors and rooms flooded with pure spectral color from commercial fluorescent
tubes (pink, green, yellow, blue). Colors mix additively in space. The `neon` preset should
produce this quality of saturated spectral wash where architectural space is dissolved in color.

### Ryoji Ikeda -- datamatics (2006-ongoing)

**Images (artist website):**
- https://www.ryojiikeda.com/data/work/concert-datamatics-03.jpg
- https://www.ryojiikeda.com/data/work/concert-datamatics-04.jpg
- https://www.ryojiikeda.com/data/work/data.scan.jpg
- https://www.ryojiikeda.com/data/work/data.flux_n%C2%BA1.jpg
- https://www.ryojiikeda.com/data/work/dataanatomy01.jpg
- https://www.ryojiikeda.com/data/work/dataanatomy02.jpg

**Characteristic:** Data streams as black-and-white spectral grids
**Look for:** Immersive projections of pure data rendered as rapidly scrolling barcode-like
patterns, binary matrices, and mathematical visualizations. Extreme contrast (pure black/white)
with occasional spectral color bursts. Reference for the grid/data-visualization aspect of
the spectral category.

---

## 7. Edge / Silhouette / Relief

**Presets:** `silhouette`, `sculpture`

### Saul Bass -- The Man with the Golden Arm (1955)

**Images (Art of the Title):**
- https://www.artofthetitle.com/assets/sm/upload/e2/t5/wr/kj/mwga_c.jpg?k=118aa37a78
- https://www.artofthetitle.com/assets/resized/sm/upload/d8/mu/3d/rb/mwga_p-0-170-0-0.jpg?k=f1e82c60fe

**Additional stills at:**
http://notcoming.com/saulbass/caps_manwgoldenarm.php

**Characteristic:** Silhouette as narrative device
**Look for:** White geometric bars on pure black, resolving into a crooked arm shape.
Extreme high-contrast reduction -- no gradients, no halftones, just presence/absence.
The `silhouette` preset should achieve this binary threshold quality where the image
is reduced to pure black and white edge shapes.

### Richard Linklater -- A Scanner Darkly (2006)

**Images (Indiana University blog -- rotoscope stills):**
- https://blogs.iu.edu/establishingshot/files/2022/03/Scanner-02-e1647973427243-1024x578.png
- https://blogs.iu.edu/establishingshot/files/2022/03/Scanner-04-e1647973455353-1024x576.png
- https://blogs.iu.edu/establishingshot/files/2022/03/Scanner-05-Fred-e1647973635463-1024x581.png
- https://blogs.iu.edu/establishingshot/files/2022/03/Scanner-06-e1647973512548-1024x581.png
- https://blogs.iu.edu/establishingshot/files/2022/03/Scanner-07-e1647973606356-1024x581.png
- https://blogs.iu.edu/establishingshot/files/2022/03/Scanner-08-e1647973668794-1024x578.png
- https://blogs.iu.edu/establishingshot/files/2022/03/Scanner-09-e1647973695294-1024x578.png
- https://blogs.iu.edu/establishingshot/files/2022/03/Scanner-10-e1647973726924-1024x578.png
- https://blogs.iu.edu/establishingshot/files/2022/03/Scanner-11-e1647973752192-1024x578.png

**Characteristic:** Interpolated rotoscope as shifting edge detection
**Look for:** Live-action footage traced frame-by-frame via Rotoshop software. Colors
flatten into poster-like regions, edges wobble between frames, the boundary between
figure and ground is in constant flux. This is the intersection of `silhouette` and
edge detection -- the algorithm finds edges but they shift, creating an unstable,
hallucinatory quality. 500 hours per minute of animation.

### Daniel Rozin -- Wooden Mirror (1999)

**Images (artist website):**
- https://www.smoothware.com/danny/mirror.jpg
- https://www.smoothware.com/danny/woodenmirrormuseum.jpg

**Additional (Google Arts & Culture):**
https://artsandculture.google.com/asset/wooden-mirror-daniel-rozin/HgFVjCw9buhwqg

**Characteristic:** Camera feed converted to physical relief sculpture
**Look for:** 830 square wooden tiles tilted by servo motors to create light/shadow
pixels from live camera input. The image is quantized into ~830 brightness levels
rendered as physical angles. The `sculpture` preset should produce this Rutt/Etra-style
3D displacement effect where brightness maps to depth.

---

## 8. Halftone / Mosaic / Character

**Presets:** `halftone_preset`, `ascii_preset`

### Knowlton & Harmon -- Studies in Perception I (1966)

**Images:**
- https://images.albrightknox.org/piction/ump.di?e=3B14D5A0ECC6274FCDE09FED9298CAFD788B67B9EC75D5D57B70049F242A5AEF&s=21&se=191315952&v=1&f=P2014_002_BD2022_support_o2.jpg
  (Buffalo AKG Art Museum -- high resolution)

**Characteristic:** Foundational computer mosaic / halftone
**Look for:** Photograph of dancer Deborah Hay reduced to a grid of grey squares,
with telephony circuit diagram symbols assigned to greyscale values. At 12x5 feet,
it reads as an abstract pattern up close but resolves into a nude figure from distance.
The `halftone_preset` should achieve this dual-resolution quality where micro-patterns
aggregate into macro-images.

### Vuk Cosic -- ASCII History of Moving Images (1998)

**Image:**
- https://live.staticflickr.com/2338/2442692593_70f2b6f2f2_b.jpg
  (Flickr -- ASCII rendering of Psycho shower scene)

**Characteristic:** Moving image reduced to ASCII character grid
**Look for:** Green ASCII characters on black background rendering recognizable film scenes
(Psycho, Battleship Potemkin, Deep Throat). Each character's density approximates a
brightness value. The `ascii_preset` should convert brightness to character density
in a monospaced grid.

### Roy Lichtenstein -- Ben-Day Dots

**Characteristic:** Hand-painted halftone dots as fine art
**Look for:** Regular dot grids in primary colors (magenta, cyan, yellow) that simulate
commercial printing halftones. Dots are uniform in size but vary in spacing/density to create
tonal gradation. Up close: abstract dot pattern. At distance: recognizable imagery.
*Widely reproduced. Search "Lichtenstein dot detail" for macro photography of his canvases.*

---

## 9. Geometric Distortion / Symmetry

**Presets:** `fisheye_pulse`, `kaleidodream`, `mirror_rorschach`, `tunnelvision`, `voronoi_crystal`

### Hype Williams / Missy Elliott -- The Rain (Supa Dupa Fly) (1997)

**Characteristic:** Fisheye lens as hip hop visual identity
**Look for:** Extreme barrel distortion magnifying central subject (Missy in inflated suit),
compressing periphery into curved horizon. The fish-eye becomes its own character,
giving realistic environments a cartoonish pop. The `fisheye_pulse` preset should
reproduce this field-of-vision magnification and peripheral compression.

### James Whitney -- Lapis (1966)

**Images:**
- https://upload.wikimedia.org/wikipedia/en/1/1a/JWlapis.jpg
  (Wikipedia -- film still)
- https://www.johncoulthart.com/feuilleton/wp-content/uploads/2006/11/lapis1.jpg
- https://www.johncoulthart.com/feuilleton/wp-content/uploads/2006/11/lapis2.jpg
- https://www.johncoulthart.com/feuilleton/wp-content/uploads/2006/11/lapis3.jpg

**Characteristic:** Analog computer mandala animation
**Look for:** Thousands of precise points of light forming mandala outlines against
black background. Smaller circles oscillate in and out in arrays of color.
Created using WWII anti-aircraft guidance hardware converted to animation control.
The `kaleidodream` preset should produce this quality of radial symmetry with
particle-like points forming and dissolving geometric patterns.

### Rorschach Inkblot Test Cards

**Images (Wikimedia Commons -- public domain, all 10 cards):**
- https://upload.wikimedia.org/wikipedia/commons/7/70/Rorschach_blot_01.jpg
- https://upload.wikimedia.org/wikipedia/commons/b/bc/Rorschach_blot_02.jpg
- https://upload.wikimedia.org/wikipedia/commons/8/82/Rorschach_blot_03.jpg
- https://upload.wikimedia.org/wikipedia/commons/1/14/Rorschach_blot_04.jpg
- https://upload.wikimedia.org/wikipedia/commons/5/54/Rorschach_blot_05.jpg
- https://upload.wikimedia.org/wikipedia/commons/7/74/Rorschach_blot_06.jpg
- https://upload.wikimedia.org/wikipedia/commons/2/2d/Rorschach_blot_07.jpg
- https://upload.wikimedia.org/wikipedia/commons/4/43/Rorschach_blot_08.jpg
- https://upload.wikimedia.org/wikipedia/commons/b/b7/Rorschach_blot_09.jpg
- https://upload.wikimedia.org/wikipedia/commons/3/32/Rorschach_blot_10.jpg

**Characteristic:** Bilateral mirror symmetry
**Look for:** Ink folded along a vertical axis producing perfect left-right symmetry.
Cards 1, 4, 5, 6, 7 are achromatic (black/grey). Cards 2, 3 add red.
Cards 8, 9, 10 are fully polychromatic. The `mirror_rorschach` preset should
mirror the live camera feed along the vertical axis to produce this inkblot symmetry.

### Douglas Trumbull -- 2001: A Space Odyssey Stargate (1968)

**Images (slit-scan analysis):**
- https://www.seriss.com/people/erco/2001/images/seq29-shot27-orig.jpg
- https://www.seriss.com/people/erco/2001/images/seq29-shot27-slitscan.jpg
- https://www.seriss.com/people/erco/2001/images/seq29-shot4-orig.jpg
- https://www.seriss.com/people/erco/2001/images/seq29-shot4-slitscan.jpg
- https://www.seriss.com/people/erco/2001/images/seq29-shot8-orig.jpg
- https://www.seriss.com/people/erco/2001/images/seq29-shot8-slitscan.jpg

**Characteristic:** Slit-scan tunnel / infinite corridor
**Look for:** Symmetrical corridors of streaming colored light converging toward
a central vanishing point. Created by long-exposure photography through a moving slit
over illuminated transparencies. 36-hour continuous camera runs per take.
The `tunnelvision` preset should produce this infinite-depth tunnel of radiating color.

---

## 10. Biometric / Reactive

**Presets:** `heartbeat`, `diff_preset`, `slitscan_preset`

### Rafael Lozano-Hemmer -- Pulse Room (2006)

**Images (artist website -- multiple installations):**
- https://www.lozano-hemmer.com/image_sets/pulse_room/venice_2007/pulseroom_venice_01_t.jpg
- https://www.lozano-hemmer.com/image_sets/pulse_room/venice_2007/pulseroom_venice_02_t.jpg
- https://www.lozano-hemmer.com/image_sets/pulse_room/venice_2007/pulseroom_venice_03_t.jpg
- https://www.lozano-hemmer.com/image_sets/pulse_room/mexico_2015/pulse_room_mexico_2015_rlh_001_t.jpg
- https://www.lozano-hemmer.com/image_sets/pulse_room/washington_2018/pulse_room_washington_2018_cc_001_t.jpg
- https://www.lozano-hemmer.com/image_sets/pulse_room/washington_2018/pulse_room_washington_2018_cc_002_t.jpg
- https://www.lozano-hemmer.com/image_sets/pulse_room/kanazawa_2025/pulse_room_kanazawa_2025_ko_001_t.jpg

**Characteristic:** Heartbeat driving visual output
**Look for:** 300 incandescent bulbs pulsing with recorded cardiac rhythms of visitors.
Each bulb flashes in time with a captured heartbeat, creating an asynchronous luminous
field. The `heartbeat` preset should modulate visual parameters (brightness, scale,
saturation) in sync with detected heart rate, producing a pulsing rhythm that
matches the operator's cardiac cycle.

### Daniel Rozin -- Mechanical Mirrors Series (1999-ongoing)

**Images (artist website):**
- https://www.smoothware.com/danny/newsmallwoodenmirror.jpg (Wooden Mirror)
- https://www.smoothware.com/danny/newsmalltrashmirror.jpg (Trash Mirror)
- https://www.smoothware.com/danny/Penguins-Mirror.jpg (Penguin Mirror)
- https://www.smoothware.com/danny/PomPom-Mirror.jpg (PomPom Mirror)
- https://www.smoothware.com/danny/smallpeg.jpg (Peg Mirror)

**Characteristic:** Frame differencing driving physical actuators
**Look for:** Live camera input converted to coarse-pixel physical display. Each "pixel"
is a physical object (wood tile, trash piece, penguin toy, pompom) rotated by a motor
to show its light or dark side based on camera brightness at that grid position.
The `diff_preset` should capture this quality of live motion detection where
frame-to-frame differences are visualized as bright regions on dark ground.

### Douglas Trumbull -- Slit-Scan Rig (1968)

**Characteristic:** Temporal-spatial scanning apparatus
**Look for:** Same slit-scan mechanism as the Stargate sequence but applied to arbitrary
content -- scanning a narrow strip of time across the frame, creating temporal smearing
where past and present coexist in adjacent columns. The `slitscan_preset` should
scan one column of pixels per frame from left to right, building up a temporal
cross-section of the scene.

---

## URL Verification Notes

All URLs were gathered 2026-04-03. Museum collection URLs (Smithsonian, SFMOMA, Tate,
Buffalo AKG, Chinati) are stable institutional links. WordPress-hosted blog URLs may be
less stable. Wikimedia Commons URLs are permanent.

For images that returned 403 or were behind paywalls, the source page URL is provided
instead so the image can be retrieved manually via browser.

## Cross-Reference: Preset to Reference Work

| Preset | Primary Reference | Image Available |
|--------|------------------|-----------------|
| ambient | Warhol Screen Tests | Yes |
| clean | Viola Reflecting Pool | Yes (SFMOMA) |
| ghost | Rybczynski Tango | Internet Archive only |
| trails | Vasulka Noisefields | Yes (vasulka.org) |
| feedback_preset | Paik TV Buddha | Yes (Wikimedia + publicdelivery) |
| echo | Vasulka Noisefields | Yes |
| reverie_vocabulary | Paik TV Buddha | Yes |
| vhs_preset | Rist I'm Not The Girl | Yes (Tate + SFMOMA) |
| dither_retro | Menkman Vernacular | Yes (Lumen Prize) |
| nightvision | Zero Dark Thirty | Production stills only |
| datamosh | Murata Monster Movie | Yes (8 stills, Smithsonian) |
| datamosh_heavy | Kanye Welcome to Heartbreak | KnowYourMeme reference |
| glitch_blocks_preset | Menkman Vernacular | Yes |
| pixsort_preset | Asendorf Mountain Tour | Yes (8 images) |
| screwed | A$AP Rocky L$D | Music video only |
| trap | Travis Scott SICKO MODE | Music video only |
| neon | Flavin / Enter the Void | Yes (Chinati + Art of Title) |
| thermal_preset | Mosse Enclave/Incoming | Yes (extensive gallery) |
| silhouette | Saul Bass Golden Arm | Yes (Art of the Title) |
| sculpture | Rozin Wooden Mirror / Rutt-Etra | Yes |
| halftone_preset | Knowlton & Harmon | Yes (Buffalo AKG) |
| ascii_preset | Cosic ASCII History | Yes (Flickr) |
| fisheye_pulse | Hype Williams The Rain | Music video only |
| kaleidodream | Whitney Lapis | Yes (3 stills) |
| mirror_rorschach | Rorschach Cards | Yes (10 cards, Wikimedia) |
| tunnelvision | Trumbull Stargate | Yes (6 slit-scan analyses) |
| voronoi_crystal | Ikeda datamatics | Yes (artist website) |
| heartbeat | Lozano-Hemmer Pulse Room | Yes (7+ installation photos) |
| diff_preset | Rozin Mechanical Mirrors | Yes (5 variants) |
| slitscan_preset | Trumbull slit-scan rig | Yes (shared with Stargate) |
