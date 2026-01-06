from dotenv import load_dotenv
load_dotenv()
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain.tools import tool
import os
import requests
from langchain.messages import AIMessage,HumanMessage,ToolMessage,SystemMessage,RemoveMessage
from langchain_core.messages  import BaseMessage
from langchain.agents.middleware import before_model, after_model, wrap_model_call
import sys
from pathlib import Path
from langgraph.graph import START,END,StateGraph
from typing_extensions import TypedDict
from langgraph.runtime import Runtime
import json
from loguru import logger
script_path=Path(__file__).parent
sys.path.insert(0,str(script_path))
from tool_vl import tool_runtime,draw_wall,Name_romm,get_current_house_type_json,add_plan
from langchain.agents.middleware import ToolCallLimitMiddleware,TodoListMiddleware,SummarizationMiddleware,before_model,AgentState
from typing import Optional
from uuid import uuid4
from deepagents import create_deep_agent
from copy import deepcopy
from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
with open("json/json2解析.md","r",encoding='utf-8') as f:
    json_prompt=f.read()
with open("json/example1.json","r",encoding='utf-8') as f:
    house_type_json=f.read()
with open("json/example1_wall.json",'r',encoding='utf-8') as f:
    points=f.read()
with open("/app/AI_Design/AI_Design/户型.txt",'r',encoding='utf-8') as f:
    house_type_ascii=f.read()
REMOVE_ALL_MESSAGES = "__remove_all__"
model_doubao=ChatOpenAI(model=os.getenv("DOUBAO_MODEL_NAME_VL"),api_key=os.getenv("DOUBAO_API_KEY"),base_url=os.getenv("DOUABO_BASE_URL"))
model_minimax=ChatOpenAI(model=os.getenv("MINIMAX_MODEL"),base_url=os.getenv("MINIMAX_BASE_URL"),api_key=os.getenv("MINIMAX_API_KEY"))
model_aly=ChatOpenAI(model=os.getenv("aly_model_vl"),api_key=os.getenv("aly_api_key"),base_url=os.getenv("aly_base_url"))
model_gemini=ChatOpenAI(api_key=os.getenv("agicto_api_key"),base_url=os.getenv("agicto_base_url"),model=os.getenv("agicto_model"))
system_prompt=f"""你是一位房屋户型绘制设计助手,你需要根据用户的户型需求输出/编辑/修改户型json文件,
                   json文件可以导出为一张户型图,这是示例json文件:
                   {house_type_json}
                   这是json文件的解析:
                   {json_prompt}\n\n你只需要输出关于窗户/墙体/梁/柱/门的json部分数据,json中的窗户/墙体/梁/柱/门的数值属性的单位都是mm,
                   后续会对json做预处理得到完整的json文件的.现在你只需要编辑墙体的信息以及房间的信息,在绘制墙体形成一个封闭区域后,系统会自动
                   将其识别为一个房间并且输出json文件解析中的完整json,你只需要对该房间进行命名即可
                   ---注意---
                   3.设计墙体时一定要考虑到房间的封闭性以及墙体之间的连接性,并且不要出现墙体之间有重叠,墙体可以端点连接共线,或者交叉连接,但不能出现同方向的墙体是有重叠部分的情况.墙体的两个端点必须与其他墙体的端点或者内部点连接起来。
                   5.尽可能使用较少的墙体数量来绘制户型图,比如两个相邻的房间之间只需要绘制一条墙体共用即可,而不是绘制两条墙体,否则会系统很容易出现检测不到房间的情况
                   9.坐标点系统是往右x值变大,往下y值变大
                   11.一般客餐厅是房间封闭区域中面积最大的,而且卧室/厨房等都会与客餐厅直接相邻,卫生间一般与客餐厅/卧室相邻.请默认按照这个规则设计户型，除非用户明确提出不一样的户型设计需求
                   12.避免整体为规则矩形,设计应包含凹凸转折和非对称布局。整体轮廓呈L型或不规则多边形,拒绝单一矩形框架。禁止使用单一矩形作为外框,需有多个墙体转折形成复杂边界。
                   13.绘制墙体时最好在当前只专注于一个房间的墙体绘制,而不是同时绘制多个房间的墙体分散任务，要一步一步来
                   14.需要认真思考外围墙体的形状规则布局,多去参考示例户型json的外围墙体布局以及坐标点
                   15.外围墙体应该有超过10个拐折点,也就是说外围墙体至少需要有20个,不能仅仅只是一个很简单的不规则多边形.而且外围墙体尽量不要出现共线的情况,共线的墙体应该是一整个墙体
                   12.不要刻意得去设计外围墙体的复杂形状,比如刻意得营造外围拐折点。其实外围墙体的拐折点一般是由于这里有一个房间,所以在最外围的房间的外围墙体往往会有一些拐折点。
                   13.阳台也算是房间,应该由墙体连接形成封闭区域.
                   14.在初始绘制外围墙体时,不要着急去绘制外围墙体,而是仔细思考外围墙体的坐标点布局以及户型中每一个房间的位置布局,把这些先考虑好再来绘制户型
                   15.如果绘制墙体A时需要与另一个墙体B进行T形连接,那么墙体A的端点必须与墙体B的端点或者内部点连接起来,比如墙体B的端点坐标为(1000,0)与(6000,0),墙体的厚度是240mm,那么墙体A的T形连接的端点为(2000,b)时,b不能是120或者-120,而是0,否则无法被识别为T形连接
                   17.由于会话消息会做压缩处理，所以会给你整体的户型设计的规划任务列表以及当前正在执行的任务,每当你要绘制墙体的时候当会对应一个步骤的任务,命名一个房间都会对应一个完成的最新任务
                   19.绘制的墙体必须是水平/垂直的,不是歪斜的,并且墙体之间不能是靠得非常近有点重叠的
                   """

summary_prompt=f"""你是一位总结助手,用来总结户型设计绘制智能体与用户的会话内容，这是户型设计智能体的系统提示词:
{system_prompt}\n\n
由于输出以及返回的户型json占了大量的token数量,所以你需要对户型json方面的内容进行压缩,并且我会把你的总结替换成户型设计智能体的中间的消息。
以下是会话消息\n\n
 """
summary_agent=create_agent(model_doubao,system_prompt=summary_prompt)
class State(TypedDict):
    messages:list[BaseMessage]
    image_url:Optional[str]
    house_type_json:dict={}

def summary_func(messages):
    logger.info('进入总结函数')
    summary_result=summary_agent.invoke({'messages':messages})
    result=summary_result['messages'][-1].content
    logger.info(f'-------------总结------------\n{result}')
    return result
@after_model
def summary(state: AgentState, runtime: Runtime[tool_runtime]):
    messages=state["messages"]
    logger.info(f'消息的长度为{len(messages)}')
    if 'todos' in state:
        logger.info(state['todos'])
    if isinstance(messages[-1],AIMessage) and messages[-1].response_metadata['token_usage']['total_tokens']>20000:
        logger.info('消息长度超限')
        state['messages']=[*messages[:4],SystemMessage(content=f"消息会话省略部分.....\n这是任务规划列表:\n{runtime.context.plan}\n这是当前正在执行的任务:\n{runtime.context.current_task}\n这是已经完成的任务(有可能是当前执行的任务已经完成了):\n{runtime.context.completed_task}\n\n这是整体的布局设计方案:\n{runtime.context.design_state}\n"),messages[-1]]
        logger.info(f'总结结束')
        return {'messages':[RemoveMessage(id=REMOVE_ALL_MESSAGES),*state['messages']]}
    logger.info(f'总结结束')
    return state
agent=create_agent(model_gemini,system_prompt=system_prompt,tools=[draw_wall,Name_romm,get_current_house_type_json],debug=False,context_schema=tool_runtime,
                   middleware=[TodoListMiddleware()])
graph=StateGraph(State)
def chat(state:State):
    if "house_type_json" not in state:
        state['house_type_json']={"version": "1.0","unit": "mm","floorHeight": 2700,
  "wallHeight": 2700,"outerPoints":[],"wallList":[],"roomList":[],"doorList": [],
  "windowList": [],
  "beamList": [],
  "columnList": []}
    if "image_url" not in state:
        state['image_url']=None
    result=agent.invoke(state,
                        context=tool_runtime(house_type_json=state['house_type_json'],image_url=state['image_url']))
    return result

graph.add_node('chat',chat)
graph.add_edge(START,'chat')
graph.add_edge('chat',END)
graph_agent=graph.compile()