"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { EmptyState } from "@/components/empty-state";
import { PaginationControls } from "@/components/pagination-controls";
import { ProductCard } from "@/components/product-card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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

const SORTS = [
  { value: "name", label: "Name A→Z" },
  { value: "-name", label: "Name Z→A" },
  { value: "price", label: "Price ↑" },
  { value: "-price", label: "Price ↓" },
  { value: "stores", label: "Most widely stocked" },
];

export default function ProductsPage() {
  const [q, setQ] = useState("");
  const [category, setCategory] = useState<string | undefined>();
  const [brand, setBrand] = useState<string | undefined>();
  const [onSale, setOnSale] = useState(false);
  const [availableLocally, setAvailableLocally] = useState(true);
  const [sort, setSort] = useState("name");
  const [minPrice, setMinPrice] = useState("");
  const [maxPrice, setMaxPrice] = useState("");
  const [page, setPage] = useState(1);
  const pageSize = 24;

  const categories = useQuery({ queryKey: ["categories"], queryFn: api.categories });
  const brands = useQuery({ queryKey: ["brands"], queryFn: api.brands });

  const products = useQuery({
    queryKey: [
      "products",
      q,
      category,
      brand,
      onSale,
      availableLocally,
      sort,
      minPrice,
      maxPrice,
      page,
    ],
    queryFn: () =>
      api.listProducts({
        q: q || undefined,
        category,
        brand,
        on_sale: onSale || undefined,
        available_locally: availableLocally,
        lang: "en",
        min_price: minPrice ? Number(minPrice) : undefined,
        max_price: maxPrice ? Number(maxPrice) : undefined,
        sort,
        page,
        page_size: pageSize,
      }),
  });

  function resetFilters() {
    setQ("");
    setCategory(undefined);
    setBrand(undefined);
    setOnSale(false);
    setAvailableLocally(true);
    setMinPrice("");
    setMaxPrice("");
    setPage(1);
  }

  return (
    <div className="container mx-auto max-w-7xl px-4 py-8">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Products</h1>
          <p className="text-sm text-muted-foreground">
            {products.data?.total.toLocaleString() ?? "…"} matching items
          </p>
        </div>
        <Select value={sort} onValueChange={setSort}>
          <SelectTrigger className="w-48">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {SORTS.map((s) => (
              <SelectItem key={s.value} value={s.value}>
                {s.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="grid gap-6 lg:grid-cols-[260px_1fr]">
        <aside className="space-y-4">
          <div>
            <Label htmlFor="q">Search</Label>
            <Input
              id="q"
              className="mt-1"
              placeholder="Name or brand…"
              value={q}
              onChange={(e) => {
                setQ(e.target.value);
                setPage(1);
              }}
            />
          </div>
          <div>
            <Label>Category</Label>
            <Select
              value={category ?? "all"}
              onValueChange={(v) => {
                setCategory(v === "all" ? undefined : v);
                setPage(1);
              }}
            >
              <SelectTrigger className="mt-1">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All categories</SelectItem>
                {categories.data?.map((c) => (
                  <SelectItem key={c.name} value={c.name}>
                    {c.name} ({c.count.toLocaleString()})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label>Brand</Label>
            <Select
              value={brand ?? "all"}
              onValueChange={(v) => {
                setBrand(v === "all" ? undefined : v);
                setPage(1);
              }}
            >
              <SelectTrigger className="mt-1">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="max-h-72">
                <SelectItem value="all">All brands</SelectItem>
                {brands.data?.slice(0, 100).map((b) => (
                  <SelectItem key={b.name} value={b.name}>
                    {b.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>Price range</Label>
            <div className="flex gap-2">
              <Input
                placeholder="min"
                inputMode="decimal"
                value={minPrice}
                onChange={(e) => {
                  setMinPrice(e.target.value);
                  setPage(1);
                }}
              />
              <Input
                placeholder="max"
                inputMode="decimal"
                value={maxPrice}
                onChange={(e) => {
                  setMaxPrice(e.target.value);
                  setPage(1);
                }}
              />
            </div>
          </div>
          <div className="flex items-center gap-2">
            <input
              id="locally"
              type="checkbox"
              checked={availableLocally}
              onChange={(e) => {
                setAvailableLocally(e.target.checked);
                setPage(1);
              }}
              className="size-4"
            />
            <Label htmlFor="locally" className="cursor-pointer">
              Available locally only
            </Label>
          </div>
          <div className="flex items-center gap-2">
            <input
              id="onsale"
              type="checkbox"
              checked={onSale}
              onChange={(e) => {
                setOnSale(e.target.checked);
                setPage(1);
              }}
              className="size-4"
            />
            <Label htmlFor="onsale" className="cursor-pointer">
              On sale only
            </Label>
          </div>
          <Button variant="outline" size="sm" onClick={resetFilters} className="w-full">
            Clear filters
          </Button>
        </aside>

        <section>
          {products.isLoading && (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
              {Array.from({ length: 12 }).map((_, i) => (
                <Skeleton key={i} className="aspect-[2/3]" />
              ))}
            </div>
          )}
          {products.data && products.data.items.length === 0 && (
            <EmptyState
              title="No products match"
              description="Try clearing some filters."
              action={
                <Button variant="outline" onClick={resetFilters}>
                  Clear filters
                </Button>
              }
            />
          )}
          {products.data && products.data.items.length > 0 && (
            <>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
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
    </div>
  );
}
