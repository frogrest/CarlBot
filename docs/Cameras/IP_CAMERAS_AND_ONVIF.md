# IP Cameras & ONVIF Standards

## Overview
Internet Protocol (IP) cameras are digital video capture devices containing an optical image sensor, image signal processor (ISP), system-on-chip (SoC) video compression encoder, and network interface controller (NIC). Unlike analog surveillance cameras, IP cameras encode video streams into digital bitstreams (H.264/H.265) directly within the device and stream them across local IP networks.

## ONVIF Standards
ONVIF (Open Network Video Interface Forum) is the global open industry standard providing standardized communication interfaces for physical IP-based security products:
- **Profile S**: Basic video streaming via RTSP, device discovery via WS-Discovery, and basic PTZ control.
- **Profile G**: Edge storage management, local SD-card recording retrieval, and search.
- **Profile T**: Advanced video streaming supporting H.265 compression, HTTPS transport, and analytics metadata events.
- **Profile M**: Metadata payload transport for smart analytics and classification events.

## Camera Types: Fixed vs PTZ
- **Fixed Cameras (Dome / Bullet / Turret)**: Fixed optical orientation covering a dedicated viewing angle.
- **PTZ Cameras (Pan-Tilt-Zoom)**: Mechanical motors allow continuous 360-degree panning, vertical tilting, and high-ratio optical zoom. Require higher PoE power budgets (PoE+ or PoE++).
