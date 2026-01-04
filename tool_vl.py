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
import subprocess
from typing import *
def get_time() ->str:
    now = datetime.now()
    return now.strftime("%H:%M:%S")

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
    plan:Optional[list[str]]=None
    design_state:Optional[str]=None
    current_task:Optional[str]=None
    completed_task:Optional[str]=None
@tool()
def add_plan(plan:list[str],design_state:str,runtime:ToolRuntime[tool_runtime]):
    """
    为当前的绘制户型的设计规划步骤任务以及规划整体的细节布局
    Args:
        plan (list[str]): 添加的设计计划
        design_state:str:整体的户型设计布局,尽量详细一些,尤其是对于外轮廓的设计以及房间的布局,一定要说清楚
    """
    runtime.context.plan=plan
    runtime.context.design_state=design_state
    logger.info(f"\n\n添加的设计计划为:{plan}\n\n添加的设计布局为:{design_state}\n\n")
    return f"规划成功"
@tool()
def get_current_house_type_json(runtime:ToolRuntime[tool_runtime]):
    """
    获取当前的户型json以及户型图片,当会话进行了总结而无法完整看到当前的户型json时,可以使用这个工具来获取当前的户型json
    Returns:
        当前的户型json
    """
    return ToolMessage(content=[{'type':'text','text':f'这是当前的户型json:\n{runtime.context.house_type_json}\n这是对应的户型图\n'},
                                {'type':'image','url':runtime.context.image_url}],tool_call_id=str(uuid4()))
@tool()
def Name_romm(names:list[str],completed_task:str,room_ids:list[str],runtime:ToolRuntime[tool_runtime]):
    """
    为房间命名
    Args:
        names (list[str]): 若干个要命名的房间的名称
        room_ids (list[str]): 若干个要命名房间的id
        completed_task (str): 命名完当前的房间后完成的最新任务
    Returns:
        返回的户型json中房间的数据信息
    """
    data_json:dict=runtime.context.house_type_json
    runtime.context.completed_task=completed_task
    room_list:list[dict]=data_json['roomList']
    for i,r in enumerate(room_list):
        if r['id'] in room_ids:
            room_list[i]['name']=names[room_ids.index(r['id'])]
    data_json['roomList']=room_list
    runtime.context.house_type_json=data_json
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
    with open('test.json','w',encoding='utf-8') as f:
        p=json.dumps(data_json,ensure_ascii=False,indent=4)
        f.write(p)
    return ToolMessage(content=[{'type':'text','text':f'这是更新后的房间信息:\n{room_list}\n,这是户型图'},{'type':'image','url':image_url}],
                       tool_call_id=str(uuid4()))

@tool()
def draw_wall(walls:list[Wall],task:str,delete_walls:list[str],runtime:ToolRuntime[tool_runtime]):
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
        task (str): 当前绘制墙体对应的任务
        delete_walls (list[str]): 需要删除的墙体id
    Returns:
        Tuple[dict,str]: 更新后处理后的户型json数据,处理报告
    """
    runtime.context.current_task=task
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
    data_json=complete_floor_plan(wall_list, [], [], [], [],data_json['roomList'])
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
    with open(now.replace('.json','.png'),'wb') as f:
        f.write(response.content)
    content=[{'type':'text','text':f"""这是更新后的户型json数据\n{data_json}\n,这是处理报告\n{reports}\n这是对应的户型图""",
              'type':"image",
              'url':image_url}]
    logger.info(f"消息的长度:{len(runtime.state['messages'])}")
    return ToolMessage(content=content,tool_call_id=str(uuid4()))