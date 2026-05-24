"use client";

import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2, Clock } from "lucide-react";

import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

const JOB_LABELS: Record<string, string> = {
  ocs_new_arrivals: "OCS catalog",
  hibuddy_store_details: "Store details",
  agco_retailers: "AGCO licences",
  compute_promo_duration: "Promo durations",
};

function formatRelative(minutes: number | null): string {
  if (minutes === null) return "—";
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${Math.round(minutes)} min ago`;
  if (minutes < 60 * 24) return `${Math.round(minutes / 60)}h ago`;
  return `${Math.round(minutes / 60 / 24)}d ago`;
}

function statusFor(minutes: number | null): "fresh" | "stale" | "very-stale" {
  if (minutes === null) return "very-stale";
  if (minutes < 60 * 36) return "fresh"; // < 36 hours
  if (minutes < 60 * 24 * 8) return "stale"; // < 8 days
  return "very-stale";
}

export function DataFreshness() {
  const { data, isLoading } = useQuery({
    queryKey: ["pipeline-freshness"],
    queryFn: api.pipelineFreshness,
    refetchInterval: 60_000,
  });

  if (isLoading || !data || data.length === 0) {
    return null;
  }

  return (
    <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
      <span className="font-medium">Data freshness:</span>
      {data.map((job) => {
        const status = statusFor(job.minutes_since_success);
        const label = JOB_LABELS[job.job_name] ?? job.job_name;
        const Icon =
          status === "fresh"
            ? CheckCircle2
            : status === "stale"
              ? Clock
              : AlertTriangle;
        return (
          <span
            key={job.job_name}
            title={
              job.last_success_at
                ? `Last success: ${new Date(job.last_success_at).toLocaleString()}`
                : "No successful run yet"
            }
            className={cn(
              "inline-flex items-center gap-1",
              status === "fresh" && "text-emerald-600 dark:text-emerald-500",
              status === "stale" && "text-amber-600 dark:text-amber-500",
              status === "very-stale" && "text-destructive",
            )}
          >
            <Icon className="size-3" />
            <span>{label}</span>
            <span className="opacity-70">· {formatRelative(job.minutes_since_success)}</span>
          </span>
        );
      })}
    </div>
  );
}
