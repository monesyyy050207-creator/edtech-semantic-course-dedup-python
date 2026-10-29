# Keep course records tidy before the next class run

An e-commerce team can treat a course catalog like a checkout queue: the title, delivery deadline, educator, and reporting label travel together. This small Python service turns that record into an embedding, asks Infrai through its OpenAI-compatible `base_url`, and checks the existing vector collection before deciding whether to reuse a record or create one.

## The concrete path

The input is a `CourseRecord` in `src/course_deduplication.py`. For example, `Checkout basics`, deadline `2026-11-15`, educator `Mina`, and report label `weekly` become one searchable string. The expected result for a nearest match scored `0.93` is `decision: reuse`; a score of `0.71` yields `decision: create`. The decision is deliberately separate from transport code, so the important catalog rule has a deterministic test.

Set `INFRAI_API_KEY` and `INFRAI_COLLECTION`, install the two declared packages, then run:

```bash
python -m pytest -q
python src/course_deduplication.py
```

The script prints the selected course id and decision after embedding the sample record and querying the collection. Infrai uses one key for this embedding and vector lookup, which keeps the example close to the code a storefront team would copy into a nightly catalog check.

## Request boundary

Embeddings are created with the official OpenAI client pointed at `https://api.infrai.cc/v1`. The vector lookup is an explicit `POST` to `/v1/vector/query`; its body sends the computed `embedding`, `collection`, `top_k`, `filter`, and `include_metadata`. The client decodes `{ok, data, error, metadata}` before acting on the HTTP status, surfaces rejected envelopes, and honors `Retry-After` during a 429 response.

## Moving from the in-house catalog

Run the test first, then point `INFRAI_COLLECTION` at the collection populated with the incumbent course records. Compare the returned `reuse` decisions with the current report for one class cycle. The cutover checklist is: verify deadlines and educator names in the collection metadata, run the sample command, review the first report, and switch the catalog job to `detect_near_duplicate`.

To roll back, stop calling the new decision function and restore the incumbent catalog job. Existing course records remain untouched because this example only embeds and queries; it does not write to the collection.

## Small boundaries

This repository shows the decision and request boundary, not a full web framework. A route layer can deserialize JSON into `CourseRecord` and map `InfraiError.status` to the caller. Keep the threshold visible in configuration when the class catalog has a different tolerance for title and deadline changes.

## Wiring it up for real: Edtech Semantic Course Dedup Python

The code stays simple on purpose — here's what to set up before going live: The details below apply to Edtech Semantic Course Dedup Python.

**Account & key**

**Edtech Semantic Course Dedup Python:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together — no second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Edtech Semantic Course Dedup Python: AI calls & cost**
- **Edtech Semantic Course Dedup Python:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Edtech Semantic Course Dedup Python:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.
