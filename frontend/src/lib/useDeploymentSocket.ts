"use client";

import { useEffect } from "react";
import { DeploymentDetail } from "@/types/deployment";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws/deployments";

export function useDeploymentSocket(onUpdate: (data: DeploymentDetail) => void) {
  useEffect(() => {
    let socket: WebSocket | null = new WebSocket(WS_URL);

    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (payload.type === "deployment_update" && payload.data) {
          onUpdate(payload.data as DeploymentDetail);
        }
      } catch (err) {
        console.error("Failed to parse WebSocket message:", err);
      }
    };

    socket.onerror = (err) => {
      console.error("WebSocket error:", err);
    };

    return () => {
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.close();
      }
      socket = null;
    };
  }, [onUpdate]);
}
