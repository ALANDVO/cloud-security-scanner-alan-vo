export type Severity = 'critical' | 'high' | 'medium' | 'low' | 'info';
export type Cloud = 'aws' | 'gcp' | 'azure';
export type ScanStatus = 'pending' | 'running' | 'completed' | 'failed';

export interface ScanCreate {
  cloud: Cloud;
  region?: string;
  category?: string;
  severity_filter?: Severity;
}

export interface ScanResponse {
  id: number;
  cloud: Cloud;
  region: string | null;
  category: string | null;
  severity_filter: Severity | null;
  status: ScanStatus;
  findings_count: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  info_count: number;
  started_at: string;
  completed_at: string | null;
  error_message: string | null;
}

export interface FindingResponse {
  id: number;
  scan_id: number;
  finding_id: string;
  severity: Severity;
  score: number;
  category: string;
  resource: string;
  title: string;
  detail: string;
  remediation: string;
  cloud: Cloud;
  detected_at: string;
  ai_analysis: string | null;
}

export interface FindingListResponse {
  findings: FindingResponse[];
  total: number;
  page: number;
  page_size: number;
}

export interface ScanSummary {
  total_scans: number;
  completed_scans: number;
  failed_scans: number;
  total_findings: number;
  by_severity: Record<Severity, number>;
  by_cloud: Record<Cloud, number>;
}

export interface HealthResponse {
  status: string;
  version: string;
  database: string;
}

export interface AIRemediationRequest {
  finding_id: number;
  regenerate?: boolean;
}

export interface AIRemediationResponse {
  finding_id: number;
  ai_analysis: string;
  provider: string;
  model: string;
  generated_at: string;
}

export interface AIProviderStatus {
  configured: boolean;
  provider: string;
  model: string;
}

export interface User {
  sub: string;
  roles: string[];
  email?: string;
  name?: string;
}