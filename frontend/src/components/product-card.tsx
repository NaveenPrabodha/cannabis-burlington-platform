import { Leaf } from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import type { Product } from "@/lib/api";
import { cn, formatCurrency, formatPercent } from "@/lib/utils";

interface ProductCardProps {
  product: Product;
  className?: string;
}

export function ProductCard({ product, className }: ProductCardProps) {
  const onSale = (product.stores_on_sale ?? 0) > 0;
  const minRetail = product.min_retail_price ?? product.price;
  const minSale = product.min_sale_price;
  const discountAvail = onSale && minRetail && minSale
    ? Math.round((1 - Number(minSale) / Number(minRetail)) * 100)
    : null;

  return (
    <Card
      className={cn(
        "group overflow-hidden p-0 transition-shadow hover:shadow-md",
        className,
      )}
    >
      <Link href={`/products/${product.product_id}`} className="block">
        <div className="relative aspect-square bg-muted">
          {product.image_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={product.image_url}
              alt=""
              className="size-full object-cover transition-transform group-hover:scale-105"
              loading="lazy"
              onError={(e) => {
                e.currentTarget.style.display = "none";
                const sib = e.currentTarget.nextElementSibling as HTMLElement | null;
                if (sib) sib.classList.remove("hidden");
              }}
            />
          ) : null}
          <div
            className={cn(
              "flex size-full flex-col items-center justify-center gap-2 bg-gradient-to-br from-muted to-muted/60 p-3 text-center",
              product.image_url && "hidden",
            )}
          >
            <Leaf className="size-8 text-primary/40" />
            <div className="line-clamp-3 text-xs text-muted-foreground">
              {product.name ?? "Untitled product"}
            </div>
          </div>
          {discountAvail !== null && discountAvail >= 5 && (
            <Badge className="absolute left-2 top-2 bg-destructive text-destructive-foreground">
              -{formatPercent(discountAvail)}
            </Badge>
          )}
        </div>
        <div className="space-y-1 p-3">
          <div className="text-xs text-muted-foreground">{product.brand ?? "—"}</div>
          <div className="line-clamp-2 text-sm font-medium leading-tight">
            {product.name ?? "Untitled product"}
          </div>
          <div className="flex items-baseline justify-between gap-2 pt-1">
            <div>
              {onSale && minSale ? (
                <>
                  <span className="text-base font-semibold text-destructive">
                    {formatCurrency(minSale)}
                  </span>
                  <span className="ml-1 text-xs text-muted-foreground line-through">
                    {formatCurrency(minRetail)}
                  </span>
                </>
              ) : (
                <span className="text-base font-semibold">
                  {formatCurrency(minRetail)}
                </span>
              )}
            </div>
            <span className="text-xs text-muted-foreground">
              {product.stores_carrying ?? 0} {product.stores_carrying === 1 ? "store" : "stores"}
            </span>
          </div>
          <div className="flex flex-wrap gap-1 pt-1">
            {product.category && (
              <Badge variant="secondary" className="text-[10px]">
                {product.category}
              </Badge>
            )}
            {product.size && (
              <Badge variant="outline" className="text-[10px]">
                {product.size}
              </Badge>
            )}
          </div>
        </div>
      </Link>
    </Card>
  );
}
