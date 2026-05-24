"use client";

import { useQuery } from "@tanstack/react-query";
import { ExternalLink, Globe, MapPin, Phone, ShieldCheck } from "lucide-react";
import { use, useState } from "react";

import { EmptyState } from "@/components/empty-state";
import { PaginationControls } from "@/components/pagination-controls";
import { ProductCard } from "@/components/product-card";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { formatHoursList, isOpenNow, todayKey } from "@/lib/hours";

interface PageProps {
  params: Promise<{ id: string }>;
}

export default function StoreDetailPage({ params }: PageProps) {
  const { id } = use(params);
  const storeId = Number(id);
  const [q, setQ] = useState("");
  const [category, setCategory] = useState<string | undefined>(undefined);
  const [page, setPage] = useState(1);
  const pageSize = 24;

  const store = useQuery({
    queryKey: ["store", storeId],
    queryFn: () => api.getStore(storeId),
  });
  const products = useQuery({
    queryKey: ["store-products", storeId, q, category, page],
    queryFn: () =>
      api.storeProducts(storeId, {
        q: q || undefined,
        category,
        page,
        page_size: pageSize,
      }),
  });
  const categories = useQuery({ queryKey: ["categories"], queryFn: api.categories });

  if (store.isLoading) {
    return <Skeleton className="m-4 h-96" />;
  }
  if (!store.data) {
    return (
      <EmptyState
        title="Store not found"
        description="It may have been removed from the AGCO list."
      />
    );
  }

  const s = store.data;
  const open = isOpenNow(s.hours_json);
  const hoursList = formatHoursList(s.hours_json);

  return (
    <div className="container mx-auto max-w-7xl space-y-6 px-4 py-8">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{s.store_name}</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {s.product_count ?? 0} products carried · {s.deals_count ?? 0} active deals
          </p>
        </div>
        {open === true && <Badge className="bg-primary text-primary-foreground">Open now</Badge>}
        {open === false && <Badge variant="secondary">Closed now</Badge>}
      </header>

      <div className="grid gap-4 md:grid-cols-3">
        <Card className="md:col-span-2">
          <CardHeader>
            <CardTitle className="text-base">Store info</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            {s.address && (
              <p className="flex items-start gap-2">
                <MapPin className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
                {s.address}
              </p>
            )}
            {s.phone && (
              <p className="flex items-center gap-2">
                <Phone className="size-4 text-muted-foreground" />
                <a href={`tel:${s.phone}`}>{s.phone}</a>
              </p>
            )}
            {s.website && (
              <p className="flex items-center gap-2">
                <Globe className="size-4 text-muted-foreground" />
                <a
                  href={s.website}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 hover:underline"
                >
                  {s.website.replace(/^https?:\/\//, "")}
                  <ExternalLink className="size-3" />
                </a>
              </p>
            )}
            {s.agco_licence_number && (
              <p className="flex items-center gap-2 text-muted-foreground">
                <ShieldCheck className="size-4" />
                AGCO licence&nbsp;{s.agco_licence_number}
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Hours</CardTitle>
          </CardHeader>
          <CardContent className="text-sm">
            {hoursList.length > 0 ? (
              <ul className="space-y-1">
                {hoursList.map((h, idx) => {
                  const dayKeyLower = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"][idx];
                  const isToday = dayKeyLower === todayKey();
                  return (
                    <li
                      key={h.day}
                      className={`flex justify-between ${isToday ? "font-semibold" : ""}`}
                    >
                      <span>{h.day}</span>
                      <span>{h.time}</span>
                    </li>
                  );
                })}
              </ul>
            ) : (
              <p className="text-muted-foreground">Hours not yet sourced</p>
            )}
          </CardContent>
        </Card>
      </div>

      <section>
        <h2 className="pb-3 text-lg font-semibold">Products carried</h2>
        <div className="mb-3 flex flex-wrap gap-2">
          <Input
            placeholder="Search products…"
            value={q}
            onChange={(e) => {
              setQ(e.target.value);
              setPage(1);
            }}
            className="max-w-xs"
          />
          <Select
            value={category ?? "all"}
            onValueChange={(v) => {
              setCategory(v === "all" ? undefined : v);
              setPage(1);
            }}
          >
            <SelectTrigger className="w-44">
              <SelectValue placeholder="All categories" />
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

        {products.isLoading && (
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4 lg:grid-cols-6">
            {Array.from({ length: 8 }).map((_, i) => (
              <Skeleton key={i} className="aspect-[2/3]" />
            ))}
          </div>
        )}
        {products.data && products.data.items.length === 0 && (
          <EmptyState
            title="No products"
            description="This store hasn't had recent menu data refreshed."
          />
        )}
        {products.data && products.data.items.length > 0 && (
          <>
            <div className="grid grid-cols-2 gap-3 md:grid-cols-4 lg:grid-cols-6">
              {products.data.items.map((p) => (
                <ProductCard key={p.product_id} product={p} />
              ))}
            </div>
            <PaginationControls
              page={page}
              pageSize={pageSize}
              total={products.data.total}
              hasNext={products.data.has_next}
              onPageChange={setPage}
            />
          </>
        )}
      </section>
    </div>
  );
}
