from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import AzureChatOpenAI
from tools.rag_tools import search_formulation_docs
from tools.web_tools import web_search
from tools.ingredient_lookup_tool import ingredient_lookup_tool
from tools.pubchem_property_tool import pubchem_property_tool
from tools.rdkit_analysis_tool import rdkit_analysis_tool
from tools.semantic_scholar_tool import semantic_scholar_search
from tools.experimental_rheology_tool import experimental_rheology_tool
from tools.settling_analysis_tool import settling_analysis_tool
from tools.experimental_bridge_tool import experimental_bridge_tool
from config import AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, CHAT_DEPLOYMENT_NAME
from models.agent_models import AgentResponse
from agent.prompt import SYSTEM_PROMPT

TOOLS = [
    search_formulation_docs,
    web_search,
    ingredient_lookup_tool,
    pubchem_property_tool,
    rdkit_analysis_tool,
    semantic_scholar_search,
    experimental_rheology_tool,
    settling_analysis_tool,
    experimental_bridge_tool,
]


def create_agent():
    parser = PydanticOutputParser(pydantic_object=AgentResponse)

    llm = AzureChatOpenAI(
        azure_deployment=CHAT_DEPLOYMENT_NAME,
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_API_KEY,
        api_version="2024-12-01-preview",
        temperature=1,
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            ("human", "{input}"),
            MessagesPlaceholder("agent_scratchpad"),
        ]
    ).partial(format_instructions=parser.get_format_instructions())

    tool_calling_agent = create_tool_calling_agent(llm, TOOLS, prompt)
    executor = AgentExecutor(
        agent=tool_calling_agent,
        tools=TOOLS,
        verbose=False,
        return_intermediate_steps=True,
    )
    return executor, parser