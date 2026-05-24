"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { use, useState } from "react";

import { EmptyState } from "@/components/empty-state";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { api } from "@/lib/api";
import { formatCurrency } from "@/lib/utils";

interface PageProps {
  params: Promise<{ id: string }>;
}

type SortKey = "store" | "regular" | "sale" | "discount";

export default function ProductDetailPage({ params }: PageProps) {
  const { id } = use(params);
  const productId = Number(id);
  const [sortKey, setSortKey] = useState<SortKey>("sale");

  const product = useQuery({
    queryKey: ["product", productId],
    queryFn: () => api.getProduct(productId),
  });

  if (product.isLoading) {
    return <Skeleton className="m-4 h-96" />;
  }
  if (!product.data) {
    return (
      <EmptyState
        title="Product not found"
        description="It may have been removed from the OCS catalog."
      />
    );
  }

  const p = product.data;

  const sorted = [...p.available_at].sort((a, b) => {
    const toNum = (v: string | null) => (v === null ? Infinity : Number(v));
    switch (sortKey) {
      case "regular":
        return toNum(a.regular_price) - toNum(b.regular_price);
      case "sale":
        return toNum(a.sale_price ?? a.regular_price) - toNum(b.sale_price ?? b.regular_price);
      case "discount":
        return toNum(b.discount_percent) - toNum(a.discount_percent);
      default:
        return (a.store_name ?? "").localeCompare(b.store_name ?? "");
    }
  });

  return (
    <div className="container mx-auto max-w-6xl space-y-8 px-4 py-8">
      <div className="grid gap-8 md:grid-cols-2">
        <div className="aspect-square overflow-hidden rounded-lg bg-muted">
          {p.image_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={p.image_url}
              alt={p.name ?? ""}
              className="size-full object-cover"
            />
          ) : (
            <div className="flex size-full items-center justify-center text-muted-foreground">
              no image
            </div>
          )}
        </div>
        <div className="space-y-4">
          <div>
            <div className="flex flex-wrap gap-2 pb-2">
              {p.category && <Badge variant="secondary">{p.category}</Badge>}
              {p.size && <Badge variant="outline">{p.size}</Badge>}
              {p.brand && <Badge variant="outline">{p.brand}</Badge>}
            </div>
            <h1 className="text-2xl font-bold tracking-tight">{p.name}</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Available at {p.stores_carrying} {p.stores_carrying === 1 ? "store" : "stores"}
            </p>
          </div>
          {(p.thc_min || p.cbd_min) && (
            <div className="grid grid-cols-2 gap-3 rounded-lg bg-muted p-3">
              {p.thc_min && (
                <div>
                  <div className="text-xs uppercase text-muted-foreground">THC</div>
                  <div className="text-lg font-semibold">
                    {p.thc_min}
                    {p.thc_max && p.thc_max !== p.thc_min ? `–${p.thc_max}` : ""}%
                  </div>
                </div>
              )}
              {p.cbd_min && (
                <div>
                  <div className="text-xs uppercase text-muted-foreground">CBD</div>
                  <div className="text-lg font-semibold">
                    {p.cbd_min}
                    {p.cbd_max && p.cbd_max !== p.cbd_min ? `–${p.cbd_max}` : ""}%
                  </div>
                </div>
              )}
            </div>
          )}
          {p.description && (
            <div className="space-y-2">
              {p.description_lang === "fr" && (
                <p className="rounded-md border border-dashed bg-muted/50 px-3 py-2 text-xs text-muted-foreground">
                  OCS only publishes this product&apos;s description in French.
                  English copy isn&apos;t yet available from the catalog.
                </p>
              )}
              <p
                lang={p.description_lang ?? undefined}
                className="text-sm leading-relaxed text-muted-foreground"
              >
                {p.description}
              </p>
            </div>
          )}
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            Available at {sorted.length} {sorted.length === 1 ? "store" : "stores"}
          </CardTitle>
        </CardHeader>
        <CardContent className="overflow-x-auto p-0">
          {sorted.length === 0 ? (
            <p className="p-6 text-sm text-muted-foreground">
              No Burlington stores currently carry this product. (It may be a new
              OCS arrival that hasn't been picked up by retailers yet.)
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead
                    className="cursor-pointer"
                    onClick={() => setSortKey("store")}
                  >
                    Store
                  </TableHead>
                  <TableHead
                    className="cursor-pointer text-right"
                    onClick={() => setSortKey("regular")}
                  >
                    Regular
                  </TableHead>
                  <TableHead
                    className="cursor-pointer text-right"
                    onClick={() => setSortKey("sale")}
                  >
                    Sale
                  </TableHead>
                  <TableHead
                    className="cursor-pointer text-right"
                    onClick={() => setSortKey("discount")}
                  >
                    Discount
                  </TableHead>
                  <TableHead>Stock</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sorted.map((row) => (
                  <TableRow key={row.store_id}>
                    <TableCell className="font-medium">
                      <Link
                        href={`/stores/${row.store_id}`}
                        className="hover:underline"
                      >
                        {row.store_name}
                      </Link>
                      {row.address && (
                        <div className="text-xs text-muted-foreground">{row.address}</div>
                      )}
                    </TableCell>
                    <TableCell className="text-right">
                      {formatCurrency(row.regular_price)}
                    </TableCell>
                    <TableCell className="text-right">
                      {row.sale_price ? (
                        <span className="font-semibold text-destructive">
                          {formatCurrency(row.sale_price)}
                        </span>
                      ) : (
                        <span className="text-muted-foreground">—</span>
                      )}
                    </TableCell>
                    <TableCell className="text-right">
                      {row.discount_percent ? (
                        <Badge className="bg-destructive text-destructive-foreground">
                          -{Math.round(Number(row.discount_percent))}%
                        </Badge>
                      ) : (
                        <span className="text-muted-foreground">—</span>
                      )}
                    </TableCell>
                    <TableCell>
                      {row.in_stock === true && <Badge variant="secondary">In stock</Badge>}
                      {row.in_stock === false && <Badge variant="outline">Out</Badge>}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
