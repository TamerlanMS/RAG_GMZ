from __future__ import annotations

import re
from itertools import count
from typing import Annotated, Any, List, Optional, Sequence, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, BaseMessage, SystemMessage
from langchain_core.tools import BaseTool, tool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, StateGraph, add_messages
from langgraph.prebuilt import ToolNode

from src.common.llm_model import LLM
from src.common.Schemas.icecream_schemas import ItemOrder, Order
from src.common.vector_store import vector_store
from src.db.CRUD import get_product_price, get_products_by_name, get_product_price_by_name
from src.db.database import get_db
from src.settings.config import AGENT_PROMPT

load_dotenv()

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]

@tool  # type: ignore
def add(a: int, b: int) -> int:
    """Сложить два целых числа."""
    return a + b

@tool  # type: ignore
def check_phone_number(phone_number: str) -> Optional[str]:
    """
    Приводит номер к формату +7XXXXXXXXXX.
    Возвращает нормализованный номер или None.
    """
    cleaned = re.sub(r"[^\d+]", "", phone_number)
    if cleaned.startswith("+7"):
        number = cleaned[2:]
    elif cleaned.startswith("8"):
        number = cleaned[1:]
    else:
        return None
    if len(number) == 10 and number.isdigit():
        return f"+7{number}"
    return None

@tool  # type: ignore
def find_product_in_vector_store(product_name: str) -> Any:
    """
    Найти похожие товары: сначала БД по подстроке, если пусто — векторный поиск.
    """
    db_search_result = get_products_by_name(product_name)
    if not db_search_result:
        return vector_store.search(product_name)
    return db_search_result

@tool
def get_current_price(product_name: str):
    """
    Верни текущую цену товара по названию (поиск нечувствителен к регистру и неполному совпадению).
    Возвращает: {"name": "...", "external_id": "...", "price": ...} или None.
    """
    db = next(get_db())
    return get_product_price_by_name(db, product_name)

@tool(parse_docstring=True, args_schema=Order)  # type: ignore
def create_order(
    order_data: str,
    client_name: str,
    client_number: str,
    delivery_address: str,
    payment: str,
    items: List[ItemOrder],
) -> str:
    """
    Сформировать текст заказа.
    Требуются: Дата доставки, Имя клиента, Телефон, Адрес доставки, Способ оплаты, Список позиций.
    """
    total = 0.0
    lines: List[str] = []
    count = 1
    for it in items:
        line_total = float(it.quantity) * float(it.price)
        total += line_total
        lines.append(f"№{count}. {it.name} x{it.quantity} = {line_total:.2f}")
        count += 1

    lines_str = "\n".join(lines)
    date_str = order_data or "не указана"

    return (
        "Ваш заказ:\n"
        f"Дата доставки: {date_str}\n"
        f"Имя клиента: {client_name}\n"
        f"Номер клиента: {client_number}\n"
        f"Адрес доставки: {delivery_address}\n"
        f"Метод оплаты: {payment}\n\n"
        f"Товары:\n{lines_str}\n\n"
        f"Итого: {total:.2f}\n"
    )

tools: List[BaseTool] = [
    add,
    find_product_in_vector_store,
    get_current_price,
    check_phone_number,
    create_order,
]
tool_node = ToolNode(tools)
llm = LLM.bind_tools(tools)

def model_call(state: AgentState) -> AgentState:
    system_prompt = SystemMessage(content=AGENT_PROMPT)
    response = llm.invoke([system_prompt] + list(state["messages"]))
    return {"messages": [response]}

def should_continue(state: AgentState) -> str:
    last = state["messages"][-1]
    if isinstance(last, AIMessage) and last.tool_calls:
        return "continue"
    return "end"

graph = StateGraph(AgentState)
graph.add_node("agent", model_call)
graph.add_node("tools", tool_node)
graph.set_entry_point("agent")
graph.add_conditional_edges("agent", should_continue, {"continue": "tools", "end": END})
graph.add_edge("tools", "agent")

agent = graph.compile(checkpointer=InMemorySaver(), debug=True)
