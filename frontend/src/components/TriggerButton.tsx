"use client";

import React, { useState } from "react";
import { triggerDeployment } from "@/lib/api";
import { DeploymentSummary } from "@/types/deployment";

interface TriggerButtonProps {
  isHealing: boolean;
  onTriggered: (deployment: DeploymentSummary) => void;
  onError: (errorMsg: string) => void;
}

export function TriggerButton({ isHealing, onTriggered, onError }: TriggerButtonProps) {
  const [loading, setLoading] = useState(false);

  const handleClick = async () => {
    if (isHealing || loading) return;
    setLoading(true);
    try {
      const newDep = await triggerDeployment();
      onTriggered(newDep);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to trigger demo pipeline.";
      onError(msg);
    } finally {
      setLoading(false);
    }
  };

  const disabled = isHealing || loading;

  return (
    <button
      onClick={handleClick}
      disabled={disabled}
      className={`trigger-btn ${disabled ? "disabled" : ""}`}
    >
      {loading ? (
        <span className="btn-content">
          <span className="spinner-sm" /> Initializing Demo...
        </span>
      ) : isHealing ? (
        <span className="btn-content">
          <span className="spinner-sm" /> Self-Healing Active...
        </span>
      ) : (
        <span className="btn-content">
          <span className="play-icon">▶</span> Run Demo Pipeline
        </span>
      )}
    </button>
  );
}
