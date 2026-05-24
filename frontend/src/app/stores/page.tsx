"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { EmptyState } from "@/components/empty-state";
import { PaginationControls } from "@/components/pagination-controls";
import { StoreCard } from "@/components/store-card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";

export default function StoresPage() {
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const pageSize = 12;

  const stores = useQuery({
    queryKey: ["stores", q, page],
    queryFn: () => api.listStores({ q: q || undefined, page, page_size: pageSize }),
  });

  return (
    <div className="container mx-auto max-w-7xl space-y-4 px-4 py-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Burlington Stores</h1>
        <p className="text-sm text-muted-foreground">
          {stores.data?.total ?? "…"} AGCO-authorized cannabis retailers
        </p>
      </div>

      <Input
        placeholder="Search by name or address…"
        value={q}
        onChange={(e) => {
          setQ(e.target.value);
          setPage(1);
        }}
        className="max-w-sm"
      />

      {stores.isLoading && (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-56" />
          ))}
        </div>
      )}

      {stores.data && stores.data.items.length === 0 && (
        <EmptyState
          title="No stores match"
          description="Try clearing the search filter."
        />
      )}

      {stores.data && stores.data.items.length > 0 && (
        <>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {stores.data.items.map((s) => (
              <StoreCard key={s.store_id} store={s} />
            ))}
          </div>
          <PaginationControls
            page={page}
            pageSize={pageSize}
            total={stores.data.total}
            hasNext={stores.data.has_next}
            onPageChange={setPage}
          />
        </>
      )}
    </div>
  );
}
