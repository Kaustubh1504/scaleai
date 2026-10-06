import time
from dataclasses import dataclass
from urllib.parse import urlencode

from .parsing import parse_completion
from .retry import RetryPolicy, send_with_retries
from .transport import send


@dataclass
class Result:
    request_id: str
    status: str
    http_status: int | None = None
    score: float | None = None
    passed: bool | None = None


class ModelClient:
    def __init__(self, base_url, api_key, config, sleep=time.sleep):
        self.base_url = base_url.rstrip("/")
        self.config = config
        self.sleep = sleep
        self.headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        self.policy = RetryPolicy(config.max_retries, config.backoff_seconds)

    def build_request(self, request_id, question, answer):
        return {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": self.config.system_prompt},
                {"role": "user", "content": f"Question: {question}\nAnswer: {answer}"},
            ],
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "metadata": {"request_id": request_id},
        }

    def grade(self, request_id, question, answer):
        payload = self.build_request(request_id, question, answer)
        url = f"{self.base_url}/v1/chat/completions"
        response = send_with_retries(lambda: send("POST", url, self.headers, payload), self.policy, self.sleep)
        if response.status >= 400:
            return Result(request_id, "http_error", http_status=response.status)
        grade = parse_completion(response.body)
        if grade is None:
            return Result(request_id, "parse_error", http_status=response.status)
        return Result(request_id, "ok", http_status=response.status, score=grade.score, passed=grade.passed)

    def usage_page(self, cursor=None):
        query = {"limit": self.config.page_size}
        if cursor:
            query["cursor"] = cursor
        response = send("GET", f"{self.base_url}/v1/usage?{urlencode(query)}", self.headers)
        if response.status != 200:
            raise RuntimeError(f"usage request failed with HTTP {response.status}")
        return response.body
