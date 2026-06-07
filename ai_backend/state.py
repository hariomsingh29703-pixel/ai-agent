"""
State models for Antigravity Clone.
Same Pydantic pattern as ai_agent/state.py — but for a general-purpose coding agent.
"""
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class AgentMessage(BaseModel):
    """A single message in the conversation."""
    role: str = Field(description="'user', 'assistant', or 'tool'")
    content: str = Field(description="The message content")


class AgentState(BaseModel):
    """
    The main state that flows through the LangGraph.
    Same concept as the dict state in ai_agent/graph.py.
    """
    model_config = ConfigDict(extra="allow")

    # Conversation
    messages: list[AgentMessage] = Field(default_factory=list, description="Chat history")
    
    # Current task
    user_message: str = Field("", description="The latest user input")
    plan: Optional[str] = Field(None, description="The agent's plan for the current task")
    
    # Tool execution
    tool_calls: list[dict] = Field(default_factory=list, description="Pending tool calls")
    tool_results: list[str] = Field(default_factory=list, description="Results from tool executions")
    
    # Control flow
    is_complete: bool = Field(False, description="Whether the task is done")
    response: Optional[str] = Field(None, description="Final response to user")
    iteration: int = Field(0, description="Current loop iteration (safety limit)")
    max_iterations: int = Field(15, description="Max loops before forced stop")
