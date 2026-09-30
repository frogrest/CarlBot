# Simulated CCTV Troubleshooting Knowledge Base

## RTSP Stream Issues

- **RTSP down with healthy ping** commonly indicates a stream worker or service-level
  issue rather than total network loss. The camera is reachable but the RTSP service
  has crashed or is unresponsive.
  - *Safe action*: Reconnect the RTSP stream (simulated).
  - *Verify*: RTSP check should return `true` after reconnect.

- **RTSP authentication failure** means the camera is reachable and the RTSP service
  is running, but the supplied credentials are rejected. This typically happens after
  a password rotation where the NVR/monitoring profile was not updated.
  - *Technician action*: Verify and correct RTSP credentials on both the camera and
    the NVR/monitoring configuration.
  - The agent must NEVER change credentials automatically.

- **Wrong RTSP path** means the configured stream path (e.g., `/live/ch0`) does not
  match what the camera expects. This happens after firmware updates that change the
  default path, or after misconfiguration.
  - *Technician action*: Verify the correct RTSP path in the camera's web interface
    and update the monitoring configuration.

## Power and Connectivity

- **PoE / power off** makes the camera completely unreachable. PoE telemetry confirms
  power is not being delivered. Common causes: tripped PoE port, cable fault,
  PoE budget exceeded on the switch.
  - *Human action*: Inspect the PoE switch port, cabling, and power budget.
  - Do NOT automatically reboot or alter production power equipment.

- **Network down** (camera unreachable, PoE may be fine) suggests a network path issue:
  switch port down, VLAN misconfiguration, cable fault, or upstream router issue.
  - *Human action*: Inspect network path from the monitoring server to the camera.

- **Intermittent connectivity** shows transient packet loss. The camera alternates
  between reachable and unreachable. Common causes: loose cable, overloaded switch
  port, electromagnetic interference.
  - *Safe action*: Clear transient state and retest.
  - *If persistent*: Escalate for cabling/switch investigation.

## NVR Issues

- **NVR unavailable** means the NVR device is completely unreachable. Could be a
  hardware failure, power issue, or network path issue.
  - *Human action*: Physically check the NVR and its network connection.

- **Storage full** (utilisation ≥ 95%) means the NVR may stop recording soon.
  - *Human action*: Review retention policy, clean old recordings, or expand storage.
  - The agent should NOT delete recordings automatically.

## AI Box Issues

- **AI Box service failure** means the AI detection/analytics service on the box has
  crashed or stopped, but the host itself is reachable.
  - *Safe action*: Restart the simulated AI service.
  - *Verify*: Service health check should return `up`.

- **High CPU** (≥ 90%) on the AI Box indicates resource pressure. The analytics
  may be slow or dropping frames.
  - *Human action*: Investigate workload, consider reducing analysis load or
    upgrading hardware.

- **Cloud synchronisation failure** means the AI Box cannot upload detections or
  analytics results to the cloud platform.
  - *Safe action*: Retry the simulated cloud upload.
  - *Verify*: Cloud sync status should return `up`.

## Multi-Site / Multi-Camera

- **Multi-camera site outage** means all cameras at a site are down simultaneously.
  This usually indicates a site-level issue: power outage, switch failure, or
  upstream network cut.
  - *Human action*: Investigate site-level infrastructure (power, core switch, WAN link).

## General Principles

1. Always check the simplest explanation first (cable, power, reachability).
2. Never assume a successful repair — always verify with a follow-up check.
3. Correlate multiple symptoms: if several devices at the same site are down,
   suspect a site-level issue rather than individual device failures.
4. Historical incidents with the same root cause are strong evidence for diagnosis.
5. The agent automates investigation and safe recovery, not the technician's judgment.
