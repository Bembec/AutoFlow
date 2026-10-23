"use client";

import "@xyflow/react/dist/style.css";

import { Background, Controls, Handle, Position, ReactFlow, type Edge, type Node, type NodeProps } from "@xyflow/react";
import { useMemo } from "react";

import type { Condition, ConditionGroup, Definition, Step } from "@/lib/types";

type StepNodeData = {
  kind: "trigger" | "step";
  title: string;
  subtitle: string;
  badges: string[];
  status?: string;
  selected?: boolean;
};

type StepNode = Node<StepNodeData, "step">;

const STATUS_RING: Record<string, string> = {
  succeeded: "border-emerald-400 bg-emerald-50",
  skipped: "border-slate-300 bg-slate-50 opacity-70",
  failed: "border-red-400 bg-red-50",
  rejected: "border-red-400 bg-red-50",
  waiting_approval: "border-amber-400 bg-amber-50",
  waiting: "border-amber-400 bg-amber-50",
  running: "border-blue-400 bg-blue-50",
};

function StepCard({ data }: NodeProps<StepNode>) {
  const tone = data.status
    ? STATUS_RING[data.status] ?? "border-slate-200 bg-white"
    : data.kind === "trigger"
      ? "border-brand-300 bg-brand-50"
      : "border-slate-200 bg-white";

  return (
    <div
      className={`w-64 rounded-xl border-2 px-3 py-2 shadow-sm ${tone} ${data.selected ? "ring-2 ring-brand-500" : ""}`}
    >
      {data.kind !== "trigger" && <Handle type="target" position={Position.Top} className="!bg-slate-400" />}
      <p className="text-[11px] font-medium uppercase tracking-wide text-slate-500">{data.subtitle}</p>
      <p className="truncate text-sm font-semibold text-slate-900">{data.title}</p>
      {(data.badges.length > 0 || data.status) && (
        <div className="mt-1.5 flex flex-wrap gap-1">
          {data.status && (
            <span className="rounded bg-white/80 px-1.5 text-[10px] font-medium text-slate-700 ring-1 ring-slate-200">
              {data.status.replaceAll("_", " ")}
            </span>
          )}
          {data.badges.map((badge) => (
            <span key={badge} className="rounded bg-slate-900/5 px-1.5 text-[10px] text-slate-600">
              {badge}
            </span>
          ))}
        </div>
      )}
      <Handle type="source" position={Position.Bottom} className="!bg-slate-400" />
    </div>
  );
}

const nodeTypes = { step: StepCard };

const OP_WORDS: Record<string, string> = {
  eq: "is", neq: "is not", contains: "contains", not_contains: "doesn't contain",
  exists: "has a value", not_exists: "is empty", gt: ">", gte: "≥", lt: "<", lte: "≤",
};

function describeOne(condition: Condition | ConditionGroup): string {
  if ("all" in condition && condition.all) return condition.all.map(describeOne).join(" and ");
  if ("any" in condition && condition.any) return `(${condition.any.map(describeOne).join(" or ")})`;
  const plain = condition as Condition;
  const left = String(plain.left).replace(/\{\{\s*(?:steps\.(\w+)\.output|trigger)\.([\w.]+)\s*\}\}/, (_, step, path) => (step ? `${step}.${path}` : path));
  return `${left} ${OP_WORDS[plain.op] ?? plain.op} ${plain.right ?? ""}`.trim();
}

function describeCondition(step: Step) {
  const parts = [];
  if (step.for_each) parts.push(`for each in ${step.for_each.replace(/[{}\s]/g, "").replace(/^trigger\./, "")}`);
  if (step.when) parts.push(`if ${describeOne(step.when)}`);
  return parts.length ? parts.join(" · ") : null;
}

export function WorkflowCanvas({
  definition,
  stepStatus,
  selectedStep,
  onSelectStep,
  height = 520,
}: {
  definition: Definition;
  stepStatus?: Record<string, string>;
  selectedStep?: string | null;
  onSelectStep?: (stepId: string | null) => void;
  height?: number;
}) {
  const { nodes, edges } = useMemo(() => {
    const triggerLabels: Record<Definition["trigger"]["type"], string> = {
      manual: "When you start it",
      webhook: "When another app sends data",
      schedule: `On a schedule (${definition.trigger.schedule})`,
      email: `When an email arrives (${definition.trigger.connection ?? "mailbox"})`,
      document: "When you upload a document",
    };
    const triggerLabel = triggerLabels[definition.trigger.type];

    const nodes: StepNode[] = [
      {
        id: "__trigger",
        type: "step",
        position: { x: 0, y: 0 },
        data: { kind: "trigger", title: triggerLabel, subtitle: "Trigger", badges: [] },
        draggable: false,
      },
      ...definition.steps.map<StepNode>((step, index) => {
        const badges: string[] = [];
        const condition = describeCondition(step);
        if (condition) badges.push(condition);
        if (step.action === "send_email" || step.action === "smtp_send_email" || step.requires_approval) {
          badges.push("needs approval");
        }
        if (step.retry && step.retry.max_attempts > 1) badges.push(`retry ×${step.retry.max_attempts}`);
        if (step.action === "delay") {
          const { minutes, hours, days } = step.inputs as { minutes?: number; hours?: number; days?: number };
          badges.push(`wait ${[days && `${days}d`, hours && `${hours}h`, minutes && `${minutes}m`].filter(Boolean).join(" ")}`);
        }
        if (step.action.startsWith("ai_") || step.action === "classify_enquiry") badges.push("AI");

        return {
          id: step.id,
          type: "step",
          position: { x: 0, y: (index + 1) * 120 },
          data: {
            kind: "step",
            title: step.name ?? step.id,
            subtitle: step.action.replaceAll("_", " "),
            badges,
            status: stepStatus?.[step.id],
            selected: selectedStep === step.id,
          },
          draggable: false,
        };
      }),
    ];

    const order = ["__trigger", ...definition.steps.map((step) => step.id)];
    const edges: Edge[] = order.slice(1).map((id, index) => ({
      id: `${order[index]}->${id}`,
      source: order[index],
      target: id,
      animated: stepStatus?.[id] === "running",
    }));

    return { nodes, edges };
  }, [definition, stepStatus, selectedStep]);

  return (
    <div style={{ height }} className="rounded-xl border border-slate-200 bg-slate-50">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.2, maxZoom: 1 }}
        nodesConnectable={false}
        onNodeClick={(_, node) => onSelectStep?.(node.id === "__trigger" ? null : node.id)}
        onPaneClick={() => onSelectStep?.(null)}
      >
        <Background gap={20} color="#e2e8f0" />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}
