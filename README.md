# mdm-to-fbx

Turn a text prompt into a real-time 3D animation in your browser.

```
"a person waves their hand" → 3D animated character → browser
```

Built on top of [Motion Diffusion Model (MDM)](https://github.com/GuyTevet/motion-diffusion-model) by Tevet et al., 2022.

---

## How it works

```
Text Prompt
    ↓
MDM (diffusion model)         → .npy  (~19s)
    ↓
SMPL param extraction         → .pkl  (~14s)
    ↓
Blender headless export       → .fbx  (~8s)
    ↓
Three.js web frontend         → 3D animation in browser
```

Total: ~43 seconds on a laptop GPU.

---

## Project Structure

```
mdm-to-fbx/
├── avatar/
│   └── default_male.fbx       # Default T-pose shown on load
├── results/
│   ├── fbx/                   # Generated FBX animations
│   ├── npy/                   # Raw MDM outputs
│   └── pickle/                # SMPL param files
├── services/
│   ├── server.py              # Flask backend — orchestrates the pipeline
│   └── blender_export.py      # Headless Blender script — applies pose + exports FBX
├── views/
│   └── index.html             # Three.js frontend
└── requirements.txt
```

---

## Prerequisites

- [MDM repo](https://github.com/GuyTevet/motion-diffusion-model) set up with conda env `mdm`
- [Blender 5.1](https://www.blender.org/download/) installed (Windows)
- [SMPL Blender Addon v1.0.0](https://github.com/softcat477/SMPL-to-FBX/releases/tag/v1.0.0) installed in Blender
- WSL2 (Ubuntu) for running the Flask server
- CUDA-capable GPU

---

## Setup

**1. Clone this repo**
```bash
git clone https://github.com/yourusername/mdm-to-fbx.git
cd mdm-to-fbx
```

**2. Install Python dependencies**
```bash
conda activate mdm
pip install flask flask-cors
```

**3. Update paths in `services/server.py`**

Edit the CONFIG section at the top:
```python
MDM_DIR     = "~/motion-diffusion-model"
BLENDER     = "/mnt/c/Program Files/Blender Foundation/Blender 5.1/blender.exe"
PROJECT_DIR = "/mnt/c/path/to/mdm-to-fbx"
```

---

## Running

```bash
conda activate mdm
python services/server.py
```

Then open `views/index.html` in your browser, type a prompt, and hit generate.

---

## Usage

1. Type a motion description in the text box — e.g. `"a person jumps and claps"`
2. Hit Enter or click the arrow button
3. Wait ~43 seconds while the pipeline runs
4. The animated 3D character loads automatically

You can orbit the camera by dragging, zoom with scroll, and pause/play the animation.

---

## References

- [Human Motion Diffusion Model](https://arxiv.org/abs/2209.14916) — Tevet et al., 2022
- [SMPL Body Model](https://smpl.is.tue.mpg.de/) — MPI-IS
- [SMPL Blender Addon](https://github.com/softcat477/SMPL-to-FBX) — softcat477
- [Three.js](https://threejs.org)