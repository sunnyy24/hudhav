# AIMD External Origin Discovery

AIMD external origin discovery is an explicit, opt-in provider operation. Local forensic analysis and local provenance continue to run without any external transmission.

## Provider Architecture

Providers implement an asynchronous `OriginProvider` protocol and return a normalized `ProviderResult`. The current adapter is `google_web_detection`, which calls the official Google Cloud Vision Web Detection API. Provider output is attributed and normalized without adding missing fields.

The route is:

```text
POST /api/origin/search/{file_id}
```

The request must contain `{ "consent": true }`. Consent is checked before the uploaded file is opened or sent anywhere.

## Policy

External discovery is disabled unless:

```text
ORIGIN_SEARCH_ENABLED=true
GOOGLE_VISION_API_KEY=<server-side secret>
```

The API key must remain server-side. It is never returned in provider responses or sent to Next.js.

The default development state is disabled. With discovery disabled, the endpoint returns `UNAVAILABLE` and local analysis remains unaffected.

## Provider Results

- `VERIFIED`: the provider returned one or more source matches.
- `UNKNOWN`: the provider completed a search but returned no verified public source.
- `ERROR`: the provider request failed, timed out, or returned an unusable response.
- `UNAVAILABLE`: policy, configuration, or provider capability prevents a search.

Google full matching images are normalized as `EXACT` with `VERIFIED` strength. Google partial matching images are normalized as `PARTIAL` with `INFERRED` strength. URLs, titles, and evidence are included only when returned by Google. Missing first-seen dates and platforms remain `null`.

## Privacy

The user must explicitly choose `Trace Online Origin` and confirm that the image may be transmitted to a third-party provider. AIMD does not automatically send uploads to external services.

## Cache

Successful `VERIFIED` and `UNKNOWN` provider responses are cached in the existing local SQLite provenance database for ten minutes per file/provider. This prevents repeated clicks from issuing unnecessary provider calls. Errors and unavailable results are not used as successful search cache entries.

The database stores search metadata and normalized matches only. It does not store another copy of the image.

## Scope and Limitations

Google Web Detection searches Google's web index; it does not guarantee coverage of every social platform or private content. A result is evidence returned by Google, not proof of original authorship or first publication. No result does not prove that the image has never appeared online.

AIMD does not scrape Google Lens, Yandex, Instagram, Facebook, X, TikTok, YouTube, or Reddit. It does not bypass authentication, rate limits, robots controls, or platform terms.

AIMD does not claim that a media file originated from a social-media platform unless verifiable source evidence is returned by a provider.