# Getting started

This guide covers setting up Senna on a new computer. Steps marked **(first time only)** are done once, by one person, to create the project.

## 1. Install the tools

1. **Epic Games Launcher**: <https://www.unrealengine.com/download>
2. **Unreal Engine 4.27**: in the launcher, go to *Unreal Engine → Library*, click **+** next to *Engine Versions*, choose **4.27**, and install it. It needs about 40 GB of disk space.
3. **Git**: <https://git-scm.com/downloads>. Git LFS comes with it on Windows.
4. **A Git app (optional)**: [GitHub Desktop](https://desktop.github.com/) is easiest for beginners, and it supports LFS.

## 2. Get the repo

```sh
git lfs install            # once per computer
git clone https://github.com/TarZac317/Senna.git
```

Or in GitHub Desktop: *File → Clone repository → TarZac317/Senna*.

## 3. Create the Unreal project (first time only)

Unreal won't create a project inside a folder that already has files in it, so create the project somewhere else and then move it in.

1. Open **Unreal Engine 4.27** from the launcher.
2. Choose **Games → Blank**, then set:
   - **Blueprint** (not C++)
   - **Desktop / Console**
   - **Maximum Quality**
   - **Raytracing disabled**
   - **No Starter Content**. This keeps the repo small.
3. Pick a temporary location, such as your Desktop, and name the project **`Senna`**. Click **Create Project**.
4. Close the editor once it opens.
5. From the new temporary `Senna` folder, copy **`Senna.uproject`**, **`Config/`** and **`Content/`** into the root of the cloned repo, next to this `docs/` folder.
   Don't copy `Saved/`, `Intermediate/` or `DerivedDataCache/`. Unreal rebuilds them, and Git ignores them.
6. Open `Senna.uproject` from the repo folder and check that it loads.
7. Create the folders from [project-layout.md](project-layout.md) in the Content Browser.
8. Commit and push. The `.uasset` and `.umap` files go to Git LFS automatically.

Delete the temporary project afterwards.

## 4. Everyday work

- **Pull** before you start working.
- **Lock** an asset before you edit it, because Unreal assets can't be merged:
  `git lfs lock Content/Senna/Ships/BP_PlayerShip.uasset`
  Unlock it after you push: `git lfs unlock <path>`
- Commit small and often, with a clear message.
- Do experiments in your own folder under `Content/Developers/<YourName>/` so they don't break shared maps.
