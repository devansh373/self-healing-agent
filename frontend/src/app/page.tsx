"use client";

import React, { useEffect, useState, useCallback } from "react";
import { listDeployments, getDeployment } from "@/lib/api";
import { useDeploymentSocket } from "@/lib/useDeploymentSocket";
import { DeploymentSummary, DeploymentDetail as DeploymentDetailType } from "@/types/deployment";
import { TriggerButton } from "@/components/TriggerButton";
import { DeploymentList } from "@/components/DeploymentList";
import { DeploymentDetail } from "@/components/DeploymentDetail";

export default function DashboardPage() {
  const [deployments, setDeployments] = useState<DeploymentSummary[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<DeploymentDetailType | null>(null);
  const [loadingDetail, setLoadingDetail] = useState<boolean>(false);
  const [errorBanner, setErrorBanner] = useState<string | null>(null);

  // Initial fetch of deployment history on mount
  useEffect(() => {
    async function initFetch() {
      try {
        const list = await listDeployments();
        setDeployments(list);
        if (list.length > 0 && !selectedId) {
          setSelectedId(list[0].id);
        }
      } catch (err: unknown) {
        console.error("Failed to load initial history:", err);
      }
    }
    initFetch();
  }, []);

  // Fetch detailed diagnostics whenever selectedId changes
  useEffect(() => {
    const sid = selectedId;
    if (!sid) return;
    async function loadDetail(id: string) {
      setLoadingDetail(true);
      try {
        const d = await getDeployment(id);
        setDetail(d);
      } catch (err: unknown) {
        console.error(err);
        setErrorBanner(`Failed to load detail for #${id.split("-")[0]}`);
      } finally {
        setLoadingDetail(false);
      }
    }
    loadDetail(sid);
  }, [selectedId]);

  // Handle live WebSocket pushes from backend orchestrator
  const handleSocketUpdate = useCallback((incomingDetail: DeploymentDetailType) => {
    // 1. Update list item summary
    setDeployments((prev) => {
      const exists = prev.some((d) => d.id === incomingDetail.id);
      if (exists) {
        return prev.map((d) =>
          d.id === incomingDetail.id
            ? {
                id: incomingDetail.id,
                fault_category: incomingDetail.fault_category,
                status: incomingDetail.status,
                created_at: incomingDetail.created_at,
                resolved_at: incomingDetail.resolved_at,
              }
            : d
        );
      } else {
        // Prepend newly triggered deployment
        return [
          {
            id: incomingDetail.id,
            fault_category: incomingDetail.fault_category,
            status: incomingDetail.status,
            created_at: incomingDetail.created_at,
            resolved_at: incomingDetail.resolved_at,
          },
          ...prev,
        ];
      }
    });

    // 2. If the updated deployment is currently selected, update its detail view live
    setSelectedId((currentSelected) => {
      if (currentSelected === incomingDetail.id || !currentSelected) {
        setDetail(incomingDetail);
        return incomingDetail.id;
      }
      return currentSelected;
    });
  }, []);

  useDeploymentSocket(handleSocketUpdate);

  const isAnyHealing = deployments.some((d) => d.status === "HEALING");

  return (
    <main className="dashboard-root">
      {/* Top Navigation Bar */}
      <header className="navbar">
        <div className="nav-left">
          <div className="logo-icon">🛡️</div>
          <div>
            <h1 className="app-title">Autonomous Self-Healing Agent</h1>
            <p className="app-subtitle">Phase 1 Foundation — Infrastructure Resilience & Live AI Telemetry</p>
          </div>
        </div>
        <div className="nav-right">
          <TriggerButton
            isHealing={isAnyHealing}
            onTriggered={(newDep) => {
              setErrorBanner(null);
              setDeployments((prev) => [newDep, ...prev.filter((d) => d.id !== newDep.id)]);
              setSelectedId(newDep.id);
            }}
            onError={(msg) => setErrorBanner(msg)}
          />
        </div>
      </header>

      {/* Error Alert Banner */}
      {errorBanner && (
        <div className="alert-banner">
          <span>⚠ {errorBanner}</span>
          <button onClick={() => setErrorBanner(null)} className="alert-close">✕</button>
        </div>
      )}

      {/* Main Split Content Area */}
      <div className="dashboard-grid">
        <aside className="sidebar">
          <DeploymentList
            deployments={deployments}
            selectedId={selectedId}
            onSelect={(id) => setSelectedId(id)}
          />
        </aside>
        <section className="main-content">
          <DeploymentDetail detail={detail} loading={loadingDetail} />
        </section>
      </div>
    </main>
  );
}
