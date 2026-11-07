# Senna slice — design brief

**Goal:** a short, playable test that answers one question: *is flying a Momentum Line fun, and does skill matter more than gear?*

**Scope:** one ship, one Momentum Line, one test course of about 60–90 seconds, and a timer. No story, no NPCs, no final art.

> Items marked **[prototype guess]** are placeholders made up for testing. They are not canon. Lore listed as OPEN in the [compendium](../lore/senna-lore-compendium.md) stays open. Whatever we learn here gets proposed back to Logan before it goes into the lore.

## Pillars (from the lore)

1. **The pilot beats the parts.** A skilled run on starter parts should beat a sloppy run on better ones.
2. **Lines are fast and dangerous.** The fastest route is the riskiest.
3. **Read the world.** Players can spot a Line from the environment, without needing a HUD marker.
4. **Builds change the route.** Different ships solve the same course in different ways. This comes in step 4.
5. **Senna looks fast even when nothing is moving.**

## The ship

The player's own ship, fitted with starter racing parts.

- **Controls:** throttle, pitch, yaw, roll, boost, and a stabilize button. Keyboard/mouse and gamepad.
- **Feel:** responsive but heavy enough that lining up an entry takes planning. **[prototype guess]**
- **Camera:** third-person chase cam. *(Logan, 2026-11-07)*

## Momentum Line behaviour **[prototype guess, since the detailed physics are OPEN in the lore]**

| Moment | What happens |
|---|---|
| **Spotting** | The Line shows as a ribbon of cloud and streaming particles, and nearby plants lean toward it. |
| **Entry** | The entry is graded on angle and speed. A clean entry gives a big speed boost and full stability. A poor entry gives less speed and some shake. A bad entry throws the ship out. |
| **Riding** | The Line carries the ship with little thrust. The player steers to stay in the core, where it's fastest. Drifting toward the edge adds turbulence. |
| **Leaving** | Leaving on purpose keeps most of the speed. A bad exit **wrecks the ship** *(Logan, 2026-11-07)*. The player respawns at the last checkpoint, and the lost time is the penalty. **[prototype guess: checkpoint respawn]** |
| **Risk** | The fastest stretch of the Line runs close to the canyon walls. |

## Test course

One canyon map built from placeholder shapes *(canyon confirmed by Logan, 2026-11-07)*:

- Checkpoints every 15–20 seconds of flying, used for respawns. **[prototype guess]**
- A start straight, then a canyon with **two routes**:
  - **Safe route:** an open valley. Easy flying, no Line, slower.
  - **Line route:** a tight entry under a stone arch that leads into the Momentum Line. Faster if you hit the entry, slower if you miss it.
- The routes rejoin, then there's a short finish through rock arches.
- Ghost replay of your best lap. **[nice to have]**

## Success test

The slice works if:

- A new player can finish within a few tries.
- After practice, the Line route is clearly faster, roughly 10–20% **[prototype guess]**.
- Missing the entry feels like your own mistake, not like random bad luck.
- Testers want "one more run."

## Out of scope for this slice

Ship parts and upgrades (step 4), mechanics, the Worldline, cities, Houses, story, final art, and multiplayer.

## Decisions

- **Camera:** chase cam.
- **Bad Line exit:** wrecks the ship, with a respawn at the last checkpoint.
- **First setting:** a canyon.
