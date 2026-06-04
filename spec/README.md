# Packaging Files

This folder contains Windows packaging files for MeowTool.

Contents:

- `MeowTool.spec` — stable `onedir` PyInstaller spec
- `MeowTool.onefile.spec` — experimental `onefile` PyInstaller spec
- `build_windows.ps1` — build script for stable `onedir`
- `build_windows_onefile.ps1` — build script for experimental `onefile`
- `BUILD_WINDOWS.md` — packaging notes and setup instructions

Run from repo root:

```powershell
.\spec\build_windows.ps1
```

Or test onefile:

```powershell
.\spec\build_windows_onefile.ps1
```
