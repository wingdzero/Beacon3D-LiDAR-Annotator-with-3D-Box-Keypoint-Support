[**English**](./README.md) | [**中文**](./README_zh.md)

📄 [Project Structure & Technical Walkthrough](./docs/project_walkthrough_en.md)

# Beacon3D

**Web-based LiDAR 3D Box & Keypoint Annotation Tool**

Beacon3D is a lightweight, web-based annotation tool designed for LiDAR 3D point cloud data. Unlike most existing tools that only support bounding box annotation, Beacon3D natively supports **both 3D bounding boxes and keypoint annotation** — making it one of the few open-source tools with this capability.

**Why Beacon3D?**
- 🎯 **Box + Keypoint**: Annotate 3D boxes and associate keypoints in a single workflow — keypoints are auto-linked to parent boxes
- 🖥️ **Quad-View**: Main 3D view + Top/Side/Front orthographic views for precise annotation
- 🤖 **Smart Assist**: Auto-Fit (K) shrinks box to point cloud; Ground Snap (G) aligns to ground plane
- 📦 **KITTI + Keypoints Export**: Extends standard KITTI format with keypoint world coordinates
- ⚡ **Zero Setup**: Pure web app — just `pip install` and open browser, no GPU required
- 🔗 **Sequence Support**: Frame propagation, ghost overlay, and annotation progress tracking

## ✨ Core Features

*   **Professional Visualization**:
    *   **Quad-View**: Main 3D view + three orthogonal auxiliary views (Top / Side / Front).
    *   **Advanced Rendering**: Supports Height/Intensity coloring modes, ground filtering, and circular point cloud rendering.
    *   **Context Awareness**: Mouse hover highlighting (with bold borders), and real-time highlighting of points within the box.
*   **Intelligent Assistance**:
    *   **Auto-Fit (K)**: Automatically shrinks the box to fit the internal point cloud tightly (with configurable margins).
    *   **Ground Snap (G)**: Automatically snaps the bottom of the box to the ground plane.
    *   **Sequence Propagation**: One-click copy of the current frame's annotations to the next frame.
    *   **Ghost Display**: Displays a ghost of the previous frame's annotations to assist in trajectory tracking.
*   **Efficient Workflow**:
    *   **Strict Mode**: Independent Box / Point mode switching to prevent category mixing.
    *   **Category Management**: Custom categories and their default dimensions (L/W/H).
    *   **Auto-Association**: Points are automatically associated with the most recently operated box.
    *   **Axis Lock**: Locks Z-axis rotation to prevent box tilting.
    *   **Batch Conversion**: Supports batch conversion from JSON to KITTI format.
    *   **Data Integrity**: Automatically synchronizes multiple formats upon saving; the list displays annotation progress (green/gray dots).

## 🛠️ Installation Guide

### Prerequisites
*   **Python 3.8+**
*   **Modern Browser** (Chrome/Edge/Firefox)

### Steps

1.  **Clone or download** this repository.
2.  **Install Python dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
    *Core dependencies: `fastapi`, `uvicorn`, `numpy`, `open3d` (optional, for PCD support).*

3.  **Start the server**:
    ```bash
    python backend.py
    ```
    The server will start at `http://127.0.0.1:8000`.

## 📖 User Guide

### 1. Data Loading
*   Open `http://127.0.0.1:8000` in your browser.
*   In the top-left **"Data Directory"** input box, enter the absolute path to your dataset (e.g., `/home/user/data/kitti/2011_09_26/`).
    *   *Note: The tool automatically searches for subdirectories like `lidar`, `velodyne`, `pointcloud`.*
*   Click **"Load Directory"**.
*   **Progress Dots**:
    *   ⚪ Gray: Unannotated.
    *   🟢 Green: Annotated (JSON exists).

### 2. Basic Interaction
*   **Camera Controls**:
    *   **Left-click drag**: Rotate.
    *   **Middle / Right-click drag**: Pan (Middle click is recommended to avoid browser gesture conflicts).
    *   **Scroll wheel**: Zoom (supports very close observation).
*   **Tools**:
    *   **W (Box Mode)**: Switch to the Box category list and add boxes.
    *   **S (Point Mode)**: Switch to the Point category list and add points.
    *   **1 / 2 / 3**: Switch between **Translate / Rotate / Scale** modes.
    *   **Esc**: Deselect / Free-roam mode.
    *   **Del**: Delete selected object.
*   **Visualization Conventions**:
    *   **Green Box**: Annotated object.
    *   **Cyan Arrow**: Indicates the heading direction (Local +Y axis).
    *   **Green Axis (Gizmo)**: Represents straight ahead.

### 3. Smart Tools & Shortcuts
*   **G (Ground Snap)**: Select a box -> Press `G`. The box will automatically snap to the ground below.
*   **K (Auto-Fit)**: Select a box -> Press `K`. The box dimension will automatically shrink to fit the internal point cloud (+ margin).
*   **Propagate (>>>)**: Click the "Propagate to Next Frame" button to copy all current boxes to the next frame.
*   **M**: Show/hide category statistics histogram.
*   **? or /**: Show/hide shortcut cheat sheet.

### 4. Configuration & Export
*   **Category Management**:
    *   **Independent Box / Point Management**: Categories can be created and managed separately in the two modes.
    *   **Import/Export**: Save configurations as JSON files for reuse.
*   **Export Formats**:
    *   **KITTI with Keypoints**: 
        *   ✅ **On (Default)**: Auto-detected. If a box contains keypoints, the exported KITTI file will append keypoint coordinates (x y z ...) and realign.
        *   ⬜ **Off**: Force truncation. Only exports standard 15-column KITTI data, ignoring all keypoints.
    *   **Auto-Sync**: Automatically updates files under `label_json/` and `label_kitti/` upon saving.
    *   **Batch Conversion**: Batch conversion of the entire dataset is triggered when switching formats.

## 📂 Directory Structure (Auto-generated)

Upon saving, the tool automatically organizes data into the following structure:

```
Dataset_Root/
├── lidar/              # Original .bin/.pcd files
├── label_json/         # Standard annotations (Data source)
│   ├── 000001.json
│   └── ...
├── label_kitti/        # Auto-generated KITTI format .txt
│   ├── 000001.txt
│   └── ...
└── ...
```

## ⌨️ Shortcut Cheat Sheet

| Key            | Function                           |
| :------------- | :--------------------------------- |
| **W**          | Add Box                            |
| **S**          | Add Point                          |
| **1 / 2 / 3**  | Translate / Rotate / Scale         |
| **F**          | Focus on selected object           |
| **G**          | Ground Snap                        |
| **K**          | Auto-Fit sizes                     |
| **M**          | Show statistics                    |
| **? or /**     | Show help (press any key to close) |
| **Esc**        | Deselect                           |
| **Del**        | Delete                             |
| **Ctrl+C / V** | Copy / Paste                       |
| **Ctrl+S**     | Save                               |
| **A / D**      | Previous / Next Frame              |

## 🔧 Utility Scripts

Two utility Python scripts are provided in the project root directory for data migration and enhanced format export.

### `json_to_kitti_with_keypoints.py` (Enhanced Export)
**Function**: Converts JSON annotations to the extended **"KITTI + Keypoints"** format.
**Output Format**: 
`Type ... H W L X Y Z Ry [K1_x K1_y K1_z] [K2_x K2_y K2_z] ...`
*   First 15 columns: Standard KITTI 3D box format.
*   Subsequent columns: World coordinates of keypoints associated with the box.
**Usage**:
```bash
python json_to_kitti_with_keypoints.py
```
*Output Directory: `dataset_bin_output/label_kitti_keypoints`*

## 📜 License

This project is licensed under the [MIT License](./LICENSE).