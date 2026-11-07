# Prototype build guide (UE 4.27, Blueprints)

This guide builds the slice described in the [design brief](../design/senna-slice-brief.md): a ship, one Momentum Line, a canyon test course, checkpoints, wrecks, and a race timer. Everything is Blueprint and placeholder art.

Do the parts in order. Each one ends with something you can test by pressing **Play**.

Folder and naming rules are in [project-layout.md](../project-layout.md). Starting values for numbers are marked *(tune)*. Expect to change them a lot.

---

## Part 1 — Input

*Edit → Project Settings → Input*. Add these **Axis Mappings**:

| Axis | Keyboard / mouse | Gamepad |
|---|---|---|
| `Throttle` | W = 1, S = −1 | Right Trigger = 1, Left Trigger = −1 |
| `Pitch` | Mouse Y = −1 | Left Stick Y = −1 |
| `Yaw` | A = −1, D = 1 | Left Stick X = 1 |
| `Roll` | Q = −1, E = 1 | Right Stick X = 1 |

Add these **Action Mappings**: `Boost` (Left Shift / Gamepad Face Button Bottom), `Stabilize` (Space / Gamepad Left Shoulder) and `Restart` (R / Gamepad Special Right).

## Part 2 — The ship (`Content/Senna/Ships/BP_PlayerShip`)

Create a **Blueprint Class → Pawn** named `BP_PlayerShip`.

**Components**

- `Collision`: a **Box Collision**, set as the root. Size about 200 × 120 × 60. Collision preset `Pawn`.
- `ShipMesh`: a **Static Mesh**, such as a flattened cube or cone, as a placeholder. Set collision to *No Collision*.
- `SpringArm`: Target Arm Length 800 *(tune)*. Turn on **Enable Camera Lag** (speed 8) and **Enable Camera Rotation Lag** (speed 6).
- `Camera`: attached to `SpringArm`. This is the chase cam.

In *Class Defaults*, set **Auto Possess Player** to *Player 0*.

**Variables** (all Float unless noted)

| Name | Start value | Meaning |
|---|---|---|
| `Velocity` (Vector) | 0,0,0 | Current movement, in cm/s |
| `Thrust` | 3000 *(tune)* | How hard the engines push |
| `BoostMultiplier` | 1.8 | Thrust × this while boosting |
| `Drag` | 0.6 | How fast speed bleeds off |
| `TurnRate` | 70 | Degrees per second for pitch and yaw |
| `RollRate` | 120 | Degrees per second for roll |
| `MaxSpeed` | 9000 | Speed cap outside a Line |
| `WreckSpeed` | 2500 | Hitting a wall faster than this wrecks the ship |
| `bInLine` (Bool) | false | Set by the Momentum Line |
| `LineAssist` (Vector) | 0,0,0 | Push from the Line this frame |
| `RespawnTransform` (Transform) | — | Last checkpoint |
| `bWrecked` (Bool) | false | |

**Event Graph: Event Tick (use Delta Seconds)**

1. If `bWrecked`, do nothing.
2. **Rotate:** `AddActorLocalRotation` with Pitch = `Pitch axis × TurnRate × Delta`, Yaw = `Yaw axis × TurnRate × Delta`, and Roll = `Roll axis × RollRate × Delta`.
3. **Thrust:** `accel = GetActorForwardVector × Throttle axis × Thrust`. Multiply by `BoostMultiplier` while Boost is held.
4. **Drag:** `Velocity = Velocity − Velocity × Drag × Delta`.
5. **Integrate:** `Velocity = Velocity + (accel + LineAssist) × Delta`.
6. **Stabilize** (while held): rotate the actor toward zero roll, and blend `Velocity` toward the forward vector with `VInterpTo`, speed 2.
7. **Cap:** if not `bInLine`, `ClampVectorSize(Velocity, 0, MaxSpeed)`.
8. **Move:** `AddActorWorldOffset(Velocity × Delta, Sweep = true)`.
9. If the sweep hit something and `VectorLength(Velocity) > WreckSpeed`, call `Wreck`. Otherwise, slide along the wall: set `Velocity` to its projection onto the hit plane, using `ProjectVectorOnToPlane` with the hit normal.
10. Set `LineAssist` back to 0,0,0. The Line sets it again each frame.

**Custom events**

- `Wreck`: set `bWrecked` = true, hide `ShipMesh`, spawn a placeholder explosion (any particle), and after a **Delay** of 1.5 s call `Respawn`.
- `Respawn`: `SetActorTransform(RespawnTransform)`, set `Velocity` to 0, `bWrecked` = false and `bInLine` = false, and show `ShipMesh`.
- On **BeginPlay**, set `RespawnTransform` to the actor's transform.
- **Restart** action: open the current level again.

✅ **Test:** drop the ship into an empty level and fly around. Hitting the floor fast should wreck you and respawn you.

## Part 3 — Momentum Line (`Content/Senna/MomentumLines/BP_MomentumLine`)

Create a **Blueprint Class → Actor** named `BP_MomentumLine`.

**Components:** `Spline` (the root), plus a **Niagara** or **Cascade** particle trail for the visual. Placing a few particle systems along the spline in the Construction Script works for now.

**Variables**

| Name | Start value | Meaning |
|---|---|---|
| `CoreRadius` | 300 | Fastest zone around the spline |
| `OuterRadius` | 900 | Edge of the Line |
| `LineSpeed` | 16000 *(tune)* | Speed the Line pulls you toward |
| `PullStrength` | 4 | How quickly you reach `LineSpeed` |
| `CenteringStrength` | 2 | How strongly the Line pulls you toward its core |
| `GoodEntryDot` | 0.85 | How aligned you must be for a clean entry |
| `BadExitDot` | 0.5 | Leaving through the side while this misaligned wrecks you |
| `Ship` (BP_PlayerShip) | — | Set on BeginPlay with `GetPlayerPawn → Cast` |
| `bShipInside` (Bool) | false | |
| `EntryQuality` | 1 | 0–1, graded at entry |

**Event Tick**

1. `Closest = Spline.FindLocationClosestToWorldLocation(Ship location)`, `Dir = Spline.FindDirectionClosestToWorldLocation(...)`, and `Dist = distance(Ship, Closest)`.
2. **Entering** (`Dist < OuterRadius` and not `bShipInside`): set `bShipInside`, then `Ship.bInLine` = true. Grade the entry: `EntryQuality = clamp((dot(normalize(Ship.Velocity), Dir) − 0.5) / (GoodEntryDot − 0.5), 0, 1)`. If `EntryQuality` is 0, call `Ship.Wreck`, because a bad entry throws you out hard.
3. **Riding** (`bShipInside`):
   - `core = 1 − clamp((Dist − CoreRadius) / (OuterRadius − CoreRadius), 0, 1)`. This is 1 at the core and 0 at the edge.
   - `target = Dir × LineSpeed × (0.6 + 0.4 × core) × (0.5 + 0.5 × EntryQuality)`
   - `Ship.LineAssist = (target − Ship.Velocity) × PullStrength + normalize(Closest − Ship location) × CenteringStrength × Dist`
   - Turbulence: add a small random camera shake that grows as `core` drops.
4. **Leaving** (`Dist > OuterRadius` while `bShipInside`): set `bShipInside` = false and `Ship.bInLine` = false.
   - If you're near the spline's **end**, check with `Spline.FindInputKeyClosestToWorldLocation`, then compare against the last spline point. That's a clean exit, and you keep your speed.
   - If you leave through the **side** and `dot(normalize(Ship.Velocity), Dir) < BadExitDot`, call `Ship.Wreck`.
   - Any other side exit is survivable but rough: multiply `Ship.Velocity` by 0.7.

✅ **Test:** place a straight Line in the empty level and fly into it head-on, then at an angle. A clean entry should feel like a slingshot, and a sloppy one should hurt.

## Part 4 — Checkpoints, start, finish (`Content/Senna/Core/`)

- **`BP_Checkpoint`**: an Actor with a Box Collision (Generate Overlap Events on) and an Arrow component that shows the respawn direction. On **Begin Overlap** with `BP_PlayerShip`, set the ship's `RespawnTransform` to the Arrow's world transform.
- **`BP_RaceGameMode`**: a GameModeBase with Default Pawn = `BP_PlayerShip`. It holds the variables `RaceTime` (Float), `bRacing` (Bool) and `BestTime` (Float, starting at 0). While `bRacing` is true, Tick adds Delta Seconds to `RaceTime`.
- **`BP_StartLine`** and **`BP_FinishLine`**: box triggers. The start line sets `bRacing` = true and `RaceTime` = 0. The finish line sets `bRacing` = false and updates `BestTime`.
- **`WBP_RaceHUD`**: text for the current time, best time and speed (`VectorLength(Velocity) × 0.036` gives km/h). Create it on the ship's BeginPlay with **Add to Viewport**.

Set `BP_RaceGameMode` in *World Settings → GameMode Override* for the course level.

## Part 5 — The canyon course (`Content/Senna/Courses/L_TestCourse`)

Block it out with **BSP brushes** or scaled cubes. *Modes → Geometry* is quick for canyon walls.

1. **Start straight**, about 15 s of flying, with `BP_StartLine` at the beginning.
2. **The split:**
   - **Safe route:** a wide, open valley that curves around. Put two checkpoints along it.
   - **Line route:** a narrow gap under a stone arch, a stretched and bent cube, lined up with a `BP_MomentumLine` whose spline threads through the canyon close to the walls. Put one checkpoint just before the arch.
3. **The merge**, then a short run through two or three rock arches to `BP_FinishLine`.
4. To make the Line visible without a HUD marker, add a cloud ribbon or particle trail along the spline, and a few cone "plants" leaning in the direction it flows.

Add a **Directional Light**, a **Sky Atmosphere** and an **Exponential Height Fog** so the canyon reads at speed.

✅ **Test (the real one):** time both routes. After a few practice runs, the Line route should be roughly 10–20% faster, and missing the entry should feel like your own fault. If it doesn't, tune `LineSpeed`, `GoodEntryDot` and `OuterRadius` first.

---

## When you're stuck

- Print values to the screen with **Print String**, such as `EntryQuality`, `Dist` and speed.
- Draw the Line's radius with **Draw Debug Sphere** at the closest spline point.
- Commit after each part works, so you can always go back.
