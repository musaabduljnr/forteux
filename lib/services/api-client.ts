export interface ApiProblem {
  error?: {
    code?: string;
    message?: string;
    details?: unknown;
  };
  request_id?: string;
}

export class ApiRequestError extends Error {
  readonly status: number;
  readonly code: string;
  readonly requestId?: string;

  constructor(status: number, problem: ApiProblem) {
    super(problem.error?.message ?? "The request could not be completed.");
    this.name = "ApiRequestError";
    this.status = status;
    this.code = problem.error?.code ?? "request_failed";
    this.requestId = problem.request_id;
  }
}

export interface ApiProject {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface ApiAudit {
  id: string;
  project_id: string;
  name: string;
  mode: "single" | "multi";
  status: string;
  created_at: string;
}

export interface UploadIntent {
  asset_id: string;
  upload_url: string;
  required_headers: Record<string, string>;
  expires_in_seconds: number;
}

export interface ApiAsset {
  id: string;
  project_id: string;
  original_filename: string;
  declared_content_type: string;
  declared_size: number;
  status: "pending_upload" | "uploaded_unverified" | "deleting" | "deleted";
  created_at: string;
}

function assertSafePath(path: string): string {
  if (!path.startsWith("/") || path.startsWith("//") || path.split("/").some((part) => part === "." || part === "..")) {
    throw new Error("API paths must be absolute paths without traversal segments.");
  }
  return path;
}

export async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`/api/backend${assertSafePath(path)}`, {
    ...init,
    credentials: "same-origin",
    cache: "no-store",
    headers: {
      Accept: "application/json",
      ...(init.body ? { "Content-Type": "application/json" } : {}),
      ...init.headers,
    },
  });
  const requestId = response.headers.get("x-request-id") ?? undefined;
  const payload = response.status === 204 ? undefined : await response.json().catch(() => undefined);
  if (!response.ok) {
    const problem = (payload && typeof payload === "object" ? payload : {}) as ApiProblem;
    if (requestId && !problem.request_id) problem.request_id = requestId;
    throw new ApiRequestError(response.status, problem);
  }
  return payload as T;
}

export function listProjects(): Promise<ApiProject[]> {
  return apiRequest<ApiProject[]>("/projects");
}

export function createProject(input: Pick<ApiProject, "name" | "description">): Promise<ApiProject> {
  return apiRequest<ApiProject>("/projects", { method: "POST", body: JSON.stringify(input) });
}

export function createAudit(
  projectId: string,
  input: { name: string; mode: "single" | "multi"; context?: Record<string, string> },
): Promise<ApiAudit> {
  return apiRequest<ApiAudit>(`/projects/${encodeURIComponent(projectId)}/audits`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function initiateScreenshotUpload(
  projectId: string,
  input: { filename: string; content_type: "image/png" | "image/jpeg"; size: number },
  idempotencyKey: string,
): Promise<UploadIntent> {
  return apiRequest<UploadIntent>(`/projects/${encodeURIComponent(projectId)}/uploads`, {
    method: "POST",
    headers: { "Idempotency-Key": idempotencyKey },
    body: JSON.stringify(input),
  });
}

export function uploadToSignedUrl(
  file: File,
  intent: UploadIntent,
  onProgress: (progress: number) => void,
  signal?: AbortSignal,
): Promise<void> {
  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest();
    const abort = () => request.abort();
    const cleanup = () => signal?.removeEventListener("abort", abort);
    const fail = (error: Error) => {
      cleanup();
      reject(error);
    };
    request.open("PUT", intent.upload_url);
    for (const [name, value] of Object.entries(intent.required_headers)) {
      request.setRequestHeader(name, value);
    }
    request.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress(Math.round((event.loaded / event.total) * 100));
    };
    request.onerror = () => fail(new Error("Upload network request failed."));
    request.onabort = () => fail(new DOMException("Upload cancelled.", "AbortError"));
    request.onload = () => {
      if (request.status >= 200 && request.status < 300) {
        cleanup();
        onProgress(100);
        resolve();
      } else {
        fail(new Error(`Storage rejected the upload (HTTP ${request.status}).`));
      }
    };
    if (signal?.aborted) {
      fail(new DOMException("Upload cancelled.", "AbortError"));
      return;
    }
    signal?.addEventListener("abort", abort, { once: true });
    try {
      request.send(file);
    } catch (error) {
      cleanup();
      reject(error instanceof Error ? error : new Error("Upload could not be started."));
    }
  });
}

export function completeScreenshotUpload(projectId: string, assetId: string): Promise<ApiAsset> {
  return apiRequest<ApiAsset>(
    `/projects/${encodeURIComponent(projectId)}/assets/${encodeURIComponent(assetId)}/complete`,
    { method: "POST", body: "{}" },
  );
}

export function getScreenshotDownloadUrl(
  projectId: string,
  assetId: string,
): Promise<{ asset_id: string; download_url: string; expires_in_seconds: number }> {
  return apiRequest(
    `/projects/${encodeURIComponent(projectId)}/assets/${encodeURIComponent(assetId)}/download`,
  );
}

export function deleteScreenshot(projectId: string, assetId: string): Promise<void> {
  return apiRequest<void>(
    `/projects/${encodeURIComponent(projectId)}/assets/${encodeURIComponent(assetId)}`,
    { method: "DELETE" },
  );
}
