# AI Box Analytics & Inferencing

## Overview
An AI Box is an on-premises edge computing hardware appliance equipped with dedicated neural processing units (NPUs), embedded GPUs, or machine-learning vision accelerators. It connects to the local surveillance network, ingests live RTSP camera feeds, and executes deep learning computer vision algorithms directly at the edge, reducing cloud bandwidth requirements and enabling sub-second response times.

## Core Analytics Capabilities
1. **Object Detection & Classification**: Identifies and categorizes objects in real-time (people, vehicles, motorcycles, bicycles, animals).
2. **Behavioral Analytics**: Detects perimeter line-crossing, loitering, wrong-way movement, and unauthorized zone entry.
3. **Safety & Compliance**: Monitors personal protective equipment (PPE like hardhats and high-visibility vests), vehicle parking violations, and overcrowding.
4. **Metadata & Telemetry Stream**: Translates pixel feeds into structured telemetry events forwarded to the central helpdesk and security dispatch dashboards.

## Operational Failure Modes & Safe Recovery
- **AI Service Down (`ai_service_down`)**:
  - *Symptom*: RTSP camera stream is alive and reachable, but the edge computer vision inference process has stopped responding, exited unexpectedly, or frozen.
  - *Diagnostics*: Verify device reachability, check process status for the inference daemon, and review system memory/CPU counters.
  - *Safe Autonomous Action*: In our technical lab, the agent is permitted to execute `restart-ai-service`. This restarts the containerized edge inference daemon.
  - *Verification*: Verify that detection events resume emitting within 30 seconds post-restart.
- **Resource Saturation & Thermal Throttling**:
  - When stream channel count exceeds NPU compute capacity or ambient temperatures cause thermal throttling, the inference worker may drop frames.
  - A technician must rebalance channel load or inspect physical cooling rather than modifying camera resolutions arbitrarily.
