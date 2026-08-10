# InI.ai Knowledge Source Registry

This registry records every external knowledge source permitted to enter InI's
retrieval pipeline. Inclusion here is source-specific and does not grant blanket
permission to retrieve other websites linked by that source.

## Wikidata structured data

- Status: enabled
- Purpose: topic identity, aliases, classification, and selected conceptual relationships
- Access method: official MediaWiki/Wikibase API (`https://www.wikidata.org/w/api.php`)
- Retrieved scope: labels, descriptions, aliases, and an explicit allowlist of entity relationships
- Excluded scope: Wikipedia prose, Wikimedia Commons media, discussion pages, external linked pages, and arbitrary claim values
- Licence: Creative Commons CC0 1.0
- Licence record: https://www.wikidata.org/wiki/Wikidata:Licensing
- API guidance: https://www.wikidata.org/wiki/Wikidata:REST_API/en
- Attribution: not legally required for CC0 structured data; source and entity URL are nevertheless retained in response metadata
- Commercial use: permitted for the CC0 structured data used by this connector
- Storage: bounded in-memory cache only; default TTL 24 hours
- Failure behavior: fail open to InI's existing LLM pipeline; never block a response
- Traffic behavior: one identified User-Agent, bounded result sets, no concurrent fan-out, no retry through rate limits
- Privacy behavior: only short public-topic queries are sent; personal, sensitive, URL, email, credential-like, and long free-form inputs are rejected locally

### Configuration

- `INI_WIKIDATA_ENABLED=1` enables the connector (default).
- `INI_WIKIDATA_ENABLED=0` disables it immediately.
- `INI_WIKIDATA_TIMEOUT=4` sets the request timeout in seconds (bounded to 1–10).
- `INI_WIKIDATA_CACHE_SECONDS=86400` sets the in-memory cache lifetime (bounded to 60–604800).
- `INI_WIKIDATA_USER_AGENT` may override the identifying User-Agent when a maintained contact URL is available.

## Admission rule for future sources

No additional source should be connected until its copyright status, licence,
commercial-use terms, attribution requirements, API terms, storage/indexing
permission, and redistribution limits have been recorded here.
