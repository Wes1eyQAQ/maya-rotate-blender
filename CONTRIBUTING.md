# Contributing

Report Blender version, operating system, mode, transform orientation and whether the target has constraints/drivers. Include a short reproduction and a minimal shareable file if possible.

Run `blender --background --factory-startup --python tests/smoke_test.py` with Blender 4.4.3. Tests use synthetic objects/bones and a temporary configuration folder. Interactive visuals still need manual checks.

Keep rotations separate from translation/scale changes. Test cancellation and rotation-only auto-keying, especially with pose bones and multiple targets. UI language strings live in StableRotate/i18n.py.
