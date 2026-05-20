#!/usr/bin/env python3
"""
Motion Generation Backend
Usage: conda activate mdm && python server.py
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import subprocess, os, time, glob, time


app = Flask(__name__)
CORS(app)

# ── CONFIG ────────────────────────────────────────────────────────────────
MDM_DIR         = os.path.expanduser("~/motion-diffusion-model")
BLENDER         = "/mnt/c/Program Files/Blender Foundation/Blender 5.1/blender.exe"
PROJECT_DIR     = "/mnt/c/Users/ROG/OneDrive - The University of Chicago/Desktop/Uchicago/HCI/mdm-to-fbx"
BLENDER_SCRIPT  = f"{PROJECT_DIR}/services/blender_export.py"
RESULTS_NPY     = f"{PROJECT_DIR}/results/npy"
RESULTS_PICKLE  = f"{PROJECT_DIR}/results/pickle"
RESULTS_FBX     = f"{PROJECT_DIR}/results/fbx"
# ─────────────────────────────────────────────────────────────────────────

def wsl_to_win(path):
    return path.replace("/mnt/c/", "C:\\").replace("/", "\\")

@app.route('/generate', methods=['POST'])
def generate():
    data = request.json
    prompt = data.get('prompt', '').strip()

    if not prompt:
        return jsonify({'error': 'No prompt provided'}), 400

    print(f"\n[GEN] Prompt: {prompt}")
    timestamp = int(time.time())

    try:
        # Step 1 — MDM generation
        t1 = time.time()
        print("[1/4] Running MDM...")
        save_dir = os.path.join(MDM_DIR, f"save/{timestamp}_{prompt[:20].replace(' ', '_')}")
        os.makedirs(save_dir, exist_ok=True)

        mdm_cmd = [
            "bash", "-c",
            f"source ~/miniconda3/etc/profile.d/conda.sh && conda activate mdm && "
            f"cd {MDM_DIR} && "
            f"python -m sample.generate "
            f"--model_path ./save/humanml_enc_512_50steps/model000750000.pt "
            f"--text_prompt '{prompt}' "
            f"--num_samples 1 --num_repetitions 1 "
            f"--output_dir '{save_dir}' "
            f"--device 0"
        ]
        result = subprocess.run(mdm_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(result.stderr)
            return jsonify({'error': 'MDM generation failed'}), 500
        print(f"[1/4] MDM took {time.time()-t1:.1f}s")

        # Step 2 — render_mesh to get SMPL params
        t2 = time.time()  
        print("[2/4] Running render_mesh...")
        fake_mp4 = os.path.join(save_dir, "sample00_rep00.mp4")
        # Create empty file just for path parsing
        open(fake_mp4, 'w').close()

        render_cmd = [
            "bash", "-c",
            f"source ~/miniconda3/etc/profile.d/conda.sh && conda activate mdm && "
            f"cd {MDM_DIR} && "
            f"python -m visualize.render_mesh "
            f"--input_path '{fake_mp4}' "
            f"--cuda True --device 0"
        ]
        result = subprocess.run(render_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(result.stderr)
            return jsonify({'error': 'render_mesh failed'}), 500
        print(f"[2/4] render_mesh took {time.time()-t2:.1f}s")

        # Step 3 — Convert to pkl
        t3 = time.time()
        print("[3/4] Converting to pkl...")
        smpl_npy = os.path.join(save_dir, "sample00_rep00_smpl_params.npy")
        pkl_path = f"{RESULTS_PICKLE}/{timestamp}.pkl"

        convert_cmd = [
            "bash", "-c",
            f"source ~/miniconda3/etc/profile.d/conda.sh && conda activate mdm && "
            f"cd {MDM_DIR} && python3 -c \""
            f"import numpy as np, torch, pickle; "
            f"import utils.rotation_conversions as geometry; "
            f"data = np.load('{smpl_npy}', allow_pickle=True).item(); "
            f"thetas = torch.tensor(data['thetas']).permute(2, 0, 1); "
            f"rot_matrices = geometry.rotation_6d_to_matrix(thetas); "
            f"axis_angles = geometry.matrix_to_axis_angle(rot_matrices); "
            f"smpl_poses = axis_angles.numpy().reshape(-1, 72); "
            f"smpl_trans = data['root_translation'].T; "
            f"pkl_out = {{'smpl_poses': smpl_poses.astype('float32'), 'smpl_trans': smpl_trans.astype('float32'), 'smpl_scaling': [1.0]}}; "
            f"pickle.dump(pkl_out, open('{pkl_path}', 'wb'), protocol=2); "
            f"print('pkl done')\""
        ]
        result = subprocess.run(convert_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(result.stderr)
            return jsonify({'error': 'pkl conversion failed'}), 500
        print(f"[3/4] pkl took {time.time()-t3:.1f}s")

        # Step 4 — Blender headless export FBX
        t4 = time.time()
        print("[4/4] Exporting FBX with Blender...")
        fbx_output = f"{RESULTS_FBX}/output_animation.fbx"
        win_pkl = pkl_path.replace('/mnt/c/', 'C:\\').replace('/', '\\')
        win_fbx = fbx_output.replace('/mnt/c/', 'C:\\').replace('/', '\\')

        blender_cmd = [
            BLENDER, "--background",
            "--python", r"C:\Users\ROG\OneDrive - The University of Chicago\Desktop\Uchicago\HCI\mdm-to-fbx\services\blender_export.py",            "--",
            "--pkl", win_pkl,
            "--output", win_fbx
        ]
        result = subprocess.run(blender_cmd, capture_output=True, text=True)

        print("[Blender stdout]", result.stdout[-2000:])
        print("[Blender stderr]", result.stderr[-2000:])

        if result.returncode != 0:
            print(result.stderr)
            return jsonify({'error': 'Blender export failed'}), 500
        print(f"[4/4] Blender export took {time.time()-t4:.1f}s")

        # Copy FBX to frontend avatar folder
        final_fbx = f"{RESULTS_FBX}/output_animation.fbx"
        subprocess.run(["cp", fbx_output, final_fbx])

        print(f"[DONE] FBX saved to {final_fbx}")

        print(f"[TOTAL] Total pipeline took {time.time()-t1:.1f}s")

        return jsonify({
            'success': True,
            'fbx_path': 'results/fbx/output_animation.fbx',
            'prompt': prompt
        })

    except Exception as e:
        print(f"[ERROR] {e}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("Starting Motion Generation Server on http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)