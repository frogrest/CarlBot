# NVR Architecture & Role

## Overview
A Network Video Recorder (NVR) is a specialized computing appliance or dedicated server engineered to manage, record, and process digital video streams from IP surveillance cameras transmitted across a local area network (LAN) or virtual private network (VPN). Unlike legacy Digital Video Recorders (DVRs) which require direct coaxial cable connections to analog cameras, NVRs process digital video natively over IP infrastructure.

## Key Capabilities & Architecture
1. **Multi-Channel Ingestion**: Concurrently ingests multiple RTSP/ONVIF streams across diverse sites and camera models.
2. **Storage Management**: Implements redundant storage pools (typically RAID-5 or RAID-6 arrays of enterprise SATA surveillance hard drives) with automated retention policies, FIFO disk recycling, and storage integrity monitoring.
3. **Recording Schedules & Triggers**: Supports continuous 24/7 recording, motion-triggered recording, scheduled windows, and external sensor/alarm triggers.
4. **Playback & Export**: Provides multi-camera synchronized playback, video timeline scrubbing, forensic clip export, and stream redistribution to client monitors and operations centers.

## Common Incidents & Operational Guidance
- **Channel Offline / Disconnect**:
  - Verify IP network reachability to the assigned camera.
  - Test RTSP stream endpoint directly from the NVR console or diagnostic probe.
  - Differentiate between a single camera network drop and an entire switch subnet failure.
- **Storage Degradation**:
  - High disk utilization or failing drives require immediate technician notification to avoid loss of surveillance history.
  - Automatic deletion of historical recordings is prohibited without approved retention policy authorization.
