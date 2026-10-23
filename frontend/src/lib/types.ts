// Shapes returned by the AutoFlow API (see backend/src/autoflow/api).

export type Role = "viewer" | "member" | "admin" | "owner";

export interface WorkspaceWithRole {
  id: number;
  name: string;
  slug: string;
  role: Role;
}

export interface Me {
  id: number;
  email: string;
  name: string;
  workspaces: WorkspaceWithRole[];
}

export interface Condition {
  left: unknown;
  op: "eq" | "neq" | "contains" | "exists" | "not_exists";
  right?: unknown;
}

export interface Step {
  id: string;
  name?: string;
  action: string;
  inputs: Record<string, unknown>;
  when?: Condition;
  retry?: { max_attempts: number; backoff_seconds: number };
  timeout_seconds?: number;
  requires_approval?: boolean;
  review_below_confidence?: number;
}

export interface Definition {
  trigger: {
    type: "manual" | "webhook" | "schedule" | "email" | "document";
    schedule?: string;
    /** Email triggers: imap connection name and folder */
    connection?: string;
    folder?: string;
    sample_payload?: Record<string, unknown>;
  };
  steps: Step[];
}

export interface WorkflowVersion {
  number: number;
  state: "draft" | "published" | "archived";
  definition: Definition;
  created_at: string;
  published_at: string | null;
}

export interface Workflow {
  id: number;
  name: string;
  description: string;
  status: "active" | "paused" | "archived";
  minutes_saved_per_run: number;
  created_at: string;
  updated_at: string;
  versions: WorkflowVersion[];
}

export type ExecutionStatus =
  | "queued"
  | "running"
  | "waiting_approval"
  | "succeeded"
  | "failed"
  | "cancelled"
  | "needs_attention";

export interface StepExecution {
  step_id: string;
  position: number;
  action: string;
  status: string;
  attempts: number;
  input: Record<string, unknown> | null;
  output: Record<string, unknown> | null;
  error: string | null;
  started_at: string | null;
  finished_at: string | null;
}

export interface Execution {
  id: number;
  workflow_id: number;
  version_id: number;
  mode: "test" | "live";
  status: ExecutionStatus;
  trigger_payload: Record<string, unknown>;
  idempotency_key: string | null;
  error: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  /** Delayed or queued: not picked up before this time */
  run_after?: string | null;
  steps: StepExecution[];
}

export interface ApprovalPayload {
  // classification approvals
  message?: string;
  suggested_category?: string;
  reason?: string;
  // email approvals
  to?: string;
  subject?: string;
  body?: string;
  // engine step approvals and AI result reviews
  step_name?: string;
  action?: string;
  inputs?: Record<string, unknown>;
  review?: boolean;
  output?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface Approval {
  id: number;
  kind: "classification" | "email" | "step";
  status: string;
  customer_email: string;
  payload: ApprovalPayload;
  decision: Record<string, unknown> | null;
  decided_by_user_id: number | null;
  execution_id: number | null;
  step_id: string | null;
  created_at: string;
  decided_at: string | null;
}

export interface ActionInfo {
  name: string;
  description: string;
  inputs: Record<string, { type: string; required: boolean; description: string }>;
  outputs: Record<string, string>;
  side_effect: boolean;
  requires_approval: boolean;
  connection_provider: string | null;
}

export interface TemplateInfo {
  slug: string;
  name: string;
  description: string;
  category: string;
  /** What must be set up for the template to work live */
  requires: string[];
}

export interface InvoiceSummary {
  number: string;
  order: string;
  customer_name: string;
  customer_email: string;
  total: string;
  currency: string;
  issued_at: string;
  url: string;
}

export interface NotificationSettings {
  notify_email: string | null;
  notify_smtp_connection: string | null;
  notify_slack_connection: string | null;
  notify_on_approval: boolean;
  notify_on_failure: boolean;
}

export interface BusinessProfile {
  business_name: string | null;
  business_address: string | null;
  tax_id: string | null;
  invoice_prefix: string;
}

export interface Dashboard {
  automation_paused: boolean;
  paused_reason: string | null;
  workflows: { total: number; active: number; paused: number };
  executions_today: Partial<Record<ExecutionStatus, number>>;
  pending_approvals: number;
  minutes_saved_30d: number;
  per_workflow: {
    id: number;
    name: string;
    status: string;
    runs_succeeded_30d: number;
    minutes_saved_30d: number;
  }[];
  recent_executions: {
    id: number;
    workflow_id: number;
    workflow_name: string;
    mode: string;
    status: ExecutionStatus;
    created_at: string;
  }[];
  usage_today: { executions: number; ai_calls: number; emails: number };
  limits: { executions: number; ai_calls: number; emails: number };
}

export interface IntegrationInfo {
  name: string;
  label: string;
  auth: "api_key" | "password" | "oauth2";
  secret_fields: string[];
  config_fields: string[];
  required_config: string[];
  available: boolean;
}

export interface Connection {
  id: number;
  provider: string;
  name: string;
  config: Record<string, unknown>;
  secrets: Record<string, string>;
  status: "active" | "error" | "revoked";
  last_error: string | null;
  created_at: string;
  last_used_at: string | null;
}

export interface Member {
  user_id: number;
  email: string;
  name: string;
  role: Role;
}

export interface Policies {
  automation_paused: boolean;
  paused_reason: string | null;
  approve_all_side_effects: boolean;
  max_executions_per_day: number;
  max_ai_calls_per_day: number;
  max_emails_per_day: number;
  usage_today: { executions: number; ai_calls: number; emails: number };
}

export interface AIDraft {
  status: "ready" | "needs_details";
  name: string;
  description: string;
  definition: Definition | null;
  questions: string[];
  assumptions: string[];
  unsupported: string[];
  provider: string;
  attempts: number;
  workflow: Workflow | null;
}

export type OnboardingStep = "business" | "email" | "template" | "test" | "publish" | "live";

export interface Onboarding {
  steps: { id: OnboardingStep; done: boolean }[];
  completed: number;
  total: number;
  complete: boolean;
}
