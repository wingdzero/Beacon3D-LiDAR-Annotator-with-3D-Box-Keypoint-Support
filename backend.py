import os
import glob
import json
import struct
import numpy as np
from fastapi import FastAPI, HTTPException, Body
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
from typing import List, Dict, Any

# Try importing Open3D, but provide a fallback or error if missing
try:
    import open3d as o3d
    HAS_OPEN3D = True
except ImportError:
    HAS_OPEN3D = False
    print("Warning: Open3D not found. PCD files might not load correctly.")

app = FastAPI()

# --- PyInstaller Resource Helper ---
import sys
import webbrowser
import threading
import time

def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# Allow CORS for development convenience
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SaveRequest(BaseModel):
    file_path: str
    boxes: List[Dict[str, Any]]
    points: List[Dict[str, Any]]
    export_format: str = "json" # json, kitti, nuscenes
    kitti_export_keypoints: bool = True # Feature toggle (Default ON for auto-detect)
    kitti_export_keypoints: bool = False # Feature toggle

@app.get("/api/files")
def list_files(dir_path: str):
    """Lists .bin or .pcd files in the directory."""
    if not os.path.exists(dir_path):
        raise HTTPException(status_code=404, detail="Directory not found")
    
    # Check for bin or pcd in root
    bin_files = sorted(glob.glob(os.path.join(dir_path, "*.bin")))
    pcd_files = sorted(glob.glob(os.path.join(dir_path, "*.pcd")))
    
    # If not found, try common subdirectories
    if not bin_files and not pcd_files:
        for sub in ['lidar', 'velodyne', 'pointcloud', 'data']:
            sub_path = os.path.join(dir_path, sub)
            if os.path.exists(sub_path):
                bin_files = sorted(glob.glob(os.path.join(sub_path, "*.bin")))
                pcd_files = sorted(glob.glob(os.path.join(sub_path, "*.pcd")))
                if bin_files or pcd_files:
                    break
    
    files = bin_files if bin_files else pcd_files
    file_type = "bin" if bin_files else ("pcd" if pcd_files else "unknown")
    
    # Determine annotation root for check
    # Assumes consistent structure
    dataset_root = dir_path
    dir_name = os.path.basename(dir_path)
    if dir_name.lower() in ['lidar', 'velodyne', 'pointcloud']:
        dataset_root = os.path.dirname(dir_path)
    
    result_files = []
    for f in files:
        base = os.path.splitext(os.path.basename(f))[0]
        
        # Check standard paths
        has_anno = False
        possible_jsons = [
            os.path.join(dataset_root, "label_json", base + ".json"),
            os.path.join(dir_path, "label_json", base + ".json"),
            os.path.join(dir_path, base + ".json")
        ]
        
        for p in possible_jsons:
            if os.path.exists(p):
                has_anno = True
                break

        result_files.append({
            "path": os.path.abspath(f),
            "name": os.path.basename(f),
            "has_annotation": has_anno
        })
        
    return {"type": file_type, "files": result_files}

@app.get("/api/pointcloud")
def get_pointcloud(file_path: str):
    """Returns binary point cloud data (N, 4) float32: x, y, z, intensity."""
    print(f"[Debug] 请求加载文件: {file_path}")
    
    # 去除可能的引号 (虽然理论上前端不应该传，但以防万一)
    file_path = file_path.strip('"').strip("'")
    
    if not os.path.exists(file_path):
        print(f"[Debug] 文件不存在: {file_path}")
        raise HTTPException(status_code=404, detail="File not found")
    
    ext = os.path.splitext(file_path)[1].lower()
    points_array = None

    try:
        if ext == ".bin":
            # 读取原始 float32 数据
            raw_data = np.fromfile(file_path, dtype=np.float32)
            print(f"[Debug] 原始数据大小: {raw_data.size} (float32 elements)")
            
            # 尝试适配不同的列数
            if raw_data.size % 4 == 0:
                # 标准 KITTI 格式 (x, y, z, intensity)
                points_array = raw_data.reshape(-1, 4)
                print(f"[Debug] 解析为 Nx4 格式, 点数: {points_array.shape[0]}")
                
            elif raw_data.size % 3 == 0:
                # 仅 XYZ 格式 -> 补充强度列
                xyz = raw_data.reshape(-1, 3)
                intensity = np.full((xyz.shape[0], 1), 0.5, dtype=np.float32)
                points_array = np.hstack((xyz, intensity))
                print(f"[Debug] 解析为 Nx3 格式并补充强度, 点数: {points_array.shape[0]}")
                
            elif raw_data.size % 5 == 0:
                # 包含额外信息的格式 -> 取前 4 列
                points_array = raw_data.reshape(-1, 5)[:, :4]
                print(f"[Debug] 解析为 Nx5 格式, 点数: {points_array.shape[0]}")
                
            else:
                print(f"[Debug] 数据不对齐: {raw_data.size} % 3/4/5 != 0")
                raise HTTPException(status_code=400, detail=f"无法解析 .bin 文件: 数据长度 {raw_data.size} 无法被 3, 4 或 5 整除")
            
        elif ext == ".pcd":
            if not HAS_OPEN3D:
                raise HTTPException(status_code=500, detail="Open3D not installed, cannot read PCD")
            
            pcd = o3d.io.read_point_cloud(file_path)
            # Open3D points are Nx3
            xyz = np.asarray(pcd.points)
            
            # Try to get intensity if available, otherwise 0
            # Open3D doesn't always expose intensity easily depending on version/file format
            # For simplicity, we'll try to use colors or just pad with 0.5
            # Some PCDs store intensity in colors[0] or separate fields.
            # Here we just send XYZ and a dummy intensity if simple read.
            
            # Advanced: Access raw tensors if needed, but basic XYZ is priority.
            intensity = np.zeros((xyz.shape[0], 1), dtype=np.float32)
            
            # Combine to Nx4
            points_array = np.hstack((xyz, intensity)).astype(np.float32)

        else:
            raise HTTPException(status_code=400, detail="Unsupported file format")
            
        if points_array is None:
             raise HTTPException(status_code=500, detail="Failed to load data")

        # Return as binary blob
        return Response(content=points_array.tobytes(), media_type="application/octet-stream")

    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/save")
def save_annotations(data: SaveRequest):
    """Saves annotations to structured directories based on export_format."""
    try:
        # Determine Dataset Root
        # Data path: /path/to/dataset/lidar/0001.bin OR /path/to/dataset/0001.bin
        point_cloud_path = os.path.abspath(data.file_path)
        point_cloud_dir = os.path.dirname(point_cloud_path)
        file_name = os.path.basename(point_cloud_path)
        base_name = os.path.splitext(file_name)[0]
        
        # Check if inside 'lidar' or 'velodyne' folder
        parent_dir = os.path.dirname(point_cloud_dir)
        dir_name = os.path.basename(point_cloud_dir)
        
        if dir_name.lower() in ['lidar', 'velodyne', 'pointcloud']:
            dataset_root = parent_dir
        else:
            # Flat structure, create folders inside current dir
            dataset_root = point_cloud_dir

        # Helper to ensure dir exists
        def ensure_dir(path):
            if not os.path.exists(path):
                os.makedirs(path)
            return path

        # 1. Always save JSON (Source of Truth)
        json_dir = ensure_dir(os.path.join(dataset_root, "label_json"))
        json_path = os.path.join(json_dir, base_name + ".json")
        
        output = {
            "file_path": data.file_path,
            "objects": data.boxes, 
            "points": data.points  
        }
        
        with open(json_path, "w") as f:
            json.dump(output, f, indent=4)
            
        saved_msg = "Saved JSON"

        # 2. Sync Extra Formats
        # Logic: If 'label_kitti' exists, we MUST update the txt file to keep it in sync.
        # Or if the user explicitly requested 'kitti' export.
        
        target_fmt = data.export_format
        kitti_dir = os.path.join(dataset_root, "label_kitti")
        
        if target_fmt == "kitti" or os.path.exists(kitti_dir):
            if not os.path.exists(kitti_dir):
                os.makedirs(kitti_dir)
                
            txt_path = os.path.join(kitti_dir, base_name + ".txt")
            
            # --- Extended Keypoint Logic (Switch + Auto-Detect) ---
            # Export ONLY if Switch is ON AND Points exist
            export_kps = data.kitti_export_keypoints and (len(data.points) > 0)
            
            points_map = {}
            max_kps_count = 0
            
            if export_kps:
                # 1. Build Index
                for p in data.points:
                    pid = p.get('parent_id')
                    if pid:
                        if pid not in points_map:
                            points_map[pid] = []
                        points_map[pid].append(p)
                
                # 2. Find Max Keypoints Count for Padding
                for b in data.boxes:
                    box_id = b.get('id')
                    if box_id in points_map:
                        count = len(points_map[box_id])
                        if count > max_kps_count:
                            max_kps_count = count

            with open(txt_path, "w") as f:
                for b in data.boxes:
                    cls = b.get('class_name', 'Car')
                    x = b['position']['x']
                    y = b['position']['y']
                    z = b['position']['z']
                    l = b['scale']['x'] # W -> Scale X (New Convention)
                    w = b['scale']['y'] # L -> Scale Y (New Convention)
                    h = b['scale']['z']
                    ry = b['rotation']['z']
                    
                    # KITTI: h w l x y z ry
                    line = f"{cls} 0.00 0 0.00 0 0 0 0 {h:.2f} {w:.2f} {l:.2f} {x:.2f} {y:.2f} {z:.2f} {ry:.2f}"
                    
                    # Append Keypoints if enabled
                    if export_kps and max_kps_count > 0:
                        box_id = b.get('id')
                        current_kps = points_map.get(box_id, [])
                        
                        # Write actual points
                        for kp in current_kps:
                            kx = kp['position']['x']
                            ky = kp['position']['y']
                            kz = kp['position']['z']
                            line += f" {kx:.3f} {ky:.3f} {kz:.3f}"
                        
                        # Pad with zeros
                        remaining = max_kps_count - len(current_kps)
                        for _ in range(remaining):
                            line += " 0.000 0.000 0.000"
                            
                    f.write(line + "\n")
            saved_msg += " + KITTI"

        if target_fmt == "nuscenes":
            # Just create dummy folder for now as requested
            nu_dir = ensure_dir(os.path.join(dataset_root, "label_nuscenes"))
            # NuScenes is usually a DB, not per-file. But we can dump per-file JSON.
            nu_path = os.path.join(nu_dir, base_name + ".json")
            with open(nu_path, "w") as f:
                json.dump(output, f, indent=4)
            saved_msg += " + NuScenes"

        return {"status": "success", "saved_to": saved_msg}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class LoadRequest(BaseModel):
    file_path: str

@app.post("/api/load_annotations")
def load_annotations(data: LoadRequest):
    """Loads annotations. Checks 'label_json' folder first, then adjacent file."""
    try:
        file_path = data.file_path
        point_cloud_dir = os.path.dirname(file_path)
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        
        # Check logic:
        # 1. dataset/label_json/name.json
        # 2. adjacent/name.json
        
        # Determine root
        parent_dir = os.path.dirname(point_cloud_dir)
        dir_name = os.path.basename(point_cloud_dir)
        
        possible_paths = []
        
        if dir_name.lower() in ['lidar', 'velodyne', 'pointcloud']:
            # Structured: root/label_json/
            possible_paths.append(os.path.join(parent_dir, "label_json", base_name + ".json"))
        else:
            # Flat: root/label_json/ (created inside)
            possible_paths.append(os.path.join(point_cloud_dir, "label_json", base_name + ".json"))
            
        # Adjacent fallback
        possible_paths.append(os.path.join(point_cloud_dir, base_name + ".json"))
        
        json_path = None
        for p in possible_paths:
            if os.path.exists(p):
                json_path = p
                break
        
        if not json_path:
            return {"found": False}
            
        with open(json_path, "r") as f:
            content = json.load(f)
            
        return {"found": True, "data": content}
    except Exception as e:
        print(f"Error reading json: {e}")
        return {"found": False}

class BatchConvertRequest(BaseModel):
    dir_path: str
    target_format: str

@app.post("/api/batch_convert")
def batch_convert(data: BatchConvertRequest):
    """Converts all existing JSON annotations to target format. Scans label_json first, then flat root."""
    try:
        # Determine roots
        scan_dir = data.dir_path
        dataset_root = scan_dir
        if os.path.basename(scan_dir).lower() in ['lidar', 'velodyne', 'pointcloud']:
            dataset_root = os.path.dirname(scan_dir)
            
        json_dir = os.path.join(dataset_root, "label_json")
        
        # 1. Identify Source Files
        source_files = []
        if os.path.exists(json_dir):
            source_files = glob.glob(os.path.join(json_dir, "*.json"))
        
        # Fallback: Scan root for flat JSONs if label_json is empty or missing
        if not source_files:
            # We suspect flat structure.
            # Scan scan_dir (lidar folder) or dataset_root?
            # Usually annotations are in dataset_root (if flat) or adjacent to bin (scan_dir).
            # Let's check adjacent to bin first.
            flat_files_scan = glob.glob(os.path.join(scan_dir, "*.json"))
            if not flat_files_scan and scan_dir != dataset_root:
                 flat_files_scan = glob.glob(os.path.join(dataset_root, "*.json"))
            
            source_files = flat_files_scan

        if not source_files:
             return {"status": "error", "message": "No JSON annotations found to convert."}

        # 2. Prepare Target Directory
        target_dir_name = f"label_{data.target_format}" # label_kitti
        target_dir = os.path.join(dataset_root, target_dir_name)
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
            
        # 3. Perform Conversion
        converted_count = 0
        for jf in source_files:
            try:
                with open(jf, "r") as f:
                    content = json.load(f)
                
                # Check structure
                if 'objects' not in content: continue 

                base_name = os.path.splitext(os.path.basename(jf))[0]
                
                if data.target_format == "kitti":
                    txt_path = os.path.join(target_dir, base_name + ".txt")
                    with open(txt_path, "w") as tf:
                        for b in content.get('objects', []):
                            cls = b.get('class_name', 'Car')
                            pos = b.get('position', {'x':0,'y':0,'z':0})
                            scl = b.get('scale', {'x':1,'y':1,'z':1})
                            rot = b.get('rotation', {'x':0,'y':0,'z':0})
                            # KITTI: type ... h w l x y z ry
                            # Mapping: h=scale.z, w=scale.y, l=scale.x (Standard mapping)
                            line = f"{cls} 0.00 0 0.00 0 0 0 0 {scl['z']:.2f} {scl['y']:.2f} {scl['x']:.2f} {pos['x']:.2f} {pos['y']:.2f} {pos['z']:.2f} {rot['z']:.2f}\n"
                            tf.write(line)
                    converted_count += 1
                
                # We could also Auto-Migrate the JSON to label_json here if we wanted.
                # But let's stick to conversion to avoid unexpected file moves.
                
            except Exception as e:
                print(f"Skipping corrupt file {jf}: {e}")
                
        return {"status": "success", "count": converted_count, "target_dir": target_dir}

    except Exception as e:
        print(f"Batch convert error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class DebugLogRequest(BaseModel):
    message: str

@app.post("/api/debug_log")
def debug_log(data: DebugLogRequest):
    """接收前端日志并在后端终端打印"""
    print(f"[Frontend Log] {data.message}")
    return {"status": "ok"}

# Mount static files (Frontend)
static_dir = get_resource_path("static")
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    
    # Auto Open Browser
    def open_browser():
        time.sleep(1.5) # Wait for server to start
        webbrowser.open("http://127.0.0.1:8000")
        
    threading.Thread(target=open_browser, daemon=True).start()

    # Use 0.0.0.0 to be accessible if needed, port 8000
    uvicorn.run(app, host="127.0.0.1", port=8000)
