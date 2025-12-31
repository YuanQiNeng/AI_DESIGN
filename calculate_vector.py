import math

def calculate_vectors(point_a, point_b):
    """
    计算两个点连线的单位方向向量和单位法线向量。
    
    Args:
        point_a (dict): {'x': float, 'y': float, 'z': float}
        point_b (dict): {'x': float, 'y': float, 'z': float}
        
    Returns:
        tuple: (unit_direction, unit_normal)
               两个元素都是 dict {'x', 'y', 'z'}
    """
    # 1. 计算连线向量 (Vector AB)
    vx = point_b['x'] - point_a['x']
    vy = point_b['y'] - point_a['y']
    vz = point_b['z'] - point_a['z']

    # 2. 计算连线的长度 (模)
    length = math.sqrt(vx**2 + vy**2 + vz**2)

    # 防止除以零（如果两点重合）
    if length == 0:
        return None, None

    # 3. 计算【单位方向向量】 (Unit Direction Vector)
    # 这是连线本身的方向，长度为1
    dir_x = vx / length
    dir_y = vy / length
    dir_z = vz / length
    unit_direction = {'x': dir_x, 'y': dir_y, 'z': dir_z}

    # 4. 计算【单位法线向量】 (Unit Normal Vector)
    # 注意：3D线段没有唯一法线。我们需要找一个"参考轴"来计算垂直向量。
    # 这里我们假设参考轴是 Z轴 (0, 0, 1)。
    # 如果连线本身就是 Z轴方向，我们改用 Y轴 (0, 1, 0) 以防叉积为0。
    
    if abs(dir_x) < 0.001 and abs(dir_y) < 0.001:
        ref_vector = (0, 1, 0) # 连线近似垂直，改用Y轴参考
    else:
        ref_vector = (0, 0, 1) # 默认使用Z轴参考

    # 叉积公式: a × b = (ay*bz - az*by, az*bx - ax*bz, ax*by - ay*bx)
    nx = dir_y * ref_vector[2] - dir_z * ref_vector[1]
    ny = dir_z * ref_vector[0] - dir_x * ref_vector[2]
    nz = dir_x * ref_vector[1] - dir_y * ref_vector[0]

    # 再次归一化法线（确保它是单位向量）
    n_length = math.sqrt(nx**2 + ny**2 + nz**2)
    
    if n_length == 0:
         # 这种情况极少发生，除非方向向量本身就是零向量(已处理)或者方向向量与参考向量完全平行(已处理)
         return unit_direction, {'x': 0, 'y': 0, 'z': 0} 

    normal_x = nx / n_length
    normal_y = ny / n_length
    normal_z = nz / n_length
    
    unit_normal = {'x': normal_x, 'y': normal_y, 'z': normal_z}

    return unit_normal

if __name__ == "__main__":
    # --- 测试 ---
    p1 = {'x': 0, 'y': 0, 'z': 0}
    p2 = {'x': 10, 'y': 0, 'z': 0} # 一条在X轴上的线

    direction, normal = calculate_vectors(p1, p2)

    print(f"点A: {p1}")
    print(f"点B: {p2}")
    print("-" * 20)
    print(f"1. 连线单位方向向量: {direction}")
    print(f"2. 计算出的单位法线: {normal}") 
