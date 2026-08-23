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

## Wikipedia introductory prose

- Status: enabled
- Access method: official English MediaWiki Action API
- Retrieved scope: one bounded introductory extract plus title and canonical URL
- Licence: Creative Commons Attribution-ShareAlike 4.0
- Attribution: `Wikipedia contributors`, article URL, and licence metadata are retained
- Excluded scope: full articles, media, references, discussions, and external links
- Storage: bounded in-memory cache only; default TTL 24 hours
- Failure and privacy behavior: fail open; reject personal, sensitive, credential-like, URL, email, and long inputs locally

## Wikibooks educational prose

- Status: enabled
- Access method: official English MediaWiki Action API
- Retrieved scope: one bounded introductory extract plus title and canonical URL
- Licence: Creative Commons Attribution-ShareAlike 4.0
- Attribution: `Wikibooks contributors`, page URL, and licence metadata are retained
- Excluded scope: full books, media, discussions, and external links
- Storage: bounded in-memory cache only; default TTL 24 hours
- Failure and privacy behavior: fail open; reject personal, sensitive, credential-like, URL, email, and long inputs locally

## Crossref bibliographic metadata

- Status: enabled
- Access method: official public REST API
- Retrieved scope: at most three records containing DOI, title, creators, publication date, container, and work type
- Licence boundary: bibliographic facts and Crossref-generated CC0 data only
- Excluded scope: abstracts, full text, publisher files, and linked-page content
- Source guidance: https://www.crossref.org/documentation/retrieve-metadata/
- Storage: bounded in-memory cache only; default TTL 24 hours
- Failure and privacy behavior: fail open; reject personal, sensitive, credential-like, URL, email, and long inputs locally

## Wikiversity learning resources

- Status: enabled
- Purpose: supplement learning sequences, lesson structure, exercises, and educational relationships
- Access method: official English MediaWiki Action API (`https://en.wikiversity.org/w/api.php`)
- Retrieved scope: one bounded introductory extract from one title-matched main-namespace learning resource
- Licence: Creative Commons Attribution-ShareAlike 4.0
- Licence record: https://en.wikiversity.org/wiki/Wikiversity:Copyrights
- Terms: https://foundation.wikimedia.org/wiki/Policy:Terms_of_Use
- Attribution: `Wikiversity contributors`, source-page URL, licence, and adaptation instruction are retained
- Commercial use: permitted when attribution and share-alike obligations are followed
- Authority boundary: community-created educational supplement; it must not override stronger factual or scholarly sources
- Excluded scope: images, audio, video, files, attachments, discussions, histories, external links, and linked-page content
- Storage: bounded in-memory cache only; default TTL 24 hours
- Failure behavior: fail open to InI's existing pipeline; never block a response; no retry through rate limits
- Traffic behavior: one identified User-Agent and one combined search/extract request with no pagination or bulk harvesting
- Privacy behavior: only short public-topic queries are sent; personal, sensitive, URL, email, credential-like, and long free-form inputs are rejected locally

### Wikiversity configuration

- `INI_WIKIVERSITY_ENABLED=1` enables the connector (default).
- `INI_WIKIVERSITY_ENABLED=0` is the immediate kill switch.
- `INI_WIKIVERSITY_TIMEOUT=4` sets the request timeout in seconds (bounded to 1–10).
- `INI_WIKIVERSITY_CACHE_SECONDS=86400` sets the in-memory cache lifetime (bounded to 60–604800).
- `INI_WIKIVERSITY_USER_AGENT` may override the identifying User-Agent.

## DataCite research-output metadata

- Status: enabled
- Purpose: discover datasets, software, reports, publications, and other DOI-identified research outputs
- Access method: unauthenticated DataCite public REST API (`https://api.datacite.org/dois`)
- Retrieved scope: at most three records containing title, creators, publication year, publisher, resource type, subjects, and DOI
- Licence: Creative Commons CC0 1.0 waiver for deposited DataCite metadata
- Licence record: https://support.datacite.org/docs/datacite-data-file-use-policy
- API guidance: https://support.datacite.org/docs/api
- Rate limits: https://support.datacite.org/docs/rate-limit
- Attribution: `DataCite DOI metadata` and DOI links are retained as a community-norm attribution
- Commercial use: permitted for the CC0 metadata used by this connector
- Excluded scope: descriptions, abstracts, files, linked resources, linked webpages, logos, and DataCite marks
- Rights boundary: a DataCite record does not grant permission to retrieve or reuse the resource identified by its DOI
- Storage: bounded in-memory cache only; default TTL 24 hours
- Failure behavior: fail open to InI's existing pipeline; never block a response; no automatic retry through rate limits
- Traffic behavior: one identified User-Agent, one bounded query, at most three records, and no pagination or bulk harvesting
- Privacy behavior: only short public-topic queries are sent; personal, sensitive, URL, email, credential-like, and long free-form inputs are rejected locally

### DataCite configuration

- `INI_DATACITE_ENABLED=1` enables the connector (default).
- `INI_DATACITE_ENABLED=0` is the immediate kill switch.
- `INI_DATACITE_TIMEOUT=4` sets the request timeout in seconds (bounded to 1–10).
- `INI_DATACITE_CACHE_SECONDS=86400` sets the in-memory cache lifetime (bounded to 60–604800).
- `INI_DATACITE_USER_AGENT` may override the identifying User-Agent.

## OpenAlex scholarly-discovery metadata

- Status: enabled
- Purpose: improve scholarly discovery, topic orientation, and citation-network awareness
- Access method: official OpenAlex Works API (`https://api.openalex.org/works`)
- Retrieved scope: at most three records containing title, authors, publication year, work type, source name, topics, DOI, citation count, OpenAlex identifier, and open-access indicator
- Terms: https://openalex.org/OpenAlex_termsofservice.pdf
- Licence guidance: https://help.openalex.org/data/licenses/
- Attribution: `OpenAlex scholarly metadata` and OpenAlex identifiers are retained
- Excluded scope: abstracts, full text, files, landing-page content, referenced works, and linked external resources
- Rights boundary: metadata, citation counts, and open-access indicators do not establish a work's findings, quality, or permission to reproduce it
- Storage: bounded in-memory cache only; default TTL 24 hours
- Failure behavior: fail open to InI's existing pipeline; never block a response; no automatic retry through rate limits
- Traffic behavior: one identified User-Agent, one bounded query, at most three records, and no pagination or bulk harvesting
- Privacy behavior: only short public-topic queries are sent; personal, URL, email, credential-like, and long free-form inputs are rejected locally

### OpenAlex configuration

- `INI_OPENALEX_ENABLED=1` enables the connector (default).
- `INI_OPENALEX_ENABLED=0` is the immediate kill switch.
- `INI_OPENALEX_TIMEOUT=4` sets the request timeout in seconds (bounded to 1–10).
- `INI_OPENALEX_CACHE_SECONDS=86400` sets the in-memory cache lifetime (bounded to 60–604800).
- `INI_OPENALEX_USER_AGENT` may override the identifying User-Agent.
- `OPENALEX_API_KEY` may supply a free OpenAlex API key for dependable production capacity; it is never hard-coded or returned in model context.

## Admission rule for future sources

No additional source should be connected until its copyright status, licence,
commercial-use terms, attribution requirements, API terms, storage/indexing
permission, and redistribution limits have been recorded here.
