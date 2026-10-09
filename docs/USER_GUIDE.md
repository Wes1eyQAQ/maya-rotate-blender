# User guide

## Three rotation gestures

Select an object in Object mode or a control bone in Pose mode, then activate the tool in N → Maya → Stable Rotate → Use Maya Rotate 1.9.

| Where you drag | Result |
| --- | --- |
| Red / green / blue ring | Rotation around the tool X / Y / Z axis |
| Sphere interior | Free 3D trackball rotation |
| Yellow outer ring | Rotation around the viewing direction |

Hold Shift for precision. Release the left mouse button or press Enter to confirm. Esc or right-click restores the starting rotation. Auto Keying inserts rotation channels on confirmation when enabled.

## Appearance and size

Sphere Size controls the display scale (0.25–4). + / - and numpad + / - resize the sphere while the custom rotation tool is active. The tool's shortcut poll does not override zoom when another tool is active.

Opacity sets transparency. Color Saturation makes the fixed red/green/blue/yellow palette more or less vivid without altering hue or brightness. Line Width sets thickness. Reset Appearance restores opacity, saturation and width; it does not reset size.

## Tool orientations

Choose Global, Local, View, or a custom transform orientation in Blender's transform orientation selector. Other orientation modes fall back to Global in this implementation. This adjusts the tool axes rather than editing a bone's rest orientation.

## Troubleshooting

If the sphere does not appear, activate the custom tool, check that a target is selected, and ensure tool gizmos are visible. This addon supports Object/Pose mode rather than mesh or armature Edit mode. If an upgrade seems unchanged, disable the older addon and restart Blender.

The tool keeps each target in place; it intentionally does not perform orbital rotations around the 3D cursor or a shared median. Constraints and drivers can override the final evaluated pose. Use a simple unconstrained object to distinguish tool behavior from rig behavior.
