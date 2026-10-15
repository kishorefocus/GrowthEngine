export interface HealthResponse {
  status: "healthy" | "degraded" | "error";
  service: string;
  timestamp: string;
  backend: {
    status: string;
    framework: string;
    environment: string;
  };
  database: {
    status: "connected" | "disconnected";
    engine: string;
    latency_ms: number | null;
    message: string;
  };
}

export interface Item {
  id: number;
  title: string;
  description: string | null;
  created_at: string;
}

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function fetchHealth(): Promise<HealthResponse> {
  const res = await fetch(`${API_BASE_URL}/health`, {
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Backend returned status ${res.status}`);
  }
  return res.json();
}

export async function fetchItems(): Promise<Item[]> {
  const res = await fetch(`${API_BASE_URL}/api/items`, {
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch items: ${res.statusText}`);
  }
  return res.json();
}

export async function createItem(title: string, description?: string): Promise<Item> {
  const res = await fetch(`${API_BASE_URL}/api/items`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ title, description }),
  });
  if (!res.ok) {
    throw new Error(`Failed to create item: ${res.statusText}`);
  }
  return res.json();
}
