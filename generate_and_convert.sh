#!/bin/bash
# Full pipeline: text prompt -> FBX
# Usage: bash generate_and_convert.sh "a person waves"

PROMPT="$1"
OUTPUT="$2"
MDM_DIR="/home/tmalikov/motion-diffusion-model"
CONVERTER_DIR="/home/tmalikov/mdm-to-fbx"
WIN_TEMP="/mnt/c/Users/ROG/AppData/Local/Temp/mdm_temp"
BLENDER="/mnt/c/Program Files/Blender Foundation/Blender 5.1/blender.exe"
EMS_AVATAR="/mnt/c/Users/ROG/OneDrive - The University of Chicago/Desktop/Uchicago/HCI/GenerativeEMS/frontend/avatar"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
MOTION_NAME="${TIMESTAMP}_$(echo "$PROMPT" | tr ' ' '_' | tr -dc '[:alnum:]_' | cut -c1-20)"
SAVE_DIR="$MDM_DIR/save/$MOTION_NAME"

mkdir -p "$WIN_TEMP"
mkdir -p "$CONVERTER_DIR/output"

if [ -z "$OUTPUT" ]; then
  OUTPUT="$CONVERTER_DIR/output/${MOTION_NAME}.fbx"
fi

echo "================================"
echo "Timestamp: $TIMESTAMP"
echo "Prompt:    $PROMPT"
echo "Output:    $OUTPUT"
echo "================================"

START=$(date +%s)

source ~/miniconda3/etc/profile.d/conda.sh
conda activate mdm

# Step 1 - Generate motion
echo "[1/4] Generating motion..."
T1=$(date +%s)
cd "$MDM_DIR"
python -m sample.generate \
  --model_path ./save/humanml_enc_512_50steps/model000750000.pt \
  --text_prompt "$PROMPT" \
  --num_samples 1 \
  --num_repetitions 1 \
  --output_dir "$SAVE_DIR"
echo "[1/4] Done in $(($(date +%s) - T1))s"

# Step 2 - render_mesh (GPU)
echo "[2/4] Running render_mesh..."
T2=$(date +%s)
cp "$SAVE_DIR/samples_00_to_00.mp4" "$SAVE_DIR/sample00_rep00.mp4"
python -m visualize.render_mesh \
  --input_path "$SAVE_DIR/sample00_rep00.mp4" \
  --cuda True \
  --device 0
echo "[2/4] Done in $(($(date +%s) - T2))s"

# Step 3 - Clean tensors
echo "[3/4] Cleaning tensors..."
T3=$(date +%s)
python -c "
import numpy as np, torch
data = np.load('$SAVE_DIR/sample00_rep00_smpl_params.npy', allow_pickle=True).item()
clean = {k: v.detach().cpu().numpy() if isinstance(v, torch.Tensor) else (np.array(v) if v is not None else v) for k, v in data.items()}
np.save('$SAVE_DIR/smpl_params_clean.npy', clean)
print('Done!')
"
echo "[3/4] Done in $(($(date +%s) - T3))s"

# Step 4 - Copy to Windows temp, run Blender, copy back
echo "[4/4] Exporting FBX..."
T4=$(date +%s)

cp "$SAVE_DIR/smpl_params_clean.npy" "$WIN_TEMP/smpl_params_clean.npy"
cp "$CONVERTER_DIR/scripts/blender_retarget.py" "$WIN_TEMP/blender_retarget.py"
cp "$CONVERTER_DIR/assets/adam.fbx" "$WIN_TEMP/adam.fbx"

"$BLENDER" --background \
  --python "C:\\Users\\ROG\\AppData\\Local\\Temp\\mdm_temp\\blender_retarget.py" \
  -- \
  --input "C:\\Users\\ROG\\AppData\\Local\\Temp\\mdm_temp\\smpl_params_clean.npy" \
  --output "C:\\Users\\ROG\\AppData\\Local\\Temp\\mdm_temp\\output.fbx" \
  --adam "C:\\Users\\ROG\\AppData\\Local\\Temp\\mdm_temp\\adam.fbx"

cp "$WIN_TEMP/output.fbx" "$OUTPUT"
cp "$OUTPUT" "$EMS_AVATAR/"   # ← added this line
echo "[4/4] Done in $(($(date +%s) - T4))s"

echo "================================"
echo "Total time: $(($(date +%s) - START))s"
echo "FBX saved to: $OUTPUT"
echo "Copied to EMS: $EMS_AVATAR"
echo "================================"
