# Windows Build Pipeline

This project should be packaged with PyInstaller in `onedir` mode for stability.
The Rust HTTP engine is built first as a Python extension (`.pyd`), then bundled with the app.

## Why PyInstaller, not Nuitka

For this project, PyInstaller is the more pragmatic default:

- simpler setup for PySide6
- fewer moving parts during fast iteration
- easier to debug packaging issues
- works fine with the Rust `.pyd` extension

Nuitka is still possible later, but for "build it reliably and ship it" PyInstaller is the safer first path.

## What Gets Pushed

Push these files from `native/http_engine`:

- `Cargo.toml`
- `pyproject.toml`
- `README.md`
- `src/*.rs`

Do not push:

- `native/http_engine/target/`
- built wheels
- `.pyd` / `.dll`
- local `.venv`

## Requirements

Install on the build machine:

1. Python
2. Rust toolchain
3. Visual Studio Build Tools 2022
4. Python packaging tools in the project venv

### Rust

```powershell
winget install Rustlang.Rustup
```

Then verify:

```powershell
cargo --version
rustc --version
```

### MSVC / Linker

Install Visual Studio Build Tools 2022 and enable:

- `Desktop development with C++`

### Python Packaging Tools

```powershell
.\.venv\Scripts\python.exe -m ensurepip --upgrade
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install maturin pyinstaller
```

## Build The Native Module

```powershell
cd native/http_engine
..\..\.venv\Scripts\python.exe -m maturin develop --release
```

## Build The Stable Windows App

From repo root:

```powershell
.\spec\build_windows.ps1
```

This will:

1. build/install the Rust extension into `.venv`
2. run PyInstaller with `spec\MeowTool.spec`
3. produce `dist\MeowTool\MeowTool.exe`

## Build The Experimental Onefile App

From repo root:

```powershell
.\spec\build_windows_onefile.ps1
```

This will produce:

- `dist\MeowTool-onefile.exe`

Use it only for comparison/testing. For the main shipped build, prefer `onedir`.

## Why `onedir`

`onedir` is chosen intentionally:

- more stable than `onefile` for PySide6 apps
- no unpack-at-startup overhead
- fewer path issues with bundled assets
- easier to inspect and debug if something is missing

## Why `onefile` Is Experimental Here

- slower startup because everything is unpacked at launch
- more fragile with PySide6 plugins and native `.pyd` modules
- harder to debug path/resource issues

## Runtime Paths In Frozen Build

Built-in assets are loaded from the bundled app data.
User-writable files are created next to the executable:

- `Settings\Configs`
- `Settings\Themes`
- `Settings\Translations`

So users can still edit configs/themes/translations after packaging.
