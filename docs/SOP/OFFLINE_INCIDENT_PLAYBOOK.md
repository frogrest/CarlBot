# SOP: Offline Incident Playbook for IT Support & Field Technicians

## Purpose
This Standard Operating Procedure (SOP) defines the troubleshooting workflows and escalation paths for technicians and IT operations when devices or services go offline in the surveillance infrastructure.

---

## 1. Camera Offline (`camera_offline` / `rtsp_down` / `poe_off`)

When a camera stream disappears from the monitoring dashboard or NVR video matrix:

### Step 1: Layer 1 (Physical & PoE Verification)
- **Check Switch Port LED**: Locate the camera's patch port on the managed PoE switch.
  - *LED completely dark*: No PoE power is being delivered, or cable is severed/unplugged.
  - *PoE LED amber/blinking*: PoE fault, power budget exceeded, or short circuit detected.
  - *Link LED green/blinking*: Physical Ethernet connection is negotiated; move to Step 2.
- **Physical Inspection**: Inspect Cat6 patch cord, punch-down blocks, and RJ45 modular jack for corrosion, moisture ingress, or bent pins.
- **PoE Power Budget**: Check overall switch power wattage consumption in switch UI.

### Step 2: Layer 3 (Network Connectivity & Ping)
- Run `ping <camera_ip>` from the gateway or server.
  - *Reply received (0% packet loss)*: Camera IP stack is running. Proceed to Step 3.
  - *Request timed out*: Camera is powered off or isolated on wrong VLAN.
  - *Destination host unreachable*: Subnet routing failure or duplicate IP conflict.
- Run `arp -a`: Verify the MAC address matches the vendor OUI of the camera. If multiple MACs respond, resolve the IP conflict.

### Step 3: Layer 7 (RTSP & Application Services)
- Test RTSP port: Probe port 554 (`Test-NetConnection -ComputerName <camera_ip> -Port 554` or `nc -zv <camera_ip> 554`).
- **If Port 554 Closed**: Camera firmware is locked up or media daemon crashed. Power cycle the camera (PoE bounce for 20 seconds).
- **If Port 554 Open**: Attempt RTSP stream pull.
  - If error is `401 Unauthorized`: Camera credentials were modified or reset to factory defaults. Escalate to credential management vault. Do not guess credentials repeatedly (avoids lockout).
  - If error is stream timeout: Autonomous agent or technician can execute `reconnect-rtsp`.

### Step 4: Verification
- Verify continuous stream ingestion for at least 60 seconds.
- Confirm video timestamp increment in NVR timeline.

---

## 2. System / AI Box / Server Offline (`system_offline` / `ai_service_down`)

When an AI Box, edge analytics server, or NVR ceases heartbeats:

### Step 1: Network & Ping Diagnostic
- Run `ping <server_ip>` to determine if the hardware host or virtual machine is responding.
- If ping fails:
  - Check physical status LEDs on server chassis (Power LED, NIC Link/Activity LED, Overheat/Fault LED).
  - Check UPS / PDU power status.
  - Verify out-of-band management controller (IPMI / iDRAC / iLO) for hardware health logs.

### Step 2: Service & Container Health Check
- If ping succeeds but AI analytics or API endpoints fail:
  - Connect via local console or SSH / Terminal.
  - Check container status: `docker compose ps` or `systemctl status ai-service`.
  - Check resource exhaustion: run `free -h` (RAM) and `df -h` (Disk storage full).
  - Review service error logs: `journalctl -u <service> -n 100` or `docker compose logs --tail=100`.
  - Safe automated or manual recovery: execute `restart-ai-service` to restore the container process.

### Step 3: Post-Recovery Verification
- Probe the health endpoint: `curl -s http://<server_ip>:8001/health` or `http://<server_ip>:8002/health`.
- Validate that inference pipelines and RTSP feed consumers reconnect cleanly.

---

## 3. Remote Desktop Offline (RDP / SSH / VNC Unreachable)

When technicians cannot establish remote desktop (port 3389) or SSH (port 22) sessions:

### Step 1: Ping & Network Reachability
- Ping the target host IP.
  - If ping fails: The entire host machine or network segment is down. Follow the System Offline playbook above.
  - If ping succeeds: The host OS is running; the issue is localized to remote access services, firewall, or network access control (ACL).

### Step 2: Port & Service Listener Probing
- Test the remote access port:
  ```powershell
  # Windows PowerShell
  Test-NetConnection -ComputerName <target_ip> -Port 3389
  ```
  ```bash
  # Linux
  nc -zv <target_ip> 3389
  ```
- *Port Filtered / Timed Out*: Firewall (Windows Defender Firewall or iptables) is blocking the port, or the technician is not on the authorized management VPN/VLAN.
- *Port Closed / Connection Refused*: The remote desktop service (`TermService` on Windows, or `sshd`/`xrdp` on Linux) has crashed or is not started.

### Step 3: Remote Service Restart (Without Console)
- From an authorized administrative workstation on the same subnet:
  - Windows: Run `sc \\<target_ip> query TermService` or `Invoke-Command -ComputerName <target_ip> { Restart-Service TermService }`.
  - Linux: If RDP is down but SSH is up, SSH into the machine and restart XRDP: `sudo systemctl restart xrdp`.

### Step 4: Physical Console / KVM Access
- If remote services cannot be re-engaged over the network:
  - Connect to the out-of-band management console (iDRAC, iLO, Pi-KVM).
  - Connect a local monitor and keyboard directly to the crash cart / server rack.
  - Log in directly at the console to inspect firewall logs and service status.
  - Perform a graceful soft reboot if the desktop subsystem is hung.
