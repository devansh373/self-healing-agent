import { DeploymentDetail, DeploymentSummary } from "@/types/deployment";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export async function triggerDeployment(): Promise<DeploymentSummary> {
  const res = await fetch(`${API_BASE_URL}/api/deployments/trigger`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
  if (!res.ok) {
    throw new Error(`Failed to trigger deployment: ${res.statusText}`);
  }
  return res.json();
}

export async function listDeployments(): Promise<DeploymentSummary[]> {
  const res = await fetch(`${API_BASE_URL}/api/deployments`, {
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to list deployments: ${res.statusText}`);
  }
  return res.json();
}

export async function getDeployment(id: string): Promise<DeploymentDetail> {
  const res = await fetch(`${API_BASE_URL}/api/deployments/${id}`, {
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to get deployment detail: ${res.statusText}`);
  }
  return res.json();
}
