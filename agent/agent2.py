from __future__ import annotations

from typing import Any

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import AzureChatOpenAI

from config import AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, CHAT_DEPLOYMENT_NAME
from tools.experimental_bridge_tool import experimental_bridge_tool
from tools.ingredient_lookup_tool import ingredient_lookup_tool
from tools.pubchem_property_tool import pubchem_property_tool
from tools.rag_tools import search_formulation_docs
from tools.semantic_scholar_tool import semantic_scholar_search

SYSTEM_PROMPT = (
    "You are a professional assistant for the Rheology and stability Analyst . "
    "You support both advanced chemistry experts and non-technical users. "
    "Adapt your explanation level to the user: use precise technical language for experts and simple plain language for beginners. "
    "Never present yourself as ChatGPT, OpenAI platform, or a generic AI product. "
    "If asked who you are, say you are the website assistant for formulation, rheology, and stability guidance. "
    "Use available tools when a question depends on formulation data, ingredient properties, or evidence. "
    "When users ask what you can do or seem unsure, briefly explain which tools you can use and exactly what input they should provide (for example: ingredient name, formulation details, or evidence topic). "
    "Keep responses concise and practical: 3-6 bullets or under 140 words unless the user explicitly asks for detail. "
    "Prefer concrete actions and decision guidance over generic explanations. "
    "If evidence is weak, clearly say what is missing and ask one focused follow-up question. "
    "Do not invent numeric values, citations, or experimental outcomes."
)

TOOLS = [
    search_formulation_docs,
    ingredient_lookup_tool,
    pubchem_property_tool,
    experimental_bridge_tool,
    semantic_scholar_search,
]


def _agent2_llm() -> AzureChatOpenAI:
    return AzureChatOpenAI(
        azure_deployment=CHAT_DEPLOYMENT_NAME,
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_API_KEY,
        api_version="2024-12-01-preview",
        # Some Azure model deployments only accept the default temperature value.
        temperature=1,
    )


def create_agent2() -> AgentExecutor:
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            ("human", "{input}"),
            MessagesPlaceholder("agent_scratchpad"),
        ]
    )

    tool_agent = create_tool_calling_agent(_agent2_llm(), TOOLS, prompt)
    return AgentExecutor(
        agent=tool_agent,
        tools=TOOLS,
        verbose=False,
        return_intermediate_steps=True,
    )


def build_agent2_messages(
    user_message: str,
    history: list[dict[str, Any]] | None = None,
    context: str | None = None,
) -> list[BaseMessage]:
    messages: list[BaseMessage] = [SystemMessage(content=SYSTEM_PROMPT)]

    if context:
        messages.append(SystemMessage(content=f"Context for this conversation:\n{context.strip()}"))

    for item in history or []:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role", "")).strip().lower()
        text = str(item.get("text", "")).strip()
        if not text:
            continue

        if role == "assistant":
            messages.append(AIMessage(content=text))
        elif role == "user":
            messages.append(HumanMessage(content=text))

    messages.append(HumanMessage(content=user_message.strip()))
    return messages


def build_agent2_input(
    user_message: str,
    history: list[dict[str, Any]] | None = None,
    context: str | None = None,
) -> str:
    lines = []

    if context:
        lines.append("Context for this conversation:")
        lines.append(context.strip())
        lines.append("")

    lines.append("Conversation context:")

    for item in history or []:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role", "")).strip().lower()
        text = str(item.get("text", "")).strip()
        if role not in {"assistant", "user"} or not text:
            continue
        lines.append(f"- {role}: {text}")

    lines.append("Current user question:")
    lines.append(user_message.strip())
    lines.append(
        "Response constraints: keep it concise; if data-dependent, use tools and cite evidence source names briefly."
    )
    return "\n".join(lines)


def run_agent2_fallback(
    user_message: str,
    history: list[dict[str, Any]] | None = None,
    context: str | None = None,
) -> str:
    """Generate a concise reply without tools when tool execution fails."""
    llm = _agent2_llm()
    response = llm.invoke(build_agent2_messages(user_message, history, context))
    return str(getattr(response, "content", "")).strip()
