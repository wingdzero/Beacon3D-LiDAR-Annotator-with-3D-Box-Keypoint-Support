import os
import random
import struct

def create_dummy_data(output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Configuration
    num_points = 50000 # Increased from 5000
    
    points = []
    
    # Generate random points (Ground + Scatter)
    for _ in range(num_points):
        x = random.uniform(-30, 30)
        y = random.uniform(-30, 30)
        
        # Ground plane with slight noise
        if random.random() < 0.7:
            z = random.uniform(-2.1, -1.9)
            i = random.uniform(0.2, 0.5)
        else:
            # Objects / Noise
            z = random.uniform(-2, 3)
            i = random.uniform(0.5, 1.0)
            
        points.append((x, y, z, i))

    # Add a "car" (box) - Dense cluster
    for _ in range(2000):
        x = random.uniform(4, 8)
        y = random.uniform(-1.5, 1.5)
        z = random.uniform(-1.8, -0.5)
        i = 1.0
        points.append((x, y, z, i))

    # --- Save as .bin (KITTI format: float32 x, y, z, i) ---
    bin_file = os.path.join(output_dir, "test_dense.bin")
    with open(bin_file, "wb") as f:
        for p in points:
            f.write(struct.pack('ffff', p[0], p[1], p[2], p[3]))
    print(f"Created {bin_file}")

if __name__ == "__main__":
    create_dummy_data("sample_data")
