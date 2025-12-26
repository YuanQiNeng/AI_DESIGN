"""
墙体预处理模块 - 处理户型JSON中的重叠墙体问题

功能：
1. 检测并合并共线重叠的墙体
2. 处理包含关系：删除被完全包含的子墙体
3. 处理部分重叠：合并两个重叠墙体为一个
4. 自动更新roomList中的墙体引用
5. 迭代处理直到无重叠
6. 生成规范的处理报告
"""

import json
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field, asdict


@dataclass
class Point:
    """2D点坐标"""
    x: float
    y: float

    def to_dict(self) -> dict:
        return {"x": round(self.x, 2), "y": round(self.y, 2)}


@dataclass
class Wall:
    """墙体数据类"""
    id: str
    start_point: Point
    end_point: Point
    thickness: float
    height: float
    wall_normal: Dict[str, float]
    left_right: str
    wall_type: str
    material: str

    @property
    def start_x(self) -> float:
        return self.start_point.x

    @property
    def start_y(self) -> float:
        return self.start_point.y

    @property
    def end_x(self) -> float:
        return self.end_point.x

    @property
    def end_y(self) -> float:
        return self.end_point.y

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "startPoint": self.start_point.to_dict(),
            "endPoint": self.end_point.to_dict(),
            "thickness": self.thickness,
            "height": self.height,
            "wallNormal": self.wall_normal,
            "leftRight": self.left_right,
            "wallType": self.wall_type,
            "material": self.material
        }

    def get_normalized_range(self) -> Tuple[float, float, str]:
        """获取规范化后的范围（确保min <= max）"""
        if abs(self.end_x - self.start_x) > abs(self.end_y - self.start_y):
            s, e = self.start_x, self.end_x
            return (s, e, 'x') if s <= e else (e, s, 'x')
        else:
            s, e = self.start_y, self.end_y
            return (s, e, 'y') if s <= e else (e, s, 'y')


def load_json(file_path: str) -> dict:
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(data: dict, file_path: str):
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def create_wall_from_dict(wall_dict: Dict) -> Wall:
    return Wall(
        id=wall_dict["id"],
        start_point=Point(wall_dict["startPoint"]["x"], wall_dict["startPoint"]["y"]),
        end_point=Point(wall_dict["endPoint"]["x"], wall_dict["endPoint"]["y"]),
        thickness=wall_dict["thickness"],
        height=wall_dict["height"],
        wall_normal=wall_dict["wallNormal"],
        left_right=wall_dict["leftRight"],
        wall_type=wall_dict["wallType"],
        material=wall_dict.get("material", "")
    )


def are_collinear(wall1: Wall, wall2: Wall, tolerance: float = 1.0) -> bool:
    """判断两个墙体是否共线"""
    dx1 = wall1.end_x - wall1.start_x
    dy1 = wall1.end_y - wall1.start_y
    dx2 = wall2.end_x - wall2.start_x
    dy2 = wall2.end_y - wall2.start_y

    cross_product = dx1 * dy2 - dy1 * dx2
    if abs(cross_product) > tolerance:
        return False

    if abs(dx1) > abs(dy1):
        expected_y = wall1.start_y
        if abs(wall2.start_y - expected_y) > tolerance:
            return False
    else:
        expected_x = wall1.start_x
        if abs(wall2.start_x - expected_x) > tolerance:
            return False

    return True


def get_overlap_info(wall1: Wall, wall2: Wall) -> Optional[Dict]:
    """获取两个共线墙体的重叠信息"""
    if not are_collinear(wall1, wall2):
        return None

    min1, max1, axis1 = wall1.get_normalized_range()
    min2, max2, axis2 = wall2.get_normalized_range()

    if axis1 != axis2:
        return None

    overlap_min = max(min1, min2)
    overlap_max = min(max1, max2)

    if overlap_min > overlap_max:
        return None

    result = {
        'has_overlap': True,
        'is_containment': False,
        'contained_id': None,
        'container_id': None,
        'is_partial': False,
        'overlap_range': (overlap_min, overlap_max),
        'merged_range': (min(min1, min2), max(max1, max2)),
        'axis': axis1
    }

    # 检查包含关系
    if min1 <= min2 and max1 >= max2:
        result['is_containment'] = True
        result['contained_id'] = wall2.id
        result['container_id'] = wall1.id
    elif min2 <= min1 and max2 >= max1:
        result['is_containment'] = True
        result['contained_id'] = wall1.id
        result['container_id'] = wall2.id
    else:
        result['is_partial'] = True

    return result


def merge_walls(wall1: Wall, wall2: Wall, merged_range: Tuple[float, float], axis: str, new_id: str) -> Wall:
    """合并两个部分重叠的墙体"""
    merged_min, merged_max = merged_range

    if axis == 'x':
        merged_start = Point(merged_min, wall1.start_y)
        merged_end = Point(merged_max, wall1.start_y)
    else:
        merged_start = Point(wall1.start_x, merged_min)
        merged_end = Point(wall1.start_x, merged_max)

    return Wall(
        id=new_id,
        start_point=merged_start,
        end_point=merged_end,
        thickness=wall1.thickness,
        height=wall1.height,
        wall_normal=wall1.wall_normal.copy(),
        left_right=wall1.left_right,
        wall_type=wall1.wall_type,
        material=wall1.material
    )


def process_overlapping_walls(walls: List[Wall], max_iterations: int = 10) -> Tuple[List[Wall], Dict[str, str]]:
    """
    迭代处理墙体列表中的重叠问题，直到没有重叠
    """
    wall_id_map: Dict[str, str] = {}  # 最终的ID映射
    iteration = 0

    while iteration < max_iterations:
        iteration += 1

        walls_to_remove: set = set()
        new_walls: List[Wall] = []
        iteration_changes = False
        processed_ids = set()

        n = len(walls)

        for i in range(n):
            if walls[i].id in processed_ids:
                continue

            current_wall = walls[i]
            processed_ids.add(current_wall.id)
            current_id = current_wall.id

            for j in range(i + 1, n):
                if walls[j].id in processed_ids:
                    continue

                other_wall = walls[j]

                overlap_info = get_overlap_info(current_wall, other_wall)

                if overlap_info is None:
                    continue

                iteration_changes = True

                if overlap_info['is_containment']:
                    contained_id = overlap_info['contained_id']

                    if contained_id == other_wall.id:
                        walls_to_remove.add(other_wall.id)
                        processed_ids.add(other_wall.id)
                        wall_id_map[other_wall.id] = current_id
                    else:
                        walls_to_remove.add(current_id)
                        processed_ids.add(current_id)
                        wall_id_map[current_id] = other_wall.id
                        current_id = other_wall.id
                        current_wall = other_wall
                else:
                    new_id = f"{current_id}_m"
                    walls_to_remove.add(current_id)
                    walls_to_remove.add(other_wall.id)
                    processed_ids.add(current_id)
                    processed_ids.add(other_wall.id)
                    wall_id_map[current_id] = new_id
                    wall_id_map[other_wall.id] = new_id

                    new_wall = merge_walls(
                        current_wall, other_wall,
                        overlap_info['merged_range'],
                        overlap_info['axis'],
                        new_id
                    )
                    new_walls.append(new_wall)
                    current_id = new_id
                    current_wall = new_wall

            if current_id not in walls_to_remove:
                new_walls.append(current_wall)

        if not iteration_changes:
            break

        remaining_walls = [w for w in walls if w.id not in walls_to_remove]
        walls = remaining_walls + new_walls

    # 规范化所有合并后的ID（使用原始ID作为最终ID）
    final_walls: List[Wall] = []
    final_ids = set()

    for wall in walls:
        if wall.id in wall_id_map:
            mapped_id = wall_id_map[wall.id]
            while mapped_id in wall_id_map:
                mapped_id = wall_id_map[mapped_id]

            if mapped_id.endswith('_m'):
                final_id = mapped_id[:-2]
            else:
                final_id = mapped_id

            wall.id = final_id

        if wall.id not in final_ids:
            final_walls.append(wall)
            final_ids.add(wall.id)

    return final_walls, wall_id_map


# ============ 处理报告相关数据结构 ============

@dataclass
class WallMergeDetail:
    """墙体合并详情"""
    source_wall_id: str  # 源墙体ID
    target_wall_id: str  # 目标墙体ID
    reason: str  # 合并原因
    overlap_range: str  # 重叠范围
    axis: str  # 重叠轴向


@dataclass
class WallRemovalDetail:
    """墙体删除详情"""
    removed_wall_id: str  # 被删除的墙体ID
    retained_wall_id: str  # 保留的墙体ID
    reason: str  # 删除原因
    overlap_range: str  # 重叠范围


@dataclass
class RoomUpdateDetail:
    """房间更新详情"""
    room_id: str  # 房间ID
    old_wall_ids: List[str]  # 更新前的墙体ID列表
    new_wall_ids: List[str]  # 更新后的墙体ID列表


@dataclass
class ProcessReport:
    """墙体处理报告"""
    total_walls_before: int = 0  # 处理前墙体总数
    total_walls_after: int = 0  # 处理后墙体总数
    walls_removed: int = 0  # 删除的墙体数量
    walls_merged: int = 0  # 合并的墙体数量
    merge_details: List[Dict] = field(default_factory=list)  # 合并详情
    removal_details: List[Dict] = field(default_factory=list)  # 删除详情
    room_updates: List[Dict] = field(default_factory=list)  # 房间更新详情

    def to_dict(self) -> dict:
        return asdict(self)


def update_room_wall_ids(room: Dict, wall_id_map: Dict[str, str]) -> bool:
    """更新房间的墙体ID引用"""
    wall_ids = room.get("wallIds", [])
    updated = False
    new_wall_ids = []

    for wall_id in wall_ids:
        # 递归查找最终ID
        current_id = wall_id
        while current_id in wall_id_map:
            current_id = wall_id_map[current_id]

        # 移除 _m 后缀
        if current_id.endswith('_m'):
            current_id = current_id[:-2]

        if current_id not in new_wall_ids:
            new_wall_ids.append(current_id)
            if current_id != wall_id:
                updated = True
        else:
            updated = True  # 有重复ID

    if updated:
        room["wallIds"] = new_wall_ids

    return updated


def process_house_json(input_json: dict) -> Tuple[dict, ProcessReport]:
    """
    处理户型JSON文件，合并重叠墙体

    Args:
        input_json: 输入的户型JSON数据

    Returns:
        Tuple[dict, ProcessReport]:
            - 处理后的户型JSON数据
            - 墙体处理报告
    """
    report = ProcessReport()

    data = input_json
    walls = [create_wall_from_dict(w) for w in data.get("wallList", [])]

    report.total_walls_before = len(walls)

    # 迭代处理
    processed_walls, wall_id_map = process_overlapping_walls(walls)

    report.total_walls_after = len(processed_walls)

    # 更新数据
    data["wallList"] = [w.to_dict() for w in processed_walls]

    # 处理房间更新并记录详情
    room_updates = []
    for room in data.get("roomList", []):
        old_ids = room.get("wallIds", [])[:]  # 复制原始列表
        updated = update_room_wall_ids(room, wall_id_map)
        new_ids = room.get("wallIds", [])
        if updated and old_ids != new_ids:
            room_updates.append({
                "room_id": room.get("id", ""),
                "room_name": room.get("name", ""),
                "old_wall_ids": old_ids,
                "new_wall_ids": new_ids
            })
    report.room_updates = room_updates

    # 分析处理详情
    # 根据wall_id_map生成合并和删除详情
    merged_sources = set()  # 记录哪些墙体是作为合并源被处理的

    for old_id, new_id in wall_id_map.items():
        # 跳过临时ID
        if '_m' in new_id:
            merged_sources.add(old_id)

    # 统计删除数量
    report.walls_removed = len([w for w in wall_id_map.values() if w not in merged_sources])

    # 统计合并数量（部分重叠产生的合并）
    report.walls_merged = len([w for w in wall_id_map.values() if '_m' in w])

    # 生成合并详情和删除详情
    merge_details = []
    removal_details = []

    for old_id, new_id in wall_id_map.items():
        if '_m' in new_id:
            # 合并操作 - 跳过作为合并基准的墙体（它没有被合并到其他墙体）
            target_id = new_id.replace('_m', '')
            if old_id != target_id:
                merge_details.append({
                    "source_wall_id": old_id,
                    "target_wall_id": target_id,
                    "reason": "墙体部分重叠，合并为单一连续墙体",
                    "overlap_range": "区间重叠",
                    "axis": "共线轴向"
                })
        else:
            # 删除操作（被包含）
            removal_details.append({
                "removed_wall_id": old_id,
                "retained_wall_id": new_id,
                "reason": "墙体被另一墙体完全包含，已合并至外层墙体",
                "overlap_range": "完全包含"
            })

    report.merge_details = merge_details
    report.removal_details = removal_details

    return data, report


def format_report(report: ProcessReport) -> str:
    """
    格式化处理报告为规范字符串

    Args:
        report: 墙体处理报告

    Returns:
        格式化的报告字符串
    """
    lines = []
    lines.append("=" * 60)
    lines.append("墙体处理报告")
    lines.append("=" * 60)

    # 统计概要
    lines.append("\n【处理概要】")
    lines.append(f"  处理前墙体总数: {report.total_walls_before}")
    lines.append(f"  处理后墙体总数: {report.total_walls_after}")
    lines.append(f"  删除墙体数量: {report.walls_removed}")
    lines.append(f"  合并墙体数量: {report.walls_merged}")
    lines.append(f"  净减少墙体数: {report.total_walls_before - report.total_walls_after}")

    # 删除详情
    if report.removal_details:
        lines.append("\n【删除详情】")
        for i, detail in enumerate(report.removal_details, 1):
            lines.append(f"  {i}. 墙体 {detail['removed_wall_id']} 已删除")
            lines.append(f"     保留墙体: {detail['retained_wall_id']}")
            lines.append(f"     删除原因: {detail['reason']}")

    # 合并详情
    if report.merge_details:
        lines.append("\n【合并详情】")
        for i, detail in enumerate(report.merge_details, 1):
            lines.append(f"  {i}. 墙体 {detail['source_wall_id']} 已合并至 {detail['target_wall_id']}")
            lines.append(f"     合并原因: {detail['reason']}")

    # 房间更新
    if report.room_updates:
        lines.append("\n【房间墙体引用更新】")
        for update in report.room_updates:
            lines.append(f"  房间 [{update['room_id']}] {update['room_name']}:")
            changed = []
            old_set = set(update['old_wall_ids'])
            new_set = set(update['new_wall_ids'])
            removed = old_set - new_set
            added = new_set - old_set
            if removed:
                lines.append(f"    移除: {list(removed)}")
            if added:
                lines.append(f"    新增: {list(added)}")

    lines.append("\n" + "=" * 60)
    return "\n".join(lines)


def analyze_overlaps(walls: List[Wall]) -> List[Dict]:
    """分析墙体之间的重叠情况"""
    overlaps = []

    for i in range(len(walls)):
        for j in range(i + 1, len(walls)):
            wall1, wall2 = walls[i], walls[j]

            overlap_info = get_overlap_info(wall1, wall2)

            if overlap_info is None or not overlap_info['has_overlap']:
                continue

            min1, max1, _ = wall1.get_normalized_range()
            min2, max2, _ = wall2.get_normalized_range()

            if overlap_info['is_containment']:
                relationship = f"{overlap_info['container_id']} 包含 {overlap_info['contained_id']}"
            else:
                relationship = "部分重叠"

            overlaps.append({
                "wall1": {"id": wall1.id, "range": f"[{min1:.0f}, {max1:.0f}]"},
                "wall2": {"id": wall2.id, "range": f"[{min2:.0f}, {max2:.0f}]"},
                "overlap_range": f"[{overlap_info['overlap_range'][0]:.0f}, {overlap_info['overlap_range'][1]:.0f}]",
                "relationship": relationship
            })

    return overlaps


if __name__ == "__main__":
    import sys

    input_file = "/app/AI_Design/test.json"
    if len(sys.argv) > 1:
        input_file = sys.argv[1]

    print("=" * 60)
    print("户型JSON墙体预处理工具")
    print("=" * 60)

    # 分析
    print("\n【重叠分析】")
    data = load_json(input_file)
    walls = [create_wall_from_dict(w) for w in data.get("wallList", [])]
    overlaps = analyze_overlaps(walls)

    if overlaps:
        print(f"发现 {len(overlaps)} 对重叠墙体:")
        for o in overlaps:
            print(f"  {o['wall1']['id']} ({o['wall1']['range']})")
            print(f"  {o['wall2']['id']} ({o['wall2']['range']})")
            print(f"  重叠范围: {o['overlap_range']}, 关系: {o['relationship']}")
            print()
    else:
        print("未发现重叠墙体")

    # 处理
    print("=" * 60)
    print("【开始处理】")
    wall_id_map = process_house_json(input_file)
