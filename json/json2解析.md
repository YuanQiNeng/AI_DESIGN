# 户型数据 JSON 解析文档

本文档详细解释了户型导出 JSON 文件中各个字段的含义、数据类型及用途。该 JSON 结构旨在作为 2D 绘图前端与 3D 渲染引擎（如 UE5）之间的数据交换标准。

## 1. 根节点属性 (Root)

描述整个户型场景的基础全局信息。

| 字段名 | 类型 | 示例值 | 描述 |
| :--- | :--- | :--- | :--- |
| `version` | string | `"1.0"` | 数据格式的版本号，用于兼容性检查。 |
| `unit` | string | `"mm"` | 全局长度单位，默认为毫米。 |
| `floorHeight` | number | `2700` | 全局默认层高（房间高度）。 |
| `wallHeight` | number | `2700` | 全局默认墙体高度。 |
| `totalArea` | number | `0` | 户型总面积（通常是所有内部房间面积之和）。 |
| `centerPos` | object | `{x,y,z}` | 户型的几何中心点坐标，用于场景定位。 |
| `outerPoints` | array | `[[{x,y,z},....],...]` | 每一个户型整体外轮廓的点集序列（顺时针或逆时针）。 |

---

## 2. 墙体列表 (wallList)

定义所有的墙体段。墙体是构建户型的核心骨架。

| 字段名 | 类型 | 描述 |
| :--- | :--- | :--- |
| `id` | string | 墙体的唯一标识符 (如 `"wall_1"`)。 |
| `startPoint` | object | 墙体中心线的**起点**坐标 `{x, y, z}`。 |
| `endPoint` | object | 墙体中心线的**终点**坐标 `{x, y, z}`。 |
| `thickness` | number | 墙体厚度 (如 `240`)。 |
| `height` | number | 墙体高度。 |
| `wallNormal` | object | 墙体的法线向量 `{x, y, z}`。通常指向墙体的"外侧"或特定参考方向，用于纹理贴图和几何计算。 |
| `leftRight` | string | 标识墙体的方向性 (`"left"` 或 `"right"`)。结合法线使用，决定内外墙面材质或门窗开启方向的基准。 |
| `wallType` | string | 墙体类型。例如 `"solid"` (实心墙), `"partition"` (隔断), `"shear"` (剪力墙)。 |
| `material` | string | 材质资源 ID 或名称。 |

---

## 3. 房间列表 (roomList)

由闭合墙体围成的区域。

| 字段名 | 类型 | 描述 |
| :--- | :--- | :--- |
| `id` | string | 房间唯一标识符 (如 `"room_1"`)。 |
| `name` | string | 房间中文名称 (如 `"卧室"`). |
| `englishName` | string | 房间英文名称 (如 `"Bedroom"`). |
| `area` | number | 房间面积 (平方米)。 |
| `points` | array | 构成房间地面的多边形顶点数组 `[{x,y,z}...]`。通常是沿内墙线的轮廓点（顺时针或逆时针）。 |
| `wallIds` | array | 围成该房间的所有墙体 ID 列表 `["wall_1", "wall_2"...]`。 |
| `bbox` | object | 房间的轴对齐包围盒 (Bounding Box)。包含 `min: {x, y}` 和 `max: {x, y}`。 |

---

## 4. 门列表 (doorList)

附着在墙体上的门对象。

| 字段名 | 类型 | 描述 |
| :--- | :--- | :--- |
| `id` | string | 门唯一标识符。 |
| `type` | string | 门类型。如 `"OT_Door"` (单开门), `"OT_ParentChildDoor"` (子母门), `"OT_SlidingDoor"` (推拉门)。 |
| `pos` | object | 门在 3D 空间中的中心位置坐标 `{x, y, z}`。 |
| `direction` | object | 门的朝向向量。通常垂直于墙体法线或与墙体走向一致。 |
| `length` | number | 门的宽度 (门洞宽度)。 |
| `height` | number | 门的高度。 |
| `width` | number | 门框/门扇的厚度。 |
| `wallId` | string | 该门所在的墙体 ID。 |
| `side` | string | 门开启方向或相对于墙的侧边位置 (`"left"` / `"right"`)。 |

---

## 5. 窗列表 (windowList)

附着在墙体上的窗对象。

| 字段名 | 类型 | 描述 |
| :--- | :--- | :--- |
| `id` | string | 窗唯一标识符。 |
| `windowType` | string | 窗户类型。如 `"OT_Window"` (标准窗), `"OT_RectBayWindow"` (飘窗), `"OT_Ground_Window"` (落地窗)。 |
| `pos` | object | 窗在 3D 空间中的中心位置坐标。 |
| `direction` | object | 窗的朝向向量。 |
| `length` | number | 窗的宽度。 |
| `height` | number | 窗的高度。 |
| `width` | number | 窗框/窗体的厚度。 |
| `heightToFloor`| number | 离地高度 (窗台高度)。 |
| `wallId` | string | 该窗所在的墙体 ID。 |
| `side` | string | 相对于墙的侧边位置。 |

---

## 6. 梁列表 (beamList)

结构部件：横梁。

| 字段名 | 类型 | 描述 |
| :--- | :--- | :--- |
| `id` | string | 梁唯一标识符。 |
| `startPoint` | object | 梁的起点坐标。 |
| `endPoint` | object | 梁的终点坐标。 |
| `width` | number | 梁的宽度。 |
| `height` | number | 梁的高度 (截面高度)。 |
| `type` | string | 类型标识 (如 `"Beam"`). |
| `direction` | object | 梁的走向向量。 |

---

## 7. 柱列表 (columnList)

结构部件：柱子。

| 字段名 | 类型 | 描述 |
| :--- | :--- | :--- |
| `id` | string | 柱子唯一标识符。 |
| `type` | string | 类型标识 (如 `"Column"`). |
| `pos` | object | 柱子中心点坐标。 |
| `width` | number | 柱子宽度 (X方向尺寸)。 |
| `length` | number | 柱子长度 (Y方向尺寸)。 |
| `height` | number | 柱子高度。 |
