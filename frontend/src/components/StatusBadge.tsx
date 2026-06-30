import React from "react";
import { DeploymentStatus } from "@/types/deployment";

interface StatusBadgeProps {
  status: DeploymentStatus;
}

export function StatusBadge({ status }: StatusBadgeProps) {
  const getBadgeStyle = (status: DeploymentStatus) => {
    switch (status) {
      case "HEALING":
        return {
          label: "● HEALING IN PROGRESS",
          className: "badge badge-healing pulse",
        };
      case "HEALED":
        return {
          label: "✓ SUCCESSFULLY HEALED",
          className: "badge badge-healed",
        };
      case "FAILED":
        return {
          label: "⚠ INITIAL FAULT DETECTED",
          className: "badge badge-failed",
        };
      case "FAILED_TO_HEAL":
        return {
          label: "✕ HEALING FAILED",
          className: "badge badge-failed-to-heal",
        };
      default:
        return {
          label: status,
          className: "badge",
        };
    }
  };

  const { label, className } = getBadgeStyle(status);

  return <span className={className}>{label}</span>;
}
