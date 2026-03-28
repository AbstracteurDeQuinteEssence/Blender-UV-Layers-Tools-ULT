bl_info = {
    "name": "UV Layers Tools (ULT)",
    "author": "Karen (Threed) and AI assistant",
    "version": (1, 0),
    "blender": (4, 5, 0),
    "location": "View3D > Sidebar > ULT",
    "description": "Powerful Add-on for Batch UV Layer Management",
    "category": "UV",
}

import array
import bpy
import time
from bpy.types import Operator, Panel, PropertyGroup, UIList
from bpy.props import IntProperty, StringProperty, EnumProperty, BoolProperty, PointerProperty, CollectionProperty

BUILTIN_UV_PRESETS = {
    "GraffPreset": ["UV_Tile", "UV_Nac", "UV_ColorAtlas"],
    "GameDevPreset": ["UV_Main", "UV_Lightmap", "UV_Decals"],
    "IndexPreset": ["UV0", "UV1", "UV2", "UV3", "UV4", "UV5", "UV6", "UV7"]
}

class UVLayersSettings(PropertyGroup):
    auto_sync_render: BoolProperty(
        name="Sync Render with Active UV",
        description="When enabled, the active UV layer is automatically used as the render UV layer for any mesh objects you select",
        default=False
    )
    
    show_detailed_info: BoolProperty(
        name="Show Detailed Info",
        description="Show detailed information about UV layers",
        default=True
    )
    
    def get_preset_items(self, context):
        items = [
            ('GraffPreset', 'GraffPreset', 'Built-in preset: GraffPreset'),
            ('GameDevPreset', 'GameDevPreset', 'Built-in preset: GameDevPreset'),
            ('IndexPreset', 'IndexPreset', 'Built-in preset: IndexPreset')
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

class MESH_UL_uv_layers_tools_list(UIList):
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

@bpy.app.handlers.persistent
def update_auto_render(dummy):
    scene = bpy.context.scene
    if not scene or not hasattr(scene, 'uv_layers_tools'):
        return
    
    if not scene.uv_layers_tools.auto_sync_render:
        return
    
    selected_objects = list(bpy.context.selected_objects)
    active_object = bpy.context.active_object
    
    objects_to_process = selected_objects
    if (active_object and 
        active_object.type == 'MESH' and 
        active_object not in selected_objects):
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

class MESH_OT_uv_add_tool_ULT(Operator):
    bl_idname = "mesh.uv_add_tool_ult"
    bl_label = "Add UV Layer"
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
        
        if success_count == 0 and maxed_count == 0:
            self.report({'WARNING'}, "No mesh objects selected")
        elif success_count == 0 and maxed_count > 0:
            if maxed_count == 1:
                self.report({'WARNING'}, "Cannot add more than 8 UV layers")
            else:
                self.report({'WARNING'}, f"Cannot add more than 8 UV layers; {maxed_count} object(s) already have 8 UV layers")
        elif success_count > 0 and maxed_count == 0:
            self.report({'INFO'}, f"Added UV layer to {success_count} object(s)")
        else:
            self.report({'INFO'}, f"Added UV layer to {success_count} object(s), {maxed_count} object(s) already have 8 layers")
            
        return {'FINISHED'}

class MESH_OT_uv_rename_tool_ULT(Operator, UV_OT_Base):
    bl_idname = "mesh.uv_rename_tool_ult"
    bl_label = "Rename UV"
    bl_description = "Rename UV layer by index for all selected mesh objects"
    bl_options = {'REGISTER', 'UNDO'}
    
    index: IntProperty(name="Index", default=1, min=1)
    new_name: StringProperty(name="New Name", default="")
    
    def execute(self, context):
        if not self.new_name.strip():
            self.report({'WARNING'}, "Name cannot be empty")
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

class MESH_OT_uv_set_active_tool_ULT(Operator, UV_OT_Base):
    bl_idname = "mesh.uv_set_active_tool_ult"
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

class MESH_OT_uv_set_render_tool_ULT(Operator):
    bl_idname = "mesh.uv_set_render_tool_ult"
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

class MESH_OT_uv_delete_tool_ULT(Operator, UV_OT_Base):
    bl_idname = "mesh.uv_delete_tool_ult"
    bl_label = "Delete UV"
    bl_description = "Delete UV layer by index for all selected mesh objects"
    bl_options = {'REGISTER', 'UNDO'}
    
    index: IntProperty(name="Index", default=1, min=1)
    
    def execute(self, context):
        idx = self.index - 1
        deleted = 0
        
        for obj in context.selected_objects:
            if obj.type == 'MESH' and idx < len(obj.data.uv_layers):
                uv_layers = obj.data.uv_layers
                
                all_layers_data = []
                for layer in uv_layers:
                    data = array.array('f', [0.0] * (len(layer.data) * 2))
                    layer.data.foreach_get("uv", data)
                    all_layers_data.append(data)
                
                uv_layers.remove(uv_layers[idx])
                
                for i, layer in enumerate(uv_layers):
                    if i < idx:
                        layer.data.foreach_set("uv", all_layers_data[i])
                    else:
                        layer.data.foreach_set("uv", all_layers_data[i + 1])
                
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

class MESH_OT_uv_delete_advanced_tool_ULT(Operator, UV_OT_Base):
    bl_idname = "mesh.uv_delete_advanced_tool_ult"
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
        else:
            self.report({'WARNING'}, "No UV layers were deleted")
        
        return {'FINISHED'}
    
    def draw(self, context):
        layout = self.layout
        layout.prop(self, "delete_mode", text="Mode")
        
        if self.delete_mode == 'BY_LIST':
            layout.label(text="Enter UV layer index/indices:")
            layout.prop(self, "index_list", text="")
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

class MESH_OT_uv_move_up_tool_ULT(Operator, UV_OT_Base):
    bl_idname = "mesh.uv_move_up_tool_ult"
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
        
        if moved:
            msg = f"Moved {moved} UV layer(s) up"
            if skipped:
                msg += f", {skipped} already at top"
            self.report({'INFO'}, msg)
        
        return {'FINISHED'}

class MESH_OT_uv_move_down_tool_ULT(Operator, UV_OT_Base):
    bl_idname = "mesh.uv_move_down_tool_ult"
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
        
        if moved:
            msg = f"Moved {moved} UV layer(s) down"
            if skipped:
                msg += f", {skipped} already at bottom"
            self.report({'INFO'}, msg)
        
        return {'FINISHED'}

class MESH_OT_sync_active_tool_ULT(Operator):
    bl_idname = "mesh.sync_active_tool_ult"
    bl_label = "Sync Active UV"
    bl_description = "Sync active UV layer index from active object to all selected mesh objects"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        if not (context.active_object and 
                context.active_object.type == 'MESH' and 
                context.active_object.data.uv_layers):
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

class MESH_OT_sync_render_tool_ULT(Operator):
    bl_idname = "mesh.sync_render_tool_ult"
    bl_label = "Sync Render UV"
    bl_description = "Sync render UV layer index from active object to all selected mesh objects"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        settings = context.scene.uv_layers_tools
        if settings.auto_sync_render:
            return False
        
        if not (context.active_object and 
                context.active_object.type == 'MESH' and 
                context.active_object.data.uv_layers):
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
        render_idx = next((i for i, uv in enumerate(active_obj.data.uv_layers) 
                          if uv.active_render), -1)
        
        if render_idx == -1:
            self.report({'ERROR'}, "Active object has no render UV layer")
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

class OBJECT_OT_select_all_meshes_ULT(Operator):
    bl_idname = "object.select_all_meshes_ult"
    bl_label = "Select All Meshes"
    bl_description = "Select all visible mesh objects in the scene"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return any(obj.type == 'MESH' for obj in context.visible_objects)
    
    def execute(self, context):
        bpy.ops.object.select_all(action='DESELECT')
        
        visible_meshes = []
        for obj in context.visible_objects:
            if obj.type == 'MESH':
                obj.select_set(True)
                visible_meshes.append(obj)
        
        if visible_meshes:
            context.view_layer.objects.active = visible_meshes[0]
        
        self.report({'INFO'}, f"Selected {len(visible_meshes)} visible mesh object(s)")
        return {'FINISHED'}

class OBJECT_OT_deselect_non_meshes_ULT(Operator):
    bl_idname = "object.deselect_non_meshes_ult"
    bl_label = "Deselect Non-Meshes"
    bl_description = "Deselect all non-mesh objects, keeping only meshes selected"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return any(obj.type != 'MESH' for obj in context.selected_objects)
    
    def execute(self, context):
        non_meshes_deselected = 0
        
        for obj in context.selected_objects:
            if obj.type != 'MESH':
                obj.select_set(False)
                non_meshes_deselected += 1
        
        if context.active_object and context.active_object.type != 'MESH':
            selected_meshes = [obj for obj in context.selected_objects if obj.type == 'MESH']
            if selected_meshes:
                context.view_layer.objects.active = selected_meshes[0]
            else:
                context.view_layer.objects.active = None
        
        self.report({'INFO'}, f"Deselected {non_meshes_deselected} non-mesh object(s)")
        return {'FINISHED'}

class MESH_OT_apply_uv_preset_ULT(Operator, UV_OT_Base):
    bl_idname = "mesh.apply_uv_preset_ult"
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
            self.report({'WARNING'}, f"Preset '{preset_name}' not found")
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

class OBJECT_OT_manage_uv_presets_ULT(Operator):
    bl_idname = "object.manage_uv_presets_ult"
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
        
        layout.label(text="Custom Presets:", icon='FILE_NEW')
        
        if not context.scene.uv_presets:
            layout.label(text="No custom presets yet", icon='INFO')
        else:
            for preset in context.scene.uv_presets:
                row = layout.row()
                row.label(text=preset.name, icon='PRESET')
                
                edit_op = row.operator("object.edit_uv_preset_ult", text="", icon='GREASEPENCIL')
                edit_op.preset_name = preset.name
                
                delete_op = row.operator("object.delete_uv_preset_ult", text="", icon='TRASH')
                delete_op.preset_name = preset.name
        
        layout.separator()
        
        row = layout.row()
        op = row.operator("object.create_uv_preset_ult", text="New", icon='ADD')
        op.context = 'INVOKE_DEFAULT'
        
        layout.separator()
        layout.label(text="Note: OK and Cancel buttons both close this dialog", icon='INFO')

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

class OBJECT_OT_create_uv_preset_ULT(Operator):
    bl_idname = "object.create_uv_preset_ult"
    bl_label = "Create UV Name Preset"
    bl_description = "Create a new UV name preset"
    bl_options = {'REGISTER', 'UNDO'}
    
    context: StringProperty(default='INVOKE_DEFAULT')
    
    preset_name: StringProperty(
        name="Preset Name", 
        default="",
        description="Name of the UV name preset (empty for default)"
    )
    
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
            final_preset_name = make_unique_preset_name(context, self.preset_name.strip())
        
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
        row.label(text="Leave empty for default name")
        
        layout.separator()
        
        box = layout.box()
        
        for i in range(1, 9):
            row = box.row(align=True)
            split = row.split(factor=0.2, align=True)
            split.label(text=f"UV {i}:")
            split.prop(self, f"uv_name_{i}", text="")
        
        layout.separator()
        layout.label(text="Note: Only filled fields will be saved to the preset", icon='INFO')

class OBJECT_OT_edit_uv_preset_ULT(Operator):
    bl_idname = "object.edit_uv_preset_ult"
    bl_label = "Edit UV Name Preset"
    bl_description = "Edit an existing UV name preset"
    bl_options = {'REGISTER', 'UNDO'}
    
    context: StringProperty(default='INVOKE_DEFAULT')
    
    preset_name: StringProperty(name="Preset Name")
    
    new_preset_name: StringProperty(
        name="Preset Name", 
        default="",
        description="Name of the UV name preset"
    )
    
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
            self.report({'ERROR'}, f"Preset '{self.preset_name}' not found")
            return {'CANCELLED'}
        
        new_name = self.new_preset_name.strip()
        if not new_name:
            new_name = make_unique_preset_name(context, "CustomPreset")
        else:
            if new_name != self.preset_name:
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
        row.label(text="Leave empty for default name")
        
        layout.separator()
        
        box = layout.box()
        
        for i in range(1, 9):
            row = box.row(align=True)
            split = row.split(factor=0.2, align=True)
            split.label(text=f"UV {i}:")
            split.prop(self, f"uv_name_{i}", text="")
        
        layout.separator()
        layout.label(text="Note: Only filled fields will be saved to the preset", icon='INFO')

class OBJECT_OT_delete_uv_preset_ULT(Operator):
    bl_idname = "object.delete_uv_preset_ult"
    bl_label = "Delete Preset"
    bl_description = "Deletes a custom UV name preset"
    bl_options = {'REGISTER', 'UNDO'}
    
    preset_name: StringProperty(name="Preset Name")
    
    @classmethod
    def poll(cls, context):
        return len(context.scene.uv_presets) > 0
    
    def execute(self, context):
        if self.preset_name in BUILTIN_UV_PRESETS:
            self.report({'ERROR'}, f"Cannot delete built-in preset '{self.preset_name}'")
            return {'CANCELLED'}
        
        for i, preset in enumerate(context.scene.uv_presets):
            if preset.name == self.preset_name:
                context.scene.uv_presets.remove(i)
                
                if context.scene.uv_layers_tools.selected_preset == self.preset_name:
                    context.scene.uv_layers_tools.selected_preset = "GraffPreset"
                
                self.report({'INFO'}, f"Deleted preset '{self.preset_name}'")
                return {'FINISHED'}
        
        self.report({'ERROR'}, f"Preset '{self.preset_name}' not found")
        return {'CANCELLED'}

class MESH_OT_uv_add_active_ULT(Operator):
    bl_idname = "mesh.uv_add_active_ult"
    bl_label = "Add UV Layer to Active"
    bl_description = "Add a new UV layer to active mesh object"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type == 'MESH'
    
    def execute(self, context):
        active_obj = context.active_object
        if active_obj and active_obj.type == 'MESH':
            if len(active_obj.data.uv_layers) >= 8:
                self.report({'WARNING'}, "Cannot add more than 8 UV layers")
                return {'CANCELLED'}
            
            active_obj.data.uv_layers.new()
            active_obj.data.update_tag()
            active_obj.update_tag()
            self.report({'INFO'}, "Added UV layer to active object")
        return {'FINISHED'}

class MESH_OT_uv_remove_active_ULT(Operator):
    bl_idname = "mesh.uv_remove_active_ult"
    bl_label = "Remove Active UV Layer"
    bl_description = "Remove active UV layer from active mesh object"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        active_obj = context.active_object
        if not (active_obj and active_obj.type == 'MESH'):
            return False
        return len(active_obj.data.uv_layers) > 0
    
    def execute(self, context):
        active_obj = context.active_object
        if active_obj and active_obj.type == 'MESH':
            uv_layers = active_obj.data.uv_layers
            if uv_layers:
                active_idx = uv_layers.active_index
                
                all_layers_data = []
                for layer in uv_layers:
                    data = array.array('f', [0.0] * (len(layer.data) * 2))
                    layer.data.foreach_get("uv", data)
                    all_layers_data.append(data)
                
                uv_layers.remove(uv_layers[active_idx])
                
                for i, layer in enumerate(uv_layers):
                    if i < active_idx:
                        layer.data.foreach_set("uv", all_layers_data[i])
                    else:
                        layer.data.foreach_set("uv", all_layers_data[i + 1])
                
                active_obj.data.update_tag()
                active_obj.update_tag()
                
                for window in bpy.context.window_manager.windows:
                    for area in window.screen.areas:
                        area.tag_redraw()
                
                self.report({'INFO'}, "Removed active UV layer from active object")
        
        return {'FINISHED'}

class MESH_OT_show_more_info_ULT(Operator):
    bl_idname = "mesh.show_more_info_ult"
    bl_label = "More Info"
    bl_description = "Show detailed information about UV layers"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        context.scene.uv_layers_tools.show_detailed_info = True
        return {'FINISHED'}
    
    @classmethod
    def poll(cls, context):
        return not context.scene.uv_layers_tools.show_detailed_info

class MESH_OT_show_less_info_ULT(Operator):
    bl_idname = "mesh.show_less_info_ult"
    bl_label = "Less Info"
    bl_description = "Show only basic information"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        context.scene.uv_layers_tools.show_detailed_info = False
        return {'FINISHED'}
    
    @classmethod
    def poll(cls, context):
        return context.scene.uv_layers_tools.show_detailed_info

class VIEW3D_PT_uv_layers_tools(Panel):
    bl_label = "UV Layers Tools"
    bl_idname = "VIEW3D_PT_uv_layers_tools"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'ULT'
    
    def draw(self, context):
        layout = self.layout
        settings = context.scene.uv_layers_tools
        
        box = layout.box()
        
        all_objects = context.selected_objects
        meshes = [obj for obj in all_objects if obj.type == 'MESH']
        non_meshes = [obj for obj in all_objects if obj.type != 'MESH']
        
        if all_objects:
            row = box.row()
            left = row.row(align=True)
            left.label(text="", icon='MESH_DATA')
            
            meshes_text = "Selected Meshes:"
            meshes_count = len(meshes)
            
            if meshes_count == 13:
                meshes_text += " (=👁  ｪ  👁=) "
            elif meshes_count == 27:
                meshes_text += " (✖╭╮✖) "
            elif meshes_count == 33:
                meshes_text += " ╰( † - † )╯ "
            elif meshes_count == 69:
                meshes_text += " ( o ͜ʖ o ) "
            elif meshes_count == 228:
                meshes_text += " | |(-_-)| | "
            elif meshes_count == 300:
                meshes_text += " (' o') c==3 "
            elif meshes_count == 322:
                meshes_text += " A. «Solo» B. "
            elif meshes_count == 404:
                meshes_text += " [Not Found] "
            elif meshes_count == 666:
                meshes_text += " ╰(◣_◢)ψ "
            elif meshes_count == 777:
                meshes_text += " [ 7 | 7 | 7 ] "
            elif meshes_count == 1488:
                meshes_text += " ОСУЖДАЮ "
            elif meshes_count == 1984:
                meshes_text += " ( ◎ _ ◎ ) "
            elif meshes_count == 2077:
                meshes_text += " [ B U G ] "
            elif meshes_count == 80085:
                meshes_text += " ( . Y . ) "
            
            left.label(text=meshes_text)
            right = row.row()
            right.alignment = 'RIGHT'
            right.label(text=f"{meshes_count}")
            
            if non_meshes:
                row = box.row()
                left = row.row(align=True)
                left.label(text="", icon='INFO')
                
                non_meshes_text = "Non-Meshes:"
                non_meshes_count = len(non_meshes)
                
                if non_meshes_count == 13:
                    non_meshes_text += " (=👁  ｪ  👁=) "
                elif non_meshes_count == 27:
                    non_meshes_text += " (✖╭╮✖) "
                elif non_meshes_count == 33:
                    non_meshes_text += " ╰( † - † )╯ "
                elif non_meshes_count == 69:
                    non_meshes_text += " ( o ͜ʖ o ) "
                elif non_meshes_count == 228:
                    non_meshes_text += " | |(-_-)| | "
                elif non_meshes_count == 300:
                    non_meshes_text += " (' o') c==3 "
                elif non_meshes_count == 322:
                    non_meshes_text += " A. «Solo» B. "
                elif non_meshes_count == 404:
                    non_meshes_text += " [Not Found] "
                elif non_meshes_count == 666:
                    non_meshes_text += " ╰(◣_◢)ψ "
                elif non_meshes_count == 777:
                    non_meshes_text += " [ 7 | 7 | 7 ] "
                elif non_meshes_count == 1488:
                    non_meshes_text += " ОСУЖДАЮ "
                elif non_meshes_count == 1984:
                    non_meshes_text += " ( ◎ _ ◎ ) "
                elif non_meshes_count == 2077:
                    non_meshes_text += " [ B U G ] "
                elif non_meshes_count == 80085:
                    non_meshes_text += " ( . Y . ) "
                
                left.label(text=non_meshes_text)
                right = row.row()
                right.alignment = 'RIGHT'
                right.label(text=f"{non_meshes_count}")
            
            if settings.show_detailed_info and meshes:
                uv_counts = set()
                layer_names_by_index = {}
                meshes_without_uv = 0
                total_meshes = len(meshes)
                
                for obj in meshes:
                    uv_layers = obj.data.uv_layers
                    uv_counts.add(len(uv_layers))
                    
                    if len(uv_layers) == 0:
                        meshes_without_uv += 1
                    
                    for i, uv in enumerate(uv_layers):
                        if i not in layer_names_by_index:
                            layer_names_by_index[i] = set()
                        layer_names_by_index[i].add(uv.name)
                
                name_mismatches = False
                for idx, names in layer_names_by_index.items():
                    if len(names) > 1:
                        name_mismatches = True
                        break
                
                if meshes_without_uv > 0:
                    if total_meshes == 1 and meshes_without_uv == 1:
                        row = box.row()
                        left = row.row(align=True)
                        left.label(text="", icon='ERROR')
                        left.label(text="Selected Mesh Has No UV")
                        right = row.row()
                        right.alignment = 'RIGHT'
                        right.label(text="")
                    elif total_meshes > 1 and meshes_without_uv == total_meshes:
                        row = box.row()
                        left = row.row(align=True)
                        left.label(text="", icon='ERROR')
                        left.label(text="Selected Meshes Have No UV")
                        right = row.row()
                        right.alignment = 'RIGHT'
                        right.label(text="")
                    else:
                        row = box.row()
                        left = row.row(align=True)
                        left.label(text="", icon='ERROR')
                        left.label(text="Meshes Without UV:")
                        right = row.row()
                        right.alignment = 'RIGHT'
                        right.label(text=f"{meshes_without_uv}")
                
                if len(uv_counts) > 1:
                    row = box.row()
                    left = row.row(align=True)
                    left.label(text="", icon='ERROR')
                    left.label(text="UV Count Mismatch")
                    right = row.row()
                    right.alignment = 'RIGHT'
                    right.label(text="")
                
                if name_mismatches:
                    row = box.row()
                    left = row.row(align=True)
                    left.label(text="", icon='ERROR')
                    left.label(text="UV Names Mismatch")
                    right = row.row()
                    right.alignment = 'RIGHT'
                    right.label(text="")
                
                if len(meshes) > 1 and not (len(uv_counts) > 1 or name_mismatches or meshes_without_uv > 0):
                    row = box.row()
                    left = row.row(align=True)
                    left.label(text="", icon='UV_SYNC_SELECT')
                    left.label(text="UV Layers Match")
                    right = row.row()
                    right.alignment = 'RIGHT'
                    right.label(text="")
            
        else:
            row = box.row()
            left = row.row(align=True)
            left.label(text="", icon='INFO')
            left.label(text="No Objects Selected   (⚆  _ ⚆)")
            right = row.row()
            right.alignment = 'RIGHT'
            right.label(text="")
        
        row = box.row(align=True)
        row.operator("mesh.show_more_info_ult", text="More Info")
        row.operator("mesh.show_less_info_ult", text="Less Info")
        
        layout.separator(factor=0.5)
        
        selection_box = layout.box()
        col = selection_box.column(align=True)
        
        row = col.row(align=True)
        row.scale_y = 1.2
        row.operator("object.select_all_meshes_ult", text="Select All Meshes", icon='RESTRICT_SELECT_OFF')
        
        col.separator(factor=0.0)
        
        row = col.row(align=True)
        row.scale_y = 1.2
        row.operator("object.deselect_non_meshes_ult", text="Deselect Non-Meshes", icon='SELECT_SUBTRACT')
        
        layout.separator(factor=0.5)
        
        basic_box = layout.box()
        col = basic_box.column(align=True)
        
        col.operator("mesh.uv_add_tool_ult", text="Add UV Layer", icon='ADD')
        col.separator(factor=0.8)
        
        row = col.row(align=True)
        row.scale_y = 1.2
        row.operator("mesh.uv_move_up_tool_ult", text="Move UV Up", icon='TRIA_UP')
        
        col.separator(factor=0.0)
        
        row = col.row(align=True)
        row.scale_y = 1.2
        row.operator("mesh.uv_move_down_tool_ult", text="Move UV Down", icon='TRIA_DOWN')
        
        col.separator(factor=0.8)
        
        row = col.row(align=True)
        row.scale_y = 1.2
        row.operator("mesh.uv_delete_tool_ult", text="Delete UV", icon='TRASH')
        
        col.separator(factor=0.0)
        
        row = col.row(align=True)
        row.scale_y = 1.2
        row.operator("mesh.uv_delete_advanced_tool_ult", text="Advanced Delete UV(s)", icon='SETTINGS')
        
        layout.separator(factor=0.5)
        
        advanced_box = layout.box()
        col = advanced_box.column(align=True)
        
        row = col.row(align=True)
        row.scale_y = 1.2
        row.operator("mesh.uv_set_active_tool_ult", text="Set Active", icon='UV_DATA')
        
        row.separator(factor=0.8)
        
        row.operator("mesh.uv_set_render_tool_ult", text="Set Render", icon='RESTRICT_RENDER_OFF')
        
        col.separator(factor=0.0)
        
        row = col.row(align=True)
        row.scale_y = 1.2
        row.operator("mesh.sync_active_tool_ult", text="Sync Active", icon='UV_SYNC_SELECT')
        
        row.separator(factor=0.8)
        
        row.operator("mesh.sync_render_tool_ult", text="Sync Render", icon='UV_SYNC_SELECT')
        
        col.separator(factor=0.8)
        
        row = col.row(align=True)
        row.prop(settings, "auto_sync_render", 
                text="Sync Render with Active UV",
                toggle=True,
                icon='CHECKBOX_HLT' if settings.auto_sync_render else 'CHECKBOX_DEHLT')
        
        layout.separator(factor=0.5)
        
        rename_box = layout.box()
        col = rename_box.column(align=True)
        
        col.operator("mesh.uv_rename_tool_ult", text="Rename UV", icon='FONT_DATA')
        
        col.separator(factor=0.8)
        
        row = col.row()
        row.label(text="Preset:", icon='PRESET')
        row.prop(settings, "selected_preset", text="")
        
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
            preset_box.label(text="No UV Name Preset Selected   (・ω・)")
        
        row = col.row(align=True)
        row.scale_y = 1.2
        row.operator("mesh.apply_uv_preset_ult", text="Apply Preset", icon='CHECKMARK')
        
        col.separator(factor=0.5)
        
        col.operator("object.manage_uv_presets_ult", text="Manage Presets...", icon='SETTINGS')
        
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
                "MESH_UL_uv_layers_tools_list",
                "",
                active_obj.data,
                "uv_layers",
                active_obj.data.uv_layers,
                "active_index",
                rows=rows
            )
        
        col_right = split.column(align=True)
        col_right.scale_x = 0.5
        col_right.operator("mesh.uv_add_active_ult", text="", icon='ADD')
        col_right.operator("mesh.uv_remove_active_ult", text="", icon='REMOVE')

classes = (
    UVLayersSettings,
    UvNameItem,
    UvPresetItem,
    MESH_UL_uv_layers_tools_list,
    MESH_OT_uv_add_tool_ULT,
    MESH_OT_uv_rename_tool_ULT,
    MESH_OT_uv_set_active_tool_ULT,
    MESH_OT_uv_set_render_tool_ULT,
    MESH_OT_uv_delete_tool_ULT,
    MESH_OT_uv_delete_advanced_tool_ULT,
    MESH_OT_uv_move_up_tool_ULT,
    MESH_OT_uv_move_down_tool_ULT,
    MESH_OT_sync_active_tool_ULT,
    MESH_OT_sync_render_tool_ULT,
    OBJECT_OT_select_all_meshes_ULT,
    OBJECT_OT_deselect_non_meshes_ULT,
    MESH_OT_apply_uv_preset_ULT,
    OBJECT_OT_manage_uv_presets_ULT,
    OBJECT_OT_create_uv_preset_ULT,
    OBJECT_OT_edit_uv_preset_ULT,
    OBJECT_OT_delete_uv_preset_ULT,
    MESH_OT_uv_add_active_ULT,
    MESH_OT_uv_remove_active_ULT,
    MESH_OT_show_more_info_ULT,
    MESH_OT_show_less_info_ULT,
    VIEW3D_PT_uv_layers_tools,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    bpy.types.Scene.uv_layers_tools = PointerProperty(type=UVLayersSettings)
    bpy.types.Scene.uv_presets = CollectionProperty(type=UvPresetItem)
    
    if update_auto_render not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(update_auto_render)

def unregister():
    if update_auto_render in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(update_auto_render)
    
    del bpy.types.Scene.uv_presets
    del bpy.types.Scene.uv_layers_tools
    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()