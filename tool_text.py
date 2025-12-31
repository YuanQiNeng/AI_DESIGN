import sys
from pathlib import Path
script_path=Path(__file__).parent
sys.path.insert(0,str(script_path))
from calculate_vector import calculate_vectors
import requests
from langchain.tools import tool,ToolRuntime
from dotenv import load_dotenv
load_dotenv()
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langgraph.graph import StateGraph,START,END
from langchain.agents.structured_output import ToolStrategy
import os
from dataclasses import dataclass
from langgraph.config import get_stream_writer
from pydantic import BaseModel,Field
from typing import Literal
from loguru import logger
import  json
import time as Time
from copy import  deepcopy
from uuid import  uuid4
from langchain.messages import  ToolMessage,HumanMessage,AIMessage,SystemMessage
from oss_service import upload_image_bytes_to_oss
from export_house_type import complete_floor_plan
from process_json import process_house_json,format_report
from datetime import datetime
from langgraph.config import get_stream_writer
import subprocess
def get_time() ->str:
    now = datetime.now()
    return now.strftime("%H:%M:%S")
with open("json/json2解析.md",'r',encoding='utf-8') as f:
    json_state=f.read()
model=ChatOpenAI(model=os.getenv("DOUBAO_MODEL_NAME_VL"),api_key=os.getenv("DOUBAO_API_KEY"),base_url=os.getenv("DOUABO_BASE_URL"))
vl_agent=create_agent(model=model,system_prompt=f"""你是一位房屋户型设计智能辅助助手,你会收到当前绘制的户型图以及对应的json文件,你需要根据当前用户的户型设计需求以及当前的户型图以及对应的json,
给出户型json的修复优化建议,给出的建议需要有量化的表达，比如:id为"wall_a"的墙体的坐标应该....长度应该....\n,目前只需要对墙体进行绘制,这是户型json的解析\n\n{json_state} \n\n\n
----注意----
1.你只需要给出户型json的修复优化建即可,如果你认真分析后觉得它与用户的需求有矛盾有问题的话
2.户型需要符合常识,各个封闭房间的面积也应该是合理的,除非用户明确有要求,否则不应该出现卫生间比客餐厅的面积还大等墙体不合理的情况
3.房间卧室卫生间一般都是从客餐厅那里出发进去的,绘制的户型一定要考虑到这个卫生间/卧室/厨房等能不能从客餐厅那里直接到达
6.如果你觉得某一个房间面积比较大,某一个比较小,那么可以考虑仅仅只是将这两个房间的命名进行变动,而不是建议去直接修改房间组成的墙体,也就是对于户型的布局建议,
优先考虑对房间的命名进行变动或者互换而不是修改墙体。当然如果却是需要去修改墙体,也需要果断提出
7.不允许出现悬浮式或孤立的内嵌房间。
8.坐标点系统是往右x值变大,往下y值变大
9.一般客餐厅是房间封闭区域中面积最大的,而且卧室/厨房等都会与客餐厅直接相邻,卫生间一般与客餐厅/卧室相邻.请默认按照这个规则设计户型，除非用户明确提出不一样的户型设计需求
10.避免整体为规则矩形，设计应包含凹凸转折和非对称布局。整体轮廓呈L型或不规则多边形，拒绝单一矩形框架。禁止使用单一矩形作为外框，需有多个墙体转折形成复杂边界。
11.任何墙体必须至少两端连接其他墙体或边界，否则视为无效结构，应予以删除或者缩小长度。请确保最终户型图中所有墙体均参与围合封闭房间。""")
class pos(BaseModel):
    x:float=Field(description="x坐标")
    y:float=Field(description="y坐标")
    z:float=Field(description="z坐标")
class Wall(BaseModel):
    id:str=Field(description="墙体的id")
    startPoint:pos=Field(description="墙体的起始点")
    endPoint:pos=Field(description="墙体的终止点")
    thickness:float=Field(description="墙体的厚度,默认是240",default=240)
    height:float=Field(description="墙体的高度,默认是1000",default=2700)
    wallType:Literal['solid','partition']=Field(description="墙体的类型,默认是非承重墙",default="partition")
    material:Literal['',"钢架结构",'轻质砖','混凝土','红砖','木龙骨石膏板','轻钢龙骨石膏板','轻钢龙骨水泥板','硅钙板','钢筋混凝土']=Field(description="墙体的材料,默认是空字符串",default="")
@dataclass
class tool_runtime:
    image_url:str
    house_type_json:dict

@tool()
def Name_romm(names:list[str],room_ids:list[str],runtime:ToolRuntime[tool_runtime]):
    """
    为房间命名
    Args:
        names (list[str]): 若干个房间的名称
        room_ids (list[str]): 若干个房间的id
    Returns:
        返回的户型json中房间的数据信息
    """
    data_json:dict=runtime.context.house_type_json
    room_list:list[dict]=data_json['roomList']
    for i,r in enumerate(room_list):
        if r['id'] in room_ids:
            room_list[i]['name']=names[room_ids.index(r['id'])]
    data_json['roomList']=room_list
    runtime.context.house_type_json=data_json
    with open('test.json','w',encoding='utf-8') as f:
        p=json.dumps(data_json,ensure_ascii=False,indent=4)
        f.write(p)
    return room_list

@tool()
def draw_wall(walls:list[Wall],delete_walls:list[str],runtime:ToolRuntime[tool_runtime]):
    """绘制/更新/删除墙体,并且会把重叠多余的墙体进行合并实现户型json的后处理清洗
    Args:
        walls (list[dict]): 需要绘制/更新的墙体信息,dict的结构如下:
            "id":str 墙体的id,
            "startPoint":dict 墙体的起始点,是一个python字典,包含x,y,z三个键值对,分别表示起始点的x,y,z坐标,
            "endPoint":dict 墙体的终止点,是一个python字典,包含x,y,z三个键值对,分别表示终止点的x,y,z坐标,
            "thickness":float 墙体的厚度,默认是240,
            "height":float 墙体的高度,默认是1000,
            "wallType":str Literal['solid','partition']=Field(description="墙体的类型,默认是非承重墙",default="partition"),
            "material":str Literal['',"钢架结构",'轻质砖','混凝土','红砖','木龙骨石膏板','轻钢龙骨石膏板','轻钢龙骨水泥板','硅钙板','钢筋混凝土']=Field(description="墙体的材料,默认是空字符串",default=""),
        delete_wall (list[str]): 需要删除的墙体id
    Returns:
        Tuple[dict,str]: 更新后处理后的户型json数据,处理报告
    """
    data_json:dict=runtime.context.house_type_json
    wall_list:list[dict]=data_json['wallList']
    walls=[w.model_dump() for w in walls]
    for w in walls:
        ids=[i['id'] for i in wall_list]
        wall=w
        wall.update({"wallNormal":calculate_vectors(wall['startPoint'],wall['endPoint'])})
        wall.update({"leftRight":"left"})
        if wall['id'] in ids:
            wall_list[ids.index(wall['id'])]=wall
        else:
            wall_list.append(wall)
    for w in delete_walls:
        ids=[i['id'] for i in wall_list]
        if w in ids:
            wall_list.remove(wall_list[ids.index(w)])
    data_json.update({"wallList":wall_list})
    reports=''
    for _ in range(3):
        data_json, report = process_house_json(data_json)
        reports+=format_report(report)+'\n\n'
    path='/app/AI_Design/AI_Design/test1.json'
    now=f"/app/AI_Design/AI_Design/json1/{get_time()}.json"
    wall_list=data_json['wallList']
    data_json=complete_floor_plan(wall_list, [], [], [], [])
    Time.sleep(1.0)
    if not data_json:
        logger.error("调用API导出完整户型失败")
        subprocess.run(
           f'npx tsx scripts/generate_floorplan.ts -i {path} -o {now}',
           shell=True,
           cwd='/app/AI_Design/AI_Design/house_type'  # 指定工作目录
        )
        with open(now,'r',encoding='utf-8') as f:
            data_json=json.loads(f.read())
    runtime.context.house_type_json=data_json
    with open(now,'w',encoding='utf-8') as f:
        p=json.dumps(data_json,ensure_ascii=False,indent=4)
        f.write(p)
    response = requests.post(
        'http://localhost:3000/api/render',
        data=json.dumps(data_json,ensure_ascii=False).encode('utf-8'), # 确保编码正确
        headers={'Content-Type': 'application/json'}
    )
    Time.sleep(1.0)
    with open(now.replace('.json','.png'),'wb') as f:
        f.write(response.content)
    return data_json,reports
@tool()
def draw_house_type(wall_list, door_list, window_list, beam_list, column_list) ->dict:
    """输入户型图的信息
    Args:
        wall_list (list): List of wall objects.
        door_list (list): List of door objects.
        window_list (list): List of window objects.
        beam_list (list): List of beam objects.
        column_list (list): List of column objects.
        
    Returns:输出完整的户型json字符串
    """
    data_json=complete_floor_plan(wall_list, door_list, window_list, beam_list, column_list)
    with open('test.json','w',encoding='utf-8') as f:
        p=json.dumps(data_json,ensure_ascii=False,indent=4)
        f.write(p)
    return data_json

@tool()
def look_house_type_image(runtime:ToolRuntime[tool_runtime]) ->str:
    """把当前json对应的户型图片以及户型json给到多模态视觉理解模型，给出json优化建议。在调用look_house_type_image工具前,先对所有房间进行命名"""
    #检查房间是否都进行了命名
    data_json:dict=runtime.context.house_type_json
    room_list=data_json["roomList"]
    for room in room_list:
        if room['name']=='':
            with open(f'json/{get_time()}.json','w',encoding='utf-8') as f:
                p=json.dumps(data_json,ensure_ascii=False,indent=4)
                f.write(p)
            return "请把所有房间封闭区域进行命名"
    time=0
    while time<5:
        response = requests.post(
        'http://localhost:3000/api/render',
        data=json.dumps(data_json,ensure_ascii=False).encode('utf-8'), # 确保编码正确
        headers={'Content-Type': 'application/json'}
    )
        Time.sleep(1.0)
        time+=1
        if response.status_code==200:
            break
    object_name_on_oss=f"images/{str(uuid4())}.png"
    image_url=upload_image_bytes_to_oss(response.content, object_name_on_oss)
    runtime.context.image_url=image_url
    content=[{'type':"text",'text':f"这是当前的户型json\n{runtime.context.house_type_json}\n\n下面是对应的户型图"},
             {"type":"image",'url':runtime.context.image_url}]
    messages:list=deepcopy(runtime.state['messages'])
    input_messages=[]
    length=len(messages)
    for i in range(length):
        if isinstance(messages[i],HumanMessage):
            input_messages.append(messages[i])
        elif isinstance(messages[i],AIMessage):
            if not  messages[i].tool_calls:
                input_messages.append(messages[i])
    input_messages.append(SystemMessage(content="\n\n以上是用户与绘图agent的对话消息(省去了工具调用的消息).......\n\n"))
    input_messages.append(HumanMessage(content=content))
    response=vl_agent.invoke({'messages':input_messages})
    logger.info(f"多模态模型给出的建议:\n{response['messages'][-1].content}")
    return response['messages'][-1].content