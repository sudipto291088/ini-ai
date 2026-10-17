"""Recovery helpers without shared or cross-account state."""


def merge_continuation(previous, chunk):
    previous = previous or ""
    chunk = (chunk or "").strip()
    if not chunk or chunk in previous:
        return previous
    for size in range(min(len(previous), len(chunk)), 11, -1):
        if previous.endswith(chunk[:size]):
            return previous + chunk[size:]
    separator = "\n\n" if previous.rstrip().endswith((".", "!", "?", ":", "```")) else " "
    return previous.rstrip() + separator + chunk if previous else chunk


def recover_answer(record, response):
    updated = dict(record)
    previous = str(record.get("text") or "")
    chunk = str(response.get("answer") or "")
    failed = bool(response.get("error")) or (
        (response.get("llm") or {}).get("reason") in {"llm_error", "empty_answer", "http_error"}
    ) or chunk.strip().casefold() == "no answer generated."
    combined = previous if failed else merge_continuation(previous, chunk)
    progressed = combined != previous
    updated.update(text=combined, incomplete=not progressed or bool(response.get("incomplete")) or response.get("stop_reason") == "max_output_tokens",
                   stop_reason=(response.get("stop_reason") or None) if progressed else "continuation_unavailable")
    if response.get("followups"):
        updated["followups"] = response["followups"]
    if progressed:
        updated.pop("answer_views", None)
        updated.pop("answer_emphasis_version", None)
    return updated


def collect_answer(fetch, topic, *, mode, max_rounds, profile_context=None):
    response = fetch(topic, mode=mode, profile_context=profile_context)
    record = {**response, "text": response.get("answer") or ""}
    for _ in range(max_rounds):
        if not (record.get("incomplete") or record.get("stop_reason") == "max_output_tokens"):
            break
        try:
            following = fetch(topic, mode=mode, continue_mode=True,
                              previous_answer=record["text"], profile_context=profile_context)
        except Exception:
            record.update(incomplete=True, stop_reason="continuation_unavailable")
            break
        updated = recover_answer(record, following)
        if updated["text"] == record["text"]:
            record = updated
            break
        record = updated
    return {**record, "answer": record["text"]}
