"use client";

// Feature flags for the current workspace (decided by the server, see
// backend autoflow/features.py). The server also enforces them; the app
// only hides what is switched off.

import { useSession } from "@/lib/session";
import { useApi } from "@/lib/useApi";

export type FeatureName = "ai_builder" | "insights_suggestions" | "connection_checks" | "smarter_logic" | "mcp_tools" | "help_assistant" | "ai_assistants";

export function useFeatures() {
  const { base } = useSession();
  const { data } = useApi<Record<FeatureName, boolean>>(`${base}/features`);

  /** While flags load, `whileLoading` decides (true for features that are on by default). */
  return (name: FeatureName, whileLoading = true) => (data ? Boolean(data[name]) : whileLoading);
}
