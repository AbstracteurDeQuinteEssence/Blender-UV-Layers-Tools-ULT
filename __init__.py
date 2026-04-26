#ULT

import array
import time
import bpy
from bpy.types import Operator, Panel, PropertyGroup, UIList, Menu
from bpy.props import IntProperty, StringProperty, EnumProperty, BoolProperty, PointerProperty, CollectionProperty

BUILTIN_UV_PRESETS = {
    "GraffPreset": ["UV_Tile", "UV_Nac", "UV_ColorAtlas"],
    "GameDevPreset": ["UV_Main", "UV_Lightmap", "UV_Decals"],
    "IndexPreset": ["UV0", "UV1", "UV2", "UV3", "UV4", "UV5", "UV6", "UV7"],
    "   ": [
        "╭(ㆆ _ ㆆ)╮[ BO$$ ]",
        "Z z z ( - ‿ - )   _]",
        "(⌐■_■) _]  _____  [_ (・‿・)",
        "( =  _  = ) [ TASK ] [ TASK ]",
        "!DEADLINE!  L(° O °L)",
        "[_ (☉ ‿ ⚆)~~~~  ( •͡˘ _ •͡˘) _]",
        "(  ･ _･)   ——|   \\_/    (=^･ｪ･^=)",
        "(  ͡°  ͜ʖ ͡°) c[_]  [ GUARD ]  (U ^ｪ^ U)"
    ]
}

EMOTICONS = {
    8: "∞",
    13: "(=👁  ｪ  👁=)",
    27: "( ✖ ╭╮ ✖ )",
    33: "╰(  † - †  )╯",
    42: "(  -  ‿ ･ิ )",
    69: "(   o   ͜ʖ o )",
    228: "|  |(-_-)|  |",
    300: "(   '   o ' )  c==3",
    322: "$  «Solo»  $",
    404: "[ Not Found ]",
    665: "(   ◣    ﹏ ◢)",
    777: "(  $   ‿‿ $)",
    1487: "(  ಠ   _  ಠ)",
    1984: "(  ◎   _  ◎)",
    2077: "[ B  U  G ]",
    80085: "( . Y . )",
}

class UVLayersSettings(PropertyGroup):
    auto_sync_render: BoolProperty(
        name="Sync Render with Active UV",
        description="When enabled, the active UV layer is automatically used as the render UV layer for any mesh objects you select",
        default=False
    )
    info_display: BoolProperty(
        name="Info Display",
        description="When enabled, the following information about selected objects is displayed: mesh/non‑mesh counts, meshes without UV layers, meshes with zero UV area, mismatches in UV layer counts/names. And for special numbers in the mesh/non‑mesh counters, crazy emoticons will appear (・｀ω´・) – try to find them all!",
        default=False
    )
    stats_meshes_count: IntProperty(default=0)
    stats_non_meshes_count: IntProperty(default=0)
    stats_meshes_without_uv: IntProperty(default=0)
    stats_meshes_zero_uv: IntProperty(default=0)
    stats_uv_counts_mismatch: BoolProperty(default=False)
    stats_uv_names_mismatch: BoolProperty(default=False)

    def get_preset_items(self, context):
        items = [
            ('GraffPreset', 'GraffPreset', 'Built-in preset: GraffPreset'),
            ('GameDevPreset', 'GameDevPreset', 'Built-in preset: GameDevPreset'),
            ('IndexPreset', 'IndexPreset', 'Built-in preset: IndexPreset'),
            ('   ', '   ', 'Built-in preset: HiddenPreset')
        ]
        for preset in context.scene.uv_presets:
            items.append((preset.name, preset.name, f"Custom preset: {preset.name}"))
        return items

    selected_preset: EnumProperty(
        name="Preset",
        description="Choose UV name preset to apply",
        items=get_preset_items
    )

class UvNameItem(PropertyGroup):
    name: StringProperty(name="UV Name", default="")

class UvPresetItem(PropertyGroup):
    name: StringProperty(name="Preset Name", default="New Preset")
    uv_names: CollectionProperty(type=UvNameItem)

class MESH_UL_ult_uv_list(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        uv_layer = item
        settings = context.scene.uv_layers_tools
        row = layout.row(align=True)
        row.alignment = 'EXPAND'
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row.prop(uv_layer, "name", text="", emboss=False, icon_value=icon)
            if settings.auto_sync_render:
                if uv_layer.active_render:
                    row.label(text="", icon='RESTRICT_RENDER_OFF')
                else:
                    row.label(text="", icon='RESTRICT_RENDER_ON')
            else:
                if uv_layer.active_render:
                    row.prop(uv_layer, "active_render", text="", icon='RESTRICT_RENDER_OFF', emboss=False)
                else:
                    row.prop(uv_layer, "active_render", text="", icon='RESTRICT_RENDER_ON', emboss=False)
        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.label(text="", icon_value=icon)

class UV_OT_Base:
    @classmethod
    def poll(cls, context):
        if not context.selected_objects:
            return False
        meshes_with_uv = 0
        for obj in context.selected_objects:
            if obj.type == 'MESH' and obj.data.uv_layers:
                meshes_with_uv += 1
        return meshes_with_uv > 0

    def update_ui(self, context):
        for obj in context.selected_objects:
            if obj.type == 'MESH':
                obj.data.update_tag()
                obj.update_tag()
        for window in context.window_manager.windows:
            for area in window.screen.areas:
                if area.type in ['VIEW_3D', 'PROPERTIES', 'IMAGE_EDITOR', 'OUTLINER']:
                    area.tag_redraw()
        if context.scene:
            context.scene.update_tag()

def has_zero_uv_area(obj):
    if obj.type != 'MESH':
        return False
    uv_layers = obj.data.uv_layers
    if not uv_layers:
        return False
    epsilon = 1e-6
    for uv_layer in uv_layers:
        uv_data = uv_layer.data
        if not uv_data:
            continue
        u_min = v_min = float('inf')
        u_max = v_max = -float('inf')
        for loop in obj.data.loops:
            uv = uv_data[loop.index].uv
            u_min = min(u_min, uv[0])
            u_max = max(u_max, uv[0])
            v_min = min(v_min, uv[1])
            v_max = max(v_max, uv[1])
        if (u_max - u_min) < epsilon and (v_max - v_min) < epsilon:
            return True
    return False

def has_any_zero_island(obj):
    if obj.type != 'MESH':
        return False
    uv_layers = obj.data.uv_layers
    if not uv_layers:
        return False
    epsilon = 1e-6
    for uv_layer in uv_layers:
        uv_data = uv_layer.data
        if not uv_data:
            continue
        for poly in obj.data.polygons:
            u_min = v_min = float('inf')
            u_max = v_max = -float('inf')
            for loop_index in poly.loop_indices:
                uv = uv_data[loop_index].uv
                u_min = min(u_min, uv[0])
                u_max = max(u_max, uv[0])
                v_min = min(v_min, uv[1])
                v_max = max(v_max, uv[1])
            if (u_max - u_min) < epsilon and (v_max - v_min) < epsilon:
                return True
    return False

def update_uv_stats(scene, depsgraph=None):
    context = bpy.context
    settings = scene.uv_layers_tools
    selected = context.selected_objects
    meshes = [obj for obj in selected if obj.type == 'MESH']
    non_meshes = [obj for obj in selected if obj.type != 'MESH']
    settings.stats_meshes_count = len(meshes)
    settings.stats_non_meshes_count = len(non_meshes)
    if not settings.info_display:
        return
    meshes_without_uv = 0
    meshes_zero_uv = 0
    for obj in meshes:
        uv_count = len(obj.data.uv_layers)
        if uv_count == 0:
            meshes_without_uv += 1
        elif has_zero_uv_area(obj):
            meshes_zero_uv += 1
    settings.stats_meshes_without_uv = meshes_without_uv
    settings.stats_meshes_zero_uv = meshes_zero_uv
    if meshes:
        uv_counts = {len(obj.data.uv_layers) for obj in meshes}
        settings.stats_uv_counts_mismatch = len(uv_counts) > 1
        max_layers = max(uv_counts) if uv_counts else 0
        name_mismatch = False
        for i in range(max_layers):
            names = set()
            for obj in meshes:
                if i < len(obj.data.uv_layers):
                    names.add(obj.data.uv_layers[i].name)
            if len(names) > 1:
                name_mismatch = True
                break
        settings.stats_uv_names_mismatch = name_mismatch
    else:
        settings.stats_uv_counts_mismatch = False
        settings.stats_uv_names_mismatch = False

@bpy.app.handlers.persistent
def update_auto_render_and_stats(dummy):
    scene = bpy.context.scene
    if not scene or not hasattr(scene, 'uv_layers_tools'):
        return
    settings = scene.uv_layers_tools
    if settings.info_display:
        update_uv_stats(scene)
    if not settings.auto_sync_render:
        return
    selected_objects = list(bpy.context.selected_objects)
    active_object = bpy.context.active_object
    objects_to_process = selected_objects
    if (active_object and active_object.type == 'MESH' and active_object not in selected_objects):
        objects_to_process.append(active_object)
    for obj in objects_to_process:
        if obj.type == 'MESH':
            uv_layers = obj.data.uv_layers
            if uv_layers:
                active_idx = uv_layers.active_index
                if active_idx >= 0 and not uv_layers[active_idx].active_render:
                    for uv in uv_layers:
                        uv.active_render = False
                    uv_layers[active_idx].active_render = True
                    obj.data.update_tag()

class MESH_OT_ult_select_without_uv(Operator):
    bl_idname = "mesh.ult_select_without_uv"
    bl_label = "Meshes without UV"
    bl_description = "Select all mesh objects that have no UV layers"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bpy.ops.object.select_all(action='DESELECT')
        selected = 0
        for obj in bpy.data.objects:
            if obj.type == 'MESH' and not obj.hide_get():
                if len(obj.data.uv_layers) == 0:
                    obj.select_set(True)
                    selected += 1
        if selected > 0:
            for obj in bpy.data.objects:
                if obj.type == 'MESH' and obj.select_get():
                    context.view_layer.objects.active = obj
                    break
        self.report({'INFO'}, f"Selected {selected} meshes without UV")
        return {'FINISHED'}

class MESH_OT_ult_select_zero_uv_area(Operator):
    bl_idname = "mesh.ult_select_zero_uv_area"
    bl_label = "Meshes with Zero UV Area"
    bl_description = "Select mesh objects based on collapsed UV islands"
    bl_options = {'REGISTER', 'UNDO'}

    selection_mode: EnumProperty(
        items=[
            ('ALL_ISLANDS', 'All Islands', 'Select meshes where at least one UV layer has all UV islands collapsed to zero area'),
            ('ANY_ISLAND', 'Any Island', 'Select meshes where any UV island is collapsed to zero area in any UV layer')
        ],
        name="Mode",
        default='ALL_ISLANDS'
    )

    def execute(self, context):
        bpy.ops.object.select_all(action='DESELECT')
        selected = 0
        check_func = has_zero_uv_area if self.selection_mode == 'ALL_ISLANDS' else has_any_zero_island
        for obj in bpy.data.objects:
            if obj.type == 'MESH' and not obj.hide_get():
                if check_func(obj):
                    obj.select_set(True)
                    selected += 1
        if selected > 0:
            for obj in bpy.data.objects:
                if obj.type == 'MESH' and obj.select_get():
                    context.view_layer.objects.active = obj
                    break
        self.report({'INFO'}, f"Selected {selected} meshes")
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=300)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "selection_mode", text="Mode")
        if self.selection_mode == 'ANY_ISLAND':
            box = layout.box()
            box.label(text="This mode checks each polygon individually", icon='ERROR')
            box.label(text="across all UV layers of visible meshes", icon='BLANK1')
            box.label(text="and may be noticeably slow on meshes", icon='BLANK1')
            box.label(text="with heavy geometry.", icon='BLANK1')

class MESH_OT_ult_add_uv(Operator):
    bl_idname = "mesh.ult_add_uv"
    bl_label = "Add UV"
    bl_description = "Add a new UV layer to all selected mesh objects"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.selected_objects and any(o.type == 'MESH' for o in context.selected_objects)

    def execute(self, context):
        success_count = 0
        maxed_count = 0
        for obj in context.selected_objects:
            if obj.type == 'MESH':
                if len(obj.data.uv_layers) >= 8:
                    maxed_count += 1
                    continue
                obj.data.uv_layers.new()
                success_count += 1
        for obj in context.selected_objects:
            if obj.type == 'MESH':
                obj.data.update_tag()
                obj.update_tag()
        for window in context.window_manager.windows:
            for area in window.screen.areas:
                if area.type in ['VIEW_3D', 'PROPERTIES', 'IMAGE_EDITOR', 'OUTLINER']:
                    area.tag_redraw()
        if context.scene:
            context.scene.update_tag()
        if success_count == 0 and maxed_count > 0:
            if maxed_count == 1:
                self.report({'WARNING'}, "Cannot add more than 8 UV layers")
            else:
                self.report({'WARNING'}, f"Cannot add more than 8 UV layers; {maxed_count} object(s) already have 8 UV layers")
        elif success_count > 0 and maxed_count == 0:
            self.report({'INFO'}, f"Added UV layer to {success_count} object(s)")
        else:
            self.report({'INFO'}, f"Added UV layer to {success_count} object(s), {maxed_count} object(s) already have 8 layers")
        return {'FINISHED'}

class MESH_OT_ult_rename_uv(Operator, UV_OT_Base):
    bl_idname = "mesh.ult_rename_uv"
    bl_label = "Rename UV"
    bl_description = "Rename UV layer by index for all selected mesh objects"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty(name="Index", default=1, min=1)
    new_name: StringProperty(name="New Name", default="")

    def execute(self, context):
        if not self.new_name.strip():
            self.report({'WARNING'}, "UV layer name cannot be empty")
            return {'CANCELLED'}
        idx = self.index - 1
        renamed = 0
        for obj in context.selected_objects:
            if obj.type == 'MESH' and idx < len(obj.data.uv_layers):
                obj.data.uv_layers[idx].name = self.new_name
                renamed += 1
        self.update_ui(context)
        if renamed:
            self.report({'INFO'}, f"Renamed {renamed} UV layer(s)")
        return {'FINISHED'}

    def invoke(self, context, event):
        self.new_name = ""
        return context.window_manager.invoke_props_dialog(self, width=250)

    def draw(self, context):
        layout = self.layout
        layout.label(text="Index:")
        layout.prop(self, "index", text="")
        layout.separator()
        layout.label(text="New Name:")
        layout.prop(self, "new_name", text="")

class MESH_OT_ult_set_active_uv(Operator, UV_OT_Base):
    bl_idname = "mesh.ult_set_active_uv"
    bl_label = "Set Active UV"
    bl_description = "Set active UV layer by index for all selected mesh objects"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty(name="Index", default=1, min=1)

    def execute(self, context):
        idx = self.index - 1
        settings = context.scene.uv_layers_tools
        for obj in context.selected_objects:
            if obj.type == 'MESH' and idx < len(obj.data.uv_layers):
                obj.data.uv_layers.active_index = idx
                if settings.auto_sync_render:
                    for uv in obj.data.uv_layers:
                        uv.active_render = False
                    obj.data.uv_layers[idx].active_render = True
        self.update_ui(context)
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=250)

    def draw(self, context):
        layout = self.layout
        layout.label(text="Index:")
        layout.prop(self, "index", text="")

class MESH_OT_ult_set_render_uv(Operator):
    bl_idname = "mesh.ult_set_render_uv"
    bl_label = "Set Render UV"
    bl_description = "Set render UV layer by index for all selected mesh objects"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty(name="Index", default=1, min=1)

    @classmethod
    def poll(cls, context):
        settings = context.scene.uv_layers_tools
        if settings.auto_sync_render:
            return False
        if not context.selected_objects:
            return False
        meshes_with_uv = 0
        for obj in context.selected_objects:
            if obj.type == 'MESH' and obj.data.uv_layers:
                meshes_with_uv += 1
        return meshes_with_uv > 0

    def execute(self, context):
        idx = self.index - 1
        for obj in context.selected_objects:
            if obj.type == 'MESH' and idx < len(obj.data.uv_layers):
                for uv in obj.data.uv_layers:
                    uv.active_render = False
                obj.data.uv_layers[idx].active_render = True
        for obj in context.selected_objects:
            if obj.type == 'MESH':
                obj.data.update_tag()
                obj.update_tag()
        for window in context.window_manager.windows:
            for area in window.screen.areas:
                if area.type in ['VIEW_3D', 'PROPERTIES', 'IMAGE_EDITOR', 'OUTLINER']:
                    area.tag_redraw()
        if context.scene:
            context.scene.update_tag()
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=250)

    def draw(self, context):
        layout = self.layout
        layout.label(text="Index:")
        layout.prop(self, "index", text="")

class MESH_OT_ult_delete_uv(Operator, UV_OT_Base):
    bl_idname = "mesh.ult_delete_uv"
    bl_label = "Delete UV"
    bl_description = "Delete UV layer by index for all selected mesh objects"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty(name="Index", default=1, min=1)

    def execute(self, context):
        idx = self.index - 1
        deleted = 0
        for obj in context.selected_objects:
            if obj.type == 'MESH' and idx < len(obj.data.uv_layers):
                obj.data.uv_layers.remove(obj.data.uv_layers[idx])
                deleted += 1
        self.update_ui(context)
        if deleted:
            self.report({'INFO'}, f"Deleted {deleted} UV layer(s)")
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=250)

    def draw(self, context):
        layout = self.layout
        layout.label(text="Index:")
        layout.prop(self, "index", text="")

class MESH_OT_ult_delete_uv_advanced(Operator, UV_OT_Base):
    bl_idname = "mesh.ult_delete_uv_advanced"
    bl_label = "Advanced Delete UV(s)"
    bl_description = "Advanced UV layer deletion options for all selected mesh objects"
    bl_options = {'REGISTER', 'UNDO'}

    delete_mode: EnumProperty(
        items=[
            ('BY_LIST', 'By Index List', 'Delete specific UV layers by index numbers (starting from 1, e.g., 1 3 5 or 1, 3, 5) for all selected mesh objects'),
            ('EXCEPT_FIRST', 'All Except First', 'Delete all UV layers except the first one for all selected mesh objects'),
            ('EXCEPT_LAST', 'All Except Last', 'Delete all UV layers except the last one for all selected mesh objects'),
            ('DELETE_FIRST', 'First Only', 'Delete only the first UV layer for all selected mesh objects'),
            ('DELETE_LAST', 'Last Only', 'Delete only the last UV layer for all selected mesh objects'),
            ('ALL', 'All', 'Delete all UV layers for all selected mesh objects'),
        ],
        name="Delete Mode",
        default='BY_LIST'
    )
    index_list: StringProperty(
        name="Index List",
        description="Comma or space separated list of indices (e.g., 2, 4, 5)",
        default=""
    )

    def execute(self, context):
        meshes = [obj for obj in context.selected_objects if obj.type == 'MESH']
        total_deleted = 0
        for obj in meshes:
            uv_layers = obj.data.uv_layers
            if not uv_layers:
                continue
            if self.delete_mode == 'BY_LIST':
                all_layers_data = []
                for layer in uv_layers:
                    data = array.array('f', [0.0] * (len(layer.data) * 2))
                    layer.data.foreach_get("uv", data)
                    all_layers_data.append(data)
                indices = set()
                for item in self.index_list.replace(',', ' ').split():
                    if item.strip().isdigit():
                        idx = int(item.strip()) - 1
                        if 0 <= idx < len(uv_layers):
                            indices.add(idx)
                if not indices:
                    continue
                indices_sorted = sorted(indices, reverse=True)
                for idx in indices_sorted:
                    uv_layers.remove(uv_layers[idx])
                    total_deleted += 1
                for i, layer in enumerate(uv_layers):
                    source_idx = i
                    for removed_idx in sorted(indices):
                        if source_idx >= removed_idx:
                            source_idx += 1
                        else:
                            break
                    if source_idx < len(all_layers_data):
                        layer.data.foreach_set("uv", all_layers_data[source_idx])
            elif self.delete_mode == 'EXCEPT_FIRST':
                if len(uv_layers) > 1:
                    first_layer_data = array.array('f', [0.0] * (len(uv_layers[0].data) * 2))
                    uv_layers[0].data.foreach_get("uv", first_layer_data)
                    while len(uv_layers) > 1:
                        uv_layers.remove(uv_layers[-1])
                        total_deleted += 1
                    uv_layers[0].data.foreach_set("uv", first_layer_data)
            elif self.delete_mode == 'EXCEPT_LAST':
                if len(uv_layers) > 1:
                    last_layer_data = array.array('f', [0.0] * (len(uv_layers[-1].data) * 2))
                    uv_layers[-1].data.foreach_get("uv", last_layer_data)
                    while len(uv_layers) > 1:
                        uv_layers.remove(uv_layers[0])
                        total_deleted += 1
                    uv_layers[0].data.foreach_set("uv", last_layer_data)
            elif self.delete_mode == 'DELETE_FIRST':
                if len(uv_layers) > 0:
                    all_layers_data = []
                    for layer in uv_layers:
                        data = array.array('f', [0.0] * (len(layer.data) * 2))
                        layer.data.foreach_get("uv", data)
                        all_layers_data.append(data)
                    uv_layers.remove(uv_layers[0])
                    total_deleted += 1
                    for i, layer in enumerate(uv_layers):
                        if i + 1 < len(all_layers_data):
                            layer.data.foreach_set("uv", all_layers_data[i + 1])
            elif self.delete_mode == 'DELETE_LAST':
                if len(uv_layers) > 0:
                    all_layers_data = []
                    for layer in uv_layers:
                        data = array.array('f', [0.0] * (len(layer.data) * 2))
                        layer.data.foreach_get("uv", data)
                        all_layers_data.append(data)
                    uv_layers.remove(uv_layers[-1])
                    total_deleted += 1
                    for i, layer in enumerate(uv_layers):
                        if i < len(all_layers_data) - 1:
                            layer.data.foreach_set("uv", all_layers_data[i])
            elif self.delete_mode == 'ALL':
                total_deleted += len(uv_layers)
                while uv_layers:
                    uv_layers.remove(uv_layers[0])
        self.update_ui(context)
        if total_deleted > 0:
            self.report({'INFO'}, f"Deleted {total_deleted} UV layer(s)")
        return {'FINISHED'}

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "delete_mode", text="Mode")
        if self.delete_mode == 'BY_LIST':
            layout.label(text="Enter UV layer index/indices:")
            layout.prop(self, "index_list", text="")

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

class MESH_OT_ult_move_uv_up(Operator, UV_OT_Base):
    bl_idname = "mesh.ult_move_uv_up"
    bl_label = "Move UV Up"
    bl_description = "Move active UV layer up in the list for all selected mesh objects"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if context.mode == 'EDIT_MESH':
            return False
        return UV_OT_Base.poll(context)

    def execute(self, context):
        moved = 0
        skipped = 0
        settings = context.scene.uv_layers_tools
        for obj in context.selected_objects:
            if obj.type == 'MESH':
                uv_layers = obj.data.uv_layers
                active_idx = uv_layers.active_index
                if active_idx > 0:
                    idx1, idx2 = active_idx, active_idx - 1
                    layer1, layer2 = uv_layers[idx1], uv_layers[idx2]
                    name1, name2 = layer1.name, layer2.name
                    temp_name = f"__TEMP_{name2}_{id(obj)}_{int(time.time())}__"
                    layer2.name = temp_name
                    layer1.name = name2
                    layer2.name = name1
                    data1 = array.array('f', [0.0] * (len(layer1.data) * 2))
                    data2 = array.array('f', [0.0] * (len(layer2.data) * 2))
                    layer1.data.foreach_get("uv", data1)
                    layer2.data.foreach_get("uv", data2)
                    layer1.data.foreach_set("uv", data2)
                    layer2.data.foreach_set("uv", data1)
                    uv_layers.active_index = idx2
                    if settings.auto_sync_render:
                        for uv in uv_layers:
                            uv.active_render = False
                        uv_layers[idx2].active_render = True
                    moved += 1
                else:
                    skipped += 1
        self.update_ui(context)
        if moved > 0 and skipped > 0:
            self.report({'INFO'}, f"Moved {moved} UV layer(s) up, {skipped} already at the top")
        elif moved > 0:
            self.report({'INFO'}, f"Moved {moved} UV layer(s) up")
        elif skipped > 0:
            self.report({'INFO'}, f"{skipped} UV layer(s) already at the top")
        return {'FINISHED'}

class MESH_OT_ult_move_uv_down(Operator, UV_OT_Base):
    bl_idname = "mesh.ult_move_uv_down"
    bl_label = "Move UV Down"
    bl_description = "Move active UV layer down in the list for all selected mesh objects"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if context.mode == 'EDIT_MESH':
            return False
        return UV_OT_Base.poll(context)

    def execute(self, context):
        moved = 0
        skipped = 0
        settings = context.scene.uv_layers_tools
        for obj in context.selected_objects:
            if obj.type == 'MESH':
                uv_layers = obj.data.uv_layers
                active_idx = uv_layers.active_index
                if active_idx < len(uv_layers) - 1:
                    idx1, idx2 = active_idx, active_idx + 1
                    layer1, layer2 = uv_layers[idx1], uv_layers[idx2]
                    name1, name2 = layer1.name, layer2.name
                    temp_name = f"__TEMP_{name2}_{id(obj)}_{int(time.time())}__"
                    layer2.name = temp_name
                    layer1.name = name2
                    layer2.name = name1
                    data1 = array.array('f', [0.0] * (len(layer1.data) * 2))
                    data2 = array.array('f', [0.0] * (len(layer2.data) * 2))
                    layer1.data.foreach_get("uv", data1)
                    layer2.data.foreach_get("uv", data2)
                    layer1.data.foreach_set("uv", data2)
                    layer2.data.foreach_set("uv", data1)
                    uv_layers.active_index = idx2
                    if settings.auto_sync_render:
                        for uv in uv_layers:
                            uv.active_render = False
                        uv_layers[idx2].active_render = True
                    moved += 1
                else:
                    skipped += 1
        self.update_ui(context)
        if moved > 0 and skipped > 0:
            self.report({'INFO'}, f"Moved {moved} UV layer(s) down, {skipped} already at the bottom")
        elif moved > 0:
            self.report({'INFO'}, f"Moved {moved} UV layer(s) down")
        elif skipped > 0:
            self.report({'INFO'}, f"{skipped} UV layer(s) already at the bottom")
        return {'FINISHED'}

class MESH_OT_ult_sync_active_uv(Operator):
    bl_idname = "mesh.ult_sync_active_uv"
    bl_label = "Sync Active UV"
    bl_description = "Sync active UV layer index from active object to all selected mesh objects"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if not (context.active_object and context.active_object.type == 'MESH' and context.active_object.data.uv_layers):
            return False
        if len(context.selected_objects) <= 1:
            return False
        meshes_with_uv = 0
        for obj in context.selected_objects:
            if obj.type == 'MESH' and obj.data.uv_layers:
                meshes_with_uv += 1
        return meshes_with_uv > 1

    def execute(self, context):
        active_obj = context.active_object
        active_idx = active_obj.data.uv_layers.active_index
        settings = context.scene.uv_layers_tools
        synced = 0
        for obj in context.selected_objects:
            if obj.type == 'MESH' and obj != active_obj:
                if active_idx < len(obj.data.uv_layers):
                    obj.data.uv_layers.active_index = active_idx
                    if settings.auto_sync_render:
                        for uv in obj.data.uv_layers:
                            uv.active_render = False
                        obj.data.uv_layers[active_idx].active_render = True
                    synced += 1
        self.report({'INFO'}, f"Synced active UV for {synced} objects")
        return {'FINISHED'}

class MESH_OT_ult_sync_render_uv(Operator):
    bl_idname = "mesh.ult_sync_render_uv"
    bl_label = "Sync Render UV"
    bl_description = "Sync render UV layer index from active object to all selected mesh objects"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        settings = context.scene.uv_layers_tools
        if settings.auto_sync_render:
            return False
        if not (context.active_object and context.active_object.type == 'MESH' and context.active_object.data.uv_layers):
            return False
        if len(context.selected_objects) <= 1:
            return False
        meshes_with_uv = 0
        for obj in context.selected_objects:
            if obj.type == 'MESH' and obj.data.uv_layers:
                meshes_with_uv += 1
        return meshes_with_uv > 1

    def execute(self, context):
        active_obj = context.active_object
        render_idx = next((i for i, uv in enumerate(active_obj.data.uv_layers) if uv.active_render), -1)
        if render_idx == -1:
            return {'CANCELLED'}
        synced = 0
        for obj in context.selected_objects:
            if obj.type == 'MESH' and obj != active_obj:
                if render_idx < len(obj.data.uv_layers):
                    for uv in obj.data.uv_layers:
                        uv.active_render = False
                    obj.data.uv_layers[render_idx].active_render = True
                    synced += 1
        self.report({'INFO'}, f"Synced render UV for {synced} objects")
        return {'FINISHED'}

class MESH_OT_ult_apply_preset(Operator, UV_OT_Base):
    bl_idname = "mesh.ult_apply_preset"
    bl_label = "Apply UV Preset"
    bl_description = "Apply UV name preset to all selected mesh objects"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        settings = context.scene.uv_layers_tools
        preset_name = settings.selected_preset
        if not preset_name:
            self.report({'WARNING'}, "Choose UV name preset first")
            return {'CANCELLED'}
        if preset_name in BUILTIN_UV_PRESETS:
            uv_names = BUILTIN_UV_PRESETS[preset_name]
        else:
            uv_names = []
            for preset in context.scene.uv_presets:
                if preset.name == preset_name:
                    uv_names = [name.name for name in preset.uv_names]
                    break
        if not uv_names:
            return {'CANCELLED'}
        renamed_count = 0
        mesh_count = 0
        for obj in context.selected_objects:
            if obj.type == 'MESH':
                mesh_count += 1
                uv_layers = obj.data.uv_layers
                for i, uv_layer in enumerate(uv_layers):
                    if i < len(uv_names):
                        uv_layer.name = uv_names[i]
                        renamed_count += 1
        self.report({'INFO'}, f"Applied '{preset_name}' to {mesh_count} objects, renamed {renamed_count} UV layers")
        return {'FINISHED'}

class OBJECT_OT_ult_manage_presets(Operator):
    bl_idname = "object.ult_manage_presets"
    bl_label = "Manage UV Name Presets"
    bl_description = "Create, edit and delete UV name presets"

    def execute(self, context):
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=300)

    def draw(self, context):
        layout = self.layout
        layout.label(text="Built-in Presets:", icon='LOCKED')
        for preset_name in BUILTIN_UV_PRESETS:
            row = layout.row()
            row.label(text=preset_name, icon='PRESET')
        layout.separator()
        layout.label(text="Custom Presets:", icon='MODIFIER')
        if not context.scene.uv_presets:
            layout.label(text="        No custom presets yet ( ￢  _￢)", icon='NONE')
        else:
            for preset in context.scene.uv_presets:
                row = layout.row()
                row.label(text=preset.name, icon='PRESET')
                edit_op = row.operator("object.ult_edit_preset", text="", icon='GREASEPENCIL')
                edit_op.preset_name = preset.name
                delete_op = row.operator("object.ult_delete_preset", text="", icon='TRASH')
                delete_op.preset_name = preset.name
        layout.separator()
        row = layout.row()
        op = row.operator("object.ult_create_preset", text="New", icon='ADD')
        op.context = 'INVOKE_DEFAULT'
        layout.separator()
        layout.label(text="Note: OK and Cancel buttons both close this dialog", icon='INFO')

def is_ascii(s):
    return all(ord(c) < 128 for c in s)

def make_unique_preset_name(context, base_name):
    builtin_preset_names = set(BUILTIN_UV_PRESETS.keys())
    used_names = {preset.name for preset in context.scene.uv_presets}
    all_used_names = used_names.union(builtin_preset_names)
    if base_name not in all_used_names:
        return base_name
    suffix_num = 1
    while True:
        new_name = f"{base_name}.{suffix_num:03d}"
        if new_name not in all_used_names:
            return new_name
        suffix_num += 1

def make_unique_custom_preset_name(context):
    base_name = "CustomPreset"
    return make_unique_preset_name(context, base_name)

class OBJECT_OT_ult_create_preset(Operator):
    bl_idname = "object.ult_create_preset"
    bl_label = "Create UV Name Preset"
    bl_description = "Create a new UV name preset"
    bl_options = {'REGISTER', 'UNDO'}

    context: StringProperty(default='INVOKE_DEFAULT')
    preset_name: StringProperty(name="Preset Name", default="", description="Name of the UV name preset (empty for default)")
    uv_name_1: StringProperty(name="UV 1", default="")
    uv_name_2: StringProperty(name="UV 2", default="")
    uv_name_3: StringProperty(name="UV 3", default="")
    uv_name_4: StringProperty(name="UV 4", default="")
    uv_name_5: StringProperty(name="UV 5", default="")
    uv_name_6: StringProperty(name="UV 6", default="")
    uv_name_7: StringProperty(name="UV 7", default="")
    uv_name_8: StringProperty(name="UV 8", default="")

    def execute(self, context):
        uv_names = []
        for i in range(1, 9):
            name = getattr(self, f"uv_name_{i}", "")
            if name and name.strip():
                uv_names.append(name.strip())
        if not uv_names:
            self.report({'ERROR'}, "Preset must contain at least one UV name")
            return {'CANCELLED'}
        if not self.preset_name.strip():
            final_preset_name = make_unique_custom_preset_name(context)
        else:
            name_candidate = self.preset_name.strip()
            if not is_ascii(name_candidate):
                clean_name = ''.join(c for c in name_candidate if ord(c) < 128)
                self.preset_name = clean_name
                self.report({'INFO'}, f"Non-English characters removed from preset name, using: '{clean_name}'")
                if clean_name:
                    final_preset_name = make_unique_preset_name(context, clean_name)
                else:
                    final_preset_name = make_unique_custom_preset_name(context)
            else:
                final_preset_name = make_unique_preset_name(context, name_candidate)
        new_preset = context.scene.uv_presets.add()
        new_preset.name = final_preset_name
        for name in uv_names:
            uv_name = new_preset.uv_names.add()
            uv_name.name = name
        for i in range(1, 9):
            setattr(self, f"uv_name_{i}", "")
        self.report({'INFO'}, f"Created preset '{final_preset_name}' with {len(uv_names)} UV name(s)")
        return {'FINISHED'}

    def invoke(self, context, event):
        self.preset_name = ""
        for i in range(1, 9):
            setattr(self, f"uv_name_{i}", "")
        return context.window_manager.invoke_props_dialog(self, width=350)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "preset_name")
        row = layout.row(align=True)
        row.label(text="", icon='INFO')
        row.label(text="Note: Leave empty for default preset name")
        layout.separator()
        box = layout.box()
        for i in range(1, 9):
            row = box.row(align=True)
            split = row.split(factor=0.2, align=True)
            split.label(text=f"UV {i}:")
            split.prop(self, f"uv_name_{i}", text="")
        layout.separator()
        layout.label(text="Note: Only filled fields will be saved to the preset", icon='INFO')

class OBJECT_OT_ult_edit_preset(Operator):
    bl_idname = "object.ult_edit_preset"
    bl_label = "Edit UV Name Preset"
    bl_description = "Edit an existing UV name preset"
    bl_options = {'REGISTER', 'UNDO'}

    context: StringProperty(default='INVOKE_DEFAULT')
    preset_name: StringProperty(name="Preset Name")
    new_preset_name: StringProperty(name="Preset Name", default="", description="Name of the UV name preset")
    uv_name_1: StringProperty(name="UV 1", default="")
    uv_name_2: StringProperty(name="UV 2", default="")
    uv_name_3: StringProperty(name="UV 3", default="")
    uv_name_4: StringProperty(name="UV 4", default="")
    uv_name_5: StringProperty(name="UV 5", default="")
    uv_name_6: StringProperty(name="UV 6", default="")
    uv_name_7: StringProperty(name="UV 7", default="")
    uv_name_8: StringProperty(name="UV 8", default="")

    def execute(self, context):
        target_preset = None
        for preset in context.scene.uv_presets:
            if preset.name == self.preset_name:
                target_preset = preset
                break
        if not target_preset:
            return {'CANCELLED'}
        new_name = self.new_preset_name.strip()
        if not new_name:
            new_name = make_unique_preset_name(context, "CustomPreset")
        else:
            if new_name != self.preset_name:
                if not is_ascii(new_name):
                    clean_name = ''.join(c for c in new_name if ord(c) < 128)
                    self.report({'INFO'}, f"Non-English characters removed from preset name, using: '{clean_name}'")
                    new_name = clean_name if clean_name else make_unique_preset_name(context, "CustomPreset")
                new_name = make_unique_preset_name(context, new_name)
        uv_names = []
        for i in range(1, 9):
            name = getattr(self, f"uv_name_{i}", "")
            if name and name.strip():
                uv_names.append(name.strip())
        if not uv_names:
            self.report({'ERROR'}, "Preset must contain at least one UV name")
            return {'CANCELLED'}
        target_preset.name = new_name
        while len(target_preset.uv_names) > 0:
            target_preset.uv_names.remove(0)
        for name in uv_names:
            uv_name = target_preset.uv_names.add()
            uv_name.name = name
        if context.scene.uv_layers_tools.selected_preset == self.preset_name:
            context.scene.uv_layers_tools.selected_preset = new_name
        self.report({'INFO'}, f"Updated preset '{new_name}' with {len(uv_names)} UV name(s)")
        return {'FINISHED'}

    def invoke(self, context, event):
        for preset in context.scene.uv_presets:
            if preset.name == self.preset_name:
                self.new_preset_name = preset.name
                uv_names = [name.name for name in preset.uv_names]
                for i in range(1, 9):
                    if i <= len(uv_names):
                        setattr(self, f"uv_name_{i}", uv_names[i-1])
                    else:
                        setattr(self, f"uv_name_{i}", "")
                break
        return context.window_manager.invoke_props_dialog(self, width=350)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "new_preset_name")
        row = layout.row(align=True)
        row.label(text="", icon='INFO')
        row.label(text="Note: Leave empty for default preset name")
        layout.separator()
        box = layout.box()
        for i in range(1, 9):
            row = box.row(align=True)
            split = row.split(factor=0.2, align=True)
            split.label(text=f"UV {i}:")
            split.prop(self, f"uv_name_{i}", text="")
        layout.separator()
        layout.label(text="Note: Only filled fields will be saved to the preset", icon='INFO')

class OBJECT_OT_ult_delete_preset(Operator):
    bl_idname = "object.ult_delete_preset"
    bl_label = "Delete Preset"
    bl_description = "Deletes a custom UV name preset"
    bl_options = {'REGISTER', 'UNDO'}

    preset_name: StringProperty(name="Preset Name")

    @classmethod
    def poll(cls, context):
        return len(context.scene.uv_presets) > 0

    def execute(self, context):
        for i, preset in enumerate(context.scene.uv_presets):
            if preset.name == self.preset_name:
                context.scene.uv_presets.remove(i)
                if context.scene.uv_layers_tools.selected_preset == self.preset_name:
                    context.scene.uv_layers_tools.selected_preset = "GraffPreset"
                self.report({'INFO'}, f"Deleted preset '{self.preset_name}'")
                return {'FINISHED'}
        return {'CANCELLED'}

class VIEW3D_MT_ult_selection_tools(Menu):
    bl_label = "Selection Tools"
    bl_idname = "VIEW3D_MT_ult_selection_tools"

    def draw(self, context):
        layout = self.layout
        layout.operator("mesh.ult_select_without_uv", text="Meshes without UV", icon='X')
        layout.operator("mesh.ult_select_zero_uv_area", text="Meshes with Zero UV Area", icon='SNAP_FACE_CENTER')

class VIEW3D_PT_uv_layers_tools(Panel):
    bl_label = "UV Layers Tools"
    bl_idname = "VIEW3D_PT_uv_layers_tools"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'ULT'

    def draw(self, context):
        layout = self.layout
        settings = context.scene.uv_layers_tools

        row = layout.row(align=True)
        row.scale_x = 2.0
        row.prop(settings, "info_display", text="Info Display", toggle=True,
                 icon='CHECKBOX_HLT' if settings.info_display else 'CHECKBOX_DEHLT')

        box = layout.box()
        all_objects = context.selected_objects

        if all_objects and settings.info_display:
            if settings.stats_meshes_count > 0:
                row = box.row()
                left = row.row(align=True)
                left.label(text="", icon='OUTLINER_OB_MESH')
                meshes_count = settings.stats_meshes_count
                emoticon = EMOTICONS.get(meshes_count, "")
                meshes_text = f"Meshes: {emoticon}" if emoticon else "Meshes:"
                left.label(text=meshes_text)
                right = row.row()
                right.alignment = 'RIGHT'
                right.label(text=f"{meshes_count}")

            non_meshes_count = settings.stats_non_meshes_count
            if non_meshes_count > 0:
                row = box.row()
                left = row.row(align=True)
                left.label(text="", icon='OUTLINER_OB_EMPTY')
                emoticon = EMOTICONS.get(non_meshes_count, "")
                non_meshes_text = f"Non-Meshes: {emoticon}" if emoticon else "Non-Meshes:"
                left.label(text=non_meshes_text)
                right = row.row()
                right.alignment = 'RIGHT'
                right.label(text=f"{non_meshes_count}")

            if settings.stats_meshes_count > 0:
                if settings.stats_meshes_without_uv > 0:
                    row = box.row()
                    left = row.row(align=True)
                    left.label(text="", icon='ERROR')
                    left.label(text="Meshes without UV:")
                    right = row.row(align=True)
                    right.alignment = 'RIGHT'
                    right.label(text=str(settings.stats_meshes_without_uv))
                if settings.stats_meshes_zero_uv > 0:
                    row = box.row()
                    left = row.row(align=True)
                    left.label(text="", icon='ERROR')
                    left.label(text="Meshes with Zero UV Area:")
                    right = row.row(align=True)
                    right.alignment = 'RIGHT'
                    right.label(text=str(settings.stats_meshes_zero_uv))
                if settings.stats_uv_counts_mismatch:
                    row = box.row()
                    left = row.row(align=True)
                    left.label(text="", icon='ERROR')
                    left.label(text="UV Count Mismatch")
                    right = row.row()
                    right.alignment = 'RIGHT'
                    right.label(text="")
                if settings.stats_uv_names_mismatch:
                    row = box.row()
                    left = row.row(align=True)
                    left.label(text="", icon='ERROR')
                    left.label(text="UV Names Mismatch")
                    right = row.row()
                    right.alignment = 'RIGHT'
                    right.label(text="")
                if settings.stats_meshes_count > 1 and not (settings.stats_uv_counts_mismatch or settings.stats_uv_names_mismatch or settings.stats_meshes_without_uv > 0 or settings.stats_meshes_zero_uv > 0):
                    row = box.row()
                    left = row.row(align=True)
                    left.label(text="", icon='UV_SYNC_SELECT')
                    left.label(text="UV Layers Match")
                    right = row.row()
                    right.alignment = 'RIGHT'
                    right.label(text="")
        elif all_objects and not settings.info_display:
            pass
        elif not all_objects and settings.info_display:
            row = box.row()
            left = row.row(align=True)
            left.label(text="", icon='INFO')
            left.label(text="No Objects Selected   (  ⚆   _  ⚆)")
            right = row.row()
            right.alignment = 'RIGHT'
            right.label(text="")

        layout.separator(factor=0.5)

        select_box = layout.box()
        col = select_box.column(align=True)
        row = col.row(align=True)
        row.scale_y = 1.2
        row.menu("VIEW3D_MT_ult_selection_tools", text="Selection Tools", icon='RESTRICT_SELECT_OFF')

        layout.separator(factor=0.5)

        basic_box = layout.box()
        col = basic_box.column(align=True)
        col.operator("mesh.ult_add_uv", text="Add UV", icon='ADD')
        col.separator(factor=0.8)
        row = col.row(align=True)
        row.scale_y = 1.2
        row.operator("mesh.ult_move_uv_up", text="Move UV Up", icon='TRIA_UP')
        col.separator(factor=0.0)
        row = col.row(align=True)
        row.scale_y = 1.2
        row.operator("mesh.ult_move_uv_down", text="Move UV Down", icon='TRIA_DOWN')
        col.separator(factor=0.8)
        row = col.row(align=True)
        row.operator("mesh.ult_delete_uv", text="Delete UV", icon='TRASH')
        col.separator(factor=0.0)
        row = col.row(align=True)
        row.operator("mesh.ult_delete_uv_advanced", text="Advanced Delete UV(s)", icon='SETTINGS')

        layout.separator(factor=0.5)

        advanced_box = layout.box()
        col = advanced_box.column(align=True)
        row = col.row(align=True)
        row.scale_y = 1.2
        row.operator("mesh.ult_set_active_uv", text="Set Active", icon='UV_DATA')
        row.separator(factor=0.8)
        row.operator("mesh.ult_set_render_uv", text="Set Render", icon='RESTRICT_RENDER_OFF')
        col.separator(factor=0.0)
        row = col.row(align=True)
        row.scale_y = 1.2
        row.operator("mesh.ult_sync_active_uv", text="Sync Active", icon='UV_SYNC_SELECT')
        row.separator(factor=0.8)
        row.operator("mesh.ult_sync_render_uv", text="Sync Render", icon='UV_SYNC_SELECT')
        col.separator(factor=0.8)
        row = col.row(align=True)
        row.prop(settings, "auto_sync_render", text="Sync Render with Active UV", toggle=True,
                 icon='CHECKBOX_HLT' if settings.auto_sync_render else 'CHECKBOX_DEHLT')

        layout.separator(factor=0.5)

        rename_box = layout.box()
        col = rename_box.column(align=True)
        col.operator("mesh.ult_rename_uv", text="Rename UV", icon='FONT_DATA')
        col.separator(factor=0.8)
        row = col.row()
        row.label(text="Preset:", icon='PRESET')
        row.prop(settings, "selected_preset", text="")
        col.separator(factor=0.8)
        preset_box = col.box()
        if settings.selected_preset in BUILTIN_UV_PRESETS:
            uv_names = BUILTIN_UV_PRESETS[settings.selected_preset]
        else:
            uv_names = []
            for preset in context.scene.uv_presets:
                if preset.name == settings.selected_preset:
                    uv_names = [name.name for name in preset.uv_names]
                    break
        if uv_names:
            name_col = preset_box.column(align=True)
            for name in uv_names:
                name_col.label(text=name)
        else:
            preset_box.label(text="No UV Name Preset Selected   (・ω ・ )")
        row = col.row(align=True)
        row.scale_y = 1.2
        row.operator("mesh.ult_apply_preset", text="Apply Preset", icon='CHECKMARK')
        col.separator(factor=0.8)
        col.operator("object.ult_manage_presets", text="Manage Presets...", icon='SETTINGS')

        layout.separator(factor=0.5)

        box = layout.box()
        col = box.column(align=True)
        col.label(text="UV Layers of Active Mesh", icon='GROUP_UVS')
        row = box.row()
        split = row.split(factor=0.92)
        col_left = split.column()
        active_obj = context.active_object
        if active_obj and active_obj.type == 'MESH':
            uv_layers = active_obj.data.uv_layers
            rows = len(uv_layers)
            if rows == 0:
                rows = 1
            elif rows > 8:
                rows = 8
            col_left.template_list(
                "MESH_UL_ult_uv_list",
                "",
                active_obj.data,
                "uv_layers",
                active_obj.data.uv_layers,
                "active_index",
                rows=rows
            )
        col_right = split.column(align=True)
        col_right.scale_x = 0.5
        col_right.operator("mesh.uv_texture_add", text="", icon='ADD')
        col_right.operator("mesh.uv_texture_remove", text="", icon='REMOVE')

classes = (
    UVLayersSettings,
    UvNameItem,
    UvPresetItem,
    MESH_UL_ult_uv_list,
    MESH_OT_ult_select_without_uv,
    MESH_OT_ult_select_zero_uv_area,
    MESH_OT_ult_add_uv,
    MESH_OT_ult_rename_uv,
    MESH_OT_ult_set_active_uv,
    MESH_OT_ult_set_render_uv,
    MESH_OT_ult_delete_uv,
    MESH_OT_ult_delete_uv_advanced,
    MESH_OT_ult_move_uv_up,
    MESH_OT_ult_move_uv_down,
    MESH_OT_ult_sync_active_uv,
    MESH_OT_ult_sync_render_uv,
    MESH_OT_ult_apply_preset,
    OBJECT_OT_ult_manage_presets,
    OBJECT_OT_ult_create_preset,
    OBJECT_OT_ult_edit_preset,
    OBJECT_OT_ult_delete_preset,
    VIEW3D_MT_ult_selection_tools,
    VIEW3D_PT_uv_layers_tools,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.uv_layers_tools = PointerProperty(type=UVLayersSettings)
    bpy.types.Scene.uv_presets = CollectionProperty(type=UvPresetItem)
    if update_auto_render_and_stats not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(update_auto_render_and_stats)

def unregister():
    if update_auto_render_and_stats in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(update_auto_render_and_stats)
    del bpy.types.Scene.uv_presets
    del bpy.types.Scene.uv_layers_tools
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()