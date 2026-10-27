# Incident Postmortem Report

## Top-3 Failing Endpoints
1. `/api/v1/payment/charge` (1420 errors)
2. `/api/v2/auth/token` (890 errors)
3. `/api/v1/inventory/lock` (530 errors)

## Root Cause Summary
- TLS handshake timeout, Redis pool exhaustion, and SKU row-level lock contention.
