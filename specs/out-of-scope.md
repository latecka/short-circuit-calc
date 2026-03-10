# Out of Scope for V1

This document lists configurations and features not supported in V1.

| Area | System Behavior |
|------|-----------------|
| Asymmetric transformers (other than 2/3-winding) | Hard error |
| Transformers with OLTC in Z0 model | Warning - OLTC ignored in Z0 |
| Motors in min fault state | Contribution excluded |
| Dynamic stability and transients | Out of scope |
| Harmonic analysis | Out of scope |
| Protection coordination (selectivity) | Out of scope |
| CSV import | Not supported in V1 |
| Multi-phase asymmetric networks | Out of scope |
| Power flow (load flow) | Out of scope |
| PSU with multiple generators | Hard error |
