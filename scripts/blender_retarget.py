"""
Blender internal script: loads Adam FBX, applies SMPL params, exports FBX.
Input: smpl_params_clean.npy
"""

import bpy
import numpy as np
import argparse
import sys
import mathutils

SMPL_TO_MIXAMO = [
    "Hips", "LeftUpLeg", "RightUpLeg", "Spine",
    "LeftLeg", "RightLeg", "Spine1", "LeftFoot",
    "RightFoot", "Spine2", "LeftToeBase", "RightToeBase",
    "Neck", "LeftShoulder", "RightShoulder", "Head",
    "LeftArm", "RightArm", "LeftForeArm", "RightForeArm",
    "LeftHand", "RightHand", "LeftHandIndex1", "RightHandIndex1",
]

def parse_args():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input",  required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--adam",   required=True)
    return parser.parse_args(argv)

def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()

def rotation_6d_to_matrix(d6):
    a1 = d6[:3]
    a2 = d6[3:]
    b1 = a1 / (np.linalg.norm(a1) + 1e-8)
    b2 = a2 - np.dot(b1, a2) * b1
    b2 = b2 / (np.linalg.norm(b2) + 1e-8)
    b3 = np.cross(b1, b2)
    return np.stack([b1, b2, b3], axis=-1)

def matrix_to_euler(mat):
    m = mathutils.Matrix([
        [mat[0,0], mat[0,1], mat[0,2]],
        [mat[1,0], mat[1,1], mat[1,2]],
        [mat[2,0], mat[2,1], mat[2,2]],
    ])
    return m.to_euler('XYZ')

def load_smpl_params(npy_path):
    data   = np.load(npy_path, allow_pickle=True).item()
    thetas = np.array(data['thetas'])           # (24, 6, T)
    root_t = np.array(data['root_translation']) # (3, T)
    thetas = thetas.transpose(2, 0, 1)          # (T, 24, 6)
    root_t = root_t.T                           # (T, 3)
    return thetas, root_t

def import_adam(fbx_path):
    bpy.ops.import_scene.fbx(filepath=fbx_path)
    for obj in bpy.context.scene.objects:
        if obj.type == "ARMATURE":
            return obj
    raise RuntimeError("No armature found!")

def apply_motion(armature, thetas, root_t):
    bpy.context.view_layer.objects.active = armature
    armature.select_set(True)

    prefix = ""
    for bone in armature.pose.bones:
        if "Hips" in bone.name:
            prefix = bone.name.replace("Hips", "")
            break
    print(f"[blender_retarget] Bone prefix: '{prefix}'")

    T = len(thetas)
    bpy.context.scene.render.fps = 30
    bpy.context.scene.frame_start = 0
    bpy.context.scene.frame_end = T - 1

    root_start = root_t[0].copy()

    for frame_idx in range(T):
        bpy.context.scene.frame_set(frame_idx)
        for joint_idx, bone_name in enumerate(SMPL_TO_MIXAMO):
            full_name = prefix + bone_name
            if full_name not in armature.pose.bones:
                continue
            bone = armature.pose.bones[full_name]
            rot_6d = thetas[frame_idx, joint_idx]
            rot_mat = rotation_6d_to_matrix(rot_6d)
            euler = matrix_to_euler(rot_mat)
            bone.rotation_mode = 'XYZ'
            bone.rotation_euler = euler
            bone.keyframe_insert(data_path="rotation_euler", frame=frame_idx)
            if bone_name == "Hips":
                rel = root_t[frame_idx] - root_start
                bone.location = (rel[0], -rel[2], 0.0)
                bone.keyframe_insert(data_path="location", frame=frame_idx)

    print(f"[blender_retarget] Applied {T} frames")

def export_fbx(output_path):
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.fbx(
        filepath=output_path,
        use_selection=True,
        bake_anim=True,
        bake_anim_use_all_bones=True,
        bake_anim_step=1,
        bake_anim_simplify_factor=0,
        add_leaf_bones=False,
        path_mode="COPY",
        embed_textures=False,
        axis_forward='-Z',
        axis_up='Y',
    )

def main():
    args = parse_args()
    print(f"[blender_retarget] Input:  {args.input}")
    print(f"[blender_retarget] Output: {args.output}")
    print(f"[blender_retarget] Adam:   {args.adam}")
    clear_scene()
    thetas, root_t = load_smpl_params(args.input)
    armature = import_adam(args.adam)
    print(f"[blender_retarget] Frames: {len(thetas)}")
    apply_motion(armature, thetas, root_t)
    export_fbx(args.output)
    print(f"[blender_retarget] Done! FBX: {args.output}")

main()