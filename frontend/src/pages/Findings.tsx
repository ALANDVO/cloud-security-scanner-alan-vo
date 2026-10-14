import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Filter, ChevronLeft, ChevronRight, AlertTriangle, Shield, Search, Database, Network, Brain, Sparkles, RefreshCw, X } from 'lucide-react';
import { clsx } from 'clsx';
import { api } from '../api/client';
import type { FindingResponse, Severity, Cloud, AIRemediationRequest } from '../types';

const severityConfig = {
  critical: { label: 'Critical', icon: AlertTriangle, color: 'text-red-600', bg: 'bg-red-100', badge: 'badge-critical' },
  high: { label: 'High', icon: AlertTriangle, color: 'text-orange-600', bg: 'bg-orange-100', badge: 'badge-high' },
  medium: { label: 'Medium', icon: AlertTriangle, color: 'text-yellow-600', bg: 'bg-yellow-100', badge: 'badge-medium' },
  low: { label: 'Low', icon: Shield, color: 'text-green-600', bg: 'bg-green-100', badge: 'badge-low' },
  info: { label: 'Info', icon: Shield, color: 'text-blue-600', bg: 'bg-blue-100', badge: 'badge-info' },
} as const;

const categoryIcons: Record<string, React.ComponentType<{ className?: string }>> = {
  storage: Database,
  iam: Shield,
  network: Network,
  logging: Search,
};

const cloudConfig = {
  aws: { label: 'AWS', color: 'text-orange-600' },
  gcp: { label: 'GCP', color: 'text-blue-600' },
  azure: { label: 'Azure', color: 'text-indigo-600' },
} as const;

export function Findings() {
  const [filters, setFilters] = useState({ severity: '', category: '', cloud: '' });
  const [page, setPage] = useState(1);
  const [expandedFinding, setExpandedFinding] = useState<number | null>(null);
  const [aiLoading, setAiLoading] = useState<number | null>(null);
  const pageSize = 20;

  const { data: findingsData, isLoading, error } = useQuery({
    queryKey: ['findings', filters, page],
    queryFn: () => api.listFindings({
      severity: filters.severity || undefined,
      category: filters.category || undefined,
      cloud: filters.cloud || undefined,
      page,
      page_size: pageSize,
    }),
  });

  const { data: summary } = useQuery({
    queryKey: ['findings-summary'],
    queryFn: () => api.getFindingsSummary(),
  });

  const { data: aiStatus } = useQuery({
    queryKey: ['ai-status'],
    queryFn: () => api.getAIStatus(),
  });

  const categories = summary?.by_category ? Object.keys(summary.by_category) : [];
  const clouds = summary?.by_cloud ? Object.keys(summary.by_cloud) : [];
  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="animate-pulse">
            <div className="h-6 bg-gray-200 rounded w-48"></div>
          </div>
        </div>
        <div className="card animate-pulse p-6">
          <div className="space-y-3">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="h-20 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  const findings = findingsData?.findings || [];
  const total = findingsData?.total || 0;
  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Findings</h1>
          <p className="text-gray-500">Browse and filter security findings across all scans</p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-500">{total} total findings</span>
        </div>
      </div>

      <div className="card">
        <div className="p-4 border-b border-gray-200">
          <div className="flex flex-wrap gap-4">
            <div className="relative">
              <Filter className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
              <select
                value={filters.severity}
                onChange={(e) => { setFilters({ ...filters, severity: e.target.value }); setPage(1); }}
                className="input pl-10 w-auto min-w-[180px]"
                aria-label="Filter by severity"
              >
                <option value="">All Severities</option>
                <option value="critical">Critical</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
                <option value="info">Info</option>
              </select>
            </div>
            <select
              value={filters.category}
              onChange={(e) => { setFilters({ ...filters, category: e.target.value }); setPage(1); }}
              className="input w-auto min-w-[180px]"
              aria-label="Filter by category"
            >
              <option value="">All Categories</option>
              {categories.map((c) => (
                <option key={c} value={c}>{c.charAt(0).toUpperCase() + c.slice(1)}</option>
              ))}
            </select>
            <select
              value={filters.cloud}
              onChange={(e) => { setFilters({ ...filters, cloud: e.target.value }); setPage(1); }}
              className="input w-auto min-w-[180px]"
              aria-label="Filter by cloud"
            >
              <option value="">All Clouds</option>
              {clouds.map((c) => (
                <option key={c} value={c}>{cloudConfig[c as keyof typeof cloudConfig]?.label || c.toUpperCase()}</option>
              ))}
            </select>
          </div>
        </div>

        {findings.length === 0 && (
          <div className="p-12 text-center">
            <Shield className="h-16 w-16 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No findings match your filters</h3>
            <p className="text-gray-500">Try adjusting your filters or run a new scan</p>
          </div>
        )}

        {findings.length > 0 && (
          <div className="divide-y divide-gray-200">
            {findings.map((finding: FindingResponse) => {
              const sevInfo = severityConfig[finding.severity as Severity];
              const SeverityIcon = sevInfo.icon;
              const cloud = finding.cloud as Cloud;
              const cloudInfo = cloudConfig[cloud];
              const CategoryIcon = categoryIcons[finding.category] || Search;
              const isExpanded = expandedFinding === finding.id;
              const isAiLoading = aiLoading === finding.id;
              const hasAiAnalysis = finding.ai_analysis && finding.ai_analysis.trim().length > 0;

              const handleGenerateAi = async () => {
                if (isAiLoading) return;
                setAiLoading(finding.id);
                try {
                  const request: AIRemediationRequest = { finding_id: finding.id, regenerate: false };
                  await api.generateRemediation(request);
                  // Update the finding with AI analysis by refetching
                  setExpandedFinding(finding.id);
                } catch (err) {
                  console.error('Failed to generate AI remediation:', err);
                } finally {
                  setAiLoading(null);
                }
              };

              const handleRegenerateAi = async () => {
                if (isAiLoading) return;
                setAiLoading(finding.id);
                try {
                  const request: AIRemediationRequest = { finding_id: finding.id, regenerate: true };
                  await api.generateRemediation(request);
                  setExpandedFinding(finding.id);
                } catch (err) {
                  console.error('Failed to regenerate AI remediation:', err);
                } finally {
                  setAiLoading(null);
                }
              };

              const handleToggleExpand = () => {
                setExpandedFinding(isExpanded ? null : finding.id);
              };

              return (
                <div key={finding.id} className="p-4 hover:bg-gray-50">
                  <div className="flex flex-col md:flex-row md:items-center gap-4">
                    <div className="flex items-center gap-3 flex-1 min-w-0">
                      <div className={clsx('p-2 rounded-lg', sevInfo.bg)}>
                        <SeverityIcon className={clsx('h-5 w-5', sevInfo.color)} aria-hidden="true" />
                      </div>
                      <div className="min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className={clsx('badge', sevInfo.badge)}>{sevInfo.label}</span>
                          <span className={clsx('text-sm font-medium', cloudInfo.color)}>{cloudInfo.label}</span>
                          <span className="text-sm text-gray-500 bg-gray-100 px-2 py-0.5 rounded">{finding.category}</span>
                        </div>
                        <p className="mt-1 font-medium text-gray-900 truncate">{finding.title}</p>
                        <p className="text-sm text-gray-500">{finding.resource}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-4 md:ml-auto">
                      <div className="text-right">
                        <p className="text-lg font-bold text-gray-900">{finding.score.toFixed(1)}</p>
                        <p className="text-xs text-gray-500">Risk Score</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={handleGenerateAi}
                          disabled={isAiLoading || (!aiStatus?.configured && !hasAiAnalysis)}
                          className={clsx(
                            'p-2 rounded-lg transition-colors flex items-center gap-1.5',
                            isAiLoading ? 'bg-purple-100 text-purple-600 cursor-wait' :
                            !aiStatus?.configured && !hasAiAnalysis ? 'bg-gray-100 text-gray-400 cursor-not-allowed' :
                            'text-gray-400 hover:text-purple-600 hover:bg-purple-50'
                          )}
                          aria-label={hasAiAnalysis ? (isExpanded ? 'Collapse AI analysis' : 'View AI analysis') : 'Generate AI remediation'}
                          title={!aiStatus?.configured && !hasAiAnalysis ? 'AI provider not configured' : hasAiAnalysis ? (isExpanded ? 'Collapse AI analysis' : 'View AI analysis') : 'Generate AI remediation'}
                        >
                          {isAiLoading ? <RefreshCw className="h-4 w-4 animate-spin" /> : hasAiAnalysis && isExpanded ? <X className="h-4 w-4" /> : <Brain className="h-4 w-4" />}
                          {!isAiLoading && !hasAiAnalysis && <Sparkles className="h-3.5 w-3.5" />}
                        </button>
                        <button className="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors" aria-label="View details">
                          <Search className="h-4 w-4" />
                        </button>
                      </div>
                    </div>
                  </div>

                  <div className="mt-4 pt-4 border-t border-gray-100 flex flex-col md:flex-row md:items-center gap-4">
                    <div className="flex-1">
                      <p className="text-sm text-gray-600">{finding.detail}</p>
                    </div>
                    <div className="flex items-center gap-2 text-sm text-gray-600">
                      <CategoryIcon className="h-4 w-4" aria-hidden="true" />
                      <span>Remediation:</span>
                    </div>
                    <div className="flex-1 md:w-auto">
                      <p className="text-sm text-gray-600 bg-gray-50 p-2 rounded font-mono text-xs overflow-x-auto">{finding.remediation}</p>
                    </div>
                  </div>

                  {/* AI Analysis Section */}
                  {hasAiAnalysis && isExpanded && (
                    <div className="mt-4 pt-4 border-t border-purple-100 bg-purple-50 rounded-lg p-4">
                      <div className="flex items-center gap-2 mb-3">
                        <Brain className="h-5 w-5 text-purple-600" />
                        <span className="font-medium text-purple-800">AI-Powered Remediation Analysis</span>
                        <span className="text-xs text-purple-600 bg-purple-100 px-2 py-0.5 rounded">Advisory</span>
                      </div>
                      <div className="prose prose-sm max-w-none text-gray-800 whitespace-pre-wrap font-mono text-xs leading-relaxed">
                        {finding.ai_analysis}
                      </div>
                      <div className="mt-3 flex items-center gap-2">
                        <button
                          onClick={handleRegenerateAi}
                          disabled={isAiLoading}
                          className="btn-secondary text-xs"
                        >
                          <RefreshCw className="h-3.5 w-3.5 mr-1" />
                          Regenerate
                        </button>
                        <button
                          onClick={handleToggleExpand}
                          className="btn-secondary text-xs"
                        >
                          <X className="h-3.5 w-3.5 mr-1" />
                          Collapse
                        </button>
                      </div>
                    </div>
                  )}

                  {/* AI Status Indicator */}
                  {!hasAiAnalysis && aiStatus && (
                    <div className="mt-3 pt-3 border-t border-gray-100 flex items-center gap-2 text-xs text-gray-500">
                      <Sparkles className="h-3.5 w-3.5" />
                      <span>
                        {aiStatus.configured
                          ? 'AI remediation available — click the brain icon to generate'
                          : 'AI not configured — set LLM_API_KEY and LLM_PROVIDER in backend .env'}
                      </span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {error && (
          <div className="p-6 text-center text-red-600">
            <AlertTriangle className="h-8 w-8 mx-auto mb-2" />
            <p>Failed to load findings</p>
          </div>
        )}

        {totalPages > 1 && (
          <div className="p-4 border-t border-gray-200 flex items-center justify-between">
            <p className="text-sm text-gray-500">
              Page {page} of {totalPages} — {total} total
            </p>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage(page - 1)}
                disabled={page === 1}
                className="btn-secondary p-2"
                aria-label="Previous page"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
              <button
                onClick={() => setPage(page + 1)}
                disabled={page === totalPages}
                className="btn-secondary p-2"
                aria-label="Next page"
              >
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}