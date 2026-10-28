# USGS science notes

Reviewed: 2026-10-28. Scope: a small local catalogue, not a live API integration.

## Reuse boundary

USGS states that USGS-authored or produced information is in the U.S. public
domain and requests source credit. The policy does not grant blanket rights
to third-party material, personnel likenesses, multimedia, or the USGS logo.

Policy: https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits

Only short factual paraphrases from the following official educational pages
are included. No logos, images, quotations, or third-party media are copied.

- Earthquakes (page credits Lisa Wald, U.S. Geological Survey):
  https://www.usgs.gov/programs/earthquake-hazards/science-earthquakes
- Volcanic eruptions (USGS FAQ):
  https://www.usgs.gov/faqs/how-do-volcanoes-erupt
- Groundwater (USGS Water Science School):
  https://www.usgs.gov/water-science-school/science/groundwater-what-groundwater

## Runtime behavior

- No network calls, API key, or external query transmission from this adapter.
- Matches only the three supported topic groups; unrelated prompts are unchanged.
- Current-event, alert, prediction, and personal-safety queries are excluded.
- Notes expire after 180 days; review the pages before advancing REVIEWED_ON.
- Prompt context requires relevant attribution and the supporting official link
  in prose, without altering structured output schemas.
- Source metadata distinguishes reviewed notes from live retrieval.
- Disable with INI_USGS_ENABLED=0.

This is not a claim of USGS endorsement or comprehensive Earth-science coverage.
