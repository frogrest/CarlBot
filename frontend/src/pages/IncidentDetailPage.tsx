import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  ArrowLeft,
  Wrench,
  Bot,
  CheckCircle2,
  Send,
  UserCheck,
} from 'lucide-react';
import { helpdeskApi, portalApi } from '../api';
import type { Ticket, CheckResult } from '../api/types';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { PolicyBadge } from '../components/common/PolicyBadge';
import { Skeleton } from '../components/common/Skeleton';
import { ErrorState } from '../components/common/ErrorState';
import { useLab } from '../context/LabContext';

export const IncidentDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { refresh: refreshGlobal } = useLab();

  const [ticket, setTicket] = useState<Ticket | null>(null);
  const [check, setCheck] = useState<CheckResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // New comment / note form
  const [commentText, setCommentText] = useState('');
  const [authorName, setAuthorName] = useState('tech-john');
  const [isTechNote, setIsTechNote] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const fetchDetails = async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const t = await helpdeskApi.getTicket(id);
      setTicket(t);

      if (t.asset_id) {
        try {
          const c = await portalApi.checkAsset(t.asset_id);
          setCheck(c);
        } catch {
          // Asset might be simulated or removed
        }
      }
    } catch (err: any) {
      setError(err.message || 'Ticket not found');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDetails();
  }, [id]);

  const handleAddCommentOrNote = async () => {
    if (!ticket || !commentText.trim()) return;
    setSubmitting(true);
    try {
      if (isTechNote) {
        await helpdeskApi.addTechnicianNote(ticket.id, authorName, commentText.trim());
      } else {
        await helpdeskApi.addComment(ticket.id, authorName, commentText.trim());
      }
      setCommentText('');
      await fetchDetails();
      refreshGlobal();
    } catch (err: any) {
      alert(`Failed to add note: ${err.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  const handleUpdateStatus = async (newStatus: Ticket['status']) => {
    if (!ticket) return;
    try {
      await helpdeskApi.updateTicket(ticket.id, {
        status: newStatus,
        resolution: newStatus === 'resolved' ? 'Manually verified and resolved by technician' : ticket.resolution,
      });
      await fetchDetails();
      refreshGlobal();
    } catch (err: any) {
      alert(`Failed to update status: ${err.message}`);
    }
  };

  if (loading) {
    return (
      <div className="p-6 max-w-5xl mx-auto space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (error || !ticket) {
    return (
      <div className="p-6 max-w-3xl mx-auto">
        <button
          onClick={() => navigate('/incidents')}
          className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-white mb-4"
        >
          <ArrowLeft className="w-3.5 h-3.5" /> Back to Incidents
        </button>
        <ErrorState
          title="Incident Not Found"
          message={`Could not load incident details for ${id}.`}
          error={error}
          onRetry={fetchDetails}
        />
      </div>
    );
  }

  // Parse structured evidence comment from agent if available
  let agentEvidence: any = null;
  const agentComment = ticket.comments.find(
    (c) => c.author === 'autonomous-agent' && c.body.startsWith('{')
  );
  if (agentComment) {
    try {
      agentEvidence = JSON.parse(agentComment.body);
    } catch {}
  }

  const isTechnicianRequired =
    ticket.status === 'pending_technician' ||
    ticket.status === 'pending_approval' ||
    agentEvidence?.safety_class === 'HUMAN_ONLY';

  return (
    <div className="p-6 space-y-6 max-w-5xl mx-auto">
      {/* Back button & Title banner */}
      <div>
        <button
          onClick={() => navigate('/incidents')}
          className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-white mb-3"
        >
          <ArrowLeft className="w-3.5 h-3.5" /> Back to Incidents
        </button>

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <span className="text-xl font-bold font-mono text-slate-100">{ticket.id}</span>
              <Badge status={ticket.status} />
              {agentEvidence?.safety_class && (
                <PolicyBadge policyClass={agentEvidence.safety_class} />
              )}
            </div>
            <h2 className="text-base font-semibold text-slate-200 mt-1">{ticket.title}</h2>
            <div className="text-xs text-slate-400 mt-1 font-mono flex items-center gap-3">
              <span>Site: {ticket.site_id}</span>
              {ticket.asset_id && (
                <span>
                  Asset:{' '}
                  <Link
                    to={`/devices/${ticket.asset_id}`}
                    className="text-brand-400 hover:underline font-semibold"
                  >
                    {ticket.asset_id}
                  </Link>
                </span>
              )}
              <span>Opened: {new Date(ticket.created_at).toLocaleString()}</span>
            </div>
          </div>

          {/* Status Controls */}
          <div className="flex items-center gap-2">
            {ticket.status !== 'resolved' && (
              <button
                onClick={() => handleUpdateStatus('resolved')}
                className="px-3 py-1.5 rounded-md text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white transition-colors"
              >
                Mark Resolved
              </button>
            )}
            {ticket.status === 'resolved' && (
              <button
                onClick={() => handleUpdateStatus('investigating')}
                className="px-3 py-1.5 rounded-md text-xs font-semibold bg-surface-elevated hover:bg-surface-hover text-slate-200 border border-surface-border transition-colors"
              >
                Reopen Incident
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Human-in-the-loop UX banner */}
      {isTechnicianRequired && (
        <div className="p-4 rounded-xl bg-orange-950/40 border border-orange-700 text-orange-200 text-xs space-y-2">
          <div className="flex items-center gap-2 font-bold text-orange-300 uppercase tracking-wider text-xs">
            <Wrench className="w-4 h-4 text-orange-400" />
            <span>⚠️ Human Technician Action Required</span>
          </div>
          <p className="text-slate-200 leading-relaxed">
            The autonomous AI diagnosed a fault classified as{' '}
            <strong className="font-mono text-orange-300">
              {agentEvidence?.safety_class || 'HUMAN_ONLY'}
            </strong>
            . Automated modification is strictly prohibited by the safety policy engine to protect physical equipment and sensitive credentials.
          </p>
          <div className="font-semibold text-white pt-1">
            Recommended Action: {agentEvidence?.recommended_action || ticket.resolution || 'Inspect equipment physically'}
          </div>
        </div>
      )}

      {/* Grid: AI Diagnostic Evidence & Live Telemetry */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Left: AI Diagnosis & Hypothesis */}
        <Card title="AI Diagnostic Hypothesis" subtitle="Derived deterministically by safety rules">
          {agentEvidence ? (
            <div className="space-y-4 text-xs">
              <div className="p-3 rounded-lg bg-surface-subtle border border-surface-border">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-brand-300 font-bold text-sm">
                    {agentEvidence.hypothesis}
                  </span>
                  <span className="font-mono text-slate-400">
                    Confidence: {(agentEvidence.confidence * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="text-slate-300 mt-2">
                  <span className="text-slate-400">Recommendation:</span>{' '}
                  {agentEvidence.recommended_action}
                </div>
              </div>

              <div>
                <div className="font-semibold text-slate-300 mb-2 uppercase text-[11px] tracking-wider">
                  Automated Safety Execution
                </div>
                {agentEvidence.actions_performed && agentEvidence.actions_performed.length > 0 ? (
                  <div className="p-3 rounded-lg bg-emerald-950/40 border border-emerald-800 text-emerald-300">
                    <div className="font-semibold flex items-center gap-1.5">
                      <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                      Executed: {agentEvidence.actions_performed.join(', ')}
                    </div>
                    <div className="font-mono text-[11px] text-slate-300 mt-1">
                      {agentEvidence.verification}
                    </div>
                  </div>
                ) : (
                  <div className="p-3 rounded-lg bg-surface-subtle border border-surface-border text-slate-400">
                    No automated actions performed. Policy engine required human intervention.
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="text-xs text-slate-400">
              <p>Description: {ticket.description}</p>
              {ticket.root_cause && (
                <div className="mt-2 font-mono text-amber-300">Root cause: {ticket.root_cause}</div>
              )}
            </div>
          )}
        </Card>

        {/* Right: Live Telemetry Checks */}
        <Card title="Observed Telemetry Evidence" subtitle="Real-time check results for this device">
          {check ? (
            <div className="space-y-2 font-mono text-xs">
              <div className="p-2.5 rounded bg-surface-subtle flex items-center justify-between">
                <span>ICMP Ping Reachability:</span>
                <span className={check.ping ? 'text-emerald-400' : 'text-rose-400'}>
                  {check.ping ? 'PASS' : 'FAIL'}
                </span>
              </div>
              {check.kind === 'camera' && (
                <>
                  <div className="p-2.5 rounded bg-surface-subtle flex items-center justify-between">
                    <span>TCP 554 (RTSP Port):</span>
                    <span className={check.tcp554 ? 'text-emerald-400' : 'text-rose-400'}>
                      {check.tcp554 ? 'PASS' : 'FAIL'}
                    </span>
                  </div>
                  <div className="p-2.5 rounded bg-surface-subtle flex items-center justify-between">
                    <span>RTSP Stream Telemetry:</span>
                    <span className={check.rtsp === true || check.rtsp === 'up' ? 'text-emerald-400' : 'text-rose-400'}>
                      {check.rtsp === true || check.rtsp === 'up' ? 'UP' : 'DOWN'}
                    </span>
                  </div>
                  <div className="p-2.5 rounded bg-surface-subtle flex items-center justify-between">
                    <span>RTSP Authentication:</span>
                    <span className={check.rtsp_auth !== false ? 'text-emerald-400' : 'text-rose-400'}>
                      {check.rtsp_auth !== false ? 'PASS' : 'FAIL'}
                    </span>
                  </div>
                  <div className="p-2.5 rounded bg-surface-subtle flex items-center justify-between">
                    <span>PoE Power Telemetry:</span>
                    <span className={check.poe !== false ? 'text-emerald-400' : 'text-rose-400'}>
                      {check.poe !== false ? 'POWERED ON' : 'POWER OFF'}
                    </span>
                  </div>
                </>
              )}
              {check.kind === 'nvr' && (
                <div className="p-2.5 rounded bg-surface-subtle flex items-center justify-between">
                  <span>Storage Utilisation:</span>
                  <span className={(check.storage_used || 0) >= 95 ? 'text-rose-400' : 'text-emerald-400'}>
                    {check.storage_used}%
                  </span>
                </div>
              )}
              {check.kind === 'ai_box' && (
                <>
                  <div className="p-2.5 rounded bg-surface-subtle flex items-center justify-between">
                    <span>AI Detection Service:</span>
                    <span className={check.service === 'up' ? 'text-emerald-400' : 'text-rose-400'}>
                      {check.service || 'up'}
                    </span>
                  </div>
                  <div className="p-2.5 rounded bg-surface-subtle flex items-center justify-between">
                    <span>CPU Utilisation:</span>
                    <span className={(check.cpu || 0) >= 90 ? 'text-rose-400' : 'text-emerald-400'}>
                      {check.cpu}%
                    </span>
                  </div>
                </>
              )}
            </div>
          ) : (
            <div className="p-4 text-xs text-slate-400">
              No live telemetry stream linked to this ticket.
            </div>
          )}
        </Card>
      </div>

      {/* Investigation Activity Log & Comments */}
      <Card title="Activity & Investigation Log" subtitle="Comments, technician notes, and agent documentation">
        <div className="space-y-4">
          {/* Feed of comments */}
          <div className="space-y-3">
            {ticket.comments.map((c, i) => {
              const isAgent = c.author === 'autonomous-agent';
              let displayBody = c.body;
              if (isAgent && c.body.startsWith('{')) {
                displayBody = 'Documented structured diagnostic evidence and policy evaluation.';
              }
              return (
                <div
                  key={`comment-${i}`}
                  className="p-3 rounded-lg bg-surface-subtle border border-surface-border text-xs"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-semibold text-slate-200 font-mono flex items-center gap-1.5">
                      {isAgent ? <Bot className="w-3.5 h-3.5 text-brand-400" /> : <UserCheck className="w-3.5 h-3.5 text-sky-400" />}
                      {c.author}
                    </span>
                    <span className="font-mono text-[10px] text-slate-500">
                      {new Date(c.at).toLocaleString()}
                    </span>
                  </div>
                  <p className="text-slate-300 whitespace-pre-wrap">{displayBody}</p>
                </div>
              );
            })}

            {ticket.technician_notes.map((n, i) => (
              <div
                key={`note-${i}`}
                className="p-3 rounded-lg bg-orange-950/20 border border-orange-800/40 text-xs"
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="font-semibold text-orange-300 font-mono flex items-center gap-1.5">
                    <Wrench className="w-3.5 h-3.5 text-orange-400" />
                    Technician Note: {n.author}
                  </span>
                  <span className="font-mono text-[10px] text-slate-500">
                    {new Date(n.at).toLocaleString()}
                  </span>
                </div>
                <p className="text-slate-200 whitespace-pre-wrap">{n.body}</p>
              </div>
            ))}
          </div>

          {/* Add note/comment box */}
          <div className="pt-4 border-t border-surface-border space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3 text-xs">
                <label className="flex items-center gap-1.5 cursor-pointer text-slate-300">
                  <input
                    type="radio"
                    checked={!isTechNote}
                    onChange={() => setIsTechNote(false)}
                    className="text-brand-500"
                  />
                  <span>General Comment</span>
                </label>
                <label className="flex items-center gap-1.5 cursor-pointer text-slate-300">
                  <input
                    type="radio"
                    checked={isTechNote}
                    onChange={() => setIsTechNote(true)}
                    className="text-orange-500"
                  />
                  <span className="text-orange-400 font-medium">Official Technician Repair Note</span>
                </label>
              </div>

              <input
                type="text"
                value={authorName}
                onChange={(e) => setAuthorName(e.target.value)}
                placeholder="Author handle..."
                className="px-2 py-1 text-xs rounded bg-surface border border-surface-border text-slate-200 font-mono"
              />
            </div>

            <div className="flex gap-2">
              <textarea
                value={commentText}
                onChange={(e) => setCommentText(e.target.value)}
                rows={2}
                placeholder={
                  isTechNote
                    ? 'Enter physical repair steps, credential updates, or hardware replacement notes...'
                    : 'Add investigation comment...'
                }
                className="flex-1 p-2.5 rounded-lg bg-surface border border-surface-border text-xs text-slate-200 focus:outline-hidden focus:border-brand-500"
              />
              <button
                onClick={handleAddCommentOrNote}
                disabled={!commentText.trim() || submitting}
                className="px-4 rounded-lg bg-brand-600 hover:bg-brand-500 disabled:opacity-40 text-white text-xs font-semibold flex items-center justify-center transition-colors"
              >
                <Send className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
};
