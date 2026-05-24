"use client";

import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  Boxes,
  ShieldCheck,
  Sparkles,
  TrendingDown,
} from "lucide-react";
import Link from "next/link";

import { DealCard } from "@/components/deal-card";
import { EmptyState } from "@/components/empty-state";
import { ProductCard } from "@/components/product-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";

export default function HomePage() {
  const featured = useQuery({ queryKey: ["featured"], queryFn: api.featured });
  const categories = useQuery({ queryKey: ["categories"], queryFn: api.categories });

  return (
    <div className="container mx-auto max-w-7xl space-y-12 px-4 py-10">
      <section className="rounded-xl bg-gradient-to-br from-primary/10 via-accent to-background p-8 md:p-12">
        <Badge variant="outline" className="mb-3 bg-background/60">
          Burlington, ON · 35 km radius
        </Badge>
        <h1 className="text-3xl font-bold tracking-tight md:text-5xl">
          Find the best cannabis prices in Burlington.
        </h1>
        <p className="mt-3 max-w-2xl text-muted-foreground md:text-lg">
          Compare prices across 26 licensed retailers in real time. Track deals,
          discover new OCS arrivals, and shop with confidence.
        </p>
        <div className="mt-6 flex flex-wrap gap-3">
          <Button asChild size="lg">
            <Link href="/products">Browse products</Link>
          </Button>
          <Button asChild size="lg" variant="outline">
            <Link href="/deals">View deals</Link>
          </Button>
        </div>
      </section>

      <section className="grid gap-4 sm:grid-cols-3">
        <Card>
          <CardContent className="flex items-start gap-3 p-4">
            <TrendingDown className="size-5 text-primary" />
            <div>
              <div className="font-semibold">Daily price refresh</div>
              <p className="text-xs text-muted-foreground">
                Menus & sales scraped every morning at 06:00 ET
              </p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-start gap-3 p-4">
            <Boxes className="size-5 text-primary" />
            <div>
              <div className="font-semibold">7k+ OCS products</div>
              <p className="text-xs text-muted-foreground">
                Full Ontario Cannabis Store catalog, matched to local menus
              </p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-start gap-3 p-4">
            <ShieldCheck className="size-5 text-primary" />
            <div>
              <div className="font-semibold">AGCO-verified retailers</div>
              <p className="text-xs text-muted-foreground">
                Only stores authorized by the Alcohol & Gaming Commission of Ontario
              </p>
            </div>
          </CardContent>
        </Card>
      </section>

      <section>
        <div className="flex items-end justify-between pb-3">
          <h2 className="text-xl font-semibold tracking-tight">Hottest deals</h2>
          <Button variant="ghost" size="sm" asChild>
            <Link href="/deals">
              View all <ArrowRight className="size-4" />
            </Link>
          </Button>
        </div>
        {featured.isLoading && (
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4 lg:grid-cols-8">
            {Array.from({ length: 8 }).map((_, i) => (
              <Skeleton key={i} className="aspect-[2/3]" />
            ))}
          </div>
        )}
        {featured.data && featured.data.top_deals.length > 0 && (
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4 lg:grid-cols-8">
            {featured.data.top_deals.map((d) => (
              <DealCard key={d.fact_id} deal={d} />
            ))}
          </div>
        )}
        {featured.data && featured.data.top_deals.length === 0 && (
          <EmptyState
            title="No active deals"
            description="Check back tomorrow after the next price refresh."
          />
        )}
      </section>

      <section>
        <div className="flex items-end justify-between pb-3">
          <div>
            <h2 className="flex items-center gap-2 text-xl font-semibold tracking-tight">
              <Sparkles className="size-5 text-primary" /> New from OCS
            </h2>
            <p className="text-sm text-muted-foreground">
              Products that hit the Ontario Cannabis Store in the last 14 days
            </p>
          </div>
        </div>
        {featured.data && (
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4 lg:grid-cols-8">
            {featured.data.new_arrivals.map((p) => (
              <ProductCard
                key={p.product_id}
                product={{
                  product_id: p.product_id,
                  name: p.name,
                  brand: p.brand,
                  category: p.category,
                  subcategory: null,
                  size: null,
                  description: null,
                  image_url: p.image_url,
                  price: p.ocs_price,
                  thc_min: null,
                  thc_max: null,
                  cbd_min: null,
                  cbd_max: null,
                  stores_carrying: 0,
                  stores_on_sale: 0,
                }}
              />
            ))}
          </div>
        )}
      </section>

      <section>
        <h2 className="pb-3 text-xl font-semibold tracking-tight">Categories</h2>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
          {categories.data?.map((c) => (
            <Link
              key={c.name}
              href={`/products?category=${encodeURIComponent(c.name)}`}
              className="group"
            >
              <Card className="h-full transition-shadow hover:shadow-md">
                <CardContent className="p-4">
                  <div className="font-medium">{c.name}</div>
                  <div className="text-xs text-muted-foreground">
                    {c.count.toLocaleString()} products
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
