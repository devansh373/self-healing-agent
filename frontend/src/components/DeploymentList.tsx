import React from "react";
import { DeploymentSummary } from "@/types/deployment";
import { StatusBadge } from "./StatusBadge";

interface DeploymentListProps {
  deployments: DeploymentSummary[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

export function DeploymentList({ deployments, selectedId, onSelect }: DeploymentListProps) {
  if (deployments.length === 0) {
    return (
      <div className="list-empty">
        <p className="empty-title">No Pipeline Deployments Yet</p>
        <p className="empty-subtitle">Click &quot;Run Demo Pipeline&quot; above to simulate an infrastructure failure and trigger the self-healing agent.</p>
      </div>
    );
  }

  const formatTime = (isoString: string) => {
    try {
      return new Date(isoString).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch {
      return isoString;
    }
  };

  return (
    <div className="list-container">
      <h2 className="section-title">Deployment History</h2>
      <div className="list-items">
        {deployments.map((dep) => {
          const isSelected = dep.id === selectedId;
          const shortId = dep.id.split("-")[0];
          return (
            <div
              key={dep.id}
              onClick={() => onSelect(dep.id)}
              className={`list-card ${isSelected ? "selected" : ""}`}
            >
              <div className="card-header">
                <span className="id-tag">#{shortId}</span>
                <StatusBadge status={dep.status} />
              </div>
              <div className="card-body">
                <span className="fault-label">Fault:</span>
                <span className="fault-value">{dep.fault_category}</span>
              </div>
              <div className="card-footer">
                <span className="timestamp">{formatTime(dep.created_at)}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
