import { Clock } from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import type { Deal } from "@/lib/api";
import { cn, formatCurrency } from "@/lib/utils";

interface DealCardProps {
  deal: Deal;
  className?: string;
}

function formatDuration(days: number | null | undefined): string | null {
  if (days === null || days === undefined) return null;
  if (days === 0) return "started today";
  if (days === 1) return "1 day running";
  if (days < 7) return `${days} days running`;
  if (days < 14) return `~1 week running`;
  if (days < 30) return `${Math.floor(days / 7)} weeks running`;
  if (days < 60) return `~1 month running`;
  return `${Math.floor(days / 30)} months running`;
}

export function DealCard({ deal, className }: DealCardProps) {
  const duration = formatDuration(deal.promo_duration_days);

  return (
    <Card
      className={cn("group overflow-hidden p-0 transition-shadow hover:shadow-md", className)}
    >
      <Link href={`/products/${deal.product_id}`} className="block">
        <div className="relative aspect-square bg-muted">
          {deal.image_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={deal.image_url}
              alt={deal.product_name ?? ""}
              className="size-full object-cover transition-transform group-hover:scale-105"
              loading="lazy"
            />
          ) : (
            <div className="flex size-full items-center justify-center text-xs text-muted-foreground">
              no image
            </div>
          )}
          {deal.discount_percent && (
            <Badge className="absolute left-2 top-2 bg-destructive text-destructive-foreground">
              -{Math.round(Number(deal.discount_percent))}%
            </Badge>
          )}
        </div>
        <div className="space-y-1 p-3">
          <div className="text-xs text-muted-foreground">{deal.brand ?? "—"}</div>
          <div className="line-clamp-2 text-sm font-medium leading-tight">
            {deal.product_name}
          </div>
          <div className="flex items-baseline gap-2 pt-1">
            <span className="text-base font-semibold text-destructive">
              {formatCurrency(deal.sale_price)}
            </span>
            <span className="text-xs text-muted-foreground line-through">
              {formatCurrency(deal.regular_price)}
            </span>
          </div>
          <div className="text-xs text-muted-foreground">at {deal.store_name}</div>
          {duration && (
            <div className="flex items-center gap-1 pt-1 text-[11px] text-muted-foreground">
              <Clock className="size-3" />
              {duration}
            </div>
          )}
        </div>
      </Link>
    </Card>
  );
}
