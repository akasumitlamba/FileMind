# AI provider adapters

Available choices: OpenAI, Gemini, xAI, Claude, DeepSeek, Groq, Mistral, OpenRouter, and Together AI. Supply your own API key and a model ID supported by that account. Adapter payloads and responses are tested with mocked transport; live account compatibility remains unverified.

New adapter references:
- [Claude Messages](https://platform.claude.com/docs/en/api/messages/create)
- [DeepSeek](https://api-docs.deepseek.com/)
- [Groq](https://console.groq.com/docs/api-reference)
- [Mistral](https://docs.mistral.ai/api/endpoint/chat)
- [OpenRouter](https://openrouter.ai/docs/api_reference/overview)
- [Together AI](https://www.together.ai/serverless-inference)

GROK sends to the selected service. Routing services such as OpenRouter forward requests to the selected upstream provider. Provider retention, routing and billing policies apply. Attachments are queued explicitly and reviewed before transmission. Saved conversation files include sent attachment text.
