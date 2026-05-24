"use client";

import { Leaf, Search } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { ThemeToggle } from "@/components/theme-toggle";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const NAV_LINKS = [
  { href: "/products", label: "Products" },
  { href: "/stores", label: "Stores" },
  { href: "/deals", label: "Deals" },
];

export function SiteHeader() {
  const router = useRouter();
  const [q, setQ] = useState("");

  function onSearch(e: FormEvent) {
    e.preventDefault();
    const query = q.trim();
    if (!query) return;
    router.push(`/search?q=${encodeURIComponent(query)}`);
  }

  return (
    <header className="sticky top-0 z-40 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container mx-auto flex h-14 max-w-7xl items-center gap-4 px-4">
        <Link href="/" className="flex items-center gap-2 font-semibold">
          <Leaf className="size-5 text-primary" />
          <span className="hidden sm:inline">Burlington Cannabis</span>
          <span className="sm:hidden">BurlCan</span>
        </Link>

        <nav className="hidden gap-1 md:flex">
          {NAV_LINKS.map((l) => (
            <Button key={l.href} variant="ghost" size="sm" asChild>
              <Link href={l.href}>{l.label}</Link>
            </Button>
          ))}
        </nav>

        <form
          onSubmit={onSearch}
          className="ml-auto flex flex-1 max-w-sm items-center gap-2"
        >
          <div className="relative w-full">
            <Search className="absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search products or stores"
              className="pl-8"
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
          </div>
        </form>

        <ThemeToggle />
      </div>

      <nav className="container mx-auto flex max-w-7xl gap-1 px-4 pb-2 md:hidden">
        {NAV_LINKS.map((l) => (
          <Button key={l.href} variant="ghost" size="sm" asChild>
            <Link href={l.href}>{l.label}</Link>
          </Button>
        ))}
      </nav>
    </header>
  );
}
