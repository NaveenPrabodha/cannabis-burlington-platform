import { Globe, MapPin, Phone, ShieldCheck } from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { Store } from "@/lib/api";
import { isOpenNow, todaysHours } from "@/lib/hours";

interface StoreCardProps {
  store: Store;
}

export function StoreCard({ store }: StoreCardProps) {
  const open = isOpenNow(store.hours_json);
  const today = todaysHours(store.hours_json);

  return (
    <Card className="h-full transition-shadow hover:shadow-md">
      <CardHeader className="space-y-1">
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="text-base leading-tight">
            <Link href={`/stores/${store.store_id}`} className="hover:underline">
              {store.store_name}
            </Link>
          </CardTitle>
          {open === true && (
            <Badge className="bg-primary text-primary-foreground">Open now</Badge>
          )}
          {open === false && (
            <Badge variant="secondary">Closed</Badge>
          )}
        </div>
        {store.agco_licence_number && (
          <p className="flex items-center gap-1 text-xs text-muted-foreground">
            <ShieldCheck className="size-3" />
            AGCO {store.agco_licence_number}
          </p>
        )}
      </CardHeader>
      <CardContent className="space-y-2 text-sm">
        {store.address && (
          <p className="flex items-start gap-2 text-muted-foreground">
            <MapPin className="mt-0.5 size-4 shrink-0" />
            <span>{store.address}</span>
          </p>
        )}
        {store.phone && (
          <p className="flex items-center gap-2 text-muted-foreground">
            <Phone className="size-4" />
            <span>{store.phone}</span>
          </p>
        )}
        {store.website && (
          <p className="flex items-center gap-2 text-muted-foreground">
            <Globe className="size-4" />
            <a
              href={store.website}
              target="_blank"
              rel="noreferrer"
              className="truncate hover:underline"
            >
              {store.website.replace(/^https?:\/\//, "")}
            </a>
          </p>
        )}
        {today && (
          <p className="text-xs text-muted-foreground">Today: {today}</p>
        )}
        {store.product_count !== undefined && (
          <p className="pt-1 text-xs">
            <span className="font-medium">{store.product_count}</span>{" "}
            products carried
          </p>
        )}
      </CardContent>
    </Card>
  );
}
