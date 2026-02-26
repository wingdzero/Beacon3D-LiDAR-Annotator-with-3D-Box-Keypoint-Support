import os
import json
import math

# --- 配置 ---
INPUT_DIR = "dataset_bin_output/label_json"
OUTPUT_DIR = "dataset_bin_output/label_kitti_keypoints"

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def main():
    # 检查输入目录
    if not os.path.exists(INPUT_DIR):
        print(f"错误: 找不到输入目录 {INPUT_DIR}")
        return

    ensure_dir(OUTPUT_DIR)
    
    files = [f for f in os.listdir(INPUT_DIR) if f.endswith('.json')]
    print(f"找到 {len(files)} 个标注文件，准备转换...")

    for filename in files:
        file_path = os.path.join(INPUT_DIR, filename)
        
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                print(f"跳过损坏文件: {filename}")
                continue

        # 1. 建立点索引: Parent ID -> Point List
        # 这样我们可以快速找到属于某个框的所有关键点
        points_map = {}
        all_points = data.get('points', [])
        
        # 为了保证点序一致（例如前左轮、前右轮），我们需要依赖 JSON 里的列表顺序
        # 或者是 points 里的 id 排序？通常 JSON 列表顺序即为创建顺序/定义顺序
        for p in all_points:
            pid = p.get('parent_id')
            if pid:
                if pid not in points_map:
                    points_map[pid] = []
                points_map[pid].append(p)

        # 2. 遍历 Box 并生成 KITTI 行
        txt_content = []
        objects = data.get('objects', [])
        
        for box in objects:
            # --- 基础字段 ---
            cls = box.get('class_name', 'Car')
            truncated = 0.0
            occluded = 0
            alpha = 0.0
            
            # 2D BBox (雷达标注通常没有，填 0)
            bbox = [0.0, 0.0, 0.0, 0.0]
            
            # 3D 尺寸 & 坐标 & 旋转
            # 注意：基于最新修改，Green(+Y) 是正前方
            # 宽(W) = Scale X
            # 长(L) = Scale Y
            # 高(H) = Scale Z
            # KITTI 标准顺序: h, w, l, x, y, z, ry
            
            h = box['scale']['z']
            w = box['scale']['x']
            l = box['scale']['y']
            
            x = box['position']['x']
            y = box['position']['y']
            z = box['position']['z']
            
            # 旋转 (Z轴旋转)
            ry = box['rotation']['z']

            # 构造标准 KITTI 字符串
            line = f"{cls} {truncated:.2f} {occluded} {alpha:.2f} " \
                   f"{bbox[0]:.2f} {bbox[1]:.2f} {bbox[2]:.2f} {bbox[3]:.2f} " \
                   f"{h:.2f} {w:.2f} {l:.2f} {x:.2f} {y:.2f} {z:.2f} {ry:.2f}"

            # --- 3. 追加关键点 (Like YOLO Keypoints) ---
            # 格式: x1 y1 z1 x2 y2 z2 ...
            # 注意：这里使用的是【世界坐标】
            
            box_id = box.get('id')
            if box_id in points_map:
                keypoints = points_map[box_id]
                # 按照 id 排序可能更稳定？或者直接信赖列表顺序？
                # 这里假设用户按顺序点的，或者 config 生成的顺序
                for kp in keypoints:
                    kp_x = kp['position']['x']
                    kp_y = kp['position']['y']
                    kp_z = kp['position']['z']
                    # 追加到行尾
                    line += f" {kp_x:.3f} {kp_y:.3f} {kp_z:.3f}"
            
            txt_content.append(line)

        # 3. 写入 TXT
        out_filename = filename.replace('.json', '.txt')
        out_path = os.path.join(OUTPUT_DIR, out_filename)
        
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(txt_content))

    print("-" * 30)
    print(f"转换完成！输出目录: {OUTPUT_DIR}")
    print("格式说明: 标准KITTI(15列) + 关键点世界坐标(x y z x y z ...)")

if __name__ == "__main__":
    main()
