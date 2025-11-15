 import OpenAI from "openai";

  const client = new OpenAI({
    apiKey: process.env.OPENROUTER_API_KEY,
    baseURL: "https://openrouter.ai/api/v1",
  });

  async function main() {
    const resp = await client.chat.completions.create({
      model: "anthropic/claude-haiku-4.5",
      messages: [{ role: "user", content: "Say hello from Haiku 4.5." }],
    });
    console.log(resp.choices[0].message.content);
  }

  main().catch(err => {
    console.error("Haiku test failed:", err.response?.data || err.message);
  });
