import Store from "../store";
import { notFound, redirect } from "next/navigation";
export const dynamic = "force-dynamic";
const origin = () => process.env.API_ORIGIN || "http://127.0.0.1:8000";
async function get(path: string) {
  try {
    const r = await fetch(origin() + "/api/v1" + path, {
      headers:
        process.env.API_HTTPS_TERMINATED === "true"
          ? { "X-Forwarded-Proto": "https" }
          : {},
      cache: "no-store",
      signal: AbortSignal.timeout(8000),
    });
    return r.ok ? await r.json() : null;
  } catch {
    return null;
  }
}
export async function generateMetadata({
  params,
}: {
  params: Promise<{ route?: string[] }>;
}) {
  const { route = [] } = await params;
  const locale = route[0] === "ar" ? "ar" : "en";
  const cfg = await get("/store/config");
  const product =
    route[1] === "products" && route[2]
      ? await get("/store/products/" + encodeURIComponent(route[2]))
      : null;
  const name =
    locale === "ar" && cfg?.business_name_ar
      ? cfg.business_name_ar
      : cfg?.business_name || "Store";
  return {
    title: product
      ? `${locale === "ar" ? product.name_ar || product.name : product.name} | ${name}`
      : name,
    description:
      (locale === "ar" ? product?.description_ar || cfg?.tagline_ar : null) ||
      product?.description ||
      cfg?.tagline ||
      "",
    robots: {
      index: process.env.INDEXABLE === "true",
      follow: process.env.INDEXABLE === "true",
    },
  };
}
export default async function Page({
  params,
  searchParams,
}: {
  params: Promise<{ route?: string[] }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const { route = [] } = await params;
  if (!route.length) redirect("/en");
  if (route[0] === "reset-password") {
    const p = await searchParams;
    const q = new URLSearchParams();
    for (const key of ["uid", "token"])
      if (typeof p[key] === "string") q.set(key, p[key] as string);
    redirect("/en/reset-password?" + q);
  }
  if (
    !["en", "ar"].includes(route[0]) ||
    route.length > 3 ||
    ![
      "home",
      "shop",
      "offers",
      "products",
      "cart",
      "checkout",
      "login",
      "account",
      "orders",
      "wishlist",
      "compare",
      "pages",
      "reset-password",
    ].includes(route[1] || "home")
  )
    notFound();
  if (["products", "pages"].includes(route[1]) && !route[2]) notFound();
  if (route[2] && !["products", "pages"].includes(route[1])) notFound();
  const filters = await searchParams;
  const initialFilters = {
    q: typeof filters.q === "string" ? filters.q : "",
    category: typeof filters.category === "string" ? filters.category : "",
    brand: typeof filters.brand === "string" ? filters.brand : "",
  };
  const catalogQuery = new URLSearchParams({ ...initialFilters, limit: "24" });
  const [config, products, cms, product, content, categories] = await Promise.all([
    get("/store/config"),
    get("/store/products?" + catalogQuery),
    get("/store/homepage"),
    route[1] === "products"
      ? get("/store/products/" + encodeURIComponent(route[2]))
      : Promise.resolve(null),
    route[1] === "pages"
      ? get("/store/pages/" + encodeURIComponent(route[2]))
      : Promise.resolve(null),
    get("/store/categories"),
  ]);
  if (route[1] === "products" && !product) notFound();
  if (route[1] === "pages" && !content) notFound();
  return (
    <Store
      route={route}
      initialConfig={config}
      initialCategories={categories || []}
      initialFilters={initialFilters}
      initialProduct={product}
      initialContent={content}
      initialCms={cms || { sections: [], pages: [] }}
      initialProducts={products?.results || []}
    />
  );
}
