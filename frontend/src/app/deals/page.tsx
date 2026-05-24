"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { DealCard } from "@/components/deal-card";
import { EmptyState } from "@/components/empty-state";
import { PaginationControls } from "@/components/pagination-controls";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";

export default function DealsPage() {
  const [category, setCategory] = useState<string | undefined>();
  const [minDiscount, setMinDiscount] = useState<number | undefined>();
  const [page, setPage] = useState(1);
  const pageSize = 24;

  const categories = useQuery({ queryKey: ["categories"], queryFn: api.categories });

  const deals = useQuery({
    queryKey: ["deals", category, minDiscount, page],
    queryFn: () =>
      api.listDeals({
        category,
        min_discount: minDiscount,
        page,
        page_size: pageSize,
      }),
  });

  return (
    <div className="container mx-auto max-w-7xl space-y-4 px-4 py-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Deals</h1>
        <p className="text-sm text-muted-foreground">
          {deals.data?.total.toLocaleString() ?? "…"} active promotions across Burlington
        </p>
      </div>

      <div className="flex flex-wrap gap-3">
        <div>
          <Label>Category</Label>
          <Select
            value={category ?? "all"}
            onValueChange={(v) => {
              setCategory(v === "all" ? undefined : v);
              setPage(1);
            }}
          >
            <SelectTrigger className="mt-1 w-44">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All categories</SelectItem>
              {categories.data?.map((c) => (
                <SelectItem key={c.name} value={c.name}>
                  {c.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div>
          <Label>Min discount</Label>
          <Select
            value={String(minDiscount ?? "any")}
            onValueChange={(v) => {
              setMinDiscount(v === "any" ? undefined : Number(v));
              setPage(1);
            }}
          >
            <SelectTrigger className="mt-1 w-44">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="any">Any discount</SelectItem>
              <SelectItem value="10">10% or more</SelectItem>
              <SelectItem value="20">20% or more</SelectItem>
              <SelectItem value="30">30% or more</SelectItem>
              <SelectItem value="50">50% or more</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {deals.isLoading && (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4 lg:grid-cols-6">
          {Array.from({ length: 12 }).map((_, i) => (
            <Skeleton key={i} className="aspect-[2/3]" />
          ))}
        </div>
      )}
      {deals.data && deals.data.items.length === 0 && (
        <EmptyState title="No deals match" />
      )}
      {deals.data && deals.data.items.length > 0 && (
        <>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4 lg:grid-cols-6">
            {deals.data.items.map((d) => (
              <DealCard key={d.fact_id} deal={d} />
            ))}
          </div>
          <PaginationControls
            page={page}
            pageSize={pageSize}
            total={deals.data.total}
            hasNext={deals.data.has_next}
            onPageChange={setPage}
          />
        </>
      )}
    </div>
  );
}
