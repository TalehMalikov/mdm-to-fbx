"""
MDM results.npy -> FBX converter
Usage: python scripts/convert.py --input results.npy --output walk.fbx
"""

import argparse
import subprocess
import os
import sys

BLENDER = "/mnt/c/Program Files/Blender Foundation/Blender 5.1/blender.exe"
SCRIPT  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blender_retarget.py")
ADAM    = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../assets/adam.fbx")

def wsl_to_windows(path):
    path = os.path.abspath(path)
    if path.startswith("/mnt/"):
        parts = path[5:].split("/", 1)
        drive = parts[0].upper() + ":\\"
        rest  = parts[1].replace("/", "\\") if len(parts) > 1 else ""
        return drive + rest
    return path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input",  required=True, help="Path to results.npy")
    parser.add_argument("--output", required=True, help="Path to output .fbx")
    args = parser.parse_args()

    input_path  = os.path.abspath(args.input)
    output_path = os.path.abspath(args.output)
    adam_path   = os.path.abspath(ADAM)
    script_path = os.path.abspath(SCRIPT)

    if not os.path.exists(input_path):
        print(f"ERROR: Input not found: {input_path}"); sys.exit(1)
    if not os.path.exists(adam_path):
        print(f"ERROR: Adam FBX not found: {adam_path}"); sys.exit(1)

    print(f"Converting: {input_path} -> {output_path}")

    cmd = [
        BLENDER, "--background",
        "--python", wsl_to_windows(script_path),
        "--",
        "--input",  wsl_to_windows(input_path),
        "--output", wsl_to_windows(output_path),
        "--adam",   wsl_to_windows(adam_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print("Blender error:", result.stderr)
        sys.exit(1)

    if os.path.exists(output_path):
        print(f"✅ Done! FBX saved to: {output_path}")
    else:
        print("ERROR: FBX not created"); sys.exit(1)

if __name__ == "__main__":
    main()