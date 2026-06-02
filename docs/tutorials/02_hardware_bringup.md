# Tutorial 2: Hardware Bring-Up Verification

## Introduction

This tutorial demonstrates using SpecForge for a hardware bring-up
project — specifically, verifying a custom STM32-based microcontroller
board before it enters production. Hardware bring-up is a domain where
traceability and verification evidence are critical: a board that
ships without documented test evidence may fail in the field, and
without records, diagnosing the failure is expensive.

SpecForge is well-suited to hardware bring-up because it:
- Records test procedures as first-class artifacts
- Links verification evidence to specific requirements
- Generates an acceptance report suitable for manufacturing handover
- Provides an audit trail for regulatory and quality purposes

The scenario: a four-layer STM32F4 board for an industrial data logger.
The bring-up team needs to verify power, communications, storage, and
safety-critical features before signoff.

---

## Part 1: Project setup and requirements

### Initialising the project

```bash
specforge init ./board-v1.2 --git --name "STM32 Data Logger Board v1.2"
specforge config ./board-v1.2 --set git_commit=true
```

Setting `git_commit=true` means every artifact creation and status
update is automatically committed to git, building a timestamped
audit trail without any extra `--git` flags.

### Recording requirements from the hardware spec

Hardware bring-up requirements come from the electrical design
specification and the customer's interface control document (ICD). Each
requirement must be specific enough to be measured on the bench.

```bash
specforge add-req ./board-v1.2 "3.3 V rail tolerance" \
  --text "VCC_3V3 shall measure between 3.234 V and 3.366 V (±2%)
  under full load conditions. Full load is defined as:
  - MCU running at 168 MHz with FPU active
  - All four UART interfaces active
  - SPI flash read/write cycle in progress
  - SD card write operation in progress

  Measurement method: Keysight 34461A DMM at TP3 (VCC_3V3 test point).
  Measurement duration: 60 seconds continuous logging at 1 Hz." \
  --tag power

specforge add-req ./board-v1.2 "UART0 loopback data integrity" \
  --text "Debug UART (UART0, PA9/PA10, 115200 8N1) shall pass a 1000-byte
  loopback test with zero byte errors.

  Test configuration:
  - PA9 (TX) connected to PA10 (RX) via 0Ω jumper J12
  - Test firmware transmits 1000 bytes, verifies received bytes match
  - Timing: entire test must complete within 90ms (at 115200 baud)

  Acceptance: 0 errors in a 1000-byte test, repeated 100 times." \
  --tag comms

specforge add-req ./board-v1.2 "SPI flash device identification" \
  --text "Winbond W25Q64 SPI flash (U4) shall be readable at boot.
  The MCU bootloader shall:
  - Send JEDEC device ID command (0x9F) over SPI2 within 500ms of power-on
  - Receive device ID 0xEF4017 (Winbond W25Q64JV)
  - Log confirmation on UART0 debug console

  Acceptance: device ID received correctly within 500ms on 10
  consecutive power cycles." \
  --tag storage

specforge add-req ./board-v1.2 "Watchdog timer operation" \
  --text "The hardware watchdog (IWDG) shall reset the MCU if not petted
  within the configured timeout. Configuration: 2-second timeout.

  Acceptance:
  - Test firmware deliberately stops petting the watchdog
  - MCU resets within 2.0s ±200ms of last pet
  - Reset is confirmed by watchdog reset cause flag in RCC_CSR register" \
  --tag safety

specforge add-req ./board-v1.2 "ESD protection — I/O header" \
  --text "All signals on J1 (external I/O header, 12 pins) shall be
  protected by TVS diodes rated to a minimum of 15kV Human Body Model
  per IEC 61000-4-2 Level 4.

  Verification method: visual inspection of BOM and assembly drawing
  (D5-D16, PRTR5V0U2X, 5.5V clamp); functional test of I/O pins
  before and after applying 4kV ESD contact discharge." \
  --tag safety
```

### Recording constraints

```bash
specforge add-constraint ./board-v1.2 "Operating temperature −10°C to +70°C" \
  --text "All active components must be rated to the industrial temperature
  range (−40°C to +85°C minimum) or higher. Consumer-grade components
  (0°C to +70°C) are not permitted.

  This is a contractual requirement in the customer SOW, section 4.2.2." \
  --req REQ-0001 --req REQ-0002

specforge add-constraint ./board-v1.2 "RoHS 3 compliance" \
  --text "All components must be RoHS 3 (EU Directive 2015/863/EU) compliant.
  No exemptions. Component compliance must be documented in the BOM
  with manufacturer compliance certificates." \
  --req REQ-0001
```

### Recording assumptions

```bash
specforge add-assumption ./board-v1.2 "Bench supply current capacity ≥ 2A" \
  --text "Power supply tests assume a bench supply capable of 2A at 5V
  (for the 5V→3.3V LDO chain). The standard Keysight E36312A used in
  the lab has 3A capacity per channel. Verified: yes." \
  --req REQ-0001
```

---

## Part 2: Bring-up tasks

### Creating bring-up tasks

Each bring-up task corresponds to a specific test procedure. Tasks are
linked to the requirements they verify.

```bash
specforge add-task ./board-v1.2 "Measure VCC_3V3 under full load" \
  --text "
Procedure:
1. Connect bench supply to J5 (5V_IN), limit to 1.5A
2. Apply full load: run STM32_MaxLoad firmware from Flash
3. Confirm firmware running: UART0 transmits 'LOAD_ACTIVE' at 1 Hz
4. Connect Keysight 34461A to TP3, COM to GND_DIGITAL
5. Configure DMM: DC voltage, 10 readings/second
6. Log 60 consecutive readings to CSV

Pass criteria: all 60 readings within 3.234-3.366V
Record: min, max, mean, standard deviation" \
  --implements REQ-0001 --tag power

specforge add-task ./board-v1.2 "UART0 loopback test" \
  --text "
Procedure:
1. Fit loopback jumper at J12 (PA9-PA10 bridge)
2. Flash STM32_UART_Test firmware
3. Open serial terminal at 115200 8N1
4. Firmware runs 100 × 1000-byte loopback tests automatically
5. Observe PASS/FAIL on UART console and LED D1 (green=pass, red=fail)

Pass criteria: '100/100 PASS, 0 errors' on console" \
  --implements REQ-0002 --tag comms

specforge add-task ./board-v1.2 "SPI flash identification" \
  --text "
Procedure:
1. Flash STM32_Boot firmware (standard bootloader)
2. Power cycle the board
3. Observe UART0 output (115200 8N1)
4. Record time from power-on to 'FLASH OK' message
5. Repeat for 10 consecutive power cycles

Pass criteria:
- 'FLASH OK: EF4017' appears within 500ms on all 10 power cycles
- No 'FLASH ERR' or 'FLASH TIMEOUT' messages" \
  --implements REQ-0003 --tag storage

specforge add-task ./board-v1.2 "Watchdog timer test" \
  --text "
Procedure:
1. Flash STM32_WDT_Test firmware
2. Firmware pets watchdog for 30s (confirm no reset), then stops
3. Record time from last pet to reset (via UART message)
4. After reset, MCU firmware reads RCC_CSR for watchdog reset flag
5. Confirm IWDGRSTF bit is set

Pass criteria:
- Reset occurs within 1.8-2.2s of last pet
- IWDGRSTF flag confirmed set" \
  --implements REQ-0004 --tag safety

specforge add-task ./board-v1.2 "ESD protection verification" \
  --text "
Part A — Visual inspection:
1. Verify D5-D16 populated per assembly drawing revision B
2. Confirm PRTR5V0U2X marking on each TVS component
3. Verify correct orientation (polarity markers)

Part B — Functional test:
1. Configure ESD simulator to 4kV Contact Discharge, IEC 61000-4-2
2. Apply 10 discharges to each of 12 I/O pins
3. After each discharge set: verify I/O pin still functions correctly
   (GPIO toggle via STM32_IO_Test firmware, verify with logic analyser)

Pass criteria: all visual checks pass; all I/O pins functional
after ESD exposure" \
  --implements REQ-0005 --tag safety
```

---

## Part 3: Test execution and verification

### Executing and recording results

After running each bring-up task on board serial number SN-0042:

**Power rail measurement:**

```bash
specforge add-verification ./board-v1.2 "VCC_3V3 — SN-0042 PASS" \
  --text "
Board: SN-0042  |  Date: 2026-06-02  |  Tech: R.M.  |  Rev: PCB-B
DMM: Keysight 34461A #MY60123456  |  Cal. due: 2026-12-01

Results (60 readings over 60 seconds at full load):
  Min:    3.301 V ✓  (spec: 3.234 V)
  Max:    3.318 V ✓  (spec: 3.366 V)
  Mean:   3.309 V
  StdDev: 0.004 V

All 60 readings within specification.
CSV data: test_results/SN-0042_power_20260602.csv

PASS — REQ-0001 satisfied." \
  --req REQ-0001 --test TASK-0001

specforge update-status ./board-v1.2 REQ-0001 verified
```

**Communications test:**

```bash
specforge add-verification ./board-v1.2 "UART0 loopback — SN-0042 PASS" \
  --text "
Board: SN-0042  |  Date: 2026-06-02  |  Tech: R.M.

Console output:
  Running 100 loopback tests (1000 bytes each)...
  100/100 PASS, 0 errors, 87.3ms per test

Firmware: STM32_UART_Test v1.2 (build 89)
PASS — REQ-0002 satisfied." \
  --req REQ-0002 --test TASK-0002

specforge update-status ./board-v1.2 REQ-0002 verified
```

**SPI flash:**

```bash
specforge add-verification ./board-v1.2 "SPI flash ID — SN-0042 PASS" \
  --text "
Board: SN-0042  |  Date: 2026-06-02  |  Tech: R.M.

Power cycle results (10 consecutive):
  Cycle 1:  FLASH OK: EF4017  |  Time: 12ms ✓
  Cycle 2:  FLASH OK: EF4017  |  Time: 11ms ✓
  Cycle 3:  FLASH OK: EF4017  |  Time: 13ms ✓
  [... 7 more identical results ...]
  Cycle 10: FLASH OK: EF4017  |  Time: 12ms ✓

All 10 cycles: device ID correct, within 500ms spec (actual: 11-13ms).
PASS — REQ-0003 satisfied." \
  --req REQ-0003 --test TASK-0003

specforge update-status ./board-v1.2 REQ-0003 verified
```

**Watchdog:**

```bash
specforge add-verification ./board-v1.2 "Watchdog timer — SN-0042 PASS" \
  --text "
Board: SN-0042  |  Date: 2026-06-02  |  Tech: R.M.

Last pet to reset: 1.94 seconds ✓ (spec: 1.8-2.2s)
IWDGRSTF flag: SET ✓
PORRSTF (power-on reset): CLEAR ✓

Firmware: STM32_WDT_Test v1.0 (build 12)
PASS — REQ-0004 satisfied." \
  --req REQ-0004 --test TASK-0004

specforge update-status ./board-v1.2 REQ-0004 verified
```

**ESD protection:**

```bash
specforge add-verification ./board-v1.2 "ESD protection — SN-0042 PASS" \
  --text "
Board: SN-0042  |  Date: 2026-06-02  |  Tech: R.M.
ESD Simulator: Schaffner NSG 435 #SN78234  |  Cal. due: 2026-09-01

Part A (visual):
  D5-D16: All 12 TVS diodes present ✓
  Component marking: PRTR5V0U2X confirmed ✓
  Orientation: correct per drawing ✓

Part B (functional, 4kV contact, 10 shots per pin):
  All 12 pins functional after ESD exposure ✓
  GPIO toggle verified with Saleae Logic 8 on all pins ✓

PASS — REQ-0005 satisfied." \
  --req REQ-0005 --test TASK-0005

specforge update-status ./board-v1.2 REQ-0005 verified
```

### Release gate and signoff document

```bash
specforge check ./board-v1.2
# Release Gate: PASS ✅

specforge report ./board-v1.2 \
  --output ./board-v1.2/BOARD_SIGNOFF_SN-0042.md

specforge export ./board-v1.2
```

The signoff report lists every requirement, its measurement result, and
the technician who verified it. This document accompanies the board into
production and is archived in the project git history.

---

## Summary

This tutorial demonstrated SpecForge applied to hardware bring-up:

- **Requirements** were written from the hardware spec with specific,
  measurable acceptance criteria including measurement methods and
  tolerances
- **Constraints** captured non-negotiable design requirements from the
  customer contract
- **Tasks** were written as detailed test procedures, not just task
  descriptions — specific enough for any technician to follow
- **Verification evidence** recorded actual measured values, equipment
  serial numbers, calibration dates, and the technician's name —
  the kind of detail that matters in an audit
- **The release gate** confirmed all five requirements were verified
  before generating the signoff document

The approach scales naturally to more complex boards. For a 50-point
bring-up checklist, create 50 requirements, 50 tasks, and record
verification for each. The traceability matrix export shows at a glance
which tests cover which requirements and whether any gaps exist.
