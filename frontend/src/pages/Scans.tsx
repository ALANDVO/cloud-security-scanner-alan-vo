import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, RefreshCw, Trash2, Play, Clock, CheckCircle, XCircle, AlertTriangle, Cloud as CloudIcon, FileText, Sparkles, X } from 'lucide-react';
import { clsx } from 'clsx';
import { api } from '../api/client';
import type { ScanResponse, ScanCreate, ScanStatus, Cloud, AIExecutiveSummaryResponse, AIProviderStatus } from '../types';
const statusConfig = {
  pending: { label: 'Pending', icon: Clock, badge: 'badge-pending' },
  running: { label: 'Running', icon: Play, badge: 'badge-running' },
  completed: { label: 'Completed', icon: CheckCircle, badge: 'badge-completed' },
  failed: { label: 'Failed', icon: XCircle, badge: 'badge-failed' },
} as const;

const cloudConfig = {
  aws: { label: 'AWS', color: 'text-orange-600' },
  gcp: { label: 'GCP', color: 'text-blue-600' },
  azure: { label: 'Azure', color: 'text-indigo-600' },
} as const;

const severityConfig = {
  critical: { label: 'Critical', badge: 'badge-critical' },
  high: { label: 'High', badge: 'badge-high' },
  medium: { label: 'Medium', badge: 'badge-medium' },
  low: { label: 'Low', badge: 'badge-low' },
  info: { label: 'Info', badge: 'badge-info' },
} as const;

export function Scans() {
  const [filters, setFilters] = useState({ cloud: '', status: '' });
  const queryClient = useQueryClient();

  const { data: scans, isLoading, error, refetch } = useQuery({
    queryKey: ['scans', filters],
    queryFn: () => api.listScans({ cloud: filters.cloud || undefined, status: filters.status || undefined }),
  });

  const createMutation = useMutation({
    mutationFn: (scan: ScanCreate) => api.createScan(scan),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scans'] });
      queryClient.invalidateQueries({ queryKey: ['scan-summary'] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.deleteScan(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['scans'] }),
  });
  const [showCreate, setShowCreate] = useState(false);
  const [createForm, setCreateForm] = useState<ScanCreate>({ cloud: 'aws', region: 'us-east-1', category: '' });
  const [expandedScan, setExpandedScan] = useState<{ scan: ScanResponse; summary: AIExecutiveSummaryResponse | null; loading: boolean } | null>(null);
  const [aiStatus, setAiStatus] = useState<AIProviderStatus | null>(null);
  // Fetch AI status
  const { data: aiStatusData } = useQuery({
    queryKey: ['ai-status'],
    queryFn: () => api.getAIStatus(),
    staleTime: 5 * 60 * 1000,
  });

  // Update aiStatus when data changes
  useEffect(() => {
    if (aiStatusData) setAiStatus(aiStatusData);
  }, [aiStatusData]);

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    createMutation.mutate(createForm);
    setShowCreate(false);
    setCreateForm({ cloud: 'aws', region: 'us-east-1', category: '' });
  };

  const handleGenerateSummary = async (scan: ScanResponse) => {
    if (expandedScan?.scan.id === scan.id) {
      // Collapse if already expanded
      setExpandedScan(null);
      return;
    }

    setExpandedScan({ scan, summary: null, loading: true });
    try {
      const response = await api.generateExecutiveSummary({ scan_id: scan.id });
      setExpandedScan({ scan, summary: response, loading: false });
    } catch (error) {
      console.error('Failed to generate executive summary:', error);
      setExpandedScan({ scan, summary: null, loading: false });
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="animate-pulse">
            <div className="h-6 bg-gray-200 rounded w-48"></div>
          </div>
        </div>
        <div className="card animate-pulse p-6">
          <div className="h-4 bg-gray-200 rounded w-1/4 mb-4"></div>
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-16 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Scans</h1>
          <p className="text-gray-500">Manage and monitor cloud security scans</p>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={() => refetch()} className="btn-secondary" disabled={isLoading}>
            <RefreshCw className={clsx('h-4 w-4', isLoading && 'animate-spin')} />
            Refresh
          </button>
          <button onClick={() => setShowCreate(true)} className="btn-primary">
            <Plus className="h-4 w-4 mr-2" />
            New Scan
          </button>
        </div>
      </div>

      <div className="card">
        <div className="p-4 border-b border-gray-200">
          <div className="flex flex-wrap gap-4">
            <select
              value={filters.cloud}
              onChange={(e) => setFilters({ ...filters, cloud: e.target.value })}
              className="input w-auto"
              aria-label="Filter by cloud provider"
            >
              <option value="">All Clouds</option>
              <option value="aws">AWS</option>
              <option value="gcp">GCP</option>
              <option value="azure">Azure</option>
            </select>
            <select
              value={filters.status}
              onChange={(e) => setFilters({ ...filters, status: e.target.value })}
              className="input w-auto"
              aria-label="Filter by status"
            >
              <option value="">All Statuses</option>
              <option value="pending">Pending</option>
              <option value="running">Running</option>
              <option value="completed">Completed</option>
              <option value="failed">Failed</option>
            </select>
          </div>
        </div>

        {scans && scans.length === 0 && (
          <div className="p-12 text-center">
            <CloudIcon className="h-16 w-16 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No scans yet</h3>
            <p className="text-gray-500 mb-6">Create your first scan to start checking for security misconfigurations</p>
            <button onClick={() => setShowCreate(true)} className="btn-primary">
              <Plus className="h-4 w-4 mr-2" />
              Create Scan
            </button>
          </div>
        )}

        {scans && scans.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full" role="table">
              <thead>
                <tr className="border-b border-gray-200 bg-gray-50">
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Cloud</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Region</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Category</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Findings</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Started</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Completed</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {scans.map((scan: ScanResponse) => {
                  const status = scan.status as ScanStatus;
                  const statusInfo = statusConfig[status];
                  const StatusIcon = statusInfo.icon;
                  const cloud = scan.cloud as Cloud;
                  const cloudInfo = cloudConfig[cloud];
                  const isExpanded = expandedScan?.scan.id === scan.id;
                  return (
                    <>
                      <tr key={scan.id} className="hover:bg-gray-50">
                        <td className="px-4 py-4">
                          <span className={clsx('font-medium', cloudInfo.color)}>{cloudInfo.label}</span>
                        </td>
                        <td className="px-4 py-4 text-gray-900">{scan.region || '-'}</td>
                        <td className="px-4 py-4 text-gray-900">{scan.category || 'All'}</td>
                        <td className="px-4 py-4">
                          <span className={clsx('inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium', statusInfo.badge)}>
                            <StatusIcon className="h-3 w-3" aria-hidden="true" />
                            {statusInfo.label}
                          </span>
                        </td>
                        <td className="px-4 py-4">
                          <div className="flex items-center gap-2">
                            {scan.critical_count > 0 && <span className={severityConfig.critical.badge}>{scan.critical_count}</span>}
                            {scan.high_count > 0 && <span className={severityConfig.high.badge}>{scan.high_count}</span>}
                            {scan.medium_count > 0 && <span className={severityConfig.medium.badge}>{scan.medium_count}</span>}
                            {scan.low_count > 0 && <span className={severityConfig.low.badge}>{scan.low_count}</span>}
                            {scan.info_count > 0 && <span className={severityConfig.info.badge}>{scan.info_count}</span>}
                            {scan.findings_count === 0 && <span className="text-gray-400">—</span>}
                          </div>
                        </td>
                        <td className="px-4 py-4 text-gray-900">{new Date(scan.started_at).toLocaleString()}</td>
                        <td className="px-4 py-4 text-gray-900">{scan.completed_at ? new Date(scan.completed_at).toLocaleString() : '—'}</td>
                        <td className="px-4 py-4 text-right">
                          <div className="flex items-center justify-end gap-2">
                            <button
                              onClick={() => handleGenerateSummary(scan)}
                              disabled={isExpanded && expandedScan.loading || !aiStatus?.configured}
                              className={clsx(
                                'p-2 rounded-lg transition-colors flex items-center gap-1.5',
                                isExpanded && expandedScan.loading ? 'bg-purple-100 text-purple-600 cursor-wait' :
                                !aiStatus?.configured ? 'bg-gray-100 text-gray-400 cursor-not-allowed' :
                                'text-gray-400 hover:text-purple-600 hover:bg-purple-50'
                              )}
                              aria-label={isExpanded ? (expandedScan?.summary ? 'Collapse executive summary' : 'Generating...') : 'Generate executive summary'}
                              title={!aiStatus?.configured ? 'AI provider not configured' : isExpanded ? (expandedScan?.summary ? 'Collapse executive summary' : 'Generating...') : 'Generate AI executive summary'}
                            >
                              {isExpanded && expandedScan.loading ? <RefreshCw className="h-4 w-4 animate-spin" /> : isExpanded && expandedScan.summary ? <X className="h-4 w-4" /> : <FileText className="h-4 w-4" />}
                              {!expandedScan?.loading && !expandedScan?.summary && <Sparkles className="h-3.5 w-3.5" />}
                            </button>
                            <button
                              onClick={() => deleteMutation.mutate(scan.id)}
                              disabled={deleteMutation.isPending}
                              className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                              aria-label={`Delete scan ${scan.id}`}
                            >
                              <Trash2 className="h-4 w-4" />
                            </button>
                          </div>
                        </td>
                      </tr>
                      {isExpanded && expandedScan.summary && (
                        <tr key={`expanded-${scan.id}`}>
                          <td colSpan={8} className="px-4 py-4 bg-purple-50 border-t border-purple-100">
                            <div className="p-4">
                              <div className="flex items-center gap-2 mb-3">
                                <FileText className="h-5 w-5 text-purple-600" />
                                <span className="font-medium text-purple-800">AI Executive Summary</span>
                                <span className="text-xs text-purple-600 bg-purple-100 px-2 py-0.5 rounded">Advisory</span>
                                <span className="text-xs text-purple-600 bg-purple-100 px-2 py-0.5 rounded">
                                  Provider: {expandedScan.summary.provider} / {expandedScan.summary.model}
                                </span>
                              </div>
                              <div className="prose prose-sm max-w-none text-gray-800 whitespace-pre-wrap font-mono text-xs leading-relaxed">
                                {expandedScan.summary.ai_summary}
                              </div>
                              <div className="mt-3 flex items-center gap-2">
                                <button
                                  onClick={() => handleGenerateSummary(scan)}
                                  disabled={expandedScan.loading}
                                  className="btn-secondary text-xs"
                                >
                                  <RefreshCw className="h-3.5 w-3.5 mr-1" />
                                  Regenerate
                                </button>
                                <button
                                  onClick={() => handleGenerateSummary(scan)}
                                  className="btn-secondary text-xs"
                                >
                                  <X className="h-3.5 w-3.5 mr-1" />
                                  Collapse
                                </button>
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                      {isExpanded && !expandedScan.summary && aiStatus && (
                        <tr key={`expanded-${scan.id}-status`}>
                          <td colSpan={8} className="px-4 py-3 bg-purple-50 border-t border-purple-100">
                            <div className="p-3 flex items-center gap-2 text-xs text-gray-500">
                              <Sparkles className="h-3.5 w-3.5" />
                              <span>
                                {aiStatus.configured
                                  ? 'AI executive summary available — click the document icon to generate'
                                  : 'AI not configured — set LLM_API_KEY and LLM_PROVIDER in backend .env'}
                              </span>
                            </div>
                          </td>
                        </tr>
                      )}
                    </>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {error && (
          <div className="p-6 text-center text-red-600">
            <AlertTriangle className="h-8 w-8 mx-auto mb-2" />
            <p>Failed to load scans</p>
          </div>
        )}
      </div>

      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onClick={() => setShowCreate(false)}>
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6" onClick={(e) => e.stopPropagation()}>
            <h2 className="text-xl font-bold text-gray-900 mb-6">Create New Scan</h2>
            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label htmlFor="cloud" className="label">Cloud Provider</label>
                <select
                  id="cloud"
                  value={createForm.cloud}
                  onChange={(e) => setCreateForm({ ...createForm, cloud: e.target.value as Cloud })}
                  className="input"
                  required
                >
                  <option value="aws">AWS</option>
                  <option value="gcp">GCP</option>
                  <option value="azure">Azure</option>
                </select>
              </div>
              <div>
                <label htmlFor="region" className="label">Region</label>
                <input
                  id="region"
                  type="text"
                  value={createForm.region}
                  onChange={(e) => setCreateForm({ ...createForm, region: e.target.value })}
                  className="input"
                  placeholder="us-east-1"
                />
              </div>
              <div>
                <label htmlFor="category" className="label">Category (optional)</label>
                <select
                  id="category"
                  value={createForm.category}
                  onChange={(e) => setCreateForm({ ...createForm, category: e.target.value || undefined })}
                  className="input"
                >
                  <option value="">All Categories</option>
                  <option value="storage">Storage</option>
                  <option value="iam">IAM</option>
                  <option value="network">Network</option>
                  <option value="logging">Logging</option>
                </select>
              </div>
              <div className="flex justify-end gap-3 pt-4">
                <button type="button" onClick={() => setShowCreate(false)} className="btn-secondary">Cancel</button>
                <button type="submit" disabled={createMutation.isPending} className="btn-primary">
                  {createMutation.isPending ? 'Creating...' : 'Create Scan'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}