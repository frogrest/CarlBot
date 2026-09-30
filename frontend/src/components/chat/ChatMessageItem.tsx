import React, { useState } from 'react';
import {
  Bot,
  User,
  Wrench,
  BookOpen,
  ChevronDown,
  ChevronRight,
  ExternalLink,
  CheckCircle2,
} from 'lucide-react';
import type { ChatMessage } from './types';
import { PolicyBadge } from '../common/PolicyBadge';
import { ChatToolStep } from './ChatToolStep';
import { InvestigationTimeline } from '../timeline/InvestigationTimeline';
import { Link } from 'react-router-dom';

interface ChatMessageItemProps {
  message: ChatMessage;
}

export const ChatMessageItem: React.FC<ChatMessageItemProps> = ({ message }) => {
  const [showTimeline, setShowTimeline] = useState(false);
  const [showCitations, setShowCitations] = useState(false);

  const isUser = message.role === 'user';
  const isSystem = message.role === 'system';

  if (isSystem) {
    return (
      <div className="my-4 p-4 rounded-lg bg-surface-subtle border border-surface-border text-center text-xs text-slate-300 font-mono space-y-1">
        <div className="text-emerald-400 font-semibold">{message.content}</div>
        <p className="text-slate-400 text-[11px]">
          Previous chat context has been removed from this assistant session. Historical tickets, incidents, and audit records remain intact.
        </p>
      </div>
    );
  }

  return (
    <div className={`flex gap-3 my-4 ${isUser ? 'justify-end' : 'justify-start'}`}>
      {!isUser && (
        <div className="w-8 h-8 rounded-lg bg-brand-600/20 border border-brand-500/40 flex items-center justify-center text-brand-400 shrink-0 mt-0.5">
          <Bot className="w-4 h-4" />
        </div>
      )}

      <div className={`max-w-[85%] space-y-2 ${isUser ? 'items-end' : 'items-start'}`}>
        {/* Message Bubble */}
        <div
          className={`p-4 rounded-xl text-sm leading-relaxed ${
            isUser
              ? 'bg-brand-600 text-white rounded-tr-xs'
              : 'bg-surface border border-surface-border text-slate-100 rounded-tl-xs shadow-xs'
          }`}
        >
          <div className="whitespace-pre-wrap">{message.content}</div>

          {/* Diagnostic Tool Transparency */}
          {message.toolCalls && message.toolCalls.length > 0 && (
            <ChatToolStep toolCalls={message.toolCalls} />
          )}

          {/* AI Diagnosis Card */}
          {message.diagnosis && (
            <div className="mt-3 p-3.5 rounded-lg bg-surface-subtle border border-surface-border space-y-2 text-xs">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-slate-300 uppercase tracking-wider text-[11px]">
                  AI Diagnostic Hypothesis
                </span>
                <div className="flex items-center gap-2">
                  <span className="font-mono text-slate-400">
                    Confidence: {(message.diagnosis.confidence * 100).toFixed(0)}%
                  </span>
                  <PolicyBadge policyClass={message.diagnosis.safety_class} />
                </div>
              </div>

              <div className="font-mono text-xs text-brand-300 font-semibold">
                {message.diagnosis.fault}
              </div>

              <div className="text-slate-300 text-xs flex items-center gap-1.5">
                <span className="text-slate-400">Recommendation:</span>
                <span>{message.diagnosis.recommendation}</span>
              </div>
            </div>
          )}

          {/* Technician Action Required Card (Human-in-the-loop UX) */}
          {message.technicianRequired && (
            <div className="mt-3 p-4 rounded-lg bg-orange-950/40 border border-orange-700/60 text-orange-200 text-xs space-y-2">
              <div className="flex items-center gap-2 font-bold text-orange-300 uppercase tracking-wider text-[11px]">
                <Wrench className="w-4 h-4 text-orange-400" />
                <span>⚠️ Technician Action Required</span>
              </div>
              <p className="text-slate-300 leading-normal">
                {message.technicianActionText ||
                  'The AI identified an issue requiring on-site or manual technician action. Automated execution is blocked by safety policy.'}
              </p>
              {message.ticketId && (
                <div className="pt-2 border-t border-orange-800/40 flex items-center justify-between">
                  <span className="font-mono text-[11px] text-slate-400">Escalated Ticket: {message.ticketId}</span>
                  <Link
                    to={`/incidents/${message.ticketId}`}
                    className="inline-flex items-center gap-1 text-[11px] text-brand-400 hover:text-brand-300 underline font-medium"
                  >
                    <span>View Ticket Details</span>
                    <ExternalLink className="w-3 h-3" />
                  </Link>
                </div>
              )}
            </div>
          )}

          {/* Automated Recovery Success Card */}
          {message.actionExecuted && (
            <div className="mt-3 p-3 rounded-lg bg-emerald-950/40 border border-emerald-800/60 text-emerald-300 text-xs space-y-1">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5 font-semibold">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  <span>Safe Automated Recovery Executed</span>
                </div>
                <PolicyBadge policyClass="SAFE_REVERSIBLE" />
              </div>
              <div className="text-slate-300 font-mono text-[11px]">
                Action: <span className="text-emerald-300 font-bold">{message.actionExecuted}</span> • Verification Passed
              </div>
            </div>
          )}

          {/* Timeline Toggle Button */}
          {message.timeline && message.timeline.length > 0 && (
            <div className="mt-3 pt-2 border-t border-surface-border/50">
              <button
                onClick={() => setShowTimeline(!showTimeline)}
                className="flex items-center gap-1.5 text-xs text-brand-400 hover:text-brand-300 font-medium"
              >
                {showTimeline ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
                <span>
                  {showTimeline ? 'Hide' : 'View'} Full Diagnostic Investigation Timeline ({message.timeline.length} steps)
                </span>
              </button>

              {showTimeline && (
                <div className="mt-3 p-3 rounded-lg bg-surface-subtle border border-surface-border">
                  <InvestigationTimeline timeline={message.timeline} />
                </div>
              )}
            </div>
          )}

          {/* Citations / Knowledge Toggle Button */}
          {message.citations && message.citations.length > 0 && (
            <div className="mt-2">
              <button
                onClick={() => setShowCitations(!showCitations)}
                className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200"
              >
                <BookOpen className="w-3 h-3 text-sky-400" />
                <span>
                  {showCitations ? 'Hide' : 'Show'} Knowledge Citations ({message.citations.length})
                </span>
              </button>

              {showCitations && (
                <div className="mt-2 space-y-2">
                  {message.citations.map((c, i) => (
                    <div key={i} className="p-2.5 rounded bg-surface-subtle border border-surface-border text-xs">
                      <div className="font-mono text-sky-300 font-medium">{c.source}</div>
                      <p className="text-slate-400 text-[11px] mt-1 line-clamp-3">{c.snippet}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Timestamp */}
        <div className={`text-[10px] font-mono text-slate-400 px-1 ${isUser ? 'text-right' : 'text-left'}`}>
          {new Date(message.timestamp).toLocaleTimeString()}
        </div>
      </div>

      {isUser && (
        <div className="w-8 h-8 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300 shrink-0 mt-0.5">
          <User className="w-4 h-4" />
        </div>
      )}
    </div>
  );
};
