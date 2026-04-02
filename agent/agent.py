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
from config import AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, CHAT_DEPLOYMENT_NAME
from models.agent_models import AgentResponse

TOOLS = [
    search_formulation_docs,
    web_search,
    ingredient_lookup_tool,
    pubchem_property_tool,
    rdkit_analysis_tool,
    semantic_scholar_search,
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
            (
                "system", """
                You are a cosmetic formulation rheology and stability assessment agent.

                Primary mission:
                Assess physical stability and rheology risk for the provided structured cosmetic formula.

                Input contract:
                The user input contains validated structured formula JSON (ingredients with wt%, phase, process conditions, target pH, packaging, and storage conditions).
                Use this formula as the primary source of truth.

                Tool policy:
                1) Start with search_formulation_docs for domain evidence.
                2) Use ingredient_lookup_tool, pubchem_property_tool, and rdkit_analysis_tool for ingredient-level and chemistry support.
                3) Use semantic_scholar_search for scientific evidence when internal evidence is weak or incomplete.
                4) Use web_search only as last resort.
                     5) For non-trivial formulas (more than 5 ingredients), do not stop after a single tool call.
                         Minimum coverage target: use search_formulation_docs plus at least one ingredient-level tool,
                         and at least one chemistry/literature tool when risk depends on chemistry behavior.

                Reasoning policy:
                - Focus on probable failure modes: phase separation, viscosity drift, syneresis, creaming/sedimentation, and process sensitivity.
                - Tie claims to evidence; avoid unsupported speculation.
                - If confidence is limited, explicitly state uncertainty and the minimum additional data/tests needed.
                - Keep conclusions actionable for formulation decisions.

                Output policy:
                Return final output as JSON that matches the required schema exactly.
                The response field must contain a concise, practical assessment including:
                - Overall stability/rheology risk summary
                - Key risk drivers from formula/process/storage
                - Recommended next checks or mitigation actions
                - Confidence and data gaps
                The tools_used field must list every tool actually called in this run.

                {format_instructions}
                """,
            ),
            ("human", "{input}"),
            MessagesPlaceholder("agent_scratchpad"),
        ]
    ).partial(format_instructions=parser.get_format_instructions())

    tool_calling_agent = create_tool_calling_agent(llm, TOOLS, prompt)
    executor = AgentExecutor(
        agent=tool_calling_agent,
        tools=TOOLS,
        verbose=True,
        return_intermediate_steps=True,
    )
    return executor, parser