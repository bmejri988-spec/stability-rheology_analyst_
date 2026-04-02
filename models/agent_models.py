from typing import List

from pydantic import BaseModel, Field


class AgentResponse(BaseModel):
    response: str = Field(..., description="Structured agent response object")
    tools_used: List[str] = Field(default_factory=list, description="List of tool names used during reasoning")