import React from 'react';
import { Plus, MessageSquare, Trash2 } from 'lucide-react';
import type { ChatConversation } from './types';

interface ChatSidebarProps {
  conversations: ChatConversation[];
  activeId: string;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDelete: (id: string) => void;
}

export const ChatSidebar: React.FC<ChatSidebarProps> = ({
  conversations,
  activeId,
  onSelect,
  onNew,
  onDelete,
}) => {
  return (
    <aside className="w-64 bg-surface-subtle border-r border-surface-border flex flex-col h-full shrink-0">
      <div className="p-3 border-b border-surface-border">
        <button
          onClick={onNew}
          className="w-full py-2 px-3 rounded-lg bg-brand-600 hover:bg-brand-500 text-white text-xs font-semibold flex items-center justify-center gap-2 transition-colors shadow-xs"
        >
          <Plus className="w-4 h-4" />
          <span>New Investigation</span>
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        <div className="px-2 py-1 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
          Investigations & Chats
        </div>

        {conversations.length === 0 ? (
          <div className="p-4 text-center text-xs text-slate-400">
            No stored conversations yet.
          </div>
        ) : (
          conversations.map((conv) => {
            const isActive = conv.id === activeId;
            return (
              <div
                key={conv.id}
                onClick={() => onSelect(conv.id)}
                className={`group flex items-center justify-between p-2 rounded-lg text-xs cursor-pointer transition-colors ${
                  isActive
                    ? 'bg-surface-elevated text-slate-100 border border-surface-borderLight'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-surface'
                }`}
              >
                <div className="flex items-center gap-2 min-w-0">
                  <MessageSquare className={`w-3.5 h-3.5 shrink-0 ${isActive ? 'text-brand-400' : 'text-slate-500'}`} />
                  <span className="truncate font-medium">{conv.title}</span>
                </div>

                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onDelete(conv.id);
                  }}
                  className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-surface-border text-slate-400 hover:text-rose-400 transition-opacity"
                  title="Delete chat"
                >
                  <Trash2 className="w-3 h-3" />
                </button>
              </div>
            );
          })
        )}
      </div>
    </aside>
  );
};
