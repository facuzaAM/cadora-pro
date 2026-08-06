const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL;
if (!API_BASE_URL && typeof window !== "undefined") {
  console.error("NEXT_PUBLIC_API_URL is not set");
}

class ApiClient {
  private baseUrl = API_BASE_URL || "";
  private accessToken: string | null = null;

  constructor() {
    if (typeof window !== "undefined") {
      this.accessToken = readCookie("cadora_access");
    }
  }

  getBaseUrl(): string {
    return this.baseUrl;
  }

  setAccessToken(token: string | null) {
    this.accessToken = token;
  }

  getAccessToken(): string | undefined {
    return this.accessToken ?? undefined;
  }

  private _fetchTimeout = 30000;

  private async _fetch(input: RequestInfo, init?: RequestInit): Promise<Response> {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this._fetchTimeout);
    try {
      const res = await fetch(input, { ...init, signal: controller.signal });
      return res;
    } finally {
      clearTimeout(timer);
    }
  }

  async get<T>(path: string, token?: string): Promise<T> {
    const res = await this._fetch(`${this.baseUrl}${path}`, {
      credentials: "include",
      headers: this.headers(token),
    });
    return this.handleResponse<T>(res);
  }

  async post<T>(path: string, body: unknown, token?: string): Promise<T> {
    const res = await this._fetch(`${this.baseUrl}${path}`, {
      method: "POST",
      credentials: "include",
      headers: this.headers(token),
      body: JSON.stringify(body),
    });
    return this.handleResponse<T>(res);
  }

  async upload<T>(
    path: string,
    formData: FormData,
    token?: string,
    extraHeaders?: Record<string, string>,
  ): Promise<T> {
    const auth = token || this.accessToken;
    const headers: Record<string, string> = { ...extraHeaders };
    if (auth) headers["Authorization"] = `Bearer ${auth}`;
    const res = await this._fetch(`${this.baseUrl}${path}`, {
      method: "POST",
      credentials: "include",
      headers,
      body: formData,
    });
    return this.handleResponse<T>(res);
  }

  async patch<T>(path: string, body: unknown, token?: string): Promise<T> {
    const res = await this._fetch(`${this.baseUrl}${path}`, {
      method: "PATCH",
      credentials: "include",
      headers: this.headers(token),
      body: JSON.stringify(body),
    });
    return this.handleResponse<T>(res);
  }

  async put<T>(path: string, body: unknown, token?: string): Promise<T> {
    const res = await this._fetch(`${this.baseUrl}${path}`, {
      method: "PUT",
      credentials: "include",
      headers: this.headers(token),
      body: JSON.stringify(body),
    });
    return this.handleResponse<T>(res);
  }

  async delete<T>(path: string, token?: string, body?: unknown): Promise<T> {
    const res = await this._fetch(`${this.baseUrl}${path}`, {
      method: "DELETE",
      credentials: "include",
      headers: this.headers(token),
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
    if (res.status === 204) return undefined as T;
    return this.handleResponse<T>(res);
  }

  private async handleResponse<T>(res: Response): Promise<T> {
    if (res.status === 402 && typeof window !== "undefined") {
      window.location.href = "/pricing?reason=limit_reached";
      throw new ApiError(402, { detail: "Límite alcanzado. Redirigiendo..." });
    }
    if (!res.ok) {
      let body: unknown;
      try { body = await res.json(); } catch { body = { detail: `Error ${res.status}` }; }
      throw new ApiError(res.status, body);
    }
    return res.json();
  }

  private headers(token?: string): Record<string, string> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };
    const auth = token || this.accessToken;
    if (auth) headers["Authorization"] = `Bearer ${auth}`;
    return headers;
  }
}

function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(new RegExp(`(^| )${name}=([^;]+)`));
  return match ? decodeURIComponent(match[2]) : null;
}

export class ApiError extends Error {
  public status: number;
  public body: unknown;

  constructor(status: number, body: unknown) {
    const detail =
      typeof body === "object" && body !== null && "detail" in body
        ? String((body as { detail: unknown }).detail)
        : `Error ${status}`;
    super(detail);
    this.status = status;
    this.body = body;
  }
}

export const api = new ApiClient();
