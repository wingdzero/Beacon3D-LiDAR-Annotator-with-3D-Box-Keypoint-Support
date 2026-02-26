import os
import json
import math
import shutil

# --- 配置 ---
# 数据集根目录 (包含 label_json 的文件夹)
TARGET_DIR = "dataset_bin_output" 
# 备份目录名
BACKUP_DIR_NAME = "label_json_backup_x_axis"

def normalize_angle(angle):
    """将角度标准化到 [-pi, pi]"""
    while angle > math.pi:
        angle -= 2 * math.pi
    while angle < -math.pi:
        angle += 2 * math.pi
    return angle

def process_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            print(f"Skipping invalid JSON: {file_path}")
            return False

    is_modified = False
    
    if 'objects' in data:
        for obj in data['objects']:
            # 只处理 Box 类型 (通常只有 Box 有 scale/rotation 属性且需要转换)
            # 如果之前的代码里 Point 也有 scale，这里可能也需要注意，但通常 Point 是球体，scale 是均匀的，不受影响
            # 此时我们假设所有有 scale.x/y 的对象都需要转换
            
            if 'scale' in obj and 'x' in obj['scale'] and 'y' in obj['scale']:
                # 1. 交换长宽
                # Old: x=L, y=W
                # New: x=W, y=L
                old_len = obj['scale']['x']
                old_wid = obj['scale']['y']
                
                obj['scale']['x'] = old_wid
                obj['scale']['y'] = old_len
                is_modified = True

            if 'rotation' in obj and 'z' in obj['rotation']:
                # 2. 修正朝向
                # Old: 0度指向 +X
                # New: 0度指向 +Y
                # 为了让 +Y 旋转后指向原本 +X 的方向，需要 -90度 (-pi/2)
                old_yaw = obj['rotation']['z']
                new_yaw = old_yaw - (math.pi / 2)
                
                obj['rotation']['z'] = normalize_angle(new_yaw)
                is_modified = True

    if is_modified:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        return True
    return False

def main():
    # 寻找 label_json 目录
    label_dir = os.path.join(TARGET_DIR, "label_json")
    
    # 如果根目录下找不到，尝试在当前目录下找
    if not os.path.exists(label_dir):
        label_dir = "label_json"
    
    if not os.path.exists(label_dir):
        print(f"错误: 找不到标注目录 {label_dir}")
        print("请将脚本放在项目根目录运行，或者修改脚本中的 TARGET_DIR。")
        return

    # 创建备份
    parent_dir = os.path.dirname(label_dir)
    backup_dir = os.path.join(parent_dir, BACKUP_DIR_NAME)
    
    if not os.path.exists(backup_dir):
        print(f"正在创建备份: {backup_dir} ...")
        shutil.copytree(label_dir, backup_dir)
    else:
        print(f"备份目录已存在: {backup_dir}，跳过备份步骤。")

    # 遍历处理
    print(f"开始转换目录: {label_dir} ...")
    files = [f for f in os.listdir(label_dir) if f.endswith('.json')]
    count = 0
    
    for filename in files:
        file_path = os.path.join(label_dir, filename)
        if process_file(file_path):
            count += 1
            print(f"已转换: {filename}")
    
    print("-" * 30)
    print(f"转换完成! 共处理 {count} 个文件。")
    print(f"原始文件已备份至: {backup_dir}")
    print("现在您可以在新版软件中打开这些标注了。")

if __name__ == "__main__":
    main()
