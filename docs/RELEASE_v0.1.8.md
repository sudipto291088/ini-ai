# InI.ai v0.1.8

Released October 31, 2026. Alpha release.

## Highlights

- Google-only sign-in and account-owned conversation handling, with a redesigned sign-in page and mobile layout.
- PostgreSQL conversation storage support, verified TLS, pooled transaction handling, and query timeouts. Deployment configuration is still required; a version bump does not configure a database.
- Account settings with private chat export and confirmed deletion, a compact profile menu, and an additional Exit action alongside the existing red sign-out icon.
- Explicit learning choices for recognized subjects, including Kubernetes, and clarification choices for ambiguous abbreviations.
- Contextual Learning trail actions for worked examples, connections, and reasoning checks; a quieter Knowledge Structure entry action.
- Recovery for incomplete answers, stronger factual learning presentation, and guards against stale clarification context.
- Reviewed, attributed NASA and USGS science notes with narrow scope and expiry guards; these are not live research or hazard-alert feeds.
- Refined Mukut favicon, sidebar behavior, mobile sign-in, composer handoffs, and stale generation indicators.
- Conversational name and role handling distinguishes self-reported claims from authenticated identity and does not grant account privileges.

## Release surfaces

The sidebar badge, Introduction release history, product-version answers, seven-day New Chat release notice, and retrieval user-agent identifiers are aligned to v0.1.8. Earlier release notes remain available; v0.1.9 is shown as unreleased.

## Not included

- The proposed floating UIB design is a mockup, not implemented in this release.
- The uncommitted Your Question revision and OpenStax experiment are excluded.
- No claim of a comprehensive security audit, guaranteed answer accuracy, or uninterrupted hosting availability.
- My New Learning and New Project remain unavailable.

## Verification and publication

Release regression tests check version/date consistency, release-history selection, announcement isolation, historical v0.1.7 answers, and the release's account, learning, identity, and source safeguards. Publish the release commit and annotated v0.1.8 tag only after the selected checks pass. Hosted deployment and live smoke testing must be confirmed separately from a successful Git push.

197 selected regression tests passed with unmocked HTTP blocked and normal temporary-file access. The initial unrestricted discovery run was not a passing full-suite certification: sandbox file restrictions and incompletely isolated source tests required a bounded offline rerun. Local browser inspection confirmed the v0.1.8 badge, current-release selection, release date, preserved v0.1.7 entry, and unreleased v0.1.9 placeholder.
