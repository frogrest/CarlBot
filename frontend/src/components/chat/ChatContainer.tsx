import React, { useState, useEffect, useRef } from 'react';
import { Send, Bot, RefreshCw } from 'lucide-react';
import type { ChatMessage, ChatConversation, ChatToolCall } from './types';
import { ChatMessageItem } from './ChatMessageItem';
import { ChatSidebar } from './ChatSidebar';
import { agentApi, portalApi, helpdeskApi } from '../../api';
import { useLab } from '../../context/LabContext';

const STORAGE_KEY = 'eg_cctv_ai_assistant_chats_v1';

const INITIAL_CONVERSATION: ChatConversation = {
  id: 'conv-default',
  title: 'CCTV Triage & Investigation',
  createdAt: new Date().toISOString(),
  updatedAt: new Date().toISOString(),
  messages: [
    {
      id: 'msg-welcome',
      role: 'assistant',
      content:
        'Hello technician, I am the EG CCTV Operations Autonomous Assistant.\n\nI can investigate camera streams, NVR storage, PoE power status, and edge AI boxes while strictly adhering to safety policy.\n\nType `/help` to see all slash commands or ask about any camera (e.g. `/investigate CAM-001`).',
      timestamp: new Date().toISOString(),
    },
  ],
};

export const ChatContainer: React.FC = () => {
  const { assets, tickets, activeFaults, agentOnline, refresh } = useLab();
  const [conversations, setConversations] = useState<ChatConversation[]>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) return JSON.parse(saved);
    } catch {}
    return [INITIAL_CONVERSATION];
  });

  const [activeId, setActiveId] = useState<string>(() => {
    return conversations[0]?.id || 'conv-default';
  });

  const [input, setInput] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const activeConv = conversations.find((c) => c.id === activeId) || conversations[0];

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations));
    } catch (err) {
      console.error('Failed to save chats to localStorage:', err);
    }
  }, [conversations]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [activeConv?.messages, isProcessing]);

  const updateActiveMessages = (newMessages: ChatMessage[]) => {
    setConversations((prev) =>
      prev.map((c) =>
        c.id === activeId
          ? {
              ...c,
              messages: newMessages,
              updatedAt: new Date().toISOString(),
            }
          : c
      )
    );
  };

  const handleNewConversation = () => {
    const newConv: ChatConversation = {
      id: `conv-${Date.now()}`,
      title: 'New Investigation',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      messages: [
        {
          id: `msg-${Date.now()}`,
          role: 'assistant',
          content: 'New investigation session started. What asset, site, or symptom would you like to investigate?',
          timestamp: new Date().toISOString(),
        },
      ],
    };
    setConversations((prev) => [newConv, ...prev]);
    setActiveId(newConv.id);
  };

  const handleDeleteConversation = (id: string) => {
    setConversations((prev) => {
      const filtered = prev.filter((c) => c.id !== id);
      if (filtered.length === 0) {
        return [INITIAL_CONVERSATION];
      }
      return filtered;
    });
    if (activeId === id) {
      const remaining = conversations.filter((c) => c.id !== id);
      if (remaining.length > 0) {
        setActiveId(remaining[0].id);
      }
    }
  };

  // ---------------------------------------------------------------------------
  // Command & Query Processing
  // ---------------------------------------------------------------------------
  const handleSendMessage = async () => {
    const trimmed = input.trim();
    if (!trimmed || isProcessing) return;

    setInput('');
    const userMsg: ChatMessage = {
      id: `msg-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
      role: 'user',
      content: trimmed,
      timestamp: new Date().toISOString(),
    };

    const nextMessages = [...(activeConv?.messages || []), userMsg];
    updateActiveMessages(nextMessages);
    setIsProcessing(true);

    try {
      await processInput(trimmed, nextMessages);
    } catch (err: any) {
      const errorMsg: ChatMessage = {
        id: `msg-err-${Date.now()}`,
        role: 'assistant',
        content: `Error during investigation: ${err.message || 'Unknown error'}`,
        timestamp: new Date().toISOString(),
      };
      updateActiveMessages([...nextMessages, errorMsg]);
    } finally {
      setIsProcessing(false);
      refresh();
    }
  };

  const processInput = async (rawInput: string, currentHistory: ChatMessage[]) => {
    const lower = rawInput.toLowerCase().trim();

    // 1. /clear command
    if (lower === '/clear') {
      const clearNotice: ChatMessage = {
        id: `msg-${Date.now()}`,
        role: 'system',
        content: 'Conversation context cleared.',
        timestamp: new Date().toISOString(),
      };
      const assistantIntro: ChatMessage = {
        id: `msg-${Date.now() + 1}`,
        role: 'assistant',
        content: 'Previous chat context has been removed from this assistant session.\n\nHow can I help you today?',
        timestamp: new Date().toISOString(),
      };
      updateActiveMessages([clearNotice, assistantIntro]);
      return;
    }

    // 2. /help command
    if (lower === '/help') {
      const helpMsg: ChatMessage = {
        id: `msg-${Date.now()}`,
        role: 'assistant',
        content: `Available Assistant Commands:\n\n• \`/investigate <DEVICE_ID>\` — Run end-to-end autonomous diagnostic cycle, evaluate policy, execute safe recovery, or escalate to technician\n  Example: \`/investigate CAM-001\`\n\n• \`/status <DEVICE_ID>\` — Query real-time telemetry (Ping, RTSP, PoE, CPU, storage)\n  Example: \`/status CAM-002\`\n\n• \`/site <SITE_ID>\` — Check site overall health, reachable assets, and issues\n  Example: \`/site SITE-001\`\n\n• \`/history <QUERY>\` — Search historical helpdesk tickets and resolutions\n  Example: \`/history RTSP\`\n\n• \`/clear\` — Clear current conversation context (perserves tickets and system state)\n\n• \`/help\` — Display this command reference`,
        timestamp: new Date().toISOString(),
      };
      updateActiveMessages([...currentHistory, helpMsg]);
      return;
    }

    // 3. /investigate command
    if (lower.startsWith('/investigate')) {
      const parts = rawInput.split(/\s+/);
      const targetId = (parts[1] || 'CAM-001').toUpperCase();
      await executeInvestigationWorkflow(targetId, currentHistory);
      return;
    }

    // 4. /status command
    if (lower.startsWith('/status')) {
      const parts = rawInput.split(/\s+/);
      const targetId = (parts[1] || 'CAM-001').toUpperCase();
      await executeStatusQuery(targetId, currentHistory);
      return;
    }

    // 5. /site command
    if (lower.startsWith('/site')) {
      const parts = rawInput.split(/\s+/);
      const siteId = (parts[1] || 'SITE-001').toUpperCase();
      await executeSiteQuery(siteId, currentHistory);
      return;
    }

    // 6. /history command
    if (lower.startsWith('/history')) {
      const query = rawInput.replace(/^\/history\s*/i, '').trim() || 'rtsp';
      await executeHistoryQuery(query, currentHistory);
      return;
    }

    // Helper to resolve asset from text (by ID, alias, or human name)
    const findMentionedAsset = (text: string) => {
      const textLower = text.toLowerCase();
      const assetPool = assets.length > 0 ? assets : [
        { id: 'CAM-001', name: 'Lobby Camera', kind: 'camera' as const, site_id: 'SITE-001', ip: '10.10.1.11', state: {} },
        { id: 'CAM-002', name: 'Parking Camera', kind: 'camera' as const, site_id: 'SITE-002', ip: '10.10.2.11', state: {} },
        { id: 'CAM-003', name: 'Loading Dock Camera', kind: 'camera' as const, site_id: 'SITE-002', ip: '10.10.2.12', state: {} },
        { id: 'CAM-004', name: 'Server Room Camera', kind: 'camera' as const, site_id: 'SITE-003', ip: '10.10.3.11', state: {} },
        { id: 'NVR-001', name: 'Main NVR', kind: 'nvr' as const, site_id: 'SITE-003', ip: '10.10.3.10', state: {} },
        { id: 'NVR-002', name: 'Lobby NVR', kind: 'nvr' as const, site_id: 'SITE-001', ip: '10.10.1.10', state: {} },
        { id: 'AIBOX-001', name: 'Detection Box Alpha', kind: 'ai_box' as const, site_id: 'SITE-001', ip: '10.10.1.20', state: {} },
        { id: 'AIBOX-002', name: 'Detection Box Beta', kind: 'ai_box' as const, site_id: 'SITE-002', ip: '10.10.2.20', state: {} },
      ];

      // 1. Direct ID match or hyphenless (e.g. CAM-001, cam001, AIBOX-001, aibox001)
      for (const a of assetPool) {
        if (textLower.includes(a.id.toLowerCase())) return a;
        const noHyphen = a.id.toLowerCase().replace('-', '');
        if (textLower.includes(noHyphen)) return a;
        if (textLower.includes(a.name.toLowerCase())) return a;
      }
      // 2. Common CCTV natural language aliases
      if (textLower.includes('lobby camera') || textLower.includes('cam 1') || textLower.includes('camera 1')) {
        return assetPool.find((a) => a.id === 'CAM-001');
      }
      if (textLower.includes('parking camera') || textLower.includes('cam 2') || textLower.includes('camera 2')) {
        return assetPool.find((a) => a.id === 'CAM-002');
      }
      if (textLower.includes('loading dock') || textLower.includes('cam 3') || textLower.includes('camera 3')) {
        return assetPool.find((a) => a.id === 'CAM-003');
      }
      if (textLower.includes('server room camera') || textLower.includes('cam 4') || textLower.includes('camera 4')) {
        return assetPool.find((a) => a.id === 'CAM-004');
      }
      if (textLower.includes('main nvr') || textLower.includes('nvr 1') || textLower.includes('nvr1')) {
        return assetPool.find((a) => a.id === 'NVR-001');
      }
      if (textLower.includes('lobby nvr') || textLower.includes('nvr 2') || textLower.includes('nvr2')) {
        return assetPool.find((a) => a.id === 'NVR-002');
      }
      if (textLower.includes('detection box alpha') || textLower.includes('ai box 1') || textLower.includes('ai-box-001') || textLower.includes('aibox1')) {
        return assetPool.find((a) => a.id === 'AIBOX-001');
      }
      if (textLower.includes('detection box beta') || textLower.includes('ai box 2') || textLower.includes('ai-box-002') || textLower.includes('aibox2')) {
        return assetPool.find((a) => a.id === 'AIBOX-002');
      }
      return undefined;
    };

    // 7. Safety Policy Explanation intent
    if (
      lower.includes('policy') ||
      lower.includes('safe_reversible') ||
      lower.includes('human_only') ||
      lower.includes('approval_required') ||
      lower.includes('what can you fix') ||
      lower.includes('safety rule') ||
      lower.includes('what can be automated')
    ) {
      const policyMsg: ChatMessage = {
        id: `msg-${Date.now()}`,
        role: 'assistant',
        content: `### Autonomous Safety Policy Tiers\n\nThe policy engine (\`services/agent/policy.py\`) enforces strict tier boundaries to guarantee operational safety:\n\n1. 🟢 **SAFE_REVERSIBLE** (Auto-Executed)\n• Actions: \`reconnect_stream\`, \`restart_service\`, \`retry_upload\`, \`clear_transient\`\n• Behavior: Executed autonomously by the agent, bounded by retry limits, and immediately verified via fresh telemetry.\n\n2. 🟡 **APPROVAL_REQUIRED** (Human Confirmation Required)\n• Actions: \`reboot_host\`, \`update_config\`, \`firmware_upgrade\`, \`storage retention changes\`\n• Behavior: Diagnosed and proposed by the agent, but blocked until a human operator grants explicit authorization.\n\n3. 🔴 **HUMAN_ONLY** (Strictly Prohibited from Automation)\n• Actions: Physical repairs, cable replacements, lens cleaning, credential rotations, factory resets\n• Behavior: Never touched by automation. Automatically creates/escalates a ticket to \`pending_technician\` with structured diagnostic evidence.\n\n4. 🔵 **READ** (Always Safe)\n• Checks: Ping, TCP port 554, RTSP options, telemetry metrics, and knowledge searches. Always executed freely to build evidence.`,
        timestamp: new Date().toISOString(),
      };
      updateActiveMessages([...currentHistory, policyMsg]);
      return;
    }

    // 8. Fleet Status & Active Faults intent
    const isFleetStatusQuery =
      lower.includes('active fault') ||
      lower.includes('what fault') ||
      lower.includes('what faults') ||
      (lower.includes('fault') && (lower.includes('active') || lower.includes('any') || lower.includes('system') || lower.includes('all'))) ||
      lower.includes('system status') ||
      lower.includes('system health') ||
      lower.includes('fleet health') ||
      lower.includes('fleet status') ||
      lower.includes('any problem') ||
      lower.includes('any issue') ||
      lower.includes('is everything healthy') ||
      lower.includes('overview');

    if (isFleetStatusQuery) {
      const faultCount = Object.values(activeFaults).reduce((sum, f) => sum + f.length, 0);
      const monitoredCount = assets.length > 0 ? assets.length : 8;
      let statusContent = '';
      if (faultCount === 0) {
        statusContent = `### Fleet Operational Status: HEALTHY 🟢\n\nAll ${monitoredCount} monitored assets are currently operational with normal telemetry.\n\n• **Active Faults:** 0\n• **Open Incidents:** ${tickets.filter((t) => t.status !== 'resolved' && t.status !== 'closed').length}\n• **Fleet Health:** 100%\n\nYou can use the **Lab Controls** button in the header or run \`/investigate <DEVICE>\` to test targeted diagnostics.`;
      } else {
        const faultDetails = Object.entries(activeFaults)
          .filter(([_, faults]) => faults.length > 0)
          .map(([assetId, faults]) => `• **${assetId}**: \`${faults.join(', ')}\``)
          .join('\n');

        statusContent = `### Fleet Operational Status: ATTENTION REQUIRED ⚠️\n\nDetected **${faultCount} active fault(s)** currently affecting monitored endpoints:\n\n${faultDetails}\n\n**Next Steps:**\n• Run \`/investigate <DEVICE_ID>\` to trigger targeted root-cause diagnostics\n• Open **Lab Controls** to clear or simulate additional failure modes`;
      }

      const statusMsg: ChatMessage = {
        id: `msg-${Date.now()}`,
        role: 'assistant',
        content: statusContent,
        timestamp: new Date().toISOString(),
      };
      updateActiveMessages([...currentHistory, statusMsg]);
      return;
    }

    // 9. Clear faults request in natural language
    if (lower.includes('clear fault') || lower.includes('clear all fault') || lower.includes('reset fault')) {
      try {
        await portalApi.clearAllFaults();
        const clearMsg: ChatMessage = {
          id: `msg-${Date.now()}`,
          role: 'assistant',
          content: 'All active faults across the fleet have been cleared. All simulated endpoints are returning to normal telemetry state.',
          timestamp: new Date().toISOString(),
        };
        updateActiveMessages([...currentHistory, clearMsg]);
        refresh();
        return;
      } catch (err: any) {
        // Continue to general processing
      }
    }

    // 10. Natural language site queries
    if (lower.includes('site-001') || lower.includes('site 1') || lower.includes('lobby site') || lower.includes('hq')) {
      await executeSiteQuery('SITE-001', currentHistory);
      return;
    }
    if (lower.includes('site-002') || lower.includes('site 2') || lower.includes('branch') || lower.includes('parking site')) {
      await executeSiteQuery('SITE-002', currentHistory);
      return;
    }
    if (lower.includes('site-003') || lower.includes('site 3') || lower.includes('server room site') || lower.includes('data center')) {
      await executeSiteQuery('SITE-003', currentHistory);
      return;
    }

    // 11. Natural language device investigation or status
    const foundAsset = findMentionedAsset(rawInput);
    if (foundAsset) {
      if (lower.includes('status') && !lower.includes('investigate') && !lower.includes('fix') && !lower.includes('problem') && !lower.includes('issue')) {
        await executeStatusQuery(foundAsset.id, currentHistory);
        return;
      } else {
        await executeInvestigationWorkflow(foundAsset.id, currentHistory);
        return;
      }
    }

    // 12. General conversational Q&A: search knowledge base
    const docs = await agentApi.searchKnowledge(rawInput);
    if (docs && docs.length > 0) {
      const topDoc = docs[0];
      const answerMsg: ChatMessage = {
        id: `msg-${Date.now()}`,
        role: 'assistant',
        content: `### Operational SOP Guidance (${topDoc.source})\n\n${topDoc.snippet}\n\n**Actionable Options:**\n• Run \`/investigate <DEVICE_ID>\` to inspect a live asset\n• Run \`/status <DEVICE_ID>\` to check real-time telemetry\n• Open the **Knowledge Base** tab to read the full runbook`,
        citations: docs,
        timestamp: new Date().toISOString(),
      };
      updateActiveMessages([...currentHistory, answerMsg]);
    } else {
      const fallbackMsg: ChatMessage = {
        id: `msg-${Date.now()}`,
        role: 'assistant',
        content: `I analyzed your request: "${rawInput}".\n\nTo diagnose an endpoint or site, you can run:\n• \`/investigate CAM-001\`\n• \`/status CAM-002\`\n• \`/site SITE-001\`\n• \`/history rtsp\`\n\nOr ask about specific symptoms such as PoE power, RTSP authentication, or storage usage.`,
        timestamp: new Date().toISOString(),
      };
      updateActiveMessages([...currentHistory, fallbackMsg]);
    }
  };

  // ---------------------------------------------------------------------------
  // Handlers for specific commands
  // ---------------------------------------------------------------------------
  const executeInvestigationWorkflow = async (assetId: string, currentHistory: ChatMessage[]) => {
    // Initial tool call progress state
    const toolCalls: ChatToolCall[] = [
      { name: 'check_telemetry', label: `Checking network & telemetry on ${assetId}`, status: 'running' },
      { name: 'search_history', label: `Retrieving historical incident tickets`, status: 'skipped' },
      { name: 'search_knowledge', label: `Searching operational knowledge base`, status: 'skipped' },
      { name: 'evaluate_policy', label: `Evaluating action safety policy`, status: 'skipped' },
      { name: 'verify', label: `Verifying recovery or documenting escalation`, status: 'skipped' },
    ];

    const progressMsgId = `msg-inv-${Date.now()}`;
    const initialAssistantMsg: ChatMessage = {
      id: progressMsgId,
      role: 'assistant',
      content: `Investigating ${assetId}...\nQuerying real-time subsystem state and historical patterns.`,
      toolCalls: [...toolCalls],
      timestamp: new Date().toISOString(),
    };

    updateActiveMessages([...currentHistory, initialAssistantMsg]);

    // Call backend API
    const report = await agentApi.investigateAsset(assetId);

    // Update tool calls with real status
    const isProb = report.is_problem;
    const isAutoRecovered = Boolean(report.action_executed);
    // CRITICAL: A device requires technician action ONLY if it has an actual problem!
    const isTechRequired = isProb && (report.policy.safety_class === 'HUMAN_ONLY' || report.policy.safety_class === 'APPROVAL_REQUIRED');

    const completedToolCalls: ChatToolCall[] = [
      {
        name: 'check_telemetry',
        label: `Subsystem telemetry check for ${assetId}`,
        status: isProb ? 'failure' : 'success',
        result: report.check,
      },
      {
        name: 'search_history',
        label: `Retrieved ${report.historical_matches.length} matching incident records`,
        status: 'success',
        result: report.historical_matches,
      },
      {
        name: 'search_knowledge',
        label: `Retrieved ${report.knowledge_sources.length} knowledge base guides`,
        status: 'success',
        result: report.knowledge_sources,
      },
      {
        name: 'evaluate_policy',
        label: isProb
          ? `Safety Policy: ${report.policy.action || 'diagnostic'} is ${report.policy.safety_class}`
          : `Safety Policy: All subsystem telemetry within operational limits`,
        status: !isProb ? 'success' : report.policy.allowed_automatically ? 'success' : 'blocked',
        result: report.policy,
      },
      {
        name: 'verify',
        label: isAutoRecovered
          ? `Executed ${report.action_executed} & verified recovery`
          : isTechRequired
          ? `Escalated to human technician (${report.diagnosis.safety_class})`
          : `Asset verified healthy and operational`,
        status: isAutoRecovered ? 'success' : isTechRequired ? 'blocked' : 'success',
      },
    ];

    let responseSummary = '';
    if (!isProb) {
      responseSummary = `Investigation complete for ${assetId} (${report.asset.name}).\nAll subsystem telemetry is normal (Ping PASS, RTSP UP, PoE ON). No action required.`;
    } else if (isAutoRecovered) {
      responseSummary = `Diagnosed ${report.diagnosis.fault} on ${assetId}.\n\nPolicy engine verified action "${report.action_executed}" as SAFE_REVERSIBLE and automatically permitted. Stream recovery executed and verified successfully.`;
    } else {
      responseSummary = `Diagnosed ${report.diagnosis.fault} on ${assetId} (confidence ${(report.diagnosis.confidence * 100).toFixed(0)}%).\n\nPolicy engine classified this issue as ${report.diagnosis.safety_class}. Automated modification is strictly blocked by safety rules.\n\nTechnician action required: ${report.diagnosis.recommendation}.`;
    }

    const finalMsg: ChatMessage = {
      id: progressMsgId,
      role: 'assistant',
      content: responseSummary,
      toolCalls: completedToolCalls,
      diagnosis: report.diagnosis,
      policy: report.policy,
      actionExecuted: report.action_executed,
      technicianRequired: isTechRequired,
      technicianActionText: report.diagnosis.recommendation,
      timeline: report.timeline,
      citations: report.knowledge_sources,
      ticketId: report.ticket?.id,
      timestamp: new Date().toISOString(),
    };

    updateActiveMessages([...currentHistory, finalMsg]);
  };

  const executeStatusQuery = async (assetId: string, currentHistory: ChatMessage[]) => {
    const [asset, check] = await Promise.all([
      portalApi.getAsset(assetId),
      portalApi.checkAsset(assetId),
    ]);

    const statusLines = [
      `Device Status Report: ${asset.name} (${asset.id})`,
      `• Site: ${asset.site_id}`,
      `• Kind: ${asset.kind.toUpperCase()}`,
      `• IP: ${asset.ip}`,
      `• Reachable (Ping): ${check.ping ? 'PASS' : 'FAIL'}`,
    ];

    if (asset.kind === 'camera') {
      statusLines.push(`• RTSP Stream: ${check.rtsp === true || check.rtsp === 'up' ? 'UP' : 'DOWN'}`);
      statusLines.push(`• RTSP Auth: ${check.rtsp_auth !== false ? 'PASS' : 'FAIL'}`);
      statusLines.push(`• PoE Power: ${check.poe !== false ? 'ON' : 'OFF'}`);
    } else if (asset.kind === 'nvr') {
      statusLines.push(`• Storage Utilisation: ${check.storage_used ?? 50}%`);
    } else if (asset.kind === 'ai_box') {
      statusLines.push(`• Detection Service: ${check.service || 'up'}`);
      statusLines.push(`• CPU Load: ${check.cpu || 30}%`);
      statusLines.push(`• Cloud Sync: ${check.cloud_sync || 'up'}`);
    }

    const statusMsg: ChatMessage = {
      id: `msg-${Date.now()}`,
      role: 'assistant',
      content: statusLines.join('\n'),
      timestamp: new Date().toISOString(),
    };

    updateActiveMessages([...currentHistory, statusMsg]);
  };

  const executeSiteQuery = async (siteId: string, currentHistory: ChatMessage[]) => {
    const health = await portalApi.getSiteHealth(siteId);

    const lines = [
      `Site Health Report: ${health.name} (${health.site_id})`,
      `• Total Assets: ${health.total_assets}`,
      `• Reachable Assets: ${health.reachable_assets}`,
      `• Healthy Assets: ${health.healthy_assets}`,
    ];

    if (health.issues.length === 0) {
      lines.push('• All site devices are fully operational.');
    } else {
      lines.push(`• Active Issues (${health.issues.length}):`);
      health.issues.forEach((iss) => {
        lines.push(`  - ${iss.asset_id} (${iss.kind}): ${iss.issue}`);
      });
    }

    const siteMsg: ChatMessage = {
      id: `msg-${Date.now()}`,
      role: 'assistant',
      content: lines.join('\n'),
      timestamp: new Date().toISOString(),
    };

    updateActiveMessages([...currentHistory, siteMsg]);
  };

  const executeHistoryQuery = async (query: string, currentHistory: ChatMessage[]) => {
    const tickets = await helpdeskApi.search(query);

    if (tickets.length === 0) {
      const msg: ChatMessage = {
        id: `msg-${Date.now()}`,
        role: 'assistant',
        content: `No historical tickets found matching query "${query}".`,
        timestamp: new Date().toISOString(),
      };
      updateActiveMessages([...currentHistory, msg]);
      return;
    }

    const lines = [`Found ${tickets.length} historical tickets matching "${query}":`];
    tickets.slice(0, 5).forEach((t) => {
      lines.push(`• ${t.id} [${t.status.toUpperCase()}]: ${t.title}`);
      if (t.resolution) lines.push(`  Resolution: ${t.resolution}`);
    });

    const histMsg: ChatMessage = {
      id: `msg-${Date.now()}`,
      role: 'assistant',
      content: lines.join('\n'),
      timestamp: new Date().toISOString(),
    };

    updateActiveMessages([...currentHistory, histMsg]);
  };

  return (
    <div className="flex h-full w-full overflow-hidden bg-background">
      {/* Conversations Sidebar */}
      <ChatSidebar
        conversations={conversations}
        activeId={activeId}
        onSelect={setActiveId}
        onNew={handleNewConversation}
        onDelete={handleDeleteConversation}
      />

      {/* Main Chat Interface */}
      <div className="flex-1 flex flex-col h-full min-w-0 bg-surface/40">
        {/* Chat Header Status */}
        <div className="px-6 py-3 border-b border-surface-border flex items-center justify-between bg-surface/70">
          <div className="flex items-center gap-2.5">
            <Bot className="w-5 h-5 text-brand-400" />
            <div>
              <div className="text-xs font-bold text-slate-100 uppercase tracking-wider">
                Autonomous Technical Support Agent
              </div>
              <div className="text-[11px] text-slate-400 font-mono">Deterministic Policy Engine • Non-Destructive Safe Automation</div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full ${agentOnline ? 'bg-emerald-400 animate-pulse' : 'bg-rose-400'}`} />
            <span className="text-xs font-mono text-slate-300">
              {agentOnline ? 'AGENT ONLINE' : 'AGENT OFFLINE'}
            </span>
          </div>
        </div>

        {/* Message Feed */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
          {activeConv?.messages.map((msg) => (
            <ChatMessageItem key={msg.id} message={msg} />
          ))}

          {isProcessing && (
            <div className="flex items-center gap-2 text-xs font-mono text-brand-400 py-2">
              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
              <span>Analyzing telemetry, checking policy rules & retrieving knowledge...</span>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Quick Command Pills */}
        <div className="px-6 py-2 border-t border-surface-border/60 bg-surface-subtle/50 flex items-center gap-2 overflow-x-auto text-[11px] font-mono shrink-0">
          <span className="text-slate-400 shrink-0">Commands:</span>
          <button
            onClick={() => setInput('/investigate CAM-001')}
            className="px-2.5 py-1 rounded bg-surface border border-surface-border text-slate-300 hover:text-white hover:border-brand-500 shrink-0 transition-colors"
          >
            /investigate CAM-001
          </button>
          <button
            onClick={() => setInput('/status CAM-002')}
            className="px-2.5 py-1 rounded bg-surface border border-surface-border text-slate-300 hover:text-white hover:border-brand-500 shrink-0 transition-colors"
          >
            /status CAM-002
          </button>
          <button
            onClick={() => setInput('/site SITE-001')}
            className="px-2.5 py-1 rounded bg-surface border border-surface-border text-slate-300 hover:text-white hover:border-brand-500 shrink-0 transition-colors"
          >
            /site SITE-001
          </button>
          <button
            onClick={() => setInput('/history RTSP')}
            className="px-2.5 py-1 rounded bg-surface border border-surface-border text-slate-300 hover:text-white hover:border-brand-500 shrink-0 transition-colors"
          >
            /history RTSP
          </button>
          <button
            onClick={() => setInput('/clear')}
            className="px-2.5 py-1 rounded bg-surface border border-surface-border text-slate-300 hover:text-white hover:border-rose-500 shrink-0 transition-colors"
          >
            /clear
          </button>
          <button
            onClick={() => setInput('/help')}
            className="px-2.5 py-1 rounded bg-surface border border-surface-border text-slate-300 hover:text-white hover:border-brand-500 shrink-0 transition-colors"
          >
            /help
          </button>
        </div>

        {/* Chat Input Bar */}
        <div className="p-4 border-t border-surface-border bg-surface shrink-0">
          <div className="flex items-end gap-2 p-2 rounded-xl bg-surface-subtle border border-surface-border focus-within:border-brand-500 transition-colors">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSendMessage();
                }
              }}
              placeholder="Ask the AI or type a slash command (e.g. /investigate CAM-001, /clear, /help)..."
              rows={2}
              className="flex-1 bg-transparent resize-none border-none outline-hidden text-sm text-slate-100 placeholder-slate-500 font-sans"
            />

            <button
              onClick={handleSendMessage}
              disabled={!input.trim() || isProcessing}
              className="p-2.5 rounded-lg bg-brand-600 hover:bg-brand-500 disabled:opacity-40 disabled:hover:bg-brand-600 text-white transition-colors"
              title="Send message (Enter)"
              aria-label="Send message"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
          <div className="mt-1.5 flex items-center justify-between text-[11px] text-slate-400 font-mono px-1">
            <span>Press <kbd className="px-1 py-0.5 rounded bg-surface-elevated text-slate-300">Enter</kbd> to send, <kbd className="px-1 py-0.5 rounded bg-surface-elevated text-slate-300">Shift+Enter</kbd> for newline</span>
            <span>Safety engine authoritative</span>
          </div>
        </div>
      </div>
    </div>
  );
};
