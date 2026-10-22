# Climate Entity Devices - Phase 5: Real-Device Verification - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove on a real Home Assistant OS instance, with real devices, what unit tests cannot: that the climate-backed roles command physical equipment correctly, safely and without fighting, in both control styles, across restarts and device outages. Output is a filled-in results table and a go/no-go for release.

**Architecture:** No code. This is a checklist run by the coordinator on a HAOS instance with the branch installed as a custom component. Two rigs cover the agreed scope from the issue. Nothing here may contain real entity ids, addresses or hostnames in anything committed: use the placeholders below in notes and the results table, keep the real mapping locally.

**Tech Stack:** Home Assistant OS, the thermostat built from the feature branch, Developer Tools (States, Actions, Template, Logs), the History panel.

**Spec:** `docs/superpowers/specs/2026-10-20-climate-entity-devices-design.md`
**Previous phases:** 1 to 4 merged to the test branch; the full automated suite and `./scripts/docker-lint` are green.

---

## Placeholders

| Placeholder | Meaning |
|---|---|
| `AC` | the real air conditioner's climate entity (standalone rig) |
| `IR_AC` | the real infrared-controlled air conditioner's climate entity (mixed rig; reports an assumed state) |
| `PLUG` | the switch entity of a smart plug powering a heater |
| `ROOM_T` | a room temperature sensor |
| `ROOM_H` | a room humidity sensor |
| `WINDOW` | a window contact sensor |
| `DST` | the thermostat entity under test |

Substitute locally. Do not write the real values into this repository.

---

## Rigs

**Rig A, standalone AC.** One air conditioner that supports heat, cool, fan only and dry. All four roles (`heater`, `cooler`, `fan`, `dryer`) point at `AC`. No `target_sensor`: the AC's own `current_temperature` is the temperature source. `humidity_sensor` is `ROOM_H` if available, otherwise skip the dry cases that need it.

**Rig B, mixed room.** An infrared AC as cooler (`IR_AC`, assumed state), a smart plug powering a heater (`PLUG`), a room temperature and humidity sensor (`ROOM_T`, `ROOM_H`) and a window opening (`WINDOW`). `target_sensor` is `ROOM_T` (not the AC).

---

## Task 0: Preparation and safety

- [ ] **Step 1: Back up and isolate.** Take a HAOS backup. Use a test room or a time when the equipment may be cycled freely. Keep manual control of the devices (remote, breaker) within reach.
- [ ] **Step 2: Install the branch build** as the custom component (replace `custom_components/dual_smart_thermostat`), restart Home Assistant, confirm the integration loads with no errors in **Settings > System > Logs**.
- [ ] **Step 3: Enable debug logging** for `custom_components.dual_smart_thermostat` (Settings > Devices & services > the integration > Enable debug logging, or `logger:` in YAML) so every command the thermostat sends is visible.
- [ ] **Step 4: Record the baseline.** For each real device note entity state, supported `hvac_modes`, `min_temp`, `max_temp`, `target_temp_step`, whether `assumed_state` is true, and the unit system. A mode the device does not list cannot be a passing case: mark it N/A, do not force it.
- [ ] **Step 5: Define pass evidence.** Every case below passes only on two sources agreeing: (a) the entity state or History graph and (b) the debug log lines for the commands sent. For a physical effect (compressor, vane, display) also confirm it by sight or sound.

---

## Task 1: Setup paths (UI and YAML)

Run each once per rig on a fresh entry.

- [ ] **Step 1: Config flow.** Add the integration through the UI: the heater / cooler / fan / dryer pickers list `climate` entities; for Rig A the temperature sensor field can be left empty; the **Climate Entity Control** step appears after the entity step and before features; openings and presets are still the last two steps.
- [ ] **Step 2: Options flow.** Open the entry options: **Climate Entity Control** is the first step, shows the saved `control_style` and `setpoint_offset`, and saving changes them. The integration reloads without errors.
- [ ] **Step 3: Reconfigure.** Reconfigure the entry, swap one role between a switch and a climate entity and back; the climate step appears only while a climate role exists, and `control_style` / `setpoint_offset` are gone from the entry data after the swap back (Settings > Devices & services > entry > Download diagnostics, or `config/.storage/core.config_entries`).
- [ ] **Step 4: YAML.** Repeat the rig in YAML with `control_style: on_off`; a typo (`control_style: auto`) and `control_style` without any climate role are both rejected at config check with a readable message.
- [ ] **Step 5: Record** results in the table (Task 8).

Pass: all five behave as described; no errors in the log.

---

## Task 2: Rig A, standalone AC, `on_off`

Config: `control_style: on_off`, `setpoint_offset: 0`, `min_cycle_duration` of 5 minutes, no `target_sensor`.

- [ ] **Step 1: Temperature source.** `DST` shows `current_temperature` equal to the AC's `current_temperature` and follows it when it changes.
- [ ] **Step 2: Heat.** Set `DST` to Heat with a target above the room temperature by more than the tolerance. Log shows `set_hvac_mode heat` then `set_temperature` once; `AC` enters heat; `DST` `hvac_action` is heating. Raise the target further: exactly one extra `set_temperature`, no `set_hvac_mode`.
- [ ] **Step 3: Target reached.** Lower the target below the room temperature. After the min cycle has elapsed `AC` is turned off (`climate.turn_off`); `hvac_action` is idle. Before the min cycle has elapsed it is **not** turned off (record the time to compare).
- [ ] **Step 4: Cool.** Same as Heat for Cool with a target below the room temperature. The previous heat role must not interfere: one `set_hvac_mode cool`, no repeated mode commands on later ticks.
- [ ] **Step 5: Fan only and Dry.** Select Fan only: `AC` goes `fan_only`, no target is sent. Select Dry (needs `ROOM_H` above target): `AC` goes `dry`, no target is sent.
- [ ] **Step 6: Mode walk.** Walk Heat, Cool, Fan only, Dry, Off. After each change the AC is in exactly the expected mode and the log shows one `set_hvac_mode` per transition, never two roles commanding in the same second.
- [ ] **Step 7: Off.** Selecting Off turns `AC` off. Keep `DST` Off for 10 minutes with `keep_alive` enabled: `AC` stays off.
- [ ] **Step 8: Off means off.** With `DST` Heat or Cool and the AC engaged, set `AC` to `auto` (or any mode none of the roles owns) from its own card or remote, then switch `DST` Off: `climate.turn_off` is sent and the AC ends off. Repeat with `DST` already Off and the AC set to `auto` from the remote while `keep_alive` is enabled: the next keep-alive tick turns it off.

Pass: every step as written; no mode flapping in the 30 minute History graph; no unexpected `turn_off`.

---

## Task 3: Rig A, `setpoint`

Change `control_style` to `setpoint`, `setpoint_offset` to `0`.

- [ ] **Step 1: Engage.** Heat with a target above room: `AC` goes heat with the target pushed.
- [ ] **Step 2: No cycling.** Set the target below room temperature while staying in Heat: the thermostat sends **no** `turn_off`; the AC stays in heat and regulates itself (its own display shows idle/standby). `DST` `hvac_action` shows heating (spec OQ4: "engaged").
- [ ] **Step 3: Mirror.** Change the target, switch a preset (one with a different temperature) and change HVAC mode: every change reaches the AC (one `set_temperature` per change; none when the value did not change).
- [ ] **Step 4: Per-role offsets.** Set `cooler_setpoint_offset` to `-3` and `heater_setpoint_offset` to `2`: in Cool the AC receives target minus 3, in Heat target plus 2, each clamped to the AC's range (a target near the maximum with a positive heater offset stops at `max_temp`). Confirm half degree targets round to the AC's step. There is no other offset: fan and dryer modes send no temperature.
- [ ] **Step 5: Min cycle ignored.** With `min_cycle_duration` 30 minutes, switch Off immediately after switching on: the AC turns off at once (no cycle wait).
- [ ] **Step 6: Return to `on_off`** and confirm Task 2 step 3 behaviour is back.

Pass: as written; the AC never receives a mode or temperature command it already has.

---

## Task 4: Rig B, mixed room

Config: `heater: PLUG`, `cooler: IR_AC`, `target_sensor: ROOM_T`, `humidity_sensor: ROOM_H`, `openings: [WINDOW]`, `control_style: on_off`, `min_cycle_duration` 5 minutes.

- [ ] **Step 1: Independence.** Heat with target above room: `PLUG` turns on, the IR AC receives nothing. Cool with target below room: the IR AC receives `set_hvac_mode cool` and a target, `PLUG` is untouched (verify in History).
- [ ] **Step 2: Assumed state.** The IR AC's reported state does not confirm commands. Cool for 15 minutes with several temperature updates: the log shows **one** `set_hvac_mode cool` per engagement (not one per sensor tick); `DST` shows cooling throughout.
- [ ] **Step 3: Stop.** Reach the target: the IR AC receives `climate.turn_off` and `DST` shows idle. Verify the AC really stopped (unit, not just the entity).
- [ ] **Step 4: Opening.** Open `WINDOW` (after any configured timeout): the running device (heater or cooler) is stopped; `hvac_action_reason` shows opening. Close it: control resumes and the device restarts with the current target.
- [ ] **Step 5: Heat to cool swap.** Move the target so `DST` switches from heating to cooling (or switch the mode): `PLUG` turns off, the IR AC engages; never both on.
- [ ] **Step 6: Keep-alive resend.** With `keep_alive` enabled, confirm the assumed-state AC is re-sent its mode on the keep-alive tick while engaged (this is the intended way to resynchronise an IR device that was changed by its remote), and that an idle role never turns the other off.
- [ ] **Step 6b: Offset on the IR AC.** Give the cooler a `cooler_setpoint_offset` of `-2` (`on_off`): the IR AC receives the target minus 2 once per engagement and again only when the target changes.
- [ ] **Step 7: Setpoint variant.** Change the cooler to `setpoint`; repeat Step 4: the window pauses and restores the IR AC with its target.

Pass: as written; no moment with both heater and cooler on; no command storm in the log.

---

## Task 5: Device safety and failure modes (both rigs)

- [ ] **Step 1: Min cycle protection.** Toggle the temperature across the target quickly (or change the target repeatedly) with `on_off` and 5 minute min cycle: the compressor is never restarted inside 5 minutes (check the History timeline of the AC state).
- [ ] **Step 2: Device offline.** Make the climate entity unavailable (power the AC off at the plug or disable its integration). The log shows skipped commands and no errors that repeat every second; `DST` stays available. Bring it back: control resumes by itself within one sensor update.
- [ ] **Step 3: Sensor loss (Rig B).** Stop `ROOM_T` updates for longer than `sensor_stale_duration`: the thermostat stops the devices; on recovery it resumes. Rig A repeats this by making the AC stop reporting temperature (offline).
- [ ] **Step 4: Unsupported mode.** On a device that does not list `dry` select Dry: one warning in the log, no command sent, no repeats.
- [ ] **Step 5: Manual override.** Change the device with its remote while `DST` is idle and while it is engaged (non-assumed AC): record how the next control tick reacts (a non-assumed device re-asserts the thermostat's decision, an assumed one does not know). Note anything surprising for the docs.
- [ ] **Step 6: Restart.** Restart Home Assistant with the AC engaged and with it off, in both styles: no spurious commands at startup, the state is restored, control picks up within one sensor update. Repeat after **Developer tools > YAML > Reload** of the climate integration.
- [ ] **Step 7: Self reference.** Configure `DST` as its own device in a scratch YAML (copy): the entity is refused with a clear error, nothing loops.

Pass: no repeated error lines, no uncontrolled command bursts, equipment never short-cycled.

---

## Task 5b: Fan speed (both rigs)

Use the device's own fan modes exactly as they are listed on the climate entity (for example `quiet`, `strong`); do not expect low/medium/high.

- [ ] **Step 1: Rig A, fan modes shown.** `DST` lists the AC's `fan_modes` verbatim as its `fan_modes` and shows the AC's current `fan_mode`. Choose a different fan mode on `DST`: one `climate.set_fan_mode` reaches the AC and the unit's own display agrees.
- [ ] **Step 2: Rig A, survives a turn on.** Select a non-default fan mode, then let the thermostat stop and restart the AC (Heat to target and back, or Off then Heat). After the AC restarts the log shows `set_hvac_mode` followed by `set_fan_mode` with your selection and the unit runs at that speed (many ACs reset it; this is the case that matters).
- [ ] **Step 3: Rig A, fan role.** Select Fan only: the AC runs `fan_only` at the selected speed, and the speed is sent once, not twice.
- [ ] **Step 4: Rig A, restart.** Restart Home Assistant with a non-default fan mode selected: `DST` shows the same fan mode afterwards and applies it on the next turn on.
- [ ] **Step 5: Rig B, cooler-only IR AC.** `DST` offers the IR AC's fan modes although the AC fills only the cooler role. Select one: it is sent; after the next cooling start it is re-sent (an IR device never confirms, so check the unit itself responds, not the entity state).
- [ ] **Step 6: Rig B, separate fan entity.** Add a separate `fan` entity to the fan role (a real fan, or the plug powering a fan if it exposes presets): `DST`'s `fan_modes` become that fan's modes, changing `fan_mode` drives that fan only, and the IR AC receives no `set_fan_mode` at all, including after it restarts cooling.
- [ ] **Step 7: Late device.** Restart Home Assistant while the AC is unplugged, then plug it in: the fan modes appear on `DST` without a reload and a restored selection is applied.
- [ ] **Step 8: No `fan_modes`.** If a device exposes no fan modes `DST` shows no fan control and logs nothing repeated.

Pass: the selected speed is the speed the unit actually runs at after every start; the AC's speed is never changed when a separate fan entity is configured.

---

## Task 6: Regression of switch-only setups

- [ ] **Step 1:** Keep one existing switch-only thermostat in the same instance throughout all tasks: its behaviour (cycling, openings, presets, keep-alive) is unchanged and its log shows no climate-related lines.
- [ ] **Step 2:** Verify a valve-backed heater, if one is available, still opens and closes.

Pass: no behavioural difference from the released version.

---

## Task 7: Capture and clean up

- [ ] **Step 1:** Save the debug log slice for each rig (commands only, with entity ids replaced by the placeholders) for the PR description if useful.
- [ ] **Step 2:** Revert the instance: restore the backup or reinstall the released component; remove the test entries.
- [ ] **Step 3:** Turn debug logging off.

---

## Task 8: Results

Fill in and report back (placeholders only):

| Case | Rig | Style | Result (pass / fail / N/A) | Notes (time, log excerpt id) |
|---|---|---|---|---|
| 1.1 Config flow | A, B | | | |
| 1.2 Options flow | A, B | | | |
| 1.3 Reconfigure | A, B | | | |
| 1.4 YAML and validation | A, B | | | |
| 2.1 to 2.8 Standalone AC | A | on_off | | |
| 3.1 to 3.6 Setpoint (per-role offsets in 3.4) | A | setpoint | | |
| 4.1 to 4.7 Mixed room | B | on_off / setpoint | | |
| 5.1 to 5.7 Safety | A, B | both | | |
| 5b.1 to 5b.8 Fan speed | A, B | both | | |
| 6.1 to 6.2 Regression | any | | | |

Decision rule: release needs every non-N/A case to pass. Any fail is filed as a defect against the matching phase (cases 1 against phase 4, 2 and 4 against phases 1 and 3, 3 against phase 2, 5b against phase 3b, 5 against the area named in the note), fixed with a regression test in `tests/features/test_climate_backed_devices.py` (or the matching flow test file), and the failed case re-run.

## Acceptance (phase 5)

1. Both rigs pass every applicable case, or each failure has a tracked defect and a re-run.
2. Off-means-off on a foreign mode (2.8) and the setpoint-style `hvac_action` behaviour (3.2, "engaged") are observed and recorded for the owner.
3. No real entity ids, addresses or hostnames appear in the repository, the PR or the results.
