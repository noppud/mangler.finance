/**
 * MCP (Model Context Protocol) type definitions
 */

export interface MCPConfiguration {
  id?: string;
  user_id: string;
  name: string;
  mcp_type: 'stdio';
  command: string;
  args: string[];
  env: Record<string, string>;
  enabled: boolean;
  metadata: Record<string, any>;
  created_at?: string;
  updated_at?: string;
}

export interface MCPConfigurationCreate {
  name: string;
  command: string;
  args: string[];
  env?: Record<string, string>;
  metadata?: Record<string, any>;
}

export interface MCPConfigurationUpdate {
  name?: string;
  enabled?: boolean;
  env?: Record<string, string>;
  args?: string[];
  metadata?: Record<string, any>;
}

export interface MCPConfigurationList {
  configurations: MCPConfiguration[];
  total: number;
  max_allowed: number;
}

export interface MCPTool {
  name: string;
  description: string;
  input_schema: Record<string, any>;
  mcp_server_id: string;
  mcp_server_name: string;
}

export interface UserIdentityLink {
  id?: string;
  kinde_user_id: string;
  google_email: string;
  google_sub?: string;
  linked_at?: string;
  last_verified_at?: string;
}

export interface IdentityResolveResponse {
  kinde_user_id?: string;
  linked: boolean;
  google_email: string;
}

// Preset MCP configurations for quick setup
export const MCP_PRESETS = [
  {
    name: 'Google Drive MCP',
    command: 'npx',
    args: ['@modelcontextprotocol/server-gdrive'],
    description: 'Access and manipulate files in Google Drive',
    icon: '📁'
  },
  {
    name: 'Filesystem MCP',
    command: 'npx',
    args: ['@modelcontextprotocol/server-filesystem', '/allowed/path'],
    description: 'Read and write local files with path restrictions',
    icon: '💾'
  },
  {
    name: 'GitHub MCP',
    command: 'npx',
    args: ['@modelcontextprotocol/server-github'],
    description: 'Interact with GitHub repositories and issues',
    icon: '🐙'
  },
  {
    name: 'Memory MCP',
    command: 'npx',
    args: ['@modelcontextprotocol/server-memory'],
    description: 'Persistent memory across chat sessions',
    icon: '🧠'
  },
  {
    name: 'Slack MCP',
    command: 'npx',
    args: ['@modelcontextprotocol/server-slack'],
    description: 'Send messages and interact with Slack workspaces',
    icon: '💬'
  }
];