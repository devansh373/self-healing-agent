import React from "react";
import { DeploymentDetail as DeploymentDetailType } from "@/types/deployment";
import { StatusBadge } from "./StatusBadge";

interface DeploymentDetailProps {
  detail: DeploymentDetailType | null;
  loading: boolean;
}

export function DeploymentDetail({ detail, loading }: DeploymentDetailProps) {
  if (loading) {
    return (
      <div className="detail-panel empty-panel">
        <div className="spinner" />
        <p>Loading deployment diagnostics...</p>
      </div>
    );
  }

  if (!detail) {
    return (
      <div className="detail-panel empty-panel">
        <div className="empty-icon">⚡</div>
        <h3>Select a Deployment</h3>
        <p>Click any deployment from the history list on the left to inspect its real-time diagnostic telemetry, AI root-cause analysis, and auto-generated HCL patch.</p>
      </div>
    );
  }

  const latestAttempt = detail.attempts && detail.attempts.length > 0
    ? detail.attempts[detail.attempts.length - 1]
    : null;

  return (
    <div className="detail-panel">
      {/* Header Banner */}
      <div className={`detail-header banner-${detail.status.toLowerCase()}`}>
        <div className="header-meta">
          <span className="detail-id">Deployment #{detail.id}</span>
          <span className="detail-fault">Category: <strong>{detail.fault_category}</strong></span>
        </div>
        <div className="header-status">
          <StatusBadge status={detail.status} />
        </div>
      </div>

      {/* State banner */}
      {detail.status === "HEALING" && (
        <div className="live-status-banner healing">
          <div className="spinner-sm" />
          <span><strong>AI Agent Active:</strong> Analyzing Terraform validation error, synthesizing AST repair, and verifying sandbox sandbox patch...</span>
        </div>
      )}

      {detail.status === "HEALED" && (
        <div className="live-status-banner healed">
          <span>✨ <strong>Self-Healing Complete:</strong> The infrastructure pipeline automatically diagnosed and repaired the fault without human intervention.</span>
        </div>
      )}

      {detail.status === "FAILED_TO_HEAL" && (
        <div className="live-status-banner failed">
          <span>⚠ <strong>Remediation Unsuccessful:</strong> The AI agent could not synthesize a valid patch within attempt limits or encountered an API error.</span>
        </div>
      )}

      <div className="panels-grid">
        {/* Panel 1: Broken Code */}
        <div className="code-card">
          <div className="card-top">
            <span className="panel-title">1. Initial Broken Code (main.tf)</span>
            <span className="tag tag-error">Faulty HCL</span>
          </div>
          <pre className="code-block">{detail.broken_code}</pre>
        </div>

        {/* Panel 2: Error Log */}
        <div className="code-card">
          <div className="card-top">
            <span className="panel-title">2. Pipeline Error Log (terraform validate)</span>
            <span className="tag tag-warning">Stderr Output</span>
          </div>
          <pre className="code-block log-output">{detail.error_log}</pre>
        </div>

        {/* Panel 3: LLM Explanation & Fixed Code */}
        <div className="code-card">
          <div className="card-top">
            <span className="panel-title">3. AI Agent Synthesis & Patch</span>
            {latestAttempt ? (
              <span className="tag tag-ai">Gemini 2.5 Flash</span>
            ) : (
              <span className="tag tag-waiting">Awaiting AI...</span>
            )}
          </div>
          {latestAttempt ? (
            <div className="ai-synthesis">
              <div className="explanation-box">
                <strong>Root Cause Analysis:</strong>
                <p>{latestAttempt.llm_explanation}</p>
              </div>
              {latestAttempt.fixed_code && (
                <div className="fixed-code-section">
                  <span className="sub-label">Synthesized HCL Patch:</span>
                  <pre className="code-block patch-code">{latestAttempt.fixed_code}</pre>
                </div>
              )}
            </div>
          ) : (
            <div className="waiting-box">
              {detail.status === "HEALING" ? (
                <p className="pulse-text">Invoking Gemini LLM for structured HCL repair...</p>
              ) : (
                <p>No healing attempt recorded yet.</p>
              )}
            </div>
          )}
        </div>

        {/* Panel 4: Validation Output */}
        <div className="code-card">
          <div className="card-top">
            <span className="panel-title">4. Sandbox Verification Output</span>
            {latestAttempt ? (
              <span className={`tag ${latestAttempt.validation_success ? "tag-success" : "tag-error"}`}>
                {latestAttempt.validation_success ? "Passed Validations" : "Validation Failed"}
              </span>
            ) : (
              <span className="tag tag-waiting">Pending</span>
            )}
          </div>
          {latestAttempt ? (
            <pre className="code-block validation-output">
              {latestAttempt.validation_output || (latestAttempt.validation_success ? "Success! The synthesized Terraform patch passed 'terraform validate' cleanly." : "No output returned.")}
            </pre>
          ) : (
            <div className="waiting-box">
              <p>Sandbox verification will execute once AI patch is generated.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
