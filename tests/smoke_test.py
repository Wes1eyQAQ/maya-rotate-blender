import os,tempfile
os.environ['BLENDER_USER_CONFIG']=tempfile.mkdtemp(prefix='maya-rotate-test-')
import bpy, importlib.util, sys, math
from pathlib import Path
from mathutils import Vector, Matrix
from types import SimpleNamespace, MethodType
root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('StableRotate', root / 'StableRotate' / '__init__.py')
sr = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = sr
spec.loader.exec_module(sr)
sr.register()
area = next(a for a in bpy.context.screen.areas if a.type == 'VIEW_3D')
region = next(r for r in area.regions if r.type == 'WINDOW')
with bpy.context.temp_override(area=area, region=region):
    assert bpy.ops.sr.activate() == {'FINISHED'}
    assert bpy.context.workspace.tools.from_space_view3d_mode('OBJECT').idname == 'sr.stable_object'
    obj = bpy.context.object
    original = obj.matrix_world.copy()
    for degrees in (-360, -180, -1, 0, 1, 180, 360):
        matrix = sr.rotate_matrix(original, Vector((0,0,1)), math.radians(degrees), original.translation)
        assert (matrix.translation-original.translation).length < .001
    center = (0,0)
    # Cursor crosses the center and opposite side: no pi-sized step.
    assert sr.stable_angle_step((-100,0), (100,0), center) == 0
    assert sr.stable_angle_step((-5,0), (5,0), center) == 0
    assert abs(sr.stable_angle_step((100,0), (100,10), center)) < .2
    # Crossing the angular wrap at +/-pi remains continuous.
    assert abs(sr.stable_angle_step((-100,1), (-100,-1), center)) < .03
    class ContextProxy:
        window_manager = SimpleNamespace(modal_handler_add=lambda operator: None)
        def __getattr__(self, name):
            return getattr(bpy.context, name)
    proxy = ContextProxy()
    def event(kind, x=0, y=0, value='NOTHING'):
        return SimpleNamespace(type=kind, mouse_region_x=x, mouse_region_y=y, value=value, shift=False)
    area.spaces.active.region_3d.view_rotation = __import__('mathutils').Quaternion((1,0,0), math.pi/2)
    operator = SimpleNamespace(axis='Z')
    operator.assign = MethodType(sr.SR_OT_rotate.assign, operator)
    assert sr.SR_OT_rotate.invoke(operator, proxy, event('LEFTMOUSE', 200, 200, 'PRESS')) == {'RUNNING_MODAL'}
    assert operator.linear
    angles = []
    for x in (250, 300, 350, 400):
        sr.SR_OT_rotate.modal(operator, proxy, event('MOUSEMOVE', x, 200))
        angles.append(operator.angle)
    assert max(abs(b-a) for a,b in zip([0]+angles, angles)) < 1
    assert abs(operator.angle-2) < .001
    assert sr.SR_OT_rotate.modal(operator, proxy, event('ESC')) == {'CANCELLED'}
    assert max(abs(obj.matrix_world[i][j]-original[i][j]) for i in range(4) for j in range(4)) < .001
    bpy.ops.object.armature_add()
    bpy.ops.object.mode_set(mode='POSE')
    bpy.context.object.data.bones[0].select = True
    bpy.context.object.data.bones.active = bpy.context.object.data.bones[0]
    bpy.context.view_layer.update()
    bone = bpy.context.active_pose_bone
    original_bone = bone.matrix.copy()
    operator = SimpleNamespace(axis='Z')
    operator.assign = MethodType(sr.SR_OT_rotate.assign, operator)
    assert sr.SR_OT_rotate.invoke(operator, proxy, event('LEFTMOUSE', 200, 200, 'PRESS')) == {'RUNNING_MODAL'}
    sr.SR_OT_rotate.modal(operator, proxy, event('MOUSEMOVE', 250, 200))
    assert bone.matrix != original_bone
    bpy.context.scene.tool_settings.use_keyframe_insert_auto = True
    assert sr.SR_OT_rotate.modal(operator, proxy, event('LEFTMOUSE', 250, 200, 'RELEASE')) == {'FINISHED'}
    assert bpy.context.object.animation_data.action is not None
    bpy.ops.object.mode_set(mode='OBJECT')

print('STABLE_ROTATE_PASS: registration, tool activation, simulated modal edge-on drag without pi jumps, cancel restoration, pose rotation and auto-key')

with bpy.context.temp_override(area=area,region=region):
    bpy.ops.object.select_all(action='DESELECT')
    selected=[]
    for index in range(2):
        bpy.ops.mesh.primitive_cube_add(location=(index*3+2,1,2))
        ob=bpy.context.object
        ob.scale=(1.2,.8,1.3)
        selected.append(ob)
    for ob in selected:ob.select_set(True)
    bpy.context.view_layer.update()
    saved=[(ob.location.copy(),ob.scale.copy(),ob.matrix_world.translation.copy()) for ob in selected]
    bpy.context.scene.tool_settings.transform_pivot_point='CURSOR'
    bpy.context.scene.cursor.location=(1,0,0)
    bpy.context.scene.tool_settings.use_keyframe_insert_auto=True
    for kind in ('axis','sphere','view'):
        op=SimpleNamespace(axis='Z')
        cls={'axis':sr.SR_OT_rotate,'sphere':sr.SR_OT_free_rotate,'view':sr.SR_OT_view_rotate}[kind]
        op.assign=MethodType(cls.assign,op)
        assert cls.invoke(op,proxy,event('LEFTMOUSE',200,200,'PRESS'))=={'RUNNING_MODAL'}
        for x,y in ((225,215),(250,240),(275,230)):
            cls.modal(op,proxy,event('MOUSEMOVE',x,y))
            for ob,(loc,scale,pos) in zip(selected,saved):
                assert (ob.location-loc).length<1e-6,(kind,ob.name,'location changed')
                assert (ob.scale-scale).length<1e-6,(kind,ob.name,'scale changed')
                assert (ob.matrix_world.translation-pos).length<1e-5,(kind,ob.name,'world position changed')
        cls.modal(op,proxy,event('LEFTMOUSE',275,230,'RELEASE'))
        for ob in selected:
            assert all(fc.data_path.startswith('rotation_') for fc in ob.animation_data.action.fcurves)
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.object.armature_add(location=(3,2,1))
    bpy.ops.object.mode_set(mode='POSE')
    bone=bpy.context.object.pose.bones[0]
    bone.bone.select=True
    bpy.context.object.data.bones.active=bone.bone
    bone.location=(1,2,3)
    bone.scale=(1.1,.9,1.2)
    bpy.context.view_layer.update()
    loc,scale,pos=bone.location.copy(),bone.scale.copy(),bone.matrix.translation.copy()
    for cls in (sr.SR_OT_rotate,sr.SR_OT_free_rotate,sr.SR_OT_view_rotate):
        op=SimpleNamespace(axis='Z');op.assign=MethodType(cls.assign,op)
        cls.invoke(op,proxy,event('LEFTMOUSE',200,200,'PRESS'))
        cls.modal(op,proxy,event('MOUSEMOVE',250,230))
        assert (bone.location-loc).length<1e-6
        assert (bone.scale-scale).length<1e-6
        assert (bone.matrix.translation-pos).length<1e-5
        cls.modal(op,proxy,event('LEFTMOUSE',250,230,'RELEASE'))
    assert all('rotation_' in fc.data_path for fc in bpy.context.object.animation_data.action.fcurves)

print('ROTATION_ONLY_PASS: all three modes, multiple objects, offset cursor pivot, nonunit scales, pose bone, zero translation writes and rotation-only auto-key')


calls=[]
sr.SR_GT_ball.draw(SimpleNamespace(shape='sphere',draw_custom_shape=lambda shape:calls.append(shape)),None)
assert calls==['sphere']
import colorsys
for color in (*sr.AXIS_COLORS,sr.OUTER_COLOR):
    original=colorsys.rgb_to_hsv(*color)
    for depth in (0,.5,1):
        actual=colorsys.rgb_to_hsv(*sr.shade_color(color,depth))
        assert abs(actual[0]-original[0])<1e-6 and abs(actual[2]-original[2])<1e-6
        assert actual[1]>0
sr.unregister()
print('PUBLIC_ROTATE_SMOKE_PASS: draw callback, saturation, modal rotation and channel preservation')
