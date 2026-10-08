# RTSP Streaming & Protocols

## Overview
The Real-Time Streaming Protocol (RTSP, RFC 2326 and RFC 7826) is an application-level network protocol designed to establish and control real-time media streams between IP surveillance cameras and media clients such as Network Video Recorders (NVRs), AI video analytics boxes, and client viewing software. RTSP operates primarily over TCP port 554.

## Stream Delivery Architecture
1. **Control Session (RTSP)**: Negotiates session parameters using methods such as `DESCRIBE`, `SETUP`, `PLAY`, and `TEARDOWN`.
2. **Media Transport (RTP/RTCP)**: Video and audio payloads (typically H.264 or H.265 video codecs) are encapsulated in Real-time Transport Protocol (RTP) packets, monitored by RTCP statistics.
3. **Stream URI Format**:
   `rtsp://<username>:<password>@<device_ip>:554/stream1`

## Common Failure Modes & Diagnostics
- **RTSP Stream Down (`rtsp_down`)**:
  - *Symptom*: TCP/554 port is open and ping responds, but video stream transmission is interrupted or socket times out.
  - *Diagnosis*: Check network connectivity, ping latency, and port 554 reachability.
  - *Safe Autonomous Action*: In our technical lab, the autonomous agent is authorized to execute `reconnect-rtsp`. This initiates an RTSP session renegotiation in the emulator.
  - *Verification*: Confirm healthy video frames are received for at least 15 consecutive seconds.

- **RTSP Authentication Failure (`rtsp_auth_failure`)**:
  - *Symptom*: RTSP handshake fails with HTTP/RTSP status `401 Unauthorized`.
  - *Policy Boundary*: Autonomous credential changes are strictly prohibited. Modifying passwords or camera credentials could lock out surveillance systems or breach security policies.
  - *Action*: Escalate immediately to an on-site technician (`pending_technician`) to verify and update stream credentials in accordance with site security standards.
