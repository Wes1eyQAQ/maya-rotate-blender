# Maya Rotate for Blender

**Rotate naturally. Keep your controls in place.**

A Maya-inspired rotation sphere for Blender objects and pose controls: three axis rings, free rotation inside the sphere, and a yellow outer ring for rotation around the viewing direction.

[中文介绍](README.zh-CN.md) · [User guide](docs/USER_GUIDE.md) · [Download v1.9.1](downloads/StableRotate-1.9.1.zip)

## What makes it useful?

- **Stable edge-on dragging.** When a ring is seen nearly edge-on in an orthographic view, dragging uses a continuous screen-space motion instead of jumping 180° as the cursor crosses the center.
- **Free 3D rotation inside the sphere.** Drag the interior to turn the selected objects or pose controls with a virtual trackball.
- **A yellow outer ring.** Rotate around the current viewing direction.
- **Rotation only.** The operators restore location and scale channels and retain each target's original position. Multiple controls turn in place rather than orbiting a shared pivot.
- **Adjust the size with + / -.** Resize the custom sphere while its tool is active, including numpad shortcuts.
- **Appearance controls.** Adjust opacity, color saturation and line width. Saturation changes vividness while retaining hue and brightness; it does not fade colors into black or white. Hover highlighting remains available.
- **Precision and cancellation.** Hold Shift for finer movement. Esc or right-click cancels the rotation.
- **Object and Pose modes.** Global, Local, View and custom tool orientations are supported. Other orientation types currently fall back to Global.
- **Rotation-only auto-key.** When Blender Auto Keying is enabled, confirming a drag inserts rotation keys.
- **English by default.** One button cycles English → 中文 → 日本語 and shares the preference with the companion Maya tools.

## Install and activate

1. Download [StableRotate-1.9.1.zip](downloads/StableRotate-1.9.1.zip). The repository Source code ZIP is not the addon installer.
2. In Blender, use **Edit → Preferences → Add-ons → Install from Disk**, then enable **Stable Axis Rotate**.
3. Select an object or pose bone. In the 3D View, press **N**, open **Maya → Stable Rotate**, then click **Use Maya Rotate 1.9**.
4. Drag an axis ring, the sphere interior, or the yellow outer ring. Use **+ / -** to resize and **Shift** to refine the rotation.

On upgrades, disable the old addon first and restart Blender after installation. Enabling the addon alone does not select its custom tool.

## Compatibility and behavior

Validated on **Windows / Blender 4.4.3 / 64-bit**. The public package declares Blender 4.4 as its minimum version; other versions/platforms have not been validated.

This is a custom rotation tool, not a replacement for every Blender transform gizmo. It intentionally rotates each selected target in place even when Blender's pivot is set elsewhere. Existing rig constraints, drivers and parent relationships can affect the evaluated result; test your rig before using it throughout a production scene. It does not change bone rest axes or rewrite animation curves.

The automated smoke test covers continuous edge-on motion, cancellation, object and pose rotation, unchanged translation/scale, rotation-only auto-keying, color saturation, and the sphere draw callback. Interactive ring hit-testing and visual appearance still require Blender UI checks.

## Documentation and feedback

- [User guide](docs/USER_GUIDE.md)
- [中文使用指南](docs/USER_GUIDE.zh-CN.md)
- [Release notes](docs/RELEASE_NOTES.md)
- [Contributing and tests](CONTRIBUTING.md)
- [Companion Graph Editor addon](https://github.com/Wes1eyQAQ/maya-graph-tools-blender)

## License and credits

GPL-3.0-or-later. See [LICENSE](LICENSE).

Workflow design and hands-on iteration came from the project creator's animation work; implementation was developed with Codex. Independent community project, not affiliated with Autodesk or Blender Foundation.
