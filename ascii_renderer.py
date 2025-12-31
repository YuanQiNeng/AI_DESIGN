import json
import math

def get_char_width(char):
    # Simple heuristic: non-ASCII characters are usually wide (2 spaces)
    return 2 if ord(char) > 127 else 1

def get_string_width(s):
    return sum(get_char_width(c) for c in s)

def draw_ascii_floorplan(json_path, width=100):
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        return f"Error reading file: {e}"

    walls = data.get('wallList', [])
    rooms = data.get('roomList', [])
    
    if not walls:
        return "No walls found in JSON."

    # 1. Calculate Bounding Box
    all_x = []
    all_y = []
    
    for w in walls:
        all_x.extend([w['startPoint']['x'], w['endPoint']['x']])
        all_y.extend([w['startPoint']['y'], w['endPoint']['y']])
    
    if not all_x: return "No valid wall points."

    min_x, max_x = min(all_x), max(all_x)
    min_y, max_y = min(all_y), max(all_y)
    
    range_x = max_x - min_x
    range_y = max_y - min_y
    
    # Add some padding
    padding_x = range_x * 0.1
    padding_y = range_y * 0.1
    min_x -= padding_x
    max_x += padding_x
    min_y -= padding_y
    max_y += padding_y
    range_x = max_x - min_x
    range_y = max_y - min_y

    if range_x == 0 or range_y == 0:
        return "Invalid floorplan dimensions."

    # 2. Determine Canvas Size
    # Aspect ratio correction: char height is approx 2x char width
    aspect_ratio = range_y / range_x
    canvas_w = width
    canvas_h = int(width * aspect_ratio * 0.5) 
    if canvas_h < 15: canvas_h = 15

    # Use a list of lists for the grid
    grid = [[' ' for _ in range(canvas_w)] for _ in range(canvas_h)]

    def to_grid(x, y):
        gx = int((x - min_x) / range_x * (canvas_w - 1))
        gy = int((y - min_y) / range_y * (canvas_h - 1))
        return max(0, min(canvas_w-1, gx)), max(0, min(canvas_h-1, gy))

    def write_to_grid(gx, gy, text, overwrite=True):
        if not (0 <= gy < canvas_h): return
        
        # Calculate start position to center text
        text_width = get_string_width(text)
        start_x = gx - text_width // 2
        
        current_x = start_x
        for char in text:
            w = get_char_width(char)
            if 0 <= current_x < canvas_w:
                # Check if we are overwriting something important (like corners '+')
                # But we generally want text to be on top
                if not overwrite and grid[gy][current_x] != ' ':
                    pass 
                else:
                    grid[gy][current_x] = char
                    # If wide char, pad next space
                    if w > 1 and current_x + 1 < canvas_w:
                         grid[gy][current_x+1] = '' # Mark as placeholder
            current_x += w

    # 3. Draw Walls
    wall_legend = []
    
    for i, w in enumerate(walls):
        p1 = w['startPoint']
        p2 = w['endPoint']
        x0, y0 = to_grid(p1['x'], p1['y'])
        x1, y1 = to_grid(p2['x'], p2['y'])
        
        # Prepare Wall ID Label
        wall_short_id = f"w{i+1}"
        wall_legend.append(f"{wall_short_id}: {w.get('id', 'Unknown')}")

        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        
        line_points = []
        
        # Standard Bresenham
        curr_x, curr_y = x0, y0
        while True:
            line_points.append((curr_x, curr_y))
            if 0 <= curr_x < canvas_w and 0 <= curr_y < canvas_h:
                current_char = grid[curr_y][curr_x]
                
                # Draw wall char
                char = '-' if dx > dy else '|'
                if current_char != ' ' and current_char != char:
                    grid[curr_y][curr_x] = '+' # Junction
                else:
                    grid[curr_y][curr_x] = char

            if curr_x == x1 and curr_y == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                curr_x += sx
            if e2 < dx:
                err += dx
                curr_y += sy
        
        # Mark endpoints
        if 0 <= x0 < canvas_w and 0 <= y0 < canvas_h: grid[y0][x0] = '+'
        if 0 <= x1 < canvas_w and 0 <= y1 < canvas_h: grid[y1][x1] = '+'

        # Label Wall ID at midpoint
        if line_points:
            mid_idx = len(line_points) // 2
            mid_x, mid_y = line_points[mid_idx]
            # Simple collision avoidance: try not to overwrite '+'
            write_to_grid(mid_x, mid_y, wall_short_id)

    # 4. Label Rooms
    for i, room in enumerate(rooms):
        # Calculate centroid
        bbox = room.get('bbox')
        if bbox:
            cx = (bbox['min']['x'] + bbox['max']['x']) / 2
            cy = (bbox['min']['y'] + bbox['max']['y']) / 2
        else:
            pts = room.get('points', [])
            if not pts: continue
            cx = sum(p['x'] for p in pts) / len(pts)
            cy = sum(p['y'] for p in pts) / len(pts)
            
        gx, gy = to_grid(cx, cy)
        
        # Use Name or fallback
        name = room.get('name')
        if not name or name == "未命名":
            name = f"R{i+1}"
            
        write_to_grid(gx, gy, name)

    # 5. Render Output
    output = []
    output.append(f"Floor Plan Map ({canvas_w}x{canvas_h})")
    output.append("=" * canvas_w)
    
    for row in grid:
        # Reconstruct line handling wide chars placeholder ''
        line_str = ""
        for char in row:
            line_str += char
        output.append(line_str)
        
    output.append("=" * canvas_w)
    
    # Append Legends
    output.append("\n[Wall ID Legend]")
    # Group into columns
    col_width = 40
    num_cols = 2
    for i in range(0, len(wall_legend), num_cols):
        row_items = wall_legend[i:i+num_cols]
        print_row = "".join(item.ljust(col_width) for item in row_items)
        output.append(print_row)
        
    return "\n".join(output)

if __name__ == "__main__":
    path = "/app/AI_Design/AI_Design/json1/07:31:33.json"
    print(draw_ascii_floorplan(path))