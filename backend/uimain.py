from langgraph.graph import StateGraph, START, END
# from langchain_community.chat_models import ChatOllama
from langchain_ollama import ChatOllama
from langgraph.graph.message import add_messages
from typing import TypedDict, Annotated
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import InMemorySaver
from rich import print as rprint
from datetime import datetime
import calendar
#--------------------------------------------------
from langchain.tools import tool
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from rich import print as rprint


checkpointr = InMemorySaver()

model = ChatOllama(model="qwen3:1.7b", temperature=0.9, streaming=True)
# model = ChatOllama(model="llama3.2", temperature=0.9, streaming=True)

@tool
def datetime_now() -> str:
    """Get the current date and time and day of the week."""
    now = datetime.now()
    
    day_name = calendar.day_name[now.weekday()]
    
    return f"{now.strftime('%Y-%m-%d %H:%M:%S')} ({day_name})"

@tool
def add(x: int, y: int) -> int:
    """Adds two numbers together."""
    return x + y

@tool

def weather(city: str):
    """Get Current Weather of city"""
    import requests
    try:
        url =f"https://wttr.in/{city}?format=%C+%t+%w"
        response = requests.get(url)
        return f"weather in {city}: {response.text}"
    
    except Exception as e:
        return f"Weather data not available"

@tool
def subtract(x: int, y: int) -> int:
    """Subtract the second number from the first."""
    return x - y

@tool
def multiply(x: int, y: int) -> int:
    """Multiplies two numbers."""
    return x * y

#--------------------------------------------------


@tool
def train_status(train_number: str, day: str = "today") -> str:
    """Get live train running status using train number and day (today/yesterday)."""
    
    options = Options()
    options.add_argument("--headless=new")

    driver = webdriver.Chrome(options=options)

    try:
        driver.get(f"https://www.railrestro.com/live-train-running-status/{train_number}?day={day}")
        wait = WebDriverWait(driver, 20)

        card = wait.until(
            EC.visibility_of_element_located((
                By.XPATH,
                "//div[contains(@class,'card-body') and contains(@class,'text-center')]"
            ))
        )

        strongs = card.find_elements(By.TAG_NAME, "strong")

        if len(strongs) >= 2:
            station = strongs[0].text
            updated = strongs[1].text
            return f"Train {train_number} is at {station}. Last updated: {updated}"
        else:
            return "Train data not found."

    except Exception as e:
        return f"Error: {str(e)}"

    finally:
        driver.quit()
        
@tool
def scrape_website(url: str) -> str:
    """Extract full text content from a website URL."""
    
    options = Options()
    options.add_argument("--headless=new")

    browser = webdriver.Chrome(options=options)

    try:
        browser.get(url)

        element = WebDriverWait(browser, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        text = element.text

        return text[:2000]   # ⚠️ IMPORTANT (limit tokens)

    except Exception as e:
        return f"Error: {str(e)}"

    finally:
        browser.quit()
#--------------------------------------------------

tools = [add, subtract, multiply, datetime_now, train_status, weather, scrape_website]

model_with_tools = model.bind_tools(tools)

class TestState(TypedDict):
    messages: Annotated[list, add_messages]
    scraped_content: str 
    
def chatbot(state: TestState):
    messages = [("system",
    """You are a helpful AI assistant named Bengali Baba (nickname: Baba).
    Your owner name is ashu
You studied from IIT Kharagpur.

Guidelines:
- Be concise, clear, and do not repeat sentences.
- Respond in English or Hinglish.

Tool Usage Rules:
- Use tools only when required.
- Available tools: add, subtract, multiply, datetime_now, train_status, weather, scrape_website.

Math:
- Solve step-by-step ONLY when needed.
- Always return the final answer clearly.

Train & Weather:
- Use respective tools when user asks for live data.

Web Scraping:
- If the user provides a URL → ALWAYS use scrape_website tool.
- If scraped_content is already available:
  → Answer strictly from it
  → DO NOT call scrape_website again
  - if user ask question after scraping then give answer form scraped data

Behavior:
- Prefer tool results over assumptions.
- If no tool is needed, answer normally.
- Keep responses short and informative.
""")] + state["messages"]
    
    response = model_with_tools.invoke(messages)
    return {"messages": [response]}
def route_tool(state: TestState):
    last_message = state["messages"][-1]
    
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tool_node"
        # return {"messages": [f"The answer is {tool_result}"]}
    return END

def save_scraped_data(state: TestState):
    last_message = state["messages"][-1]

    # Tool output comes here
    if hasattr(last_message, "content"):
        return {"scraped_content": last_message.content}

    return {}
    

graph = StateGraph(TestState)
graph.add_node("chatbot", chatbot)
graph.add_node("tool_node", ToolNode(tools))

graph.add_edge(START, "chatbot")
graph.add_conditional_edges("chatbot", route_tool)
graph.add_node("save_data", save_scraped_data)
# graph.add_edge("tool_node", "chatbot")
graph.add_edge("tool_node", "save_data")
graph.add_edge("save_data", "chatbot")
abc= graph.compile(checkpointer=checkpointr)

config ={"configurable": {"thread_id": "1"}, "max_tokens": 100 }

import streamlit as st

st.set_page_config(page_title="Baba AI", layout="wide")

st.title("🤖 small chatbot")
st.caption("Chat + Tools (Weather, Train, Scraper, Math)")

# ---------------- Session Memory ----------------
if "messages" not in st.session_state:
    st.session_state.messages = []

# ---------------- Show chat history ----------------
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ---------------- Input ----------------
user_input = st.chat_input("Ask anything...")

if user_input:
    # Save user message
    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.chat_message("user"):
        st.markdown(user_input)

    # Call LangGraph
    inputs = {"messages": [("user", user_input)]}

    response_text = ""

    with st.chat_message("assistant"):
        placeholder = st.empty()

        for chunk, metadata in abc.stream(inputs, config, stream_mode="messages"):
            if hasattr(chunk, "content"):
                response_text += chunk.content
                placeholder.markdown(response_text)

    # Save assistant message
    st.session_state.messages.append({
        "role": "assistant",
        "content": response_text
    })