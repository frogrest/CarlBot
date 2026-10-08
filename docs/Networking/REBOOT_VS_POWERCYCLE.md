# Reboot vs. Power Cycling: Definitions and Procedures

## Overview
In IT technical support and field surveillance operations, restarting equipment is a standard troubleshooting step. However, **Rebooting** and **Power Cycling** are distinct procedures with different operational impacts, physical mechanisms, and risk profiles.

## What Does "Reboot" Mean? (Soft Reboot / Warm Restart)

A **Reboot** (or soft reboot) is an operating-system-directed restart where electrical power to the motherboard and components remains continuously supplied.

### Characteristics
- **Graceful Shutdown**: The operating system sends `SIGTERM` signals to running processes, closes active network sockets, flushes dirty disk buffers, and cleanly unmounts file systems (preventing database and video archive corruption).
- **Firmware Reload**: The CPU clears RAM and re-executes the bootstrap loader without cutting DC power.
- **Trigger Methods**: Software commands (`sudo reboot`, `systemctl restart service`), web management GUI restart buttons, or API automation (e.g. `restart-ai-service`).

### When to Use a Reboot
- Memory leaks or high RAM exhaustion causing service sluggishness.
- Application process crashes or hung child threads.
- Minor software updates or configuration profile reloads.
- The operating system and management interface remain responsive.

---

## What Does "Power Cycling" Mean? (Hard Reboot / Cold Boot)

A **Power Cycle** (or cold reboot) is the complete, physical interruption of electrical power to the hardware, allowing internal capacitors to fully discharge before reapplying power.

### Characteristics
- **Physical Disconnection**: AC power cords are unplugged, a smart PDU outlet is toggled off, or a PoE switch port is disabled.
- **Hardware Reset**: Clears non-volatile hardware controller states, resets network PHY chipsets, clears ASIC registers, and forces hardware thermal recalibration.
- **Wait Duration Rule (10 to 30 Seconds)**: Always wait **at least 15–30 seconds** before restoring power. This allows power supply capacitors to drain completely. Restoring power immediately can cause transient electrical surges or leave registers in undefined states.

### How to Power Cycle Surveillance Cameras
- **PoE Port Bounce**: From the managed PoE switch console or web UI, disable PoE on the specific camera port, wait 15 seconds, and re-enable PoE (`poe_bounce`).
- **Physical RJ45 Disconnect**: Unplug the Ethernet patch cable at the patch panel or switch, wait 15 seconds, and re-insert firmly until the latch clicks.
- **DC Power Adapter**: For cameras on 12V DC or 24V AC, unplug the power brick from the outlet or disconnect the screw terminal.

### When to Use a Power Cycle
- **Kernel Panic / Hard System Lockup**: The OS is completely frozen and does not respond to ping, SSH, keyboard, or console input.
- **Hardware PHY / Transceiver Freeze**: The network interface chip has stopped transmitting packets (no link lights or stuck lights) even though the camera is powered.
- **Failed Soft Reboot**: A software reboot was triggered but failed to complete after 10+ minutes.
- **PoE Power Faults**: Switch PoE controller tripped due to in-rush current or outdoor temperature fluctuations.

---

## Safety and Best Practices
1. **Prefer Soft Reboot First**: Always attempt a graceful software restart before performing a hard power cycle. Hard power-offs on NVRs or servers can corrupt database tables (such as SQLite indices or video catalog files).
2. **Never Autonomous for High-Risk Hardware**: In our operations architecture, autonomous power switching of core network switches, PDU breakers, or storage arrays is prohibited without human technician sign-off.
