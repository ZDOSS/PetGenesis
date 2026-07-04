# Visual Standards

Read this file before generating row strips, inspecting contact sheets/GIFs, or repairing visual output. These rules describe what is allowed to become part of a transparent Codex pet sprite.

## Transparency And Effects

Pet rows are processed into transparent `192x208` cells, so every generated pixel must either belong to the pet sprite or be cleanly removable chroma-key background. Prefer pose, expression, and silhouette changes over decorative effects.

The deterministic raster pipeline owns the transparency invariant: extraction removes only chroma-key pixels connected to the source strip background, pixels that become fully transparent are normalized so they do not retain hidden RGB residue, and atlas validation should fail if exported files violate that invariant. Do not paper over colored halos or transparent-pixel residue by accepting visually inconsistent outputs.

Allowed effects must satisfy all of these conditions:

- The effect is state-relevant and helps explain the animation.
- The effect is physically attached to, touching, or overlapping the pet silhouette, not floating nearby.
- The effect is inside the same frame slot as the pet and does not create a separate sprite component.
- The effect is opaque, hard-edged enough for clean extraction, and uses non-chroma-key colors.
- The effect is small enough to remain readable at `192x208` without clutter.

Avoid these by default because they usually break transparent-background cleanup or component extraction:

- wave marks, motion arcs, speed lines, action streaks, afterimages, blur, or smears
- detached stars, loose sparkles, floating punctuation, floating icons, falling tear drops, separated smoke clouds, or loose dust
- cast shadows, contact shadows, drop shadows, oval floor shadows, floor patches, landing marks, impact bursts, glow, halo, aura, or soft transparent effects
- text, labels, frame numbers, visible grids, guide marks, speech bubbles, thought bubbles, UI panels, code snippets, checkerboard transparency, white backgrounds, black backgrounds, or scenery
- chroma-key-adjacent colors in the pet, prop, effects, highlights, or shadows
- stray pixels, disconnected outline bits, speckle/noise, cropped body parts, overlapping poses, or any pose that crosses into a neighboring frame slot

## State-Specific Guidance

- `idle`: keep this calm and low-distraction. Use only subtle breathing, a tiny blink, a slight head or body bob, a very small material sway, or another quiet persona-preserving motion. The loop must still contain visible micro-variation; do not accept six effectively identical copies. Do not show waving, walking, running, jumping, talking, working, reviewing, emotional reactions, large gestures, item interactions, or new props.
- `idle`: do not force tiny accessories to be visible if doing so creates an unnatural hand pose. Prefer preserving the approved base style, clean hands, and stable calm motion over showing fragile details such as rings in every frame. A hidden or pet-scale-simplified tiny accessory is better than duplicated marks, wrong fingers, or visible paint-over artifacts.
- `waving`: show the wave through paw, hand, wing, or limb pose only. Do not draw wave marks, motion arcs, lines, sparkles, symbols, or floating effects around the gesture.
- `jumping`: show vertical motion through body position only. Do not draw shadows, dust, landing marks, impact bursts, bounce pads, or floor cues.
- `failed`: tears, attached smoke puffs, or attached stars are allowed if they obey the allowed-effects rules; do not use red X marks, floating symbols, detached smoke, detached stars, or separate tear droplets.
- `waiting`: show that Codex needs approval, help, or user input through an expectant asking pose. Keep it distinct from ordinary idle and review.
- `running`: show active task work, processing, thinking, scanning, typing, or focused effort. Do not show literal foot-running, jogging, sprinting, treadmill motion, raised knees, long steps, pumping arms, directional travel, speed lines, dust clouds, floor shadows, motion trails, or detached motion effects.
- `review`: show focus through lean, blink, eyes, head tilt, or paw/hand position. Do not add magnifying glasses, papers, code, UI, punctuation, symbols, or other new props unless they already exist in the base pet identity.
- `running-right` and `running-left`: show directional drag movement through body, limb, and prop movement only. `running-right` must face and travel right; `running-left` must face and travel left. Their cadence must visibly alternate across the loop rather than repeating one nearly static stride. Do not draw speed lines, dust clouds, floor shadows, motion trails, or detached motion effects.
