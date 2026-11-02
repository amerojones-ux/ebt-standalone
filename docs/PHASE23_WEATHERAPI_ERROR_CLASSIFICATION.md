# Phase 23 — sanitized WeatherAPI error classification

Status: **OFFLINE HARDENING / NO LIVE CALL**

WeatherAPI documents provider error codes that distinguish:
- 1002: missing API key
- 2006: invalid API key
- 2007: monthly quota exceeded
- 2008: API key disabled
- 2009: current plan does not permit the requested resource

The one-shot probe now parses at most 4 KiB of an HTTP error body, retains only the numeric provider code, maps it to a sanitized internal category, and discards the provider message. Raw error bodies and messages are never logged.

This improves diagnostics for the future bounded authentication probe without weakening the dual-consent, no-redirect, one-request, secret-safe execution gates.

Sources reviewed: WeatherAPI official error-code documentation and terms/pricing. No API request was made.
