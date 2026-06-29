export const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000"

let accessToken: string | null = null
let refreshToken: string | null = null

export function setTokens(access: string, refresh: string) {
  accessToken = access
  refreshToken = refresh
  localStorage.setItem("access_token", access)
  localStorage.setItem("refresh_token", refresh)
}

export function loadTokens() {
  accessToken = localStorage.getItem("access_token")
  refreshToken = localStorage.getItem("refresh_token")
}

export function clearTokens() {
  accessToken = null
  refreshToken = null
  localStorage.removeItem("access_token")
  localStorage.removeItem("refresh_token")
}

export function getAccessToken() {
  return accessToken
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  opts?: { formData?: boolean; rawResponse?: boolean }
): Promise<T> {
  const headers: Record<string, string> = {}
  if (!opts?.formData) {
    headers["Content-Type"] = "application/json"
  }
  if (accessToken) {
    headers["Authorization"] = `Bearer ${accessToken}`
  }

  let response = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body
      ? opts?.formData
        ? (body as FormData)
        : JSON.stringify(body)
      : undefined,
  })

  if (response.status === 401 && refreshToken) {
    const refreshed = await fetch(`${API_BASE}/v1/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    })
    if (refreshed.ok) {
      const data = await refreshed.json()
      setTokens(data.access_token, data.refresh_token)
      headers["Authorization"] = `Bearer ${accessToken}`
      response = await fetch(`${API_BASE}${path}`, {
        method,
        headers,
        body: body
          ? opts?.formData
            ? (body as FormData)
            : JSON.stringify(body)
          : undefined,
      })
    } else {
      clearTokens()
      window.location.href = "/login"
      throw new Error("Session expired")
    }
  }

  if (opts?.rawResponse) return response as unknown as T

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: response.statusText }))
    throw new Error(err.detail || "Request failed")
  }

  return response.json()
}

export const api = {
  get: <T>(path: string) => request<T>("GET", path),
  post: <T>(path: string, body?: unknown) => request<T>("POST", path, body),
  put: <T>(path: string, body?: unknown) => request<T>("PUT", path, body),
  delete: <T>(path: string) => request<T>("DELETE", path),
  upload: <T>(path: string, formData: FormData) =>
    request<T>("POST", path, formData, { formData: true }),
  raw: (method: string, path: string) =>
    request<Response>(method, path, undefined, { rawResponse: true }),
  postWithTotal: async <T>(path: string, body?: unknown): Promise<{ items: T[]; total: number }> => {
    const resp = await request<Response>("POST", path, body, { rawResponse: true })
    const items: T[] = await resp.json()
    const total = parseInt(resp.headers.get("X-Total-Count") || "0", 10)
    return { items, total }
  },
}
