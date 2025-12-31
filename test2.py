from ascii_renderer import draw_ascii_floorplan
with open('户型.txt','w',encoding='utf-8') as f:
    f.write(draw_ascii_floorplan('/app/AI_Design/AI_Design/json/example1.json'))