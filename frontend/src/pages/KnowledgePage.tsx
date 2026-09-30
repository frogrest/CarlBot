import React, { useState, useEffect } from 'react';
import { BookOpen, Search, FileText, ChevronRight } from 'lucide-react';
import { agentApi } from '../api';
import type { KnowledgeDocSummary, KnowledgeDocDetail } from '../api/types';
import { Card } from '../components/common/Card';
import { Skeleton } from '../components/common/Skeleton';

export const KnowledgePage: React.FC = () => {
  const [docs, setDocs] = useState<KnowledgeDocSummary[]>([]);
  const [selectedDocPath, setSelectedDocPath] = useState<string>('');
  const [activeDocDetail, setActiveDocDetail] = useState<KnowledgeDocDetail | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<Array<{ source: string; score: number; snippet: string }>>([]);
  const [loading, setLoading] = useState(true);
  const [docLoading, setDocLoading] = useState(false);

  useEffect(() => {
    const fetchDocs = async () => {
      setLoading(true);
      try {
        const list = await agentApi.getKnowledgeDocs();
        setDocs(list);
        if (list.length > 0) {
          setSelectedDocPath(list[0].source);
        }
      } catch (err) {
        console.error('Failed to load knowledge docs:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchDocs();
  }, []);

  useEffect(() => {
    if (!selectedDocPath) return;
    const fetchDocDetail = async () => {
      setDocLoading(true);
      try {
        const detail = await agentApi.getKnowledgeDoc(selectedDocPath);
        setActiveDocDetail(detail);
      } catch (err) {
        console.error('Failed to fetch doc detail:', err);
      } finally {
        setDocLoading(false);
      }
    };
    fetchDocDetail();
  }, [selectedDocPath]);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) {
      setSearchResults([]);
      return;
    }
    try {
      const res = await agentApi.searchKnowledge(searchQuery.trim());
      setSearchResults(res);
    } catch (err) {
      console.error('Search error:', err);
    }
  };

  if (loading) {
    return (
      <div className="p-6 max-w-6xl mx-auto space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6 max-w-6xl mx-auto">
      {/* Header & Search */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
            <BookOpen className="w-5 h-5 text-brand-400" />
            Operational Knowledge & Troubleshooting Guides
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Standard operating procedures, reference guides, and verified resolution patterns
          </p>
        </div>

        <form onSubmit={handleSearch} className="relative w-full sm:w-80">
          <Search className="w-4 h-4 absolute left-3 top-3 text-slate-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search knowledge by keywords..."
            className="w-full pl-9 pr-4 py-2 text-xs rounded-lg bg-surface border border-surface-border text-slate-200 placeholder-slate-500 focus:outline-hidden focus:border-brand-500"
          />
        </form>
      </div>

      {/* Search results banner if present */}
      {searchResults.length > 0 && (
        <div className="p-4 rounded-xl bg-surface-subtle border border-surface-border space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
              Search Results ({searchResults.length})
            </span>
            <button
              onClick={() => {
                setSearchResults([]);
                setSearchQuery('');
              }}
              className="text-xs text-slate-400 hover:text-white"
            >
              Clear Search
            </button>
          </div>

          <div className="space-y-2">
            {searchResults.map((res, i) => (
              <div
                key={i}
                onClick={() => setSelectedDocPath(res.source)}
                className="p-3 rounded-lg bg-surface hover:bg-surface-elevated border border-surface-border cursor-pointer transition-colors"
              >
                <div className="flex items-center justify-between text-xs">
                  <span className="font-mono font-semibold text-brand-300">{res.source}</span>
                  <span className="font-mono text-slate-400 text-[10px]">Keyword Score: {res.score}</span>
                </div>
                <p className="text-slate-300 text-xs mt-1.5 line-clamp-2">{res.snippet}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Main split view: Document List & Document Reader */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Left Col: Document List */}
        <div className="space-y-3">
          <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider px-1">
            Documentation Guides ({docs.length})
          </div>

          <div className="space-y-2">
            {docs.map((doc) => {
              const isSelected = doc.source === selectedDocPath;
              return (
                <div
                  key={doc.source}
                  onClick={() => setSelectedDocPath(doc.source)}
                  className={`p-3.5 rounded-lg border cursor-pointer transition-all ${
                    isSelected
                      ? 'bg-surface-elevated border-brand-500/80 shadow-xs'
                      : 'bg-surface border-surface-border hover:bg-surface-elevated/50'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 min-w-0">
                      <FileText className={`w-4 h-4 shrink-0 ${isSelected ? 'text-brand-400' : 'text-slate-400'}`} />
                      <span className="text-xs font-semibold text-slate-200 truncate">
                        {doc.title || doc.source}
                      </span>
                    </div>
                    {isSelected && <ChevronRight className="w-4 h-4 text-brand-400 shrink-0" />}
                  </div>

                  <div className="text-[11px] font-mono text-slate-400 mt-1">
                    {doc.source} • {doc.lines} lines
                  </div>

                  <p className="text-slate-400 text-[11px] mt-1.5 line-clamp-2">{doc.snippet}</p>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right 2 Cols: Document Reader */}
        <div className="md:col-span-2">
          {docLoading ? (
            <div className="panel p-6 space-y-3">
              <Skeleton className="h-6 w-1/3" />
              <Skeleton className="h-4 w-full" count={8} />
            </div>
          ) : activeDocDetail ? (
            <Card
              title={activeDocDetail.title || activeDocDetail.source}
              subtitle={`Source: data/knowledge/${activeDocDetail.source} (${activeDocDetail.lines} lines, ${activeDocDetail.size} bytes)`}
            >
              <div className="prose prose-invert max-w-none text-xs leading-relaxed font-mono">
                <pre className="p-4 rounded-lg bg-surface-subtle border border-surface-border text-slate-200 whitespace-pre-wrap font-sans text-sm leading-relaxed overflow-x-auto max-h-[70vh]">
                  {activeDocDetail.content}
                </pre>
              </div>
            </Card>
          ) : (
            <div className="panel p-8 text-center text-xs text-slate-400">
              Select a knowledge document from the list to view its contents.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
