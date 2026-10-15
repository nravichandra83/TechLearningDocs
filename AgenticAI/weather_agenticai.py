import requests

from typing import TypedDict

from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage


# ---------------------------------------------------------
# 1. State
# ---------------------------------------------------------

class AgentState(TypedDict):
    messages: list


# ---------------------------------------------------------
# 2. Weather API Tool
# ---------------------------------------------------------

@tool
def get_weather(city: str) -> dict:
    """
    Get current weather information for a city.
    """

    url = "http://localhost:5000/api/weather"

    response = requests.get(
        url,
        params={"city": city},
        timeout=5
    )

    response.raise_for_status()

    return response.json()


# ---------------------------------------------------------
# 3. LLM
# ---------------------------------------------------------

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0
)

tools = [get_weather]

llm_with_tools = llm.bind_tools(tools)


# ---------------------------------------------------------
# 4. Orchestrator Node
# ---------------------------------------------------------

def orchestrator(state: AgentState):

    response = llm_with_tools.invoke(
        state["messages"]
    )

    return {
        "messages": [response]
    }


# ---------------------------------------------------------
# 5. Tool Node
# ---------------------------------------------------------

tool_node = ToolNode(tools)


# ---------------------------------------------------------
# 6. Routing Logic
# ---------------------------------------------------------

def route_after_orchestrator(state: AgentState):

    last_message = state["messages"][-1]

    # If LLM requested a tool
    if last_message.tool_calls:
        return "tools"

    # Otherwise we have final answer
    return END


# ---------------------------------------------------------
# 7. Build LangGraph
# ---------------------------------------------------------

graph = StateGraph(AgentState)

graph.add_node(
    "orchestrator",
    orchestrator
)

graph.add_node(
    "tools",
    tool_node
)

graph.add_edge(
    START,
    "orchestrator"
)

graph.add_conditional_edges(
    "orchestrator",
    route_after_orchestrator,
    {
        "tools": "tools",
        END: END
    }
)

graph.add_edge(
    "tools",
    "orchestrator"
)


app = graph.compile()


# ---------------------------------------------------------
# 8. Execute
# ---------------------------------------------------------

result = app.invoke({
    "messages": [
        HumanMessage(
            content="What is the weather in Bengaluru?"
        )
    ]
})


print(result["messages"][-1].content)