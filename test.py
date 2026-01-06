import sys
from pathlib import Path
from main_vl import agent
from tool_vl import tool_runtime
import json
import traceback
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_core.messages import HumanMessage,SystemMessage
with open("json/example1.json",'r',encoding='utf-8') as f:
    data_json=json.loads(f.read())

with open("json/example1.json","r",encoding='utf-8') as f:
    house_type_json=f.read()
system_message=HumanMessage(content=[{'type':"text",'text':"这是示例的户型json对应的户型图"},{'type':'image','url':"https://ai--design.oss-cn-hangzhou.aliyuncs.com/example1.png"}])
result=agent.invoke({'messages':[system_message,HumanMessage(content="我想设计一个户型,包含一个主卧,一个次卧,一个客厅,一个阳台,一个厨房,主卧包含卫生间与阳台,客厅也有一个阳台与卫生间.设计的户型面积应该大一些,一道墙体至少有4500mm")]},
                        context=tool_runtime(image_url=None,house_type_json={"version": "1.0","unit": "mm","floorHeight": 2700,
      "wallHeight": 2700,"outerPoints":[],"wallList":[],"roomList":[],"doorList": [],
      "windowList": [],
      "beamList": [],
      "columnList": []}),config={"configurable": {"thread_id": "3"}},plan=[])