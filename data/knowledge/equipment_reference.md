# Simulated Site and Equipment Reference

## Sites

| Site ID   | Name                 | Location              |
|-----------|----------------------|-----------------------|
| SITE-001  | Corporate Lobby      | Building A, Floor 1   |
| SITE-002  | Parking & Loading    | Building B, External  |
| SITE-003  | Server Room          | Building A, Basement  |

## Equipment

| Asset ID   | Site      | Name                  | Type    | IP          |
|------------|-----------|------------------------|---------|-------------|
| CAM-001    | SITE-001  | Lobby Camera           | Camera  | 10.10.1.11  |
| CAM-002    | SITE-002  | Parking Camera         | Camera  | 10.10.2.11  |
| CAM-003    | SITE-002  | Loading Dock Camera    | Camera  | 10.10.2.12  |
| CAM-004    | SITE-003  | Server Room Camera     | Camera  | 10.10.3.11  |
| NVR-001    | SITE-003  | Main NVR               | NVR     | 10.10.3.10  |
| NVR-002    | SITE-001  | Lobby NVR              | NVR     | 10.10.1.10  |
| AIBOX-001  | SITE-001  | Detection Box Alpha    | AI Box  | 10.10.1.20  |
| AIBOX-002  | SITE-002  | Detection Box Beta     | AI Box  | 10.10.2.20  |

## Simulated Credentials (ALL FAKE)

- Camera RTSP: `admin` / `FakePassword123!`
- NVR Web UI: `admin` / `FakeNvrPass456!`
- AI Box SSH: `aiuser` / `FakeBoxKey789!`

> ⚠️ These credentials are entirely simulated. They do not correspond to any real device.

## Network Layout (Simulated)

- VLAN 10: SITE-001 (10.10.1.0/24)
- VLAN 20: SITE-002 (10.10.2.0/24)
- VLAN 30: SITE-003 (10.10.3.0/24)
- Management: 10.10.0.0/24

All traffic between VLANs is simulated as routed. No actual network exists.
