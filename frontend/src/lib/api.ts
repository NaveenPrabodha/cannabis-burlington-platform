/**
 * Typed API client wrapper.
 *
 * Wraps fetch with default headers, sensible error handling, and helper
 * functions per endpoint. The function shape is `(params) => Promise<T>`
 * — designed to slot into TanStack Query as the `queryFn`.
 */

const BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public detail?: unknown,
  ) {
    super(message);
  }
}

async function request<T>(
  path: string,
  params?: Record<string, string | number | boolean | null | undefined>,
  init?: RequestInit,
): Promise<T> {
  const url = new URL(`${BASE_URL}${path}`);
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      if (v === undefined || v === null || v === "") continue;
      url.searchParams.set(k, String(v));
    }
  }

  const res = await fetch(url.toString(), {
    headers: { "content-type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });

  if (!res.ok) {
    let detail: unknown;
    try {
      detail = await res.json();
    } catch {
      detail = await res.text();
    }
    throw new ApiError(`API ${res.status} on ${path}`, res.status, detail);
  }
  return (await res.json()) as T;
}

// ---------- response shapes (matched to backend Pydantic models) ----------

export interface Paginated<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  has_next: boolean;
}

export interface Store {
  store_id: number;
  store_name: string | null;
  address: string | null;
  phone: string | null;
  website: string | null;
  latitude: string | null;
  longitude: string | null;
  hibuddy_slug: string | null;
  agco_licence_number: string | null;
  is_active: boolean;
  hours_json: Record<string, string> | null;
  owner_name: string | null;
  owner_company: string | null;
  last_scraped_at: string | null;
  product_count?: number;
  deals_count?: number;
}

export interface Product {
  product_id: number;
  name: string | null;
  brand: string | null;
  category: string | null;
  subcategory: string | null;
  size: string | null;
  description: string | null;
  description_lang?: string | null;
  image_url: string | null;
  price: string | null;
  thc_min: string | null;
  thc_max: string | null;
  cbd_min: string | null;
  cbd_max: string | null;
  min_retail_price?: string | null;
  max_retail_price?: string | null;
  min_sale_price?: string | null;
  stores_carrying?: number;
  stores_on_sale?: number;
}

export interface StorePriceForProduct {
  store_id: number;
  store_name: string | null;
  address: string | null;
  distance_km: number | null;
  regular_price: string | null;
  sale_price: string | null;
  discount_percent: string | null;
  in_stock: boolean | null;
  promo_first_seen: string | null;
  promo_last_seen: string | null;
  promo_duration_days: number | null;
}

export interface ProductDetail extends Product {
  available_at: StorePriceForProduct[];
  stores_carrying: number;
}

export interface Deal {
  fact_id: number;
  store_id: number;
  store_name: string | null;
  product_id: number;
  product_name: string | null;
  brand: string | null;
  category: string | null;
  image_url: string | null;
  regular_price: string | null;
  sale_price: string | null;
  discount_percent: string | null;
  promo_first_seen: string | null;
  promo_last_seen: string | null;
  promo_duration_days: number | null;
  in_stock: boolean | null;
}

export interface NewArrival {
  launch_id: number;
  product_id: number;
  launch_date: string;
  name: string | null;
  brand: string | null;
  category: string | null;
  ocs_price: string | null;
  url: string | null;
  image_url: string | null;
}

export interface CountedItem {
  name: string;
  count: number;
}

export interface SearchResults {
  query: string;
  products: Product[];
  stores: Store[];
  total_products: number;
  total_stores: number;
}

export interface Featured {
  top_deals: Deal[];
  new_arrivals: NewArrival[];
}

export interface PipelineFreshness {
  job_name: string;
  last_success_at: string | null;
  last_run_at: string | null;
  last_run_status: string | null;
  last_rows_processed: number | null;
  minutes_since_success: number | null;
}

export interface PipelineRun {
  run_id: number;
  job_name: string;
  status: string;
  started_at: string;
  finished_at: string | null;
  duration_s: string | null;
  rows_processed: number | null;
  error_message: string | null;
  metadata_json: Record<string, unknown> | null;
}

// ---------- endpoints ----------

export const api = {
  health: () => request<{ status: string; db_ok: boolean; version: string; env: string }>("/health"),
  categories: () => request<CountedItem[]>("/categories"),
  brands: () => request<CountedItem[]>("/brands"),
  featured: () => request<Featured>("/featured"),

  listStores: (params: { q?: string; page?: number; page_size?: number }) =>
    request<Paginated<Store>>("/stores", params),
  getStore: (id: number) => request<Store>(`/stores/${id}`),
  storeProducts: (
    id: number,
    params: {
      category?: string;
      brand?: string;
      on_sale?: boolean;
      in_stock?: boolean;
      q?: string;
      page?: number;
      page_size?: number;
    },
  ) => request<Paginated<Product>>(`/stores/${id}/products`, params),

  listProducts: (params: {
    category?: string;
    brand?: string;
    min_price?: number;
    max_price?: number;
    on_sale?: boolean;
    q?: string;
    sort?: string;
    page?: number;
    page_size?: number;
    available_locally?: boolean;
    lang?: "en" | "fr";
  }) => request<Paginated<Product>>("/products", params),
  getProduct: (id: number) => request<ProductDetail>(`/products/${id}`),
  newArrivals: (params: { days?: number; limit?: number }) =>
    request<NewArrival[]>("/products/new-arrivals", params),

  listDeals: (params: {
    category?: string;
    min_discount?: number;
    page?: number;
    page_size?: number;
  }) => request<Paginated<Deal>>("/deals", params),

  search: (params: { q: string; type?: "all" | "products" | "stores"; limit?: number }) =>
    request<SearchResults>("/search", params),

  pipelineFreshness: () => request<PipelineFreshness[]>("/pipeline/freshness"),
  pipelineRuns: (params: { job_name?: string; limit?: number }) =>
    request<PipelineRun[]>("/pipeline/runs", params),
};
