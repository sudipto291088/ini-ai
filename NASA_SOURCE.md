# NASA Science source pilot

Added locally on October 8, 2026. This is a reviewed, bounded fact catalogue,
not live search, full-site ingestion, or NASA endorsement.

## Coverage and provenance

- Solar system and planetary science: https://science.nasa.gov/solar-system/
- Black holes and event horizons: https://science.nasa.gov/universe/black-holes/
- Earth science and Earth observation: https://science.nasa.gov/earth/

The adapter supplies short paraphrased factual notes, NASA Science attribution,
official page URLs, and the review date to the existing answer pipeline.
Only the supplied facts may be attributed to these pages. Broader astronomy
requests can receive the solar-system and black-hole notes; this does not
provide comprehensive astronomy coverage.

## Safeguards

- No network requests, API key, new dependency, user-data sharing, or added
  retrieval timeout.
- No NASA logos, images, third-party media, or copied article bodies.
- No blanket public-domain claim about everything hosted by NASA.
- No modifications to chat layout, streaming, navigation, or output schemas.
- `INI_NASA_ENABLED=0` disables this source.
- Notes expire after 180 days from review. To renew, verify every fact against
  the official pages before advancing `REVIEWED_ON`.

Reuse guidance: https://www.nasa.gov/nasa-brand-center/images-and-media/
Earth-site guidance: https://science.nasa.gov/earth/faq/

Test query: "What is a black hole's event horizon?"
