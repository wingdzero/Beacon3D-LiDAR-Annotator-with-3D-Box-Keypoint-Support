import open3d as o3d
import numpy as np
import os
import sys

class PointCloudViewer:
    def __init__(self, bin_folder):
        self.bin_folder = bin_folder
        # 获取并排序所有bin文件
        self.files = sorted([f for f in os.listdir(bin_folder) if f.endswith('.bin')])
        
        if not self.files:
            print(f"错误: 在 {bin_folder} 中没有找到 .bin 文件")
            sys.exit(1)
            
        self.idx = 0
        self.n_files = len(self.files)
        print(f"找到 {self.n_files} 个文件。按 '→' (右键) 下一帧， '←' (左键) 上一帧， 'Q' 退出。")

        # 1. 初始化 Open3D 可视化窗口
        self.vis = o3d.visualization.VisualizerWithKeyCallback()
        self.vis.create_window(window_name="Bin Point Cloud Player (White BG)", width=1280, height=720)
        
        # 2. 设置渲染选项 (关键修改)
        opt = self.vis.get_render_option()
        # --- 修改背景颜色为白色 ---
        opt.background_color = np.asarray([1.0, 1.0, 1.0]) 
        # 设置点的大小
        opt.point_size = 2.0 
        # 可选：关闭光照，让颜色更纯粹
        opt.light_on = False 

        # 初始化点云对象
        self.pcd = o3d.geometry.PointCloud()
        self.update_pcd() # 加载第一帧
        self.vis.add_geometry(self.pcd)

        # 注册按键回调
        self.vis.register_key_callback(262, self.next_frame) # Right Arrow
        self.vis.register_key_callback(263, self.prev_frame) # Left Arrow
        
        # 启动
        self.vis.run()
        self.vis.destroy_window()

    def load_bin_file(self, file_path):
        """
        读取 bin 文件。
        假设格式为 [N, 4] -> x, y, z, intensity (float32)
        即使不需要强度，通常读取时也需要知道原始数据结构以便正确 reshape
        """
        try:
            scan = np.fromfile(file_path, dtype=np.float32)
            scan = scan.reshape((-1, 4)) 
            points = scan[:, :3] # XYZ
            # 我们这里不再需要 intensity
            return points
        except Exception as e:
            print(f"加载文件出错: {e}")
            return np.array([])

    def update_pcd(self):
        file_path = os.path.join(self.bin_folder, self.files[self.idx])
        filename = self.files[self.idx]
        
        points = self.load_bin_file(file_path)
        
        if len(points) == 0:
            return

        # 更新点坐标
        self.pcd.points = o3d.utility.Vector3dVector(points)
        
        # --- 关键修改：设置统一的点云颜色 ---
        num_points = len(points)
        # 创建一个全是 0 的数组 (N, 3)
        colors = np.zeros((num_points, 3))
        
        # 选项 A: 设置为深蓝色 (RGB: 0, 0, 0.5) -> 推荐，在白背景下更有立体感
        colors[:] = [0.0, 0.0, 0.5] 
        
        # 选项 B: 如果您想要纯黑色，取消下面这行的注释 (RGB: 0, 0, 0)
        # colors[:] = [0.0, 0.0, 0.0]

        self.pcd.colors = o3d.utility.Vector3dVector(colors)
        # ---------------------------------------
        
        print(f"[{self.idx+1}/{self.n_files}] 显示: {filename} (点数: {len(points)})")

    def next_frame(self, vis):
        if self.idx < self.n_files - 1:
            self.idx += 1
            self.update_pcd()
            vis.update_geometry(self.pcd)
            vis.poll_events()
            vis.update_renderer()
        else:
            print("已经是最后一帧")

    def prev_frame(self, vis):
        if self.idx > 0:
            self.idx -= 1
            self.update_pcd()
            vis.update_geometry(self.pcd)
            vis.poll_events()
            vis.update_renderer()
        else:
            print("已经是第一帧")

if __name__ == "__main__":
    # --- 请在这里修改您的 bin 文件夹路径 ---
    TARGET_FOLDER = "/home/zero/DATA/temp/test/"
    # TARGET_FOLDER = "/home/zero/DATA/temp/30251225/rosbag2_2025_12_25-11_15_30_db3_10_merged/lidar/livox__lidar_192_168_1_193/"

    if not os.path.exists(TARGET_FOLDER):
        print(f"路径不存在: {TARGET_FOLDER}")
        print("请在代码底部修改 TARGET_FOLDER 为您的实际路径")
    else:
        viewer = PointCloudViewer(TARGET_FOLDER)
