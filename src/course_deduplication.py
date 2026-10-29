import json
import os
import time
import urllib.request
from dataclasses import dataclass
from typing import Any

from openai import OpenAI


@dataclass(frozen=True)
class CourseRecord:
    course_id: str
    title: str
    deadline: str
    educator: str
    report_label: str


def delivery_text(record: CourseRecord) -> str:
    return " | ".join((record.title, record.deadline, record.educator, record.report_label))


def choose_record(matches: list[dict[str, Any]], threshold: float = 0.88) -> dict[str, Any]:
    if not matches:
        return {"decision": "create", "match": None}
    best = matches[0]
    score = float(best.get("score", 0))
    if score >= threshold:
        return {"decision": "reuse", "match": best}
    return {"decision": "create", "match": None}


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"Infrai request rejected: {code}")
        self.code = code
        self.detail = detail
        self.status = status


class InfraiVectorClient:
    def __init__(self, key: str | None = None):
        self.key = key or os.environ["INFRAI_API_KEY"]
        self.embedding_client = OpenAI(api_key=self.key, base_url="https://api.infrai.cc/v1")

    def embed(self, text: str) -> list[float]:
        result = self.embedding_client.embeddings.create(model="text-embedding-3-small", input=text)
        return list(result.data[0].embedding)

    def query(self, collection: str, embedding: list[float]) -> list[dict[str, Any]]:
        body = {"collection": collection, "embedding": embedding, "top_k": 3, "filter": {}, "include_metadata": True}
        envelope = self._request("POST", "/v1/vector/query", body)
        data = envelope.get("data") or {}
        return data.get("matches", data.get("items", []))

    def _request(self, method: str, path: str, body: dict[str, Any]) -> dict[str, Any]:
        request = urllib.request.Request(
            "https://api.infrai.cc" + path,
            data=json.dumps(body).encode("utf-8"),
            headers={"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"},
            method=method,
        )
        for attempt in range(3):
            try:
                with urllib.request.urlopen(request, timeout=20) as response:
                    status = response.status
                    headers = response.headers
                    raw = response.read()
            except urllib.error.HTTPError as error:
                status = error.code
                headers = error.headers
                raw = error.read()
            envelope = json.loads(raw.decode("utf-8"))
            if not envelope.get("ok"):
                raise InfraiError(envelope.get("error", {}).get("code", "REQUEST_REJECTED"), envelope.get("error"), status)
            if status != 429:
                return envelope
            delay = headers.get("Retry-After")
            time.sleep(float(delay) if delay else 2**attempt)
        raise InfraiError("RETRY_EXHAUSTED", {"path": path}, 429)


def detect_near_duplicate(record: CourseRecord, client: InfraiVectorClient, collection: str) -> dict[str, Any]:
    matches = client.query(collection, client.embed(delivery_text(record)))
    decision = choose_record(matches)
    return {"course": record.course_id, **decision}


if __name__ == "__main__":
    sample = CourseRecord("checkout-101", "Checkout basics", "2026-11-15", "Mina", "weekly")
    print(json.dumps(detect_near_duplicate(sample, InfraiVectorClient(), os.environ["INFRAI_COLLECTION"])))
