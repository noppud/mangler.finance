from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Literal
from datetime import datetime

from pydantic import BaseModel, Field, validator


class ChatMessageRole(str, Enum):
  user = "user"
  assistant = "assistant"
  tool = "tool"
  system = "system"


class ChatMessageMetadata(BaseModel):
  toolName: Optional[str] = None
  payload: Optional[Any] = None
  plan: Optional[str] = None
  error: Optional[str] = None
  timestamp: Optional[str] = None


class ChatMessage(BaseModel):
  id: str
  role: ChatMessageRole
  content: str
  metadata: Optional[ChatMessageMetadata] = None


class SheetContext(BaseModel):
  spreadsheetId: Optional[str] = None
  sheetTitle: Optional[str] = None


class ChatRequest(BaseModel):
  messages: List[ChatMessage]
  sheetContext: SheetContext = Field(default_factory=SheetContext)
  sessionId: Optional[str] = None
  googleEmail: Optional[str] = None  # NEW - for identity linking
  mcpMentions: Optional[List[str]] = None  # NEW - detected @mentions


class ChatResponse(BaseModel):
  messages: List[ChatMessage]
  sessionId: Optional[str] = None
  mcpToolsUsed: Optional[List[str]] = None  # NEW - which MCPs were called


def chat_request_to_dict(request: ChatRequest) -> Dict[str, Any]:
  """
  Serialize ChatRequest to a plain dict compatible with the
  existing TypeScript /api/chat endpoint.
  """
  return request.model_dump(exclude_none=True)


def chat_response_from_dict(data: Dict[str, Any]) -> ChatResponse:
  """
  Parse a dict (from JSON) into ChatResponse.
  """
  return ChatResponse.model_validate(data)


# ============================================================================
# MCP Configuration Models
# ============================================================================

class MCPConfiguration(BaseModel):
    """MCP server configuration (user-scoped)"""
    id: Optional[str] = None
    user_id: str
    name: str
    mcp_type: Literal["stdio"] = "stdio"
    command: str  # e.g., "npx", "python", "node", "/path/to/binary"
    args: List[str]  # e.g., ["@modelcontextprotocol/server-gdrive"]
    env: Dict[str, str] = Field(default_factory=dict)
    enabled: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @validator('name')
    def validate_name(cls, v):
        if not v or len(v.strip()) < 3:
            raise ValueError('Name must be at least 3 characters')
        if len(v) > 50:
            raise ValueError('Name must be less than 50 characters')
        return v.strip()

    @validator('command')
    def validate_command(cls, v):
        allowed_commands = ['npx', 'node', 'python', 'python3', 'uvx']
        # Also allow absolute paths
        if v not in allowed_commands and not v.startswith('/'):
            raise ValueError(f'Command must be one of {allowed_commands} or an absolute path')
        return v

    @validator('args')
    def validate_args(cls, v):
        if not v or len(v) == 0:
            raise ValueError('At least one argument required')
        return v


class MCPConfigurationCreate(BaseModel):
    """Request model for creating MCP config"""
    name: str
    command: str = "npx"
    args: List[str]
    env: Dict[str, str] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @validator('name')
    def validate_name(cls, v):
        if not v or len(v.strip()) < 3:
            raise ValueError('Name must be at least 3 characters')
        return v.strip()


class MCPConfigurationUpdate(BaseModel):
    """Request model for updating MCP config"""
    name: Optional[str] = None
    enabled: Optional[bool] = None
    env: Optional[Dict[str, str]] = None
    args: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class MCPConfigurationList(BaseModel):
    """Response model for listing MCPs"""
    configurations: List[MCPConfiguration]
    total: int
    max_allowed: int = 5


# ============================================================================
# MCP Tool Models
# ============================================================================

class MCPTool(BaseModel):
    """Represents a tool exposed by an MCP server"""
    name: str
    description: str
    input_schema: Dict[str, Any]
    mcp_server_id: str  # UUID of the MCP configuration
    mcp_server_name: str  # User-friendly name


class MCPToolCallRequest(BaseModel):
    """Request to call an MCP tool"""
    tool_name: str
    arguments: Dict[str, Any]
    mcp_server_id: str


class MCPToolCallResponse(BaseModel):
    """Response from MCP tool execution"""
    success: bool
    tool_name: str
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time_ms: Optional[int] = None


# ============================================================================
# User Identity Linking Models
# ============================================================================

class UserIdentityLink(BaseModel):
    """Links Google user to Kinde user"""
    id: Optional[str] = None
    kinde_user_id: str
    google_email: str
    google_sub: Optional[str] = None
    linked_at: Optional[datetime] = None
    last_verified_at: Optional[datetime] = None


class UserIdentityLinkCreate(BaseModel):
    """Request to create user identity link"""
    google_email: str
    google_sub: Optional[str] = None
    # kinde_user_id comes from authenticated session


class IdentityResolveRequest(BaseModel):
    """Request to resolve Google user to Kinde user"""
    google_email: str


class IdentityResolveResponse(BaseModel):
    """Response with Kinde user ID"""
    kinde_user_id: Optional[str] = None
    linked: bool
    google_email: str


