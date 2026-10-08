import type { KnowledgeDocument } from './types'

export const fallbackKnowledgeDocuments: KnowledgeDocument[] = [
  {
    id: 'network-protocols-and-commands',
    title: 'Network Protocols & IP Diagnostics in Surveillance Systems',
    category: 'Networking',
    source_path: 'docs/Networking/NETWORK_PROTOCOLS_AND_COMMANDS.md',
    sections: [
      {
        title: 'Overview',
        content:
          'Video surveillance networks and AI operations platforms rely on a suite of standardized Internet Protocol (IP) technologies to transport media streams, execute camera telemetry, synchronize timestamps, and coordinate edge intelligence.',
      },
      {
        title: 'Core Network Protocols',
        content:
          '• IPv4 / IPv6: Logical host addressing on dedicated camera VLAN subnets (e.g. 10.20.0.0/24) with static IP assignments or DHCP MAC reservations to prevent IP turnover.\n' +
          '• Subnet Mask & Default Gateway: Defines local vs. remote routing. The default gateway connects camera VLANs to NVRs or operations servers.\n' +
          '• TCP vs. UDP: TCP provides reliable connection handshakes with retransmission (web UI, RTSP control, APIs); UDP delivers low-latency RTP media streaming.\n' +
          '• RTSP (Port 554): Real-Time Streaming Protocol governing media sessions (DESCRIBE, SETUP, PLAY, TEARDOWN).\n' +
          '• ONVIF: XML/SOAP standard for camera discovery, PTZ controls, and media profile negotiation.\n' +
          '• NTP (Port 123): Mission-critical timestamp synchronization across all cameras, NVRs, and AI Boxes for legal and forensic compliance.\n' +
          '• RDP & SSH (Ports 3389 & 22): Encrypted management protocols for remote administration.',
      },
      {
        title: 'Essential IP Diagnostic Commands for Technicians',
        content:
          '1. ping <camera_ip> -t : Tests basic layer-3 reachability, latency, and packet loss.\n' +
          '2. ipconfig /all (Windows) / ip addr (Linux) : Inspects local interface configuration and default gateway.\n' +
          '3. arp -a : Displays IP-to-MAC mapping; pinpoints duplicate IP conflicts.\n' +
          '4. traceroute / tracert <ip> : Identifies intermediate router hops and packet drop points.\n' +
          '5. Test-NetConnection -Port 554 (PowerShell) / nc -zv <ip> 554 (Linux) : Verifies if daemon ports are listening.',
      },
    ],
  },
  {
    id: 'reboot-vs-powercycle',
    title: 'Reboot vs. Power Cycling: Definitions and Procedures',
    category: 'Networking',
    source_path: 'docs/Networking/REBOOT_VS_POWERCYCLE.md',
    sections: [
      {
        title: 'What Does "Reboot" Mean? (Soft Reboot / Warm Restart)',
        content:
          'An operating-system-directed restart where electrical DC power to the motherboard and components remains continuously supplied.\n\n' +
          '• Graceful Shutdown: Sends SIGTERM signals to running processes, flushes disk buffers, and cleanly unmounts file systems (preventing SQLite and video index corruption).\n' +
          '• Firmware Reload: Clears RAM and re-executes bootstrap loader without cutting power.\n' +
          '• Trigger Methods: Software commands (sudo reboot, restart-ai-service), web UI buttons, or management APIs.\n' +
          '• When to use: High RAM consumption, process hangs, minor config profile reloads.',
      },
      {
        title: 'What Does "Power Cycling" Mean? (Hard Reboot / Cold Boot)',
        content:
          'The complete, physical interruption of electrical power to the hardware, allowing internal capacitors to fully discharge before reapplying power.\n\n' +
          '• Hardware Reset: Clears non-volatile hardware controller states, resets network PHY chipsets, and resets ASIC registers.\n' +
          '• Wait Duration Rule: Always wait at least 15–30 seconds before restoring power to allow capacitors to drain completely.\n' +
          '• How to execute on cameras: PoE switch port bounce (poe_bounce) for 20 seconds, or physically disconnect the RJ45 patch cable.\n' +
          '• When to use: Kernel panics, frozen network PHY chips, failed soft reboots, or tripped PoE controllers.',
      },
    ],
  },
  {
    id: 'offline-incident-playbook',
    title: 'SOP: Offline Incident Playbook for IT Support & Field Technicians',
    category: 'SOP',
    source_path: 'docs/SOP/OFFLINE_INCIDENT_PLAYBOOK.md',
    sections: [
      {
        title: '1. Camera Offline (camera_offline / rtsp_down / poe_off)',
        content:
          '• Step 1 (Physical & PoE): Check switch port LED. Dark = no PoE or broken cable; amber/blinking = PoE fault or budget exceeded; green = link negotiated. Inspect RJ45 jacks for moisture.\n' +
          '• Step 2 (IP & Ping): Run ping <camera_ip>. If ping fails, check VLAN routing and arp -a for MAC address conflicts.\n' +
          '• Step 3 (RTSP 554): Probe port 554. If open, pull stream. If 401 Unauthorized, verify credentials in vault. If stream timed out, execute reconnect-rtsp.\n' +
          '• Step 4 (Power Bounce): If camera hardware is unresponsive, power cycle via PoE port bounce for 20s.\n' +
          '• Step 5 (Safety Gate): Physical cable replacement or credential changes require human technician handoff (pending_technician).',
      },
      {
        title: '2. System / AI Box / Server Offline',
        content:
          '• Step 1: Run ping <server_ip>. Check chassis power LEDs, PDU power feed, and out-of-band management (IPMI/iDRAC).\n' +
          '• Step 2: If pingable, connect via SSH/terminal. Check container status (docker compose ps) and system logs.\n' +
          '• Step 3: Run free -h (RAM) and df -h (disk space) to inspect resource exhaustion.\n' +
          '• Step 4: Execute restart-ai-service to restore the container engine safely.\n' +
          '• Step 5: Probe health endpoints (http://<server_ip>:8001/health) to confirm video pipelines re-engage.',
      },
      {
        title: '3. Remote Desktop Offline (RDP / SSH Unreachable)',
        content:
          '• Step 1: Ping the host IP. If ping fails, follow System Offline playbook.\n' +
          '• Step 2: Test port 3389 (RDP) or 22 (SSH) using Test-NetConnection -Port 3389 or nc -zv <ip> 3389.\n' +
          '• Step 3: Verify technician is on authorized management VPN/VLAN and check firewall rules.\n' +
          '• Step 4: If accessible via secondary protocol, restart remote desktop service (Restart-Service TermService on Windows; sudo systemctl restart xrdp on Linux).\n' +
          '• Step 5: If hung, access via out-of-band KVM or physical crash cart monitor.',
      },
    ],
  },
  {
    id: 'rtsp-streaming',
    title: 'RTSP Streaming & Media Ingestion Protocol',
    category: 'RTSP',
    source_path: 'docs/RTSP/RTSP_STREAMING.md',
    sections: [
      {
        title: 'Protocol Architecture',
        content:
          'RTSP (RFC 2326) operates on standard port 554. It acts as a network remote control for multimedia streams, negotiating transport parameters over TCP or UDP.\n\n' +
          'URI Format: rtsp://<user>:<password>@<host>:554/stream1\n\n' +
          'Stateful handshake sequence: OPTIONS -> DESCRIBE (SDP payload) -> SETUP -> PLAY -> TEARDOWN.',
      },
      {
        title: 'Operational Failure Modes & Safety Gate',
        content:
          '• Stream Drop (rtsp_down): Physical and IP connectivity intact, but socket stream dropped. Autonomous agent executes reconnect-rtsp safely.\n' +
          '• Authentication Error (rtsp_auth_failure): HTTP 401 Unauthorized. Automated credential guessing is strictly prohibited; hand off to technician.\n' +
          '• Network Loss: Physical disconnect requires on-site technician review.',
      },
    ],
  },
  {
    id: 'nvr-architecture',
    title: 'Network Video Recorder (NVR) Multi-Channel Architecture',
    category: 'NVR',
    source_path: 'docs/NVR/NVR_ARCHITECTURE.md',
    sections: [
      {
        title: 'System Role & Storage Pools',
        content:
          'NVRs serve as the centralized recording hub for IP surveillance cameras. Key capabilities include simultaneous multi-channel video ingestion, hardware H.264/H.265 decoding, continuous and motion-indexed recording, and RAID/SATA storage management with FIFO retention cycles.',
      },
      {
        title: 'Storage Alarms & Failures',
        content:
          '• Storage Full: FIFO auto-purge failures require technician volume expansion or retention policy adjustments.\n' +
          '• Degraded RAID: Disk SMART predictive failure requires physical drive replacement.',
      },
    ],
  },
  {
    id: 'aibox-analytics',
    title: 'Edge AI Box Architecture & Video Analytics',
    category: 'AI-Box',
    source_path: 'docs/AI-Box/AIBOX_ANALYTICS.md',
    sections: [
      {
        title: 'Hardware & Inference Pipelines',
        content:
          'AI Boxes are on-premises edge computing appliances equipped with Neural Processing Units (NPUs) or GPUs to execute real-time computer vision models on camera streams.\n\n' +
          'Analytics capabilities: Object recognition, vehicle license plate recognition (LPR), PPE/safety vest detection, perimeter tripwire intrusion.',
      },
      {
        title: 'Safe Autonomous Recovery (restart-ai-service)',
        content:
          'When inference pipelines crash or container processes stall (ai_service_down), the autonomous agent is permitted to execute restart-ai-service. Post-action verification ensures inference pipelines resume within 30 seconds.',
      },
    ],
  },
  {
    id: 'poe-and-connectivity',
    title: 'PoE Standards & Network Connectivity',
    category: 'Networking',
    source_path: 'docs/Networking/POE_AND_CONNECTIVITY.md',
    sections: [
      {
        title: 'Standards & Power Allocations',
        content:
          '• IEEE 802.3af (PoE Type 1): Supplies up to 15.4W at switch port (12.95W delivered). Standard static cameras.\n' +
          '• IEEE 802.3at (PoE+ Type 2): Supplies up to 30.0W at switch port (25.5W delivered). Outdoor cameras with IR illuminators and heaters.\n' +
          '• IEEE 802.3bt (PoE++ Type 3/4): Supplies up to 60W or 90W. High-power PTZ motorized dome cameras.',
      },
      {
        title: 'PoE Outage (poe_off) & Safety Boundaries',
        content:
          'Complete loss of physical link; device does not respond to ping, ARP, or TCP handshakes. Autonomous agents cannot perform physical cable repairs or hardware testing; immediately escalate to pending_technician.',
      },
    ],
  },
  {
    id: 'ip-cameras-and-onvif',
    title: 'IP Cameras, Optics & ONVIF Interoperability',
    category: 'Cameras',
    source_path: 'docs/Cameras/IP_CAMERAS_AND_ONVIF.md',
    sections: [
      {
        title: 'Camera Types & ONVIF Profiles',
        content:
          '• Camera Types: Fixed Dome (indoor/tamper resistant), Bullet (outdoor/long-range IR), PTZ (motorized pan-tilt-zoom), 360° Fisheye (panoramic dewarping).\n' +
          '• ONVIF Profile S: Basic IP video streaming and PTZ control.\n' +
          '• ONVIF Profile T: Advanced H.265 video streaming, motion detection, and bidirectional audio.\n' +
          '• ONVIF Profile G: Edge storage and retrieval from onboard SD cards.',
      },
    ],
  },
  {
    id: 'system-overview',
    title: 'Lab Architecture & Microservices Overview',
    category: 'SOP',
    source_path: 'docs/SOP/SYSTEM_OVERVIEW.md',
    sections: [
      {
        title: 'Microservices & Ports',
        content:
          '1. Helpdesk (:8000): FastAPI incident ticket store with notes, customer replies, and CarlBot copilot.\n' +
          '2. Portal (:8001): Emulated hardware devices, cameras, PoE switch ports, and simulated fault injection.\n' +
          '3. Agent (:8002): Background autonomous monitor thread, incident dedup, specialist dispatch, and deterministic policy engine.\n' +
          '4. Frontend (:8003): React/Vite/TypeScript operations dashboard with ticket queue, diagnostics, and CarlBot copilot.',
      },
      {
        title: 'Automation Policy Layer',
        content:
          'Only two safe actions may be triggered autonomously on fake state:\n' +
          '• reconnect-rtsp (restores dropped camera streams)\n' +
          '• restart-ai-service (restarts stalled edge containers)\n\n' +
          'All destructive, physical, credential, or network configuration changes require human technician sign-off.',
      },
    ],
  },
]
