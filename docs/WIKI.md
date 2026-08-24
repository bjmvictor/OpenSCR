# OpenSCR Wiki

## Creating a screen saver

Add images, choose timing, fit, ordering, text, and transition effects, then
select **Build .SCR**. The generated screen saver contains its configuration
and images.

OpenSCR projects are UTF-8 JSON files. Use **File > Save As** to create one and
**File > Open Project** to continue editing it later.

## Installing on Windows

Use the x64 Setup package from GitHub Releases. It supports Windows Server 2016
build 14393, Windows 10, Windows 11, and newer x64 Windows Server versions. The
installer deploys every application file and the required native runtime
libraries.

If a portable `onedir` package is used, extract it completely and keep all its
files together. Windows 32-bit is not supported.

## Linux

The Linux build is a project editor. Preview and `.scr` generation remain
Windows-only because they depend on native Win32 APIs.

## Contributing

Bug fixes, effects, documentation, and translations are welcome. Follow
[`TRANSLATING.md`](TRANSLATING.md) when changing or adding a language.
