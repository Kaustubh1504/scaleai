from . import wire


class RelayClient:
    """Thin async client for the completion relay."""

    def __init__(self, base_url, api_key, model):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    def payload(self, prompt):
        return {
            "model": self.model,
            "prompt_id": prompt.id,
            "prompt": prompt.text,
            "max_tokens": prompt.max_tokens,
            "stream": True,
        }

    async def complete(self, prompt, attempt):
        headers = self.headers
        headers["X-Request-Id"] = f"{prompt.id}-{attempt}"
        return await wire.send(self.base_url, "POST", "/v1/complete", headers, self.payload(prompt))

    async def policy_blocks(self, prompt_id):
        response = await wire.send(self.base_url, "GET", f"/v1/policy/{prompt_id}", self.headers)
        if response.status != 200:
            raise wire.EvalError(f"policy check for {prompt_id} failed with HTTP {response.status}")
        return not response.json()["allowed"]

    async def get_json(self, path, params=None):
        response = await wire.send(self.base_url, "GET", path, self.headers, params=params)
        return response.status, response.json()
