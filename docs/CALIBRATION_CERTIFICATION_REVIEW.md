# Calibration Certification Review

This layer bridges the existing temporal isotonic calibration assessment into a **policy-driven human certification review** without self-certifying the model.

The purpose is to make the Black Diamond probability gate auditable while preserving V7/V7.1's rule that market-specific stress and acceptance criteria must be predeclared rather than invented after seeing results.

## Temporal fitting

The underlying calibration engine still requires:

- certified pregame forecast rows
- training outcomes available by the fit cutoff
- validation outcomes available only after the fit cutoff and by the assessment cutoff
- unique event/forecast identities
- explicit scope
- minimum training and validation rows/events
- immutable training fit

The certification review calls that engine directly; it does not accept a pasted Brier number as a substitute.

## Predeclared acceptance policy

Before the fit time, the caller must declare a market/scope-specific policy containing:

- policy ID
- declaration timestamp
- maximum held-out calibrated Brier
- maximum held-out expected calibration error (ECE)
- maximum held-out calibration gap
- minimum fitted isotonic block count
- whether held-out calibrated Brier must be no worse than the raw probability Brier

No universal values are hard-coded by this module. The values are an external predeclared policy input and are recorded in the immutable review receipt.

If the policy was declared at or after fitting, the review remains HOLD.

## Reliability metrics

From the held-out calibrated reliability table:

`ECE = sum(bin_count / N * abs(mean_probability - hit_rate))`

The maximum absolute bin gap is also recorded.

The review evaluates:

- held-out calibrated Brier
- ECE
- max calibration gap
- raw-vs-calibrated Brier, when the policy requires it
- smallest fitted isotonic block size

## Immutable evidence

The review separately hashes:

- exact training input
- exact validation input
- fitted calibration map

The complete review is also SHA-256 fingerprinted and can be reverified. Tampering with sample counts, calibration blocks, metrics, policies, or eligibility breaks the receipt.

## Strongest possible review state

A clean package may reach:

`CALIBRATION_CERTIFICATION_REVIEW_ELIGIBLE`

That is not a certificate.

Every review output remains:

- `calibration_verified = false`
- `calibration_certificate_issued = false`
- `model_promotion_applied = false`
- `requires_human_acceptance = true`
- `forecast_status = HOLD`
- `wager_status = NOT APPROVED`

Actual production certification remains a separate reviewed action.

## Candidate probability uncertainty diagnostic

For an eligible review receipt, a raw candidate probability can be mapped through the fitted isotonic blocks.

The point estimate is the isotonic block hit rate.

Local uncertainty is estimated with a Jeffreys posterior:

`p ~ Beta(wins + 0.5, losses + 0.5)`

The diagnostic uses >=100,000 deterministic-seed posterior draws and reports:

- isotonic calibrated point probability
- Jeffreys P05
- Jeffreys P50
- Jeffreys P95

It separately reports whether the modeled values clear:

- calibrated point probability >=87%
- P05 lower bound >=80%

These are **modeled probability diagnostics only** until an independently accepted calibration certificate exists and all other V7 gates pass.

## Why this matters

A raw model score of 90% is not automatically a calibrated 90% probability.

Likewise, a large projection cushion or 100,000 simulation trials do not establish calibration.

This layer forces the system to prove temporal held-out reliability before a probability can even enter certification review.

## CLI

`calibration_certification_cli.py` exposes:

- `assess`
- `verify`
- `candidate`
