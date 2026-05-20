"""
Blender headless script — applies SMPL animation and exports FBX
Run via: blender --background --python blender_export.py -- --pkl input.pkl --output output.fbx
"""

import bpy, sys, pickle, numpy as np, os

# Parse args after --
argv = sys.argv
args_start = argv.index('--') + 1 if '--' in argv else len(argv)
args = argv[args_start:]

pkl_path = None
output_path = None

for i, arg in enumerate(args):
    if arg == '--pkl' and i + 1 < len(args):
        pkl_path = args[i + 1]
    if arg == '--output' and i + 1 < len(args):
        output_path = args[i + 1]

if not pkl_path or not output_path:
    print("Usage: blender --background --python blender_export.py -- --pkl input.pkl --output output.fbx")
    sys.exit(1)

print(f"[Blender] Loading pkl: {pkl_path}")
print(f"[Blender] Output FBX: {output_path}")

# Load pkl
with open(pkl_path, 'rb') as f:
    data = pickle.load(f)

smpl_poses = data['smpl_poses']  # (N, 72)
smpl_trans = data['smpl_trans']  # (N, 3)
n_frames = smpl_poses.shape[0]

# Clear scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# Load SMPL male directly from blend file
blend_file = r"C:\Users\ROG\AppData\Roaming\Blender Foundation\Blender\5.1\scripts\addons\smpl_blender_addon\data\smpl-model-20200803.blend"
object_name = "SMPL-mesh-male"
objects_path = blend_file + "\\Object\\"

bpy.ops.wm.append(filename=object_name, directory=objects_path)
print(f"[Blender] Appended {object_name}")

# Get the SMPL armature
obj = None
for o in bpy.data.objects:
    if 'SMPL' in o.name and o.type == 'ARMATURE':
        obj = o
        break

if obj is None:
    print("[ERROR] SMPL armature not found")
    sys.exit(1)

print(f"[Blender] Found armature: {obj.name}")

bone_names = [
    'Pelvis', 'L_Hip', 'R_Hip', 'Spine1', 'L_Knee', 'R_Knee',
    'Spine2', 'L_Ankle', 'R_Ankle', 'Spine3', 'L_Foot', 'R_Foot',
    'Neck', 'L_Collar', 'R_Collar', 'Head', 'L_Shoulder', 'R_Shoulder',
    'L_Elbow', 'R_Elbow', 'L_Wrist', 'R_Wrist', 'L_Hand', 'R_Hand'
]

# Setup animation
obj.animation_data_create()
obj.animation_data.action = bpy.data.actions.new(name="SMPL_motion")

for bone in obj.pose.bones:
    bone.rotation_mode = 'XYZ'

bpy.context.scene.frame_start = 1
bpy.context.scene.frame_end = n_frames
bpy.context.scene.render.fps = 20

print(f"[Blender] Applying {n_frames} frames...")

def rotvec_to_euler(rotvec):
    import numpy as np
    angle = np.linalg.norm(rotvec)
    if angle < 1e-6:
        return (0.0, 0.0, 0.0)
    axis = rotvec / angle
    # Rodrigues → rotation matrix
    c, s = np.cos(angle), np.sin(angle)
    t = 1 - c
    x, y, z = axis
    R = np.array([
        [t*x*x + c,   t*x*y - s*z, t*x*z + s*y],
        [t*x*y + s*z, t*y*y + c,   t*y*z - s*x],
        [t*x*z - s*y, t*y*z + s*x, t*z*z + c  ]
    ])
    # Matrix → XYZ Euler
    sy = np.sqrt(R[0,0]**2 + R[1,0]**2)
    if sy > 1e-6:
        ex = np.arctan2( R[2,1], R[2,2])
        ey = np.arctan2(-R[2,0], sy)
        ez = np.arctan2( R[1,0], R[0,0])
    else:
        ex = np.arctan2(-R[1,2], R[1,1])
        ey = np.arctan2(-R[2,0], sy)
        ez = 0.0
    return (float(ex), float(ey), float(ez))

# bone_names = [
#     'Pelvis', 'L_Hip', 'R_Hip', 'Spine1', 'L_Knee', 'R_Knee',
#     'Spine2', 'L_Ankle', 'R_Ankle', 'Spine3', 'L_Foot', 'R_Foot',
#     'Neck', 'L_Collar', 'R_Collar', 'Head', 'L_Shoulder', 'R_Shoulder',
#     'L_Elbow', 'R_Elbow', 'L_Wrist', 'R_Wrist', 'L_Hand', 'R_Hand'
# ]

flip_x_bones = {'L_Shoulder', 'R_Shoulder', 'L_Collar', 'R_Collar'}

for frame in range(n_frames):
    bpy.context.scene.frame_set(frame + 1)
    poses = smpl_poses[frame].reshape(24, 3)
    for i, bone_name in enumerate(bone_names):
        if bone_name in obj.pose.bones:
            bone = obj.pose.bones[bone_name]
            ex, ey, ez = rotvec_to_euler(poses[i])
            if bone_name in flip_x_bones:
                ex, ey = -ex, -ey
            bone.rotation_euler = (ex, ey, ez)
            bone.keyframe_insert(data_path="rotation_euler", frame=frame + 1)

# Apply root translation with correct axis mapping
# MDM: X=left/right, Y=up/down, Z=forward/back
# Blender: X=left/right, Y=forward/back, Z=up
pelvis = obj.pose.bones['Pelvis']
pelvis.bone.use_local_location = True
for frame in range(n_frames):
    bpy.context.scene.frame_set(frame + 1)
    trans = smpl_trans[frame]
    pelvis.location = (trans[0], trans[1]- smpl_trans[0][1], trans[2])
    #pelvis.location = (trans[0], -trans[2], trans[1] - smpl_trans[0][1])
    
    pelvis.keyframe_insert(data_path="location", frame=frame + 1)

print("[Blender] Exporting FBX...")

# Select all objects
bpy.ops.object.select_all(action='SELECT')

bpy.ops.export_scene.fbx(
    filepath=output_path,
    use_selection=True,
    add_leaf_bones=False,
    bake_anim=True,
    bake_anim_use_all_actions=True,
    bake_anim_step=1,
    bake_anim_simplify_factor=0
)

print(f"[Blender] Done! FBX saved to {output_path}")