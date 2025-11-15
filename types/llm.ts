// Types for LLM integration

export interface LLMConfig {
  apiKey: string;
  model: string;
  temperature?: number;
  maxTokens?: number;
  baseURL?: string;
  /**
   * Optional headers to send with each request.
   * Useful for OpenRouter metadata like HTTP-Referer and X-Title.
   */
  headers?: Record<string, string>;
}

export interface LLMMessage {
  role: 'system' | 'user' | 'assistant';
  content: string;
}

export interface LLMResponse {
  content: string;
  model: string;
  usage?: {
    promptTokens: number;
    completionTokens: number;
    totalTokens: number;
  };
}

export interface LLMPromptTemplate {
  name: string;
  systemPrompt: string;
  userPromptTemplate: string;
  variables: string[];
}
