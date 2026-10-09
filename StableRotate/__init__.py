# SPDX-License-Identifier: GPL-3.0-or-later
bl_info = {'name': 'Stable Axis Rotate', 'author': 'Codex', 'version': (1, 9, 1),
           'blender': (4, 4, 0), 'location': '3D View > Sidebar > Maya > Stable Rotate',
           'description': 'Continuous rotation rings with stable edge-on dragging in orthographic views',
           'category': '3D View'}
import bpy
from .i18n import tr, ui, draw_language, register_language, unregister_language
import math
import colorsys
from mathutils import Matrix, Vector, Quaternion
from bpy.props import EnumProperty, FloatProperty, IntProperty
from bpy_extras.view3d_utils import location_3d_to_region_2d

AXIS_COLORS=((1,.43,.40),(.40,1,.48),(.43,.61,1))
OUTER_COLOR=(1,.94,.62)


def shade_color(color, depth):
    # Keep hue and brightness fixed; only adjust color saturation.
    hue, saturation, value = colorsys.rgb_to_hsv(*color)
    depth = max(0.0, min(1.0, depth))
    if depth <= .5:
        saturation *= .35 + 1.3 * depth
    else:
        saturation += (1.0 - saturation) * (depth - .5) * 2
    return colorsys.hsv_to_rgb(hue, saturation, value)


def redraw_style(scene,context):
    if context and context.window_manager:
        for window in context.window_manager.windows:
            for area in window.screen.areas:
                if area.type=='VIEW_3D':area.tag_redraw()


def apply_gizmo_style(group,scene):
    opacity=scene.sr_opacity
    for gizmo,base in zip([*group.rings,group.outer],[*AXIS_COLORS,OUTER_COLOR]):
        gizmo.color=gizmo.color_highlight=shade_color(base,scene.sr_color_depth)
        gizmo.alpha=opacity
        gizmo.alpha_highlight=min(1,opacity*1.18)
        gizmo.line_width=scene.sr_line_width
    group.ball.alpha=.025*opacity/.85
    group.ball.alpha_highlight=.1*opacity/.85


def basis(context):
    active = context.active_object
    orientation = context.scene.transform_orientation_slots[0].type
    custom = context.scene.transform_orientation_slots[0].custom_orientation
    if custom:
        return custom.matrix.copy()
    if orientation == 'LOCAL' and active:
        bone = context.active_pose_bone
        matrix = active.matrix_world @ bone.matrix if bone else active.matrix_world
        return matrix.to_quaternion().to_matrix()
    if orientation == 'VIEW' and context.region_data:
        return context.region_data.view_rotation.to_matrix()
    return Matrix.Identity(3)


def targets(context):
    if context.mode == 'POSE' and context.active_object:
        rig = context.active_object
        return [(bone, rig.matrix_world @ bone.matrix) for bone in context.selected_pose_bones or []]
    return [(obj, obj.matrix_world.copy()) for obj in context.selected_editable_objects]


def pivot(context, items):
    mode = context.scene.tool_settings.transform_pivot_point
    if mode == 'CURSOR':
        return context.scene.cursor.location.copy()
    if mode == 'ACTIVE_ELEMENT':
        bone = context.active_pose_bone
        if bone:
            return (context.active_object.matrix_world @ bone.matrix).translation.copy()
        if context.active_object:
            return context.active_object.matrix_world.translation.copy()
    positions = [matrix.translation for _, matrix in items]
    if mode == 'BOUNDING_BOX_CENTER':
        return Vector([(min(p[i] for p in positions) + max(p[i] for p in positions)) / 2 for i in range(3)])
    return sum(positions, Vector()) / len(positions)


def rotate_matrix(original, axis, angle, center):
    return Matrix.Translation(center) @ Matrix.Rotation(angle, 4, axis) @ Matrix.Translation(-center) @ original


def remember_channels(operator):
    operator.channel_state = {item.as_pointer(): (item.location.copy(), item.scale.copy())
                              for item, _ in operator.items}


def stable_angle_step(previous, current, center, dead_zone=12):
    a, b = Vector(previous) - Vector(center), Vector(current) - Vector(center)
    if a.length < dead_zone or b.length < dead_zone:
        return 0.0
    step = math.atan2(a.x*b.y-a.y*b.x, a.dot(b))
    # A sample crossing the center must never inject an opposite-side pi jump.
    return step if abs(step) < math.pi / 2 else 0.0


class SR_OT_rotate(bpy.types.Operator):
    bl_idname = 'sr.rotate'
    bl_label = 'Stable Axis Rotation'
    bl_description = 'Drag an axis ring continuously; Shift gives precision, Esc cancels'
    bl_options = {'REGISTER', 'UNDO', 'BLOCKING'}
    axis: EnumProperty(items=[('X', 'X', ''), ('Y', 'Y', ''), ('Z', 'Z', '')])

    @classmethod
    def poll(cls, context):
        return context.area and context.area.type == 'VIEW_3D' and context.mode in {'OBJECT', 'POSE'}

    def invoke(self, context, event):
        self.items = targets(context)
        if not self.items:
            return {'CANCELLED'}
        # Parents must be assigned before children when both are selected.
        def depth(item):
            parent, result = item[0].parent, 0
            while parent:
                result += 1
                parent = parent.parent
            return result
        self.items.sort(key=depth)
        remember_channels(self)
        self.rig = context.active_object if context.mode == 'POSE' else None
        self.center = pivot(context, self.items)
        self.axis_world = basis(context).col['XYZ'.index(self.axis)].normalized()
        view = context.region_data.view_rotation
        normal = view @ Vector((0, 0, 1))
        self.linear = abs(self.axis_world.dot(normal)) < .35
        projection = Vector((self.axis_world.dot(view @ Vector((1, 0, 0))),
                             self.axis_world.dot(view @ Vector((0, 1, 0)))))
        self.direction = Vector((projection.y, -projection.x))
        if self.direction.length < .01:
            self.direction = Vector((1, 0))
        self.direction.normalize()
        self.sign = 1 if self.axis_world.dot(normal) >= 0 else -1
        self.screen_center = location_3d_to_region_2d(context.region, context.region_data, self.center)
        if self.screen_center is None:
            return {'CANCELLED'}
        self.previous = Vector((event.mouse_region_x, event.mouse_region_y))
        self.angle = 0
        self.individual = context.scene.tool_settings.transform_pivot_point == 'INDIVIDUAL_ORIGINS'
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def assign(self, item, matrix):
        # Rotation only: never orbit objects or write translation/scale channels,
        # regardless of the scene's cursor/median pivot setting.
        matrix = matrix.copy()
        original = next(original for target, original in self.items if target == item)
        matrix.translation = original.translation
        if self.rig:
            item.matrix = self.rig.matrix_world.inverted_safe() @ matrix
        else:
            item.matrix_world = matrix
        location, scale = self.channel_state[item.as_pointer()]
        item.location = location
        item.scale = scale

    def modal(self, context, event):
        if event.type in {'ESC', 'RIGHTMOUSE'}:
            for item, original in self.items:
                self.assign(item, original)
            context.view_layer.update()
            context.area.header_text_set(None)
            return {'CANCELLED'}
        if (event.type == 'LEFTMOUSE' and event.value == 'RELEASE') or event.type in {'RET', 'NUMPAD_ENTER'}:
            if context.scene.tool_settings.use_keyframe_insert_auto:
                for item, _ in self.items:
                    path = ('rotation_quaternion' if item.rotation_mode == 'QUATERNION' else
                            'rotation_axis_angle' if item.rotation_mode == 'AXIS_ANGLE' else 'rotation_euler')
                    item.keyframe_insert(data_path=path, frame=context.scene.frame_current)
            context.area.header_text_set(None)
            return {'FINISHED'}
        if event.type == 'MOUSEMOVE':
            current = Vector((event.mouse_region_x, event.mouse_region_y))
            if self.linear:
                step = (current - self.previous).dot(self.direction) * .01
            else:
                step = stable_angle_step(self.previous, current, self.screen_center) * self.sign
            self.angle += step * (.1 if event.shift else 1)
            self.previous = current
            for item, original in self.items:
                center = original.translation
                self.assign(item, rotate_matrix(original, self.axis_world, self.angle, center))
            context.view_layer.update()
            context.area.header_text_set(tr('Stable Rotate %s: %.2f° · Shift: precision · Esc: cancel') %
                                         (self.axis, math.degrees(self.angle)))
            context.area.tag_redraw()
        return {'RUNNING_MODAL'}


def trackball_vector(mouse, center, radius):
    xy = (Vector(mouse) - Vector(center)) / radius
    distance = xy.length
    z = math.sqrt(1 - distance * distance) if distance < math.sqrt(.5) else .5 / max(distance, .001)
    return Vector((xy.x, xy.y, z)).normalized()


class SR_OT_free_rotate(bpy.types.Operator):
    bl_idname = 'sr.free_rotate'
    bl_label = 'Free Sphere Rotation'
    bl_options = {'REGISTER', 'UNDO', 'BLOCKING'}
    poll = classmethod(lambda cls, context: SR_OT_rotate.poll(context))

    def assign(self, item, matrix):
        SR_OT_rotate.assign(self, item, matrix)

    def invoke(self, context, event):
        self.items = targets(context)
        if not self.items:
            return {'CANCELLED'}
        def depth(item):
            parent, result = item[0].parent, 0
            while parent:
                result += 1
                parent = parent.parent
            return result
        self.items.sort(key=depth)
        remember_channels(self)
        self.rig = context.active_object if context.mode == 'POSE' else None
        self.center = pivot(context, self.items)
        self.screen_center = location_3d_to_region_2d(context.region, context.region_data, self.center)
        if self.screen_center is None:
            return {'CANCELLED'}
        self.radius = max(12, context.preferences.view.gizmo_size * .9 * context.scene.sr_gizmo_scale)
        self.view = context.region_data.view_rotation.copy()
        self.previous = trackball_vector((event.mouse_region_x, event.mouse_region_y), self.screen_center, self.radius)
        self.rotation = Quaternion()
        self.individual = context.scene.tool_settings.transform_pivot_point == 'INDIVIDUAL_ORIGINS'
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if event.type != 'MOUSEMOVE':
            return SR_OT_rotate.modal(self, context, event)
        current = trackball_vector((event.mouse_region_x, event.mouse_region_y), self.screen_center, self.radius)
        delta = self.previous.rotation_difference(current)
        if event.shift:
            axis, angle = delta.to_axis_angle()
            delta = Quaternion(axis, angle * .1)
        self.rotation = (self.view @ delta @ self.view.inverted()) @ self.rotation
        self.rotation.normalize()
        self.previous = current
        for item, original in self.items:
            center = original.translation
            matrix = Matrix.Translation(center) @ self.rotation.to_matrix().to_4x4() @ Matrix.Translation(-center) @ original
            self.assign(item, matrix)
        context.view_layer.update()
        context.area.header_text_set(tr('Free Rotate · Shift: precision · Esc: cancel'))
        context.area.tag_redraw()
        return {'RUNNING_MODAL'}


class SR_OT_view_rotate(bpy.types.Operator):
    bl_idname = 'sr.view_rotate'
    bl_label = 'View Ring Rotation'
    bl_options = {'REGISTER', 'UNDO', 'BLOCKING'}
    axis: EnumProperty(items=[('Z', 'View', '')], default='Z')
    poll = classmethod(lambda cls, context: SR_OT_rotate.poll(context))

    def assign(self, item, matrix):
        SR_OT_rotate.assign(self, item, matrix)

    def invoke(self, context, event):
        result = SR_OT_rotate.invoke(self, context, event)
        if result == {'RUNNING_MODAL'}:
            self.axis_world = context.region_data.view_rotation @ Vector((0, 0, 1))
            self.linear = False
            self.sign = 1
        return result

    def modal(self, context, event):
        return SR_OT_rotate.modal(self, context, event)


class SR_GT_ball(bpy.types.Gizmo):
    bl_idname = 'SR_GT_ball'

    def setup(self):
        vertices = []
        for i in range(64):
            a, b = i * math.tau / 64, (i + 1) * math.tau / 64
            vertices.extend(((0, 0, 0), (math.cos(a), math.sin(a), 0), (math.cos(b), math.sin(b), 0)))
        self.shape = self.new_custom_shape('TRIS', vertices)

    def draw(self, context):
        self.draw_custom_shape(self.shape)

    def draw_select(self, context, select_id):
        self.draw_custom_shape(self.shape, select_id=select_id)


class SR_GGT_rings(bpy.types.GizmoGroup):
    bl_idname = 'SR_GGT_rings'
    bl_label = 'Stable Rotation Rings'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'3D', 'PERSISTENT', 'SHOW_MODAL_ALL'}

    @classmethod
    def poll(cls, context):
        if context.mode not in {'OBJECT', 'POSE'}:
            return False
        tool = context.workspace.tools.from_space_view3d_mode(context.mode, create=False)
        return tool and tool.idname in {'sr.stable_object', 'sr.stable_pose'} and bool(targets(context))

    def setup(self, context):
        self.ball = self.gizmos.new('SR_GT_ball')
        self.ball.color = (1, 1, 1)
        self.ball.alpha = .025
        self.ball.color_highlight = (1, 1, 1)
        self.ball.alpha_highlight = .1
        self.ball.scale_basis = .92
        self.ball.use_select_background = True
        self.ball.target_set_operator('sr.free_rotate')
        self.rings = []
        for axis, color in zip('XYZ', AXIS_COLORS):
            ring = self.gizmos.new('GIZMO_GT_dial_3d')
            ring.draw_options = {'ANGLE_START_Y'}
            ring.color = color
            ring.alpha = .85
            ring.color_highlight = color
            ring.alpha_highlight = 1
            ring.line_width = 1.2
            ring.scale_basis = 1.0
            ring.use_draw_modal = True
            ring.target_set_operator('sr.rotate').axis = axis
            self.rings.append(ring)
        self.outer = self.gizmos.new('GIZMO_GT_dial_3d')
        self.outer.draw_options = {'ANGLE_START_Y'}
        self.outer.color = self.outer.color_highlight = OUTER_COLOR
        self.outer.alpha = .85
        self.outer.alpha_highlight = 1
        self.outer.line_width = 1.2
        self.outer.scale_basis = 1.2
        self.outer.use_draw_modal = True
        self.outer.target_set_operator('sr.view_rotate')

    def draw_prepare(self, context):
        apply_gizmo_style(self,context.scene)
        if any(ring.is_modal for ring in [*self.rings, self.ball, self.outer]):
            return
        items = targets(context)
        if not items:
            return
        center = pivot(context, items)
        orientation = basis(context)
        size=context.scene.sr_gizmo_scale
        self.ball.scale_basis=.92*size
        self.outer.scale_basis=1.2*size
        view_matrix = context.region_data.view_rotation.to_matrix().to_4x4()
        view_matrix.translation = center
        self.ball.matrix_basis = view_matrix
        self.outer.matrix_basis = view_matrix
        for i, ring in enumerate(self.rings):
            ring.scale_basis=size
            axis = orientation.col[i]
            matrix = axis.to_track_quat('Z', 'Y').to_matrix().to_4x4()
            matrix.translation = center
            ring.matrix_basis = matrix


class SR_WT_object(bpy.types.WorkSpaceTool):
    bl_idname = 'sr.stable_object'
    bl_label = 'Maya Rotate 1.9'
    bl_description = 'Rotation rings with continuous edge-on dragging'
    bl_space_type = 'VIEW_3D'
    bl_context_mode = 'OBJECT'
    bl_icon = 'ops.transform.rotate'
    bl_widget = 'SR_GGT_rings'
    bl_keymap = ()


class SR_WT_pose(bpy.types.WorkSpaceTool):
    bl_idname = 'sr.stable_pose'
    bl_label = 'Maya Rotate 1.9'
    bl_description = 'Stable rotation rings for pose bones'
    bl_space_type = 'VIEW_3D'
    bl_context_mode = 'POSE'
    bl_icon = 'ops.transform.rotate'
    bl_widget = 'SR_GGT_rings'
    bl_keymap = ()


class SR_OT_activate(bpy.types.Operator):
    bl_idname = 'sr.activate'
    bl_label = 'Use Maya Rotate 1.9'
    def execute(self, context):
        name = 'sr.stable_pose' if context.mode == 'POSE' else 'sr.stable_object'
        bpy.ops.wm.tool_set_by_id(name=name)
        context.space_data.show_gizmo = True
        context.space_data.show_gizmo_tool = True
        return {'FINISHED'}


class SR_OT_resize_gizmo(bpy.types.Operator):
    bl_idname='sr.resize_gizmo'
    bl_label='Resize Rotation Sphere'
    direction: IntProperty(default=1)

    @classmethod
    def poll(cls,context):
        if not context.area or context.area.type!='VIEW_3D' or context.mode not in {'OBJECT','POSE'}:
            return False
        tool=context.workspace.tools.from_space_view3d_mode(context.mode,create=False)
        return tool and tool.idname in {'sr.stable_object','sr.stable_pose'}

    def execute(self,context):
        context.scene.sr_gizmo_scale=max(.25,min(4,context.scene.sr_gizmo_scale*(1.15 if self.direction>0 else 1/1.15)))
        context.area.tag_redraw()
        return {'FINISHED'}


class SR_OT_reset_style(bpy.types.Operator):
    bl_idname='sr.reset_style'
    bl_label='Reset Appearance'
    def execute(self,context):
        context.scene.sr_opacity=.85
        context.scene.sr_color_depth=.5
        context.scene.sr_line_width=1.2
        return {'FINISHED'}


class SR_PT_tools(bpy.types.Panel):
    bl_label = 'Stable Rotate'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Maya'
    @classmethod
    def poll(cls, context):
        return context.mode in {'OBJECT', 'POSE'}
    def draw(self, context):
        draw_language(self.layout, context)
        ui(self.layout).label(text='Version 1.9 · ROTATION ONLY')
        ui(self.layout).operator('sr.activate', icon='ORIENTATION_GIMBAL')
        ui(self.layout).prop(context.scene,'sr_gizmo_scale',text='Sphere Size')
        box=ui(self.layout).box()
        box.label(text='Appearance')
        box.prop(context.scene,'sr_opacity',text='Opacity',slider=True)
        box.prop(context.scene,'sr_color_depth',text='Color Saturation',slider=True)
        box.prop(context.scene,'sr_line_width',text='Line Width')
        box.operator('sr.reset_style')
        ui(self.layout).label(text='+ / -: resize sphere')
        ui(self.layout).label(text='Edge-on rings: continuous dragging')
        ui(self.layout).label(text='Inside sphere: free 3D rotation')
        ui(self.layout).label(text='Yellow ring: rotate around view')
        ui(self.layout).label(text='Shift: precision · Esc: cancel')
        ui(self.layout).label(text='Global / Local / View orientation')


_classes = (SR_OT_rotate, SR_OT_free_rotate, SR_OT_view_rotate, SR_GT_ball, SR_GGT_rings, SR_OT_activate, SR_OT_resize_gizmo, SR_OT_reset_style, SR_PT_tools)
_keymaps=[]
def register():
    register_language(_classes)
    bpy.types.Scene.sr_gizmo_scale=FloatProperty(name='Sphere Size',default=1,min=.25,max=4)
    bpy.types.Scene.sr_opacity=FloatProperty(name='Opacity',default=.85,min=0,max=1,update=redraw_style)
    bpy.types.Scene.sr_color_depth=FloatProperty(name='Color Saturation',default=.5,min=0,max=1,update=redraw_style,
        description='Adjusts vividness while preserving hue and brightness; never turns rings white or black')
    bpy.types.Scene.sr_line_width=FloatProperty(name='Line Width',default=1.2,min=.5,max=6,update=redraw_style)
    for cls in _classes:
        bpy.utils.register_class(cls)
    for cls in (SR_WT_object, SR_WT_pose):
        bpy.utils.register_tool(cls, after={'builtin.rotate'}, separator=True, group=False)
    kc=bpy.context.window_manager.keyconfigs.addon
    if kc:
        km=kc.keymaps.new(name='3D View',space_type='VIEW_3D',region_type='WINDOW')
        for key,shift,direction in (('EQUAL',False,1),('EQUAL',True,1),('MINUS',False,-1),
                                    ('NUMPAD_PLUS',False,1),('NUMPAD_MINUS',False,-1)):
            kmi=km.keymap_items.new('sr.resize_gizmo',key,'PRESS',shift=shift,head=True)
            kmi.properties.direction=direction
            _keymaps.append((km,kmi))

def unregister():
    unregister_language()
    for km,kmi in _keymaps:km.keymap_items.remove(kmi)
    _keymaps.clear()
    for cls in (SR_WT_pose, SR_WT_object):
        bpy.utils.unregister_tool(cls)
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.sr_gizmo_scale
    del bpy.types.Scene.sr_opacity
    del bpy.types.Scene.sr_color_depth
    del bpy.types.Scene.sr_line_width

