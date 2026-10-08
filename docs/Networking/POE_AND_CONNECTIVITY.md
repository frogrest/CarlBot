# PoE & Network Connectivity

## Overview
Power over Ethernet (PoE) is an IEEE standard networking technology that enables Ethernet network switches and injectors to transmit electrical operating power alongside digital data to remote IP devices (such as IP surveillance cameras, access points, and VoIP phones) over standard Cat5e or Cat6 twisted-pair cabling.

## Standards & Power Allocations
- **IEEE 802.3af (PoE Type 1)**: Supplies up to 15.4W at the switch port (approx. 12.95W delivered to camera). Suitable for standard static indoor cameras.
- **IEEE 802.3at (PoE+ Type 2)**: Supplies up to 30.0W at the switch port (approx. 25.5W delivered to camera). Required for outdoor cameras with built-in IR illuminators and heaters.
- **IEEE 802.3bt (PoE++ Type 3 / Type 4)**: Supplies up to 60W or 90W. Required for high-power PTZ (Pan-Tilt-Zoom) dome cameras with active motorized heaters and blowers.

## PoE Outage (`poe_off`) & Safety Boundaries
- **Symptom**: Complete loss of physical link; device does not respond to ping, ARP, or TCP handshakes; camera link LEDs on switch port are unlit.
- **Root Causes**: Tripped switch port power protection, cable damage, physical water ingress in RJ45 termination, or power supply overload.
- **Safety Boundary**: Autonomous agents cannot perform physical hardware repairs, re-terminate Ethernet cables, or diagnose physical short circuits.
- **Action**: Immediately escalate to an on-site technician (`pending_technician`) for physical port inspection, cable continuity testing, and power draw verification.
