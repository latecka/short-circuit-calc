# Energa Diff Analysis

## Reference vs current model

The ENERGA-aligned dataset differs materially from the older project snapshot in these areas:

- External grid reduced from `274.15 MVA` to `199.3 MVA`, but still uses max-case IEC 60909 voltage factor `c_max = 1.1`.
- 22 kV and 6.3 kV feeders changed from single conductors to parallel cables.
  - `line_22kv_ssd_tpa`: `1 -> 2` parallel cables
  - `line_t1_6tpa`: `1 -> 2`
  - `line_t7_6tpa`: `1 -> 4`
  - `line_g1`: `1 -> 3`
  - `line_slatina`: `1 -> 4`
- `Kobka 28` is the feeder from `G1` into `R 6 kV TpA`.
- `T101` is connected to `bus_6kv_tpa` and provides the only active LV auxiliary contribution in the reference case.
- `T2` is physically present but disconnected on the 6 kV side, so it does not contribute to the reference short-circuit.
- `T102 + Ekv2` are not part of the reference ENERGA contribution path.
- Generator ratings were updated to the ENERGA values:
  - `G1`: `11.338 MVA`, `Xd'' = 14.1%`
  - `HG1`: `1.25 MVA`, `Xd'' = 14.0%`

## Probable root causes of the 40% undervaluation

1. Generator stator resistance was being interpreted as percent even when imported or stored as milliohms.
   - In the affected datasets, values like `Ra = 96` and `Ra = 127` are physically plausible as `mOhm`, but not as `%`.
   - Treating them as percent inflates generator resistance by roughly two orders of magnitude and almost removes generator fault contribution.
2. Legacy import aliases were incomplete for real plant data.
   - External-grid aliases such as `s_sc_max_mva`, `rx_max`, and `R_X`
   - Transformer aliases such as `vk_percent`, `vkr_percent`
   - Cable aliases such as `parallel_cables`
3. The remaining gap after fixing generator `Ra` was caused by the transformer model, not by the validated topology.
   - The max-case Y-bus was missing the IEC 60909 network-transformer correction factor `KT`.
   - Applying `KT = 0.95 / (1 + 0.6 * xT)` to non-PSU two-winding transformers in max mode closes the residual error without enabling extra branches.

## Checks completed

- `calc_sc()` already runs the engine in `mode="max"` for the ENERGA validation case.
- Runtime builders now normalize external-grid, transformer, cable, and generator-resistance aliases used by the plant data.
- The large undervaluation pattern matched a network where generator contribution was effectively suppressed by misinterpreted `Ra`.
- With corrected `Ra` handling and transformer `KT` applied in max mode, the ENERGA smoke calculation lands within the requested `+/-1%` band while keeping the current topology unchanged.

## Code changes made

- Added missing import aliases for external grids, transformers, lines, and generator resistance units.
- Added runtime normalization for generator `Ra` values from:
  - `Ra_ohm`
  - `Ra_mohm`
  - large legacy `Ra` values that are actually stored in `mOhm`
- Added IEC 60909 transformer correction factor `KT` for non-PSU two-winding transformers in max-case Y-bus assembly.
- Added an ENERGA regression test that asserts Ik3'' stays within `+/-1%` for:
  - `bus_22kv_tpa`
  - `bus_6kv_tpa`
  - `bus_g1`
  - `bus_hc_slatina`