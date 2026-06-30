export type DeploymentStatus = "FAILED" | "HEALING" | "HEALED" | "FAILED_TO_HEAL";

export interface DeploymentSummary {
  id: string;
  fault_category: string;
  status: DeploymentStatus;
  created_at: string;
  resolved_at: string | null;
}

export interface HealingAttempt {
  id: string;
  attempt_number: number;
  llm_explanation: string;
  fixed_code: string;
  validation_success: boolean;
  validation_output: string | null;
  created_at: string;
}

export interface DeploymentDetail extends DeploymentSummary {
  broken_code: string;
  error_log: string;
  attempts: HealingAttempt[];
}
