import React, { useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { LabControlsModal } from './LabControlsModal';

export const AppLayout: React.FC = () => {
  const [labControlsOpen, setLabControlsOpen] = useState(false);
  const location = useLocation();

  const getPageInfo = (path: string) => {
    if (path === '/') return { title: 'Operations Dashboard', subtitle: 'Live overview of CCTV streams, NVR storage, AI detection boxes & incidents' };
    if (path.startsWith('/incidents/')) return { title: 'Incident Investigation Detail', subtitle: 'Step-by-step diagnostic evidence, safety classification & technician actions' };
    if (path === '/incidents') return { title: 'Incidents & Tickets', subtitle: 'Active and historical support tickets categorized by AI state & severity' };
    if (path.startsWith('/devices/')) return { title: 'Device Telemetry & Health', subtitle: 'Real-time ping, TCP, RTSP, PoE telemetry and subsystem checks' };
    if (path === '/devices') return { title: 'Monitored Devices Inventory', subtitle: 'CCTV Cameras, NVR storage nodes, and Edge AI Detection Boxes' };
    if (path.startsWith('/sites/')) return { title: 'Site Operations & Topology', subtitle: 'Infrastructure topology and shared dependency mapping' };
    if (path === '/sites') return { title: 'Facility Sites', subtitle: 'Multi-site operational status across all monitored locations' };
    if (path === '/assistant') return { title: 'AI Technical Support Assistant', subtitle: 'Conversational troubleshooting, deterministic tool use & slash commands' };
    if (path === '/knowledge') return { title: 'Operational Knowledge Base', subtitle: 'Troubleshooting guides, equipment reference & documented resolutions' };
    if (path === '/audit') return { title: 'Action Audit & Policy Trail', subtitle: 'Traceable log of all autonomous and technician operations' };
    return { title: 'EG Support Operations', subtitle: 'CCTV & AI Infrastructure Platform' };
  };

  const { title, subtitle } = getPageInfo(location.pathname);

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-background">
      <Sidebar onOpenLabControls={() => setLabControlsOpen(true)} />

      <div className="flex-1 flex flex-col min-w-0 h-screen overflow-hidden">
        <Header
          title={title}
          subtitle={subtitle}
          onOpenLabControls={() => setLabControlsOpen(true)}
        />

        <main className="flex-1 overflow-y-auto min-h-0 bg-background">
          <Outlet />
        </main>
      </div>

      <LabControlsModal
        isOpen={labControlsOpen}
        onClose={() => setLabControlsOpen(false)}
      />
    </div>
  );
};
