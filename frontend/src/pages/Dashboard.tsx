import { useQuery } from '@tanstack/react-query';
import { Shield, AlertTriangle, CheckCircle, XCircle, Database, Cloud as CloudIcon } from 'lucide-react';
import { clsx } from 'clsx';
import { api } from '../api/client';
import type { Severity, Cloud } from '../types';
const severityConfig = {
  critical: { label: 'Critical', color: 'bg-red-500', bg: 'bg-red-100', text: 'text-red-800', icon: XCircle },
  high: { label: 'High', color: 'bg-orange-500', bg: 'bg-orange-100', text: 'text-orange-800', icon: AlertTriangle },
  medium: { label: 'Medium', color: 'bg-yellow-500', bg: 'bg-yellow-100', text: 'text-yellow-800', icon: AlertTriangle },
  low: { label: 'Low', color: 'bg-green-500', bg: 'bg-green-100', text: 'text-green-800', icon: CheckCircle },
  info: { label: 'Info', color: 'bg-blue-500', bg: 'bg-blue-100', text: 'text-blue-800', icon: Shield },
} as const;

const cloudConfig = {
  aws: { label: 'AWS', color: 'bg-orange-500', icon: CloudIcon },
  gcp: { label: 'GCP', color: 'bg-blue-500', icon: CloudIcon },
  azure: { label: 'Azure', color: 'bg-indigo-500', icon: CloudIcon },
} as const;

function StatCard({ title, value, icon: Icon, trend, color }: { title: string; value: number | string; icon: React.ComponentType<{ className?: string }>; trend?: string; color?: string }) {
  return (
    <div className="card p-6">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-medium text-gray-500">{title}</p>
          <p className="mt-1 text-3xl font-bold text-gray-900">{value}</p>
          {trend && <p className="mt-2 text-sm text-green-600 flex items-center gap-1">{trend}</p>}
        </div>
        <div className={clsx('p-3 rounded-xl', color || 'bg-blue-100')}>
          <Icon className={clsx('h-6 w-6', color?.replace('bg-', 'text-').replace('100', '600') || 'text-blue-600')} aria-hidden="true" />
        </div>
      </div>
    </div>
  );
}

function SeverityBadge({ severity, count }: { severity: Severity; count: number }) {
  const config = severityConfig[severity];
  const Icon = config.icon;
  return (
    <div className="flex items-center gap-3 p-3 bg-white rounded-lg border border-gray-200">
      <div className={clsx('p-2 rounded-lg', config.bg)}>
        <Icon className={clsx('h-5 w-5', config.text)} aria-hidden="true" />
      </div>
      <div>
        <p className="font-medium text-gray-900">{config.label}</p>
        <p className="text-2xl font-bold text-gray-900">{count}</p>
      </div>
    </div>
  );
}

function CloudBadge({ cloud, count }: { cloud: Cloud; count: number }) {
  const config = cloudConfig[cloud];
  const Icon = config.icon;
  return (
    <div className="flex items-center gap-3 p-3 bg-white rounded-lg border border-gray-200">
      <div className={clsx('p-2 rounded-lg', config.color.replace('500', '100'))}>
        <Icon className={clsx('h-5 w-5', config.color.replace('500', '600'))} aria-hidden="true" />
      </div>
      <div>
        <p className="font-medium text-gray-900">{config.label}</p>
        <p className="text-2xl font-bold text-gray-900">{count}</p>
      </div>
    </div>
  );
}

export function Dashboard() {
  const { data: summary, isLoading: summaryLoading, error: summaryError } = useQuery({
    queryKey: ['scan-summary'],
    queryFn: () => api.getScanSummary(),
  });

  const { data: health, isLoading: healthLoading } = useQuery({
    queryKey: ['health'],
    queryFn: () => api.health(),
    refetchInterval: 30000,
  });

  const { data: findingsSummary } = useQuery({
    queryKey: ['findings-summary'],
    queryFn: () => api.getFindingsSummary(),
  });

  if (summaryLoading || healthLoading) {
    return (
      <div className="space-y-6">
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="card p-6 animate-pulse">
              <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
              <div className="h-8 bg-gray-200 rounded w-1/2"></div>
            </div>
          ))}
        </div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="card p-4 animate-pulse">
              <div className="h-4 bg-gray-200 rounded w-1/2 mb-2"></div>
              <div className="h-8 bg-gray-200 rounded w-1/3"></div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (summaryError) {
    return (
      <div className="card p-8 text-center">
        <AlertTriangle className="h-12 w-12 text-red-500 mx-auto mb-4" />
        <h2 className="text-xl font-semibold text-gray-900 mb-2">Failed to load dashboard</h2>
        <p className="text-gray-500">Unable to fetch scan summary. Please try again later.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-500">Overview of your cloud security posture</p>
        </div>
        <div className="flex items-center gap-2">
          <span className={clsx('inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-medium', health?.status === 'healthy' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800')}>
            <span className={clsx('h-2 w-2 rounded-full', health?.status === 'healthy' ? 'bg-green-500' : 'bg-yellow-500')} />
            {health?.status === 'healthy' ? 'System Healthy' : 'System Degraded'}
          </span>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard title="Total Scans" value={summary?.total_scans || 0} icon={Database} color="bg-blue-100" />
        <StatCard title="Completed" value={summary?.completed_scans || 0} icon={CheckCircle} color="bg-green-100" trend="↑ 12% from last week" />
        <StatCard title="Failed" value={summary?.failed_scans || 0} icon={XCircle} color="bg-red-100" />
        <StatCard title="Total Findings" value={summary?.total_findings || 0} icon={AlertTriangle} color="bg-orange-100" trend="↓ 5% from last week" />
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
        {(Object.keys(severityConfig) as Severity[]).map((sev) => (
          <SeverityBadge key={sev} severity={sev} count={summary?.by_severity?.[sev] || 0} />
        ))}
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        {(Object.keys(cloudConfig) as Cloud[]).map((c) => (
          <CloudBadge key={c} cloud={c} count={summary?.by_cloud?.[c] || 0} />
        ))}
      </div>

      <div className="card">
        <div className="p-6 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Top Findings</h2>
        </div>
        <div className="divide-y divide-gray-200">
          {findingsSummary?.top_findings?.slice(0, 5).map((f: { id: number; finding_id: string; severity: Severity; score: number; category: string; resource: string; title: string; cloud: Cloud }) => (
            <div key={f.id} className="p-4 hover:bg-gray-50">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className={clsx('badge', `badge-${f.severity}`)}>
                      {f.severity.charAt(0).toUpperCase() + f.severity.slice(1)}
                    </span>
                    <span className="text-sm text-gray-500">{f.cloud.toUpperCase()}</span>
                    <span className="text-sm text-gray-500">{f.category}</span>
                  </div>
                  <p className="mt-1 font-medium text-gray-900 truncate">{f.title}</p>
                  <p className="mt-1 text-sm text-gray-500">{f.resource}</p>
                </div>
                <span className="text-lg font-bold text-gray-900">{f.score.toFixed(1)}</span>
              </div>
            </div>
          ))}
          {(!findingsSummary?.top_findings?.length) && (
            <div className="p-8 text-center text-gray-500">
              <Shield className="h-12 w-12 mx-auto text-gray-300 mb-4" />
              <p>No findings yet. Run a scan to see results.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}