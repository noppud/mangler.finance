// OpenRouter LLM client

import OpenAI from 'openai';
import { LLMConfig, LLMMessage, LLMResponse } from '@/types/llm';

export class LLMClient {
  private client: OpenAI;
  private config: LLMConfig;

  constructor(config: LLMConfig) {
    this.config = config;
    this.client = new OpenAI({
      apiKey: config.apiKey,
      baseURL: config.baseURL || 'https://openrouter.ai/api/v1',
      // Forward any caller-provided headers to OpenRouter
      defaultHeaders: config.headers,
    });
  }

  /**
   * Send a chat completion request
   */
  async chat(messages: LLMMessage[], overrides?: Partial<LLMConfig>): Promise<LLMResponse> {
    const model = overrides?.model || this.config.model;
    const temperature = overrides?.temperature ?? this.config.temperature ?? 0.7;
    const maxTokens = overrides?.maxTokens ?? this.config.maxTokens ?? 4000;

    try {
      const completion = await this.client.chat.completions.create({
        model,
        messages: messages.map(m => ({
          role: m.role,
          content: m.content,
        })),
        temperature,
        max_tokens: maxTokens,
      });

      const choice = completion.choices[0];
      const content = choice.message.content || '';

      return {
        content,
        model: completion.model,
        usage: completion.usage
          ? {
              promptTokens: completion.usage.prompt_tokens,
              completionTokens: completion.usage.completion_tokens,
              totalTokens: completion.usage.total_tokens,
            }
          : undefined,
      };
    } catch (error: unknown) {
      const err = error as { message?: string };
      throw new Error(`LLM API error: ${err.message ?? 'Unknown error'}`);
    }
  }

  /**
   * Send a simple prompt (convenience method)
   */
  async prompt(
    systemPrompt: string,
    userPrompt: string,
    overrides?: Partial<LLMConfig>
  ): Promise<string> {
    const messages: LLMMessage[] = [
      { role: 'system', content: systemPrompt },
      { role: 'user', content: userPrompt },
    ];

    const response = await this.chat(messages, overrides);
    return response.content;
  }

  /**
   * Send a request expecting JSON response
   */
  async chatJSON<T>(
    messages: LLMMessage[],
    overrides?: Partial<LLMConfig>
  ): Promise<T> {
    const response = await this.chat(messages, overrides);

    // Extract JSON from markdown code blocks if present
    let jsonStr = response.content.trim();
    const jsonMatch = jsonStr.match(/```(?:json)?\n([\s\S]*?)\n```/);
    if (jsonMatch) {
      jsonStr = jsonMatch[1];
    }

    try {
      return JSON.parse(jsonStr) as T;
    } catch (error) {
      throw new Error(`Failed to parse LLM response as JSON: ${error}`);
    }
  }

  /**
   * Stream a chat completion (for real-time UIs)
   */
  async *chatStream(
    messages: LLMMessage[],
    overrides?: Partial<LLMConfig>
  ): AsyncGenerator<string, void, unknown> {
    const model = overrides?.model || this.config.model;
    const temperature = overrides?.temperature ?? this.config.temperature ?? 0.7;
    const maxTokens = overrides?.maxTokens ?? this.config.maxTokens ?? 4000;

    const stream = await this.client.chat.completions.create({
      model,
      messages: messages.map(m => ({
        role: m.role,
        content: m.content,
      })),
      temperature,
      max_tokens: maxTokens,
      stream: true,
    });

    for await (const chunk of stream) {
      const content = chunk.choices[0]?.delta?.content;
      if (content) {
        yield content;
      }
    }
  }
}

/**
 * Create LLM client from environment variables
 */
export function createLLMClient(): LLMClient {
  const apiKey = process.env.OPENROUTER_API_KEY;
  if (!apiKey) {
    throw new Error('OPENROUTER_API_KEY environment variable not set');
  }

  const model =
    process.env.DEFAULT_LLM_MODEL || 'anthropic/claude-haiku-4.5';

  const headers: Record<string, string> = {};
  if (process.env.OPENROUTER_SITE_URL) {
    headers['HTTP-Referer'] = process.env.OPENROUTER_SITE_URL;
  }
  if (process.env.OPENROUTER_SITE_NAME) {
    headers['X-Title'] = process.env.OPENROUTER_SITE_NAME;
  }

  return new LLMClient({
    apiKey,
    model,
    temperature: 0.7,
    maxTokens: 4000,
    headers,
  });
}
