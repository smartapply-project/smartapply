import type { AdminRow, Application, ApplicationForm, DocumentSlot } from './types';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(path, { headers: { 'Content-Type': 'application/json', ...(options?.headers || {}) }, ...options });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || 'The request could not be completed.');
  return body as T;
}

export function createApplication(form: ApplicationForm) {
  return request<{ id: number; status: string }>('/api/applications', { method: 'POST', body: JSON.stringify(form) });
}

export function getApplication(id: number) {
  return request<Application>(`/api/applications/${id}`);
}

export async function uploadDocument(id: number, slot: DocumentSlot, file: File, onProgress?: (value: number) => void) {
  onProgress?.(14);
  const formData = new FormData();
  formData.append('slot', slot);
  formData.append('file', file);
  const xhr = new XMLHttpRequest();
  const result = await new Promise<Application>((resolve, reject) => {
    xhr.open('POST', `/api/applications/${id}/documents`);
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress?.(Math.max(14, Math.round((event.loaded / event.total) * 72)));
    };
    xhr.onload = () => {
      const body = JSON.parse(xhr.responseText || '{}');
      if (xhr.status >= 200 && xhr.status < 300) { onProgress?.(100); resolve(body as Application); }
      else reject(new Error(body.detail || 'The upload could not be analyzed.'));
    };
    xhr.onerror = () => reject(new Error('Network error while uploading. Please try again.'));
    xhr.send(formData);
  });
  return result;
}

export function analyzeApplication(id: number) {
  return request<Application>(`/api/applications/${id}/analyze`, { method: 'POST' });
}

export function listApplications(status?: string) {
  const query = status && status !== 'All statuses' ? `?status=${encodeURIComponent(status)}` : '';
  return request<AdminRow[]>(`/api/admin/applications${query}`);
}
