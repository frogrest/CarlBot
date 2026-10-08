# Network Protocols & IP Diagnostics in Surveillance Systems

## Overview
Video surveillance networks and AI operations platforms rely on a suite of standardized Internet Protocol (IP) technologies to transport media streams, execute camera telemetry, synchronize timestamps, and coordinate edge intelligence.

## Core Network Protocols

### IP (Internet Protocol - IPv4 & IPv6)
- **IPv4**: 32-bit numerical label assigned to each network interface (e.g. `192.168.1.105`). In enterprise security setups, surveillance cameras and NVRs are deployed on dedicated, isolated VLAN subnets (e.g. `10.20.0.0/24`) with static IP assignments or DHCP MAC reservations to prevent IP turnover.
- **Subnet Mask & Default Gateway**: The subnet mask (e.g. `255.255.255.0` or `/24`) defines local vs. remote routing. The default gateway is the router interface connecting camera VLANs to NVRs or operations servers.

### Transport Protocols
- **TCP (Transmission Control Protocol)**: Connection-oriented, reliable stream with retransmission and flow control. Used for HTTP/HTTPS web management, RTSP control sessions, API queries, and video streaming when packet loss causes visual corruption.
- **UDP (User Datagram Protocol)**: Connectionless, low-latency transmission without ACK handshakes. Often used for real-time video streaming (RTP) where low latency is favored over zero packet loss, and for DNS/NTP.

### Application Protocols
- **RTSP (Real-Time Streaming Protocol - Port 554)**: Session control protocol governing camera media streams. Commands include `DESCRIBE`, `SETUP`, `PLAY`, `TEARDOWN`.
- **ONVIF (Open Network Video Interface Forum - Ports 80, 8080, 5000)**: XML/SOAP standard for camera discovery, PTZ control, event triggers, and profile discovery.
- **NTP (Network Time Protocol - Port 123)**: Mission-critical protocol synchronizing clocks across all cameras, AI Boxes, and NVRs. Precise timestamp alignment is legally mandatory for evidentiary video playback.
- **DHCP & DNS (Ports 67/68, 53)**: Automated IP allocation and hostname resolution. Static addressing is preferred for field cameras to avoid loss of stream bindings.
- **RDP & SSH (Ports 3389, 22)**: Encrypted remote desktop and secure shell protocols used by systems administrators and technicians for server maintenance.

## Essential IP Diagnostic Commands for Technicians

When investigating offline devices or connectivity degradation, technicians should use standard command-line tools:

### 1. `ping` (ICMP Echo)
Tests basic IP layer connectivity and round-trip latency.
```bash
# Continuous ping to monitor link stability
ping 192.168.1.100 -t       # Windows
ping 192.168.1.100          # Linux
```
- **0% packet loss**: IP stack and physical layer are communicating.
- **Request timed out**: Physical link down, wrong IP, or camera is unpowered.
- **Destination host unreachable**: Routing table or gateway mismatch; device is on a different unrouted subnet.

### 2. `ipconfig` (Windows) / `ip addr` (Linux)
Inspects local interface configuration, subnet mask, default gateway, and DHCP lease status.
```powershell
ipconfig /all
```

### 3. `arp -a` (Address Resolution Protocol)
Displays IP-to-MAC address mapping table.
- Confirms whether the switch/server can map the camera's IP to its hardware MAC address.
- Detects **duplicate IP conflicts** (e.g., if two devices fight over the same IP, the MAC in the ARP table changes back and forth).

### 4. `traceroute` (Linux) / `tracert` (Windows)
Identifies the hop-by-hop path between the client and target device.
- Pinpoints the exact switch or router where packets drop.

### 5. `netstat` / `ss` / `nc` (Port Probing)
Verifies if listening ports are active:
```powershell
# Windows PowerShell port test
Test-NetConnection -ComputerName 192.168.1.100 -Port 554
```
```bash
# Linux netcat port test
nc -zv 192.168.1.100 554
```
- **Port 554 Open**: Camera RTSP daemon is operational.
- **Port 554 Closed / Refused**: Camera firmware running but media server daemon crashed.
