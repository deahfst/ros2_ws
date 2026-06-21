# ros2_ws

This repository contains the ROS2 workspace `ros2_ws` used for development of the arm controller and OCR tooling.

Repository summary and current project status
--------------------------------------------
- Workspace root contains:
  - `src/` — ROS2 packages (primary: `so_arm101_controller`).
  - `build/`, `install/`, `log/` — colcon build outputs (ignored by `.gitignore`).
  - `ocr_captures/`, `ocr_captures_tracking/` — datasets and debug captures used by OCR components.
  - local third-party wheel(s): `paddlepaddle_gpu-*.whl` (kept for Jetson installs).

Progress / status (high level)
-----------------------------
- `so_arm101_controller` exists in `src/` and contains ROS2 Python nodes: arm controller, OCR module, vision tracker and helper scripts. Core node implementations are present and were tested locally.
- OCR tooling and datasets are present in `ocr_captures/` and `ocr_captures_tracking/` for debugging and offline evaluation.
- A separate repository holds the Jetson-specific OCR app: https://github.com/deahfst/Jetson_OCR
- Repository metadata added: `.gitattributes` (tracks `*.whl` for Git LFS) and a minimal GitHub Actions CI workflow at `.github/workflows/ci.yml`.

Who should read this
--------------------
- Engineers setting up the workspace on a development machine or Nvidia Jetson device.
- Integrators porting the project to Jetson Orin Nano (requires careful handling of PaddlePaddle wheels).

Quick start — setup and build
----------------------------
Prerequisites:
- Ubuntu 22.04 or the JetPack-provided Ubuntu for Jetson
- ROS2 distribution compatible with code (source the appropriate `/opt/ros/<distro>/setup.bash`)
- Python 3.10 recommended

1) Clone and change to workspace

```bash
git clone https://github.com/deahfst/ros2_ws.git
cd ros2_ws
```

2) Optional: create Python virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
```

3) (Jetson) Install PaddlePaddle GPU wheel

Place the matching `paddlepaddle_gpu-*.whl` into the repo root or download it separately. Then:

```bash
source .venv/bin/activate
pip install ./paddlepaddle_gpu-*.whl
```

If you don't have the wheel, see https://github.com/deahfst/Jetson_OCR for prebuilt wheels or build from source there.

4) Build the ROS2 workspace

```bash
source /opt/ros/<distro>/setup.bash
colcon build --cmake-target-skip-unavailable
source install/setup.bash
```

5) Run nodes or scripts

Examples:

```bash
# run arm node via ros2
ros2 run so_arm101_controller arm_node

# or run package main directly (python entry)
python3 src/so_arm101_controller/so_arm101_controller/main.py
```

Repository maintenance notes
----------------------------
- Large binaries: this repository contains wheel(s). `.gitattributes` now includes `*.whl` to be tracked by Git LFS. To enable LFS locally and move existing wheels into LFS:

```bash
sudo apt install git-lfs
git lfs install
git lfs track "*.whl"
git add .gitattributes
git rm --cached "*.whl"
git commit -m "Move wheel files to Git LFS"
git push
```

If wheels are already in the history and you need to remove them, consider `git lfs migrate import --include="*.whl"` — this rewrites history and must be used carefully (coordinate with collaborators).

CI
--
- A basic GitHub Actions workflow is included at `.github/workflows/ci.yml`. It runs on push/PR to `main`. It performs Python environment setup, optional dependency install, lint (flake8) and tests (pytest) if present. Recommended improvement: add a `colcon` build step that runs a workspace build inside CI for full validation.

Contributing
------------
- Add new ROS2 packages under `src/` following ROS2 packaging conventions.
- Avoid committing build output; keep `build/`, `install/`, `log/` in `.gitignore`.
- Use Git LFS for large binary artifacts.

Planned next steps
------------------
1. Harden CI to run `colcon build` and basic node integration tests.
2. Add unit/integration tests for `so_arm101_controller` nodes.
3. Decide whether to migrate large artifacts out of Git history (use `git lfs migrate` if needed).

License
-------
See the `LICENSE` file in this repository (MIT by default).

Contact
-------
If you need help deploying on Jetson hardware or tuning the OCR models, open an issue in this repository or in the Jetson_OCR repo: https://github.com/deahfst/Jetson_OCR
