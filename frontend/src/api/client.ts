import axios, { AxiosInstance, InternalAxiosRequestConfig } from 'axios';
import type { ScanCreate, ScanResponse, FindingResponse, FindingListResponse, ScanSummary, HealthResponse, AIRemediationRequest, AIRemediationResponse, AIProviderStatus } from '../types';

const API_URL = import.meta.env.VITE_API_URL || '/api';

class ApiClient {
  private client: AxiosInstance;
  private token: string | null = null;

  constructor() {
    this.client = axios.create({
      baseURL: API_URL,
      headers: { 'Content-Type': 'application/json' },
      timeout: 30000,
    });

    this.client.interceptors.request.use((config: InternalAxiosRequestConfig) => {
      if (this.token && config.headers) {
        config.headers.Authorization = `Bearer ${this.token}`;
      }
      return config;
    });

    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          this.clearToken();
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
  }

  setToken(token: string | null) {
    this.token = token;
  }

  clearToken() {
    this.token = null;
  }

  async health(): Promise<HealthResponse> {
    const { data } = await this.client.get<HealthResponse>('/health');
    return data;
  }

  async createScan(scan: ScanCreate): Promise<ScanResponse> {
    const { data } = await this.client.post<ScanResponse>('/scans', scan);
    return data;
  }

  async listScans(params?: { cloud?: string; status?: string; limit?: number; offset?: number }): Promise<ScanResponse[]> {
    const { data } = await this.client.get<ScanResponse[]>('/scans', { params });
    return data;
  }

  async getScan(id: number): Promise<ScanResponse> {
    const { data } = await this.client.get<ScanResponse>(`/scans/${id}`);
    return data;
  }

  async getScanSummary(): Promise<ScanSummary> {
    const { data } = await this.client.get<ScanSummary>('/scans/summary');
    return data;
  }

  async getScanFindings(scanId: number, params?: { severity?: string; category?: string; page?: number; page_size?: number }): Promise<FindingListResponse> {
    const { data } = await this.client.get<FindingListResponse>(`/scans/${scanId}/findings`, { params });
    return data;
  }

  async listFindings(params?: { severity?: string; category?: string; cloud?: string; page?: number; page_size?: number }): Promise<FindingListResponse> {
    const { data } = await this.client.get<FindingListResponse>('/findings', { params });
    return data;
  }

  async getFinding(id: number): Promise<FindingResponse> {
    const { data } = await this.client.get<FindingResponse>(`/findings/${id}`);
    return data;
  }

  async getFindingsSummary() {
    const { data } = await this.client.get('/findings/stats/summary');
    return data;
  }

  async getAIStatus(): Promise<AIProviderStatus> {
    const { data } = await this.client.get<AIProviderStatus>('/ai/status');
    return data;
  }

  async generateRemediation(request: AIRemediationRequest): Promise<AIRemediationResponse> {
    const { data } = await this.client.post<AIRemediationResponse>('/ai/remediation', request);
    return data;
  }

  async deleteRemediation(findingId: number): Promise<void> {
    await this.client.delete(`/ai/remediation/${findingId}`);
  }

  async deleteScan(id: number): Promise<void> {
    await this.client.delete(`/scans/${id}`);
  }
}

export const api = new ApiClient();