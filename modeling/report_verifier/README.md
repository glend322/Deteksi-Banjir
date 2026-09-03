# Report Verification Engine

Validates crowd-sourced flood reports against rainfall, nearby reports, and CV output.

## Statuses
- **verified** — high confidence, cross-checked
- **unverified** — insufficient data
- **flagged** — suspicious, contradicts available data

## Usage

```python
from verifier import ReportVerifier

v = ReportVerifier()
result = v.verify(report)
print(result["verification_status"], result["confidence_score"])
```
