"use client";

import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";

import { EmptyState } from "@/components/empty-state";
import { ProductCard } from "@/components/product-card";
import { StoreCard } from "@/components/store-card";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { api } from "@/lib/api";

function SearchInner() {
  const sp = useSearchParams();
  const q = sp.get("q") ?? "";

  const search = useQuery({
    queryKey: ["search", q],
    queryFn: () => api.search({ q, limit: 24 }),
    enabled: q.length > 0,
  });

  if (!q) {
    return (
      <EmptyState
        title="What are you looking for?"
        description="Use the search bar to look across products and stores."
      />
    );
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">
          Search · <span className="italic">{q}</span>
        </h1>
        <p className="text-sm text-muted-foreground">
          {search.data
            ? `${search.data.total_products} products, ${search.data.total_stores} stores`
            : "…"}
        </p>
      </div>

      <Tabs defaultValue="products">
        <TabsList>
          <TabsTrigger value="products">
            Products
            {search.data && (
              <span className="ml-2 text-xs text-muted-foreground">
                {search.data.total_products}
              </span>
            )}
          </TabsTrigger>
          <TabsTrigger value="stores">
            Stores
            {search.data && (
              <span className="ml-2 text-xs text-muted-foreground">
                {search.data.total_stores}
              </span>
            )}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="products">
          {search.isLoading && (
            <div className="grid grid-cols-2 gap-3 md:grid-cols-4 lg:grid-cols-6">
              {Array.from({ length: 6 }).map((_, i) => (
                <Skeleton key={i} className="aspect-[2/3]" />
              ))}
            </div>
          )}
          {search.data && search.data.products.length === 0 && (
            <EmptyState title="No products match" />
          )}
          {search.data && search.data.products.length > 0 && (
            <div className="grid grid-cols-2 gap-3 md:grid-cols-4 lg:grid-cols-6">
              {search.data.products.map((p) => (
                <ProductCard key={p.product_id} product={p} />
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="stores">
          {search.data && search.data.stores.length === 0 && (
            <EmptyState title="No stores match" />
          )}
          {search.data && search.data.stores.length > 0 && (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {search.data.stores.map((s) => (
                <StoreCard key={s.store_id} store={s} />
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}

export default function SearchPage() {
  return (
    <div className="container mx-auto max-w-7xl px-4 py-8">
      <Suspense fallback={<Skeleton className="h-96" />}>
        <SearchInner />
      </Suspense>
    </div>
  );
}
