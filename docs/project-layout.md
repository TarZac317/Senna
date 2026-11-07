# Project layout

## Repo

```
Senna.uproject      Unreal project file
Config/             Engine and project settings
Content/            All Unreal assets (stored in Git LFS)
docs/               Design docs, lore, guides
```

## Content folders

All game assets live under `Content/Senna/`, grouped by feature so each piece of the game is easy to find:

```
Content/Senna/
  Core/            Game mode, player controller, shared Blueprints
  Ships/           The player's ship, flight controls, ship parts
  MomentumLines/   Momentum Line Blueprints, effects, tuning data
  Courses/         Race courses and test maps
  UI/              HUD, menus, race timer
  Art/             Shared materials, textures, meshes
  Audio/           Sound effects and music
Content/Developers/<YourName>/   Personal sandbox, not used by shared maps
```

## Naming

Use a short prefix so each asset's type shows in its name:

| Prefix | Type | Example |
|---|---|---|
| `BP_` | Blueprint | `BP_PlayerShip` |
| `M_` / `MI_` | Material / material instance | `M_Rock`, `MI_Rock_Canyon` |
| `SM_` | Static mesh | `SM_Arch_01` |
| `T_` | Texture | `T_Rock_D` |
| `L_` | Level (map) | `L_TestCourse` |
| `WBP_` | UI widget | `WBP_RaceHUD` |
| `DT_` | Data table | `DT_ShipParts` |
| `S_` | Sound | `S_Boost` |
