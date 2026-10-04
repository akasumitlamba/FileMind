"""Opt-in, direct HTTPS adapters. No automatic context, disk history, tools or retries."""
import json
import re
import urllib.request
import urllib.error


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError("Provider redirected the request; credentials were not forwarded.")


class AIProvider:
    name = ""
    endpoint = ""

    def request(self, key, model, messages):
        if not model or not re.fullmatch(r"[A-Za-z0-9._:/-]{1,150}", model):
            raise ValueError("Enter a model ID supported by your provider in Settings.")
        url, headers, payload = self.encode(key, model, messages)
        req = urllib.request.Request(url, json.dumps(payload).encode(), headers, method="POST")
        try:
            with urllib.request.build_opener(NoRedirect).open(req, timeout=60) as response:
                data = json.loads(response.read(4 * 1024 * 1024))
            return self.decode(data)
        except urllib.error.HTTPError as exc:
            messages = {401: "API key was rejected.", 403: "Your account cannot use this model.",
                        404: "Model not found. Check the model ID.", 429: "Provider rate or quota limit reached."}
            raise ValueError(messages.get(exc.code, f"Provider returned HTTP {exc.code}. Try again later.")) from None
        except (urllib.error.URLError, TimeoutError):
            raise ValueError("Could not reach the provider. Check your connection and try again.") from None
        except (KeyError, IndexError, TypeError, json.JSONDecodeError):
            raise ValueError("Provider returned an unsupported or empty response.") from None

    def encode(self, key, model, messages):
        return self.endpoint, {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, {
            "model": model, "messages": messages, "stream": False, "store": False}

    def decode(self, data):
        result = data["choices"][0]["message"]["content"]
        if not isinstance(result, str) or not result:
            raise ValueError("Provider returned no text response.")
        return result


class OpenAIProvider(AIProvider):
    name = "OpenAI"
    endpoint = "https://api.openai.com/v1/chat/completions"


class XAIProvider(AIProvider):
    name = "xAI"
    endpoint = "https://api.x.ai/v1/chat/completions"


class GeminiProvider(AIProvider):
    name = "Gemini"

    def encode(self, key, model, messages):
        if not re.fullmatch(r"[A-Za-z0-9._-]+", model):
            raise ValueError("Enter the Gemini model ID without a models/ prefix.")
        return f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent", {
            "x-goog-api-key": key, "Content-Type": "application/json"}, {"contents": [
                {"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]} for m in messages]}

    def decode(self, data):
        result = "\n".join(p.get("text", "") for p in data["candidates"][0]["content"]["parts"])
        if not result:
            raise ValueError("Provider returned no text; the request may have been blocked.")
        return result


PROVIDERS = {p.name: p() for p in (OpenAIProvider, GeminiProvider, XAIProvider)}


class CompatibleProvider(AIProvider):
    def __init__(self, name, endpoint):
        self.name, self.endpoint = name, endpoint

    def encode(self, key, model, messages):
        url, headers, payload = super().encode(key, model, messages)
        payload.pop("store", None)
        return url, headers, payload


class ClaudeProvider(AIProvider):
    name = "Claude"
    def encode(self, key, model, messages):
        return "https://api.anthropic.com/v1/messages", {
            "x-api-key": key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"
        }, {"model": model, "max_tokens": 4096, "messages": messages}

    def decode(self, data):
        result = "\n".join(p["text"] for p in data["content"] if p.get("type") == "text")
        if not result:
            raise ValueError("Provider returned no text response.")
        return result


PROVIDERS["Claude"] = ClaudeProvider()
for name, endpoint in {
    "DeepSeek": "https://api.deepseek.com/chat/completions",
    "Groq": "https://api.groq.com/openai/v1/chat/completions",
    "Mistral": "https://api.mistral.ai/v1/chat/completions",
    "OpenRouter": "https://openrouter.ai/api/v1/chat/completions",
    "Together AI": "https://api.together.xyz/v1/chat/completions",
}.items():
    PROVIDERS[name] = CompatibleProvider(name, endpoint)
