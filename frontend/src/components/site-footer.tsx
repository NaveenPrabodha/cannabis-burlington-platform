import Link from "next/link";

import { DataFreshness } from "@/components/data-freshness";

export function SiteFooter() {
  return (
    <footer className="border-t bg-background">
      <div className="container mx-auto max-w-7xl px-4 py-8 text-sm text-muted-foreground">
        <div className="grid gap-6 md:grid-cols-3">
          <div>
            <h3 className="mb-2 font-semibold text-foreground">Burlington Cannabis</h3>
            <p>
              Price comparison & store discovery for Burlington, ON and the
              surrounding 35&nbsp;km radius.
            </p>
          </div>
          <div>
            <h3 className="mb-2 font-semibold text-foreground">Browse</h3>
            <ul className="space-y-1">
              <li><Link href="/products">Products</Link></li>
              <li><Link href="/stores">Stores</Link></li>
              <li><Link href="/deals">Deals</Link></li>
            </ul>
          </div>
          <div>
            <h3 className="mb-2 font-semibold text-foreground">Data</h3>
            <ul className="space-y-1">
              <li>Prices: HiBuddy.ca (refreshed daily)</li>
              <li>Catalog: Ontario Cannabis Store</li>
              <li>Licence verification: AGCO</li>
            </ul>
          </div>
        </div>
        <div className="mt-6 border-t pt-4">
          <DataFreshness />
        </div>
        <p className="mt-4 text-xs">
          Not affiliated with HiBuddy, OCS, or AGCO. Cannabis is for adults
          19+. Please consume responsibly.
        </p>
      </div>
    </footer>
  );
}
