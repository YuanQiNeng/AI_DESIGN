from dotenv import load_dotenv
load_dotenv()
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain.tools import tool
import os
import requests
from langchain.messages import AIMessage,HumanMessage,ToolMessage,SystemMessage
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
from tool_text import look_house_type_image,draw_house_type,tool_runtime,draw_wall,Name_romm
from oss_service import upload_image_bytes_to_oss
from langgraph.config import get_stream_writer
from langchain.agents.middleware import AgentState
from langchain.agents.middleware import ToolCallLimitMiddleware,TodoListMiddleware
from typing import Optional
from uuid import uuid4
from deepagents import create_deep_agent
model_minimax=ChatOpenAI(model=os.getenv("MINIMAX_MODEL"),api_key=os.getenv("MINIMAX_API_KEY"),base_url=os.getenv("MINIMAX_BASE_URL"))
model_doubao=ChatOpenAI(model=os.getenv("DOUBAO_MODEL_NAME_VL"),api_key=os.getenv("DOUBAO_API_KEY"),base_url=os.getenv("DOUABO_BASE_URL"))
model_aly=ChatOpenAI(model=os.getenv("aly_model_vl"),api_key=os.getenv("aly_api_key"),base_url=os.getenv("aly_base_url"))
model_kimi=ChatOpenAI(model=os.getenv("DOUBAO_MODEL_NAME_TEXT"),api_key=os.getenv("DOUBAO_API_KEY"),base_url=os.getenv("DOUABO_BASE_URL"))
class State(TypedDict):
    messages:list[BaseMessage]
    image_url:Optional[str]
    house_type_json:dict={}
@after_model
def get_image(state:AgentState,runtime:Runtime[tool_runtime]):
    if isinstance(state['messages'][-1],ToolMessage):
        if state['messages'][-1].name=='look_house_type_image':
            pass
        elif state['messages'][-1].name=='draw_wall':
            runtime.context.house_type_json=json.loads(state['messages'][-1].content)
            response = requests.post(
        'http://localhost:3000/api/render',
        data=json.dumps(runtime.context.house_type_json).encode('utf-8'), # 确保编码正确
        headers={'Content-Type': 'application/json'}
    )
            object_name_on_oss=f"images/{str(uuid4())}.png"
            image_url=upload_image_bytes_to_oss(response.content, object_name_on_oss)
            runtime.context.image_url=image_url
    return state
with open("json/json2解析.md","r",encoding='utf-8') as f:
    json_prompt=f.read()
with open("json/example1.json","r",encoding='utf-8') as f:
    house_type_json=f.read()
with open("json/example1_wall.json",'r',encoding='utf-8') as f:
    points=f.read()
with open("/app/AI_Design/AI_Design/户型.txt",'r',encoding='utf-8') as f:
    house_type_ascii=f.read()
tool_limiter = ToolCallLimitMiddleware(
    tool_name="look_house_type_image",
    run_limit=10,
)
agent=create_agent(model_minimax,system_prompt=f"""你是一位房屋户型绘制设计助手,你需要根据用户的户型需求输出/编辑/修改户型json文件,
                   json文件可以导出为一张户型图,这是示例json文件:
                   {house_type_json}
                   这是户型图的ascii表示:
                   {house_type_ascii}
                   这是上面示例json的外围墙体的坐标点:
                   {points}
                   这是json文件的解析:
                   {json_prompt}\n\n你只需要输出关于窗户/墙体/梁/柱/门的json部分数据,json中的窗户/墙体/梁/柱/门的数值属性的单位都是mm,
                   后续会对json做预处理得到完整的json文件的.现在你只需要编辑墙体的信息以及房间的信息,在绘制墙体形成一个封闭区域后,系统会自动
                   将其识别为一个房间并且输出json文件解析中的完整json,你只需要对该房间进行命名即可
                   ---注意---
                   1.编辑墙体的信息一定要通过调用draw_wall工具,不能直接编写json文件.
                   3.设计墙体时一定要考虑到房间的封闭性以及墙体之间的连接性,并且不要出现墙体之间有重叠,墙体可以端点连接共线,或者交叉连接,但不能出现同方向的墙体是有重叠部分的情况.墙体的两个端点必须与其他墙体的端点或者内部点连接起来。
                   5.尽可能使用较少的墙体数量来绘制户型图,比如两个相邻的房间之间只需要绘制一条墙体共用即可,而不是绘制两条墙体,否则会系统很容易出现检测不到房间的情况
                   9.坐标点系统是往右x值变大,往下y值变大
                   11.一般客餐厅是房间封闭区域中面积最大的,而且卧室/厨房等都会与客餐厅直接相邻,卫生间一般与客餐厅/卧室相邻.请默认按照这个规则设计户型，除非用户明确提出不一样的户型设计需求
                   12.避免整体为规则矩形，设计应包含凹凸转折和非对称布局。整体轮廓呈L型或不规则多边形，拒绝单一矩形框架。禁止使用单一矩形作为外框，需有多个墙体转折形成复杂边界。
                   13.绘制墙体时最好在当前只专注于一个房间的墙体绘制,而不是同时绘制多个房间的墙体分散任务，要一步一步来
                   14.需要认真思考外围墙体的形状规则布局,多去参考示例户型json的外围墙体布局以及坐标点
                   15.外围墙体应该有超过10个拐折点,也就是说外围墙体至少需要有20个,不能仅仅只是一个很简单的不规则多边形.而且外围墙体尽量不要出现共线的情况,共线的墙体应该是一整个墙体
                   12.不要刻意得去设计外围墙体的复杂形状,比如刻意得营造外围拐折点。其实外围墙体的拐折点一般是由于这里有一个房间,所以在最外围的房间的外围墙体往往会有一些拐折点。
                   13.阳台也算是房间,应该由墙体连接形成封闭区域.
                   14.在初始绘制外围墙体时,不要着急去绘制外围墙体,而是仔细思考外围墙体的坐标点布局以及户型中每一个房间的位置布局,把这些先考虑好再来绘制户型
                   """,tools=[draw_wall,look_house_type_image,Name_romm],debug=False,context_schema=tool_runtime,middleware=[tool_limiter,TodoListMiddleware()])

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
ai_design=graph.compile()
if __name__=="__main__":
    agent1=graph.compile()
    from pprint import pprint
    response=None
    while True:
        user_input=input("请输入:")
        if response is None:
            response={'messages':[HumanMessage(content=user_input)],'house_type_json':{}}
        else:
            response['messages'].append(HumanMessage(content=user_input))
        if user_input=='exit':
            break
        response=agent1.invoke(response)
        pprint(response['messages'])