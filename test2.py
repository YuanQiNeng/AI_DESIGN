from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from langchain.agents import create_agent
load_dotenv()
import os
from google import genai
from google.genai import types
from typing import Any
client = genai.Client(
    api_key=os.getenv("gemini_api_key"),
    )
 
# !export HTTPS_PROXY='https://api.modelverse.cn'
# os.environ["HTTPS_PROXY"]='https://api.modelverse.cn'
# os.environ["GOOGLE_API_KEY"]=os.getenv("gemini_api_key")
# os.environ["GEMINI_API_KEY"]=os.getenv("gemini_api_key")
from langchain_google_genai import GoogleGenerativeAI,ChatGoogleGenerativeAI
llm=ChatGoogleGenerativeAI(api_key=os.getenv("gemini_api_key"),model="gemini-3-flash-preview",base_url="https://api.modelverse.cn")
from langchain.agents import  create_agent
agent=create_agent(model=llm,tools=[])
from langchain_core.messages import HumanMessage
content=[{'type':'text','text':'描述下这张图片'},{'type':'image','url':"https://ai--design.oss-cn-hangzhou.aliyuncs.com/example1.png"}]
content={'messages':[HumanMessage(content=content)]}
# result=agent.invoke(content)
result=agent.invoke(content)
print(result)