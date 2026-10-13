"use client";
import { useEffect, useState, FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, post, cash, field, safeImage } from "@shared/api";
import { QuantityInput } from "@shared/QuantityInput";
import { Icon } from "@shared/Icon";
import { messages, Locale } from "@i18n";
import Checkout from "../components/Checkout";
import { brandTheme, MarketplaceHero, CategoryTiles } from "../components/Marketplace";
import { AccountTools, PasswordReset } from "../components/AccountTools";
import {
  Consent,
  Reviews,
  Bundles,
  HomeSections,
} from "../components/ShoppingTools";

export default function Store({
  route,
  initialConfig,
  initialProducts,
  initialCategories = [],
  initialFilters = { q: "", category: "", brand: "" },
  initialProduct = null,
  initialContent = null,
  initialCms = { sections: [], pages: [] },
}: {
  route: string[];
  initialConfig: any;
  initialProducts: any[];
  initialCategories?: any[];
  initialFilters?: { q: string; category: string; brand: string };
  initialProduct?: any;
  initialContent?: any;
  initialCms?: any;
}) {
  const locale: Locale = route[0] === "ar" ? "ar" : "en";
  const t = messages[locale];
  const page = route[1] || "home";
  const slug = route[2];
  const router = useRouter();
  const [cfg, setCfg] = useState(initialConfig),
    [products, setProducts] = useState<any[]>(initialProducts),
    [categories, setCategories] = useState<any[]>(initialCategories),
    [cms, setCms] = useState<any>(initialCms);
  const [bag, setBag] = useState<any>({ items: [] }),
    [user, setUser] = useState<any>(null),
    [error, setError] = useState(""),
    [toast, setToast] = useState(""),
    [query, setQuery] = useState(initialFilters.q),
    [searchInput, setSearchInput] = useState(initialFilters.q),
    [category, setCategory] = useState(initialFilters.category),
    [sort, setSort] = useState(""),
    [stock, setStock] = useState(false),
    [brand, setBrand] = useState(initialFilters.brand),
    [brands, setBrands] = useState<any[]>([]),
    [pageNum, setPageNum] = useState(1),
    [count, setCount] = useState(initialProducts.length),
    [nextPage, setNextPage] = useState<number | null>(null),
    [compareProducts, setCompareProducts] = useState<any[]>([]),
    [busy, setBusy] = useState(false);
  const [product, setProduct] = useState<any>(initialProduct),
    [variant, setVariant] = useState<any>(
      initialProduct?.variants?.find((v: any) => v.available > 0) ||
        initialProduct?.variants?.[0],
    ),
    [qty, setQty] = useState(1),
    [orders, setOrders] = useState<any[]>([]),
    [saved, setSaved] = useState<any[]>([]),
    [compare, setCompare] = useState<string[]>([]),
    [content, setContent] = useState<any>(initialContent);
  const url = (path = "") => `/${locale}${path ? "/" + path : ""}`;
  function notify(message: string) {
    setToast(message);
    setTimeout(() => setToast(""), 3500);
  }
  async function run(fn: () => Promise<void>) {
    setError("");
    setBusy(true);
    try {
      await fn();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  useEffect(() => {
    document.documentElement.lang = locale;
    document.documentElement.dir = locale === "ar" ? "rtl" : "ltr";
  }, [locale]);
  useEffect(() => {
    api("/store/config")
      .then(setCfg)
      .catch((e) => setError(e.message));
    api("/store/brands")
      .then(setBrands)
      .catch(() => {});
    api("/store/categories")
      .then(setCategories)
      .catch(() => {});
    api("/store/homepage")
      .then(setCms)
      .catch(() => {});
    api("/cart")
      .then(setBag)
      .catch(() => {});
    api("/auth/session")
      .then((u) => setUser(u?.id ? u : null))
      .catch(() => {});
    try {
      setCompare(JSON.parse(localStorage.getItem("compare") || "[]"));
    } catch {}
  }, []);
  useEffect(() => {
    let active = true;
    setError("");
    if (product?.code !== slug) setProduct(null);
    if (content?.slug !== slug) setContent(null);
    if (page === "products" && slug)
      api("/store/products/" + slug)
        .then((p) => {
          if (!active) return;
          setProduct(p);
          setVariant(
            p.variants.find((v: any) => v.available > 0) || p.variants[0],
          );
          setQty(1);
        })
        .catch((e) => setError(e.message));
    if (page === "account" || page === "orders")
      api("/account/orders")
        .then(setOrders)
        .catch(() => {});
    if (page === "wishlist")
      api("/account/wishlist")
        .then(setSaved)
        .catch((e) => setError(e.message));
    if (page === "pages" && slug)
      api("/store/pages/" + slug)
        .then((c) => {
          if (active) setContent(c);
        })
        .catch((e) => setError(e.message));
    return () => {
      active = false;
    };
  }, [page, slug]);
  useEffect(() => {
    setQuery(initialFilters.q);
    setSearchInput(initialFilters.q);
    setCategory(initialFilters.category);
    setBrand(initialFilters.brand);
    setPageNum(1);
  }, [page, initialFilters.q, initialFilters.category, initialFilters.brand]);
  useEffect(() => setPageNum(1), [query, category, brand, sort, stock]);
  useEffect(() => {
    const controller = new AbortController();
    const timer = setTimeout(() => {
      const params = new URLSearchParams({
        q: query,
        category,
        brand,
        sort,
        in_stock: stock ? "1" : "0",
        page: String(pageNum),
        limit: "24",
      });
      api("/store/products?" + params, { signal: controller.signal })
        .then((d) => {
          setProducts(d.results);
          setCount(d.count);
          setNextPage(d.next_page);
        })
        .catch((e) => {
          if (e.name !== "AbortError") setError(e.message);
        });
    }, 250);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [query, category, brand, sort, stock, pageNum]);
  useEffect(() => {
    if (page !== "compare") return;
    let active = true;
    Promise.all(
      compare.map((code) =>
        api("/store/products/" + encodeURIComponent(code)).catch(() => null),
      ),
    ).then((rows) => {
      if (active) setCompareProducts(rows.filter(Boolean));
    });
    return () => {
      active = false;
    };
  }, [page, compare]);
  async function add(v: any, quantity = 1) {
    await run(async () => {
      setBag(await post("/cart", { variant_id: v.id, quantity }));
      notify(t.add + " ✓");
    });
  }
  async function save(p: any) {
    if (page === "wishlist") {
      await run(async () =>
        setSaved(
          await api("/account/wishlist", {
            method: "DELETE",
            body: JSON.stringify({ product_id: p.id }),
          }),
        ),
      );
      return;
    }
    if (!user) {
      router.push(url("login"));
      return;
    }
    await run(async () => {
      await post("/account/wishlist", { product_id: p.id });
      notify(t.save + " ✓");
    });
  }
  function toggleCompare(id: string) {
    const next = compare.includes(id)
      ? compare.filter((x) => x !== id)
      : [...compare, id].slice(-4);
    setCompare(next);
    localStorage.setItem("compare", JSON.stringify(next));
    notify(t.compare + ` (${next.length})`);
  }
  function art(p: any, large = false) {
    return safeImage(p?.image_url) ? (
      <img
        loading="lazy"
        src={safeImage(p.image_url)}
        alt={field(p, "name", locale)}
      />
    ) : (
      <div className="product-glyph">
        <Icon name="box" size={large ? 95 : 50} />
      </div>
    );
  }
  function cards(items: any[]) {
    return items.length ? (
      <div className="product-grid">
        {items.map((p) => {
          const v =
            p.variants.find(
              (v: any) =>
                p.matching_variant_ids?.includes(v.id) && v.available > 0,
            ) ||
            p.variants.find((v: any) => v.available > 0) ||
            p.variants[0];
          return (
            <article className="product-card" key={p.id}>
              <div className="product-image">
                <Link
                  href={url("products/" + p.code)}
                  aria-label={field(p, "name", locale)}
                >
                  {art(p)}
                </Link>
                <button
                  className="icon-btn"
                  aria-label={page === "wishlist" ? t.remove : t.save}
                  onClick={() => save(p)}
                >
                  <Icon name="heart" size={17} />
                </button>
                {Number(v?.price) > 0 && v?.sale_price != null && Number(v.sale_price) < Number(v.price) && (
                  <span className="pill">{Math.floor((1 - Number(v.sale_price) / Number(v.price)) * 100)}% {locale === "ar" ? "خصم" : "off"}</span>
                )}
              </div>
              <div className="product-info">
                <span className="category-label">
                  {field(p.category, "name", locale)}
                </span>
                <h3>
                  <Link href={url("products/" + p.code)}>
                    {field(p, "name", locale)}
                  </Link>
                </h3>
                <div className="between">
                  <div>
                    <span className="money">
                      {cash(
                        v?.sale_price ?? v?.price ?? 0,
                        cfg.currency,
                        locale,
                      )}
                    </span>
                    {v?.sale_price != null && Number(v.sale_price) < Number(v.price) && (
                      <span className="old-price">
                        {cash(v.price, cfg.currency, locale)}
                      </span>
                    )}
                  </div>
                  <button
                    className="icon-btn"
                    disabled={!v?.available || busy}
                    aria-label={p.variants.length > 1 ? (locale === "ar" ? "اختر الخيارات" : "Choose options") : t.add}
                    onClick={() =>
                      p.variants.length > 1
                        ? router.push(url("products/" + p.code))
                        : add(v)
                    }
                  >
                    <Icon name="plus" size={18} />
                  </button>
                </div>
                <p className="availability">{v?.available > 0 ? (p.variants.length > 1 ? (locale === "ar" ? "خيارات متعددة" : "Options available") : t.stock) : (locale === "ar" ? "غير متوفر حالياً" : "Currently unavailable")}</p>
                <button
                  className="compare-link link"
                  onClick={() => toggleCompare(p.code)}
                >
                  {t.compare}
                </button>
              </div>
            </article>
          );
        })}
      </div>
    ) : (
      <div className="empty muted">{t.noResults}</div>
    );
  }
  if (!cfg)
    return (
      <div className="loading">
        <div>
          <h2>Store setup</h2>
          <p>
            {error ||
              "Connect the API and configure your store to get started."}
          </p>
        </div>
      </div>
    );
  const title = field(cfg, "business_name", locale);
  const total = bag.items.reduce(
    (sum: number, i: any) => sum + Number(i.price || 0) * i.quantity,
    0,
  );
  return (
    <div
      className="store-shell"
      dir={locale === "ar" ? "rtl" : "ltr"}
      style={brandTheme(cfg.primary_color, cfg.accent_color)}
    >
      <div className="topbar">{field(cfg, "tagline", locale) || t.details}</div>
      <header className="store-header">
        <Link className="wordmark" href={url()}>
          {safeImage(cfg.logo_url) ? (
            <img src={safeImage(cfg.logo_url)} alt="" style={{ height: 32 }} />
          ) : (
            <span className="brand-mark">
              <Icon name="box" size={20} />
            </span>
          )}
          {title}
        </Link>
        <form
          className="searchbox"
          onSubmit={(e) => {
            e.preventDefault();
            setQuery(searchInput.trim());
            setCategory(""); setBrand(""); setPageNum(1);
            router.push(url("shop") + "?" + new URLSearchParams({ q: searchInput.trim() }));
          }}
        >
          <Icon name="search" size={18} />
          <input
            aria-label={t.search}
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder={t.search}
          />
          <button className="search-submit" aria-label={t.search} type="submit"><Icon name="arrow" size={19} /></button>
        </form>
        <div className="header-actions">
          <Link
            href={`/${locale === "en" ? "ar" : "en"}/${route.slice(1).join("/")}${page === "shop" ? "?" + new URLSearchParams({ q: query, category, brand }) : ""}`}
          >
            {t.language}
          </Link>
          <Link aria-label={t.account} href={url(user ? "account" : "login")}>
            <Icon name="user" />
            <span className="label">{t.account}</span>
          </Link>
          <Link aria-label={t.cart} href={url("cart")}>
            <Icon name="bag" />
            <span className="label">{t.cart}</span><span className="badge-count">
              {bag.items.reduce((n: number, i: any) => n + i.quantity, 0)}
            </span>
          </Link>
        </div>
      </header>
      <nav className="store-nav" aria-label={locale === "ar" ? "تصفح المتجر" : "Store navigation"}>
        <div className="row">
          <details className="category-menu"><summary><Icon name="grid" size={17} />{locale === "ar" ? "كل الفئات" : "All categories"}</summary>
            <div className="category-menu-panel">
              <Link href={url("shop")}>{t.all}</Link>
              {categories.map((c) => <Link key={c.id} href={url("shop") + "?category=" + encodeURIComponent(c.code)} onClick={(event) => event.currentTarget.closest("details")?.removeAttribute("open")}>{field(c, "name", locale)}</Link>)}
            </div>
          </details>
          {categories.slice(0, 4).map((c) => <Link className="nav-category" key={c.id} href={url("shop") + "?category=" + encodeURIComponent(c.code)}>{field(c, "name", locale)}</Link>)}
          <Link href={url("offers")}>{t.offers}</Link>
          <Link href={url("wishlist")}>{t.wishlist}</Link>
          <Link href={url("compare")}>
            {t.compare}
            {compare.length ? ` (${compare.length})` : ""}
          </Link>
        </div>
        <span className="muted">{cfg.phone || t.secure}</span>
      </nav>
      <main id="main" className="store-main" aria-busy={busy}>
        {error && (
          <div className="error" role="alert" style={{ marginBottom: 24 }}>
            {error}
            <button
              className="icon-btn"
              onClick={() => setError("")}
              aria-label="Dismiss"
            >
              <Icon name="close" size={15} />
            </button>
          </div>
        )}
        {["home", "shop", "offers"].includes(page) && (
          <>
            {page === "home" && !cms.sections.length && (
              <>
                <MarketplaceHero section={{ title: t.welcome, body: field(cfg, "tagline", locale) || t.details }} products={products} locale={locale} />
                <CategoryTiles rows={categories} locale={locale} />
                <div className="benefits">
                  {[
                    ["truck", t.delivery, t.pickup],
                    ["shield", t.secure, t.cod],
                    ["heart", t.curated, t.details],
                  ].map(([icon, heading, sub]) => (
                    <div className="benefit" key={icon}>
                      <span>
                        <Icon name={icon} />
                      </span>
                      <div>
                        <strong>{heading}</strong>
                        <small>{sub}</small>
                      </div>
                    </div>
                  ))}
                </div>
              </>
            )}
            {page === "home" && cms.sections.length > 0 && (
              <HomeSections
                sections={cms.sections}
                products={products}
                categories={categories}
                brands={brands}
                locale={locale}
                cards={cards}
              />
            )}
            {page !== "home" && (
              <Bundles
                locale={locale}
                currency={cfg.currency}
                run={run}
                busy={busy}
                refresh={async () => setBag(await api("/cart"))}
              />
            )}
            {(page !== "home" || !cms.sections.length) && (
              <>
                <div className="section-heading">
                  <div>
                    <span className="eyebrow muted">
                      {page === "offers" ? t.offers : t.curated}
                    </span>
                    <h2>{page === "offers" ? t.offers : t.all}</h2>
                  </div>
                  <span className="muted" style={{ fontSize: 12 }}>
                    {count} {locale === "ar" ? "منتج" : "products"}
                  </span>
                </div>
                <div className="categories">
                  <button
                    className={"category-tab " + (!category ? "active" : "")}
                    onClick={() => setCategory("")}
                  >
                    {t.all}
                  </button>
                  {categories.map((c) => (
                    <button
                      key={c.id}
                      className={
                        "category-tab " + (category === c.code ? "active" : "")
                      }
                      onClick={() => setCategory(c.code)}
                    >
                      {field(c, "name", locale)}
                    </button>
                  ))}
                </div>
                {page !== "home" && (
                  <div className="shop-toolbar">
                    <label>
                      <input
                        type="checkbox"
                        checked={stock}
                        onChange={(e) => setStock(e.target.checked)}
                      />
                      {t.stock}
                    </label>
                    <select
                      aria-label={t.brands}
                      value={brand}
                      onChange={(e) => setBrand(e.target.value)}
                    >
                      <option value="">{t.brands}</option>
                      {brands.map((b) => (
                        <option key={b.id} value={b.id}>
                          {field(b, "name", locale)}
                        </option>
                      ))}
                    </select>
                    <select
                      aria-label={t.sort}
                      value={sort}
                      onChange={(e) => setSort(e.target.value)}
                    >
                      <option value="">{t.featured}</option>
                      <option value="price_asc">{t.priceLow}</option>
                      <option value="price_desc">{t.priceHigh}</option>
                    </select>
                  </div>
                )}
                {cards(
                  page === "offers"
                    ? products.filter((p) =>
                        p.variants.some((v: any) => v.sale_price !== null),
                      )
                    : products,
                )}
                {false &&
                  cms.sections
                    .filter(
                      (s: any) => s.kind === "text" || s.kind === "promotion",
                    )
                    .map((s: any, i: number) => (
                      <section
                        className="card"
                        key={i}
                        style={{ marginTop: 35, background: "var(--canvas)" }}
                      >
                        <h2>{field(s, "title", locale)}</h2>
                        <p>{field(s, "body", locale)}</p>
                      </section>
                    ))}
                <nav
                  className="pagination"
                  aria-label={
                    locale === "ar" ? "صفحات المنتجات" : "Product pages"
                  }
                >
                  <button
                    className="btn secondary small"
                    disabled={pageNum === 1}
                    onClick={() => setPageNum((p) => p - 1)}
                  >
                    {locale === "ar" ? "السابق" : "Previous"}
                  </button>
                  <span>{pageNum}</span>
                  <button
                    className="btn secondary small"
                    disabled={!nextPage}
                    onClick={() => setPageNum(nextPage!)}
                  >
                    {locale === "ar" ? "التالي" : "Next"}
                  </button>
                </nav>
              </>
            )}
          </>
        )}
        {page === "products" && !product && !error && (
          <div className="loading" role="status">
            {t.loading}
          </div>
        )}
        {page === "products" && product && (
          <>
            <div className="breadcrumb">
              <Link href={url("shop")}>{t.shop}</Link> /{" "}
              {field(product.category, "name", locale)} /{" "}
              {field(product, "name", locale)}
            </div>
            <div className="product-detail">
              <div className="product-image">{art(product, true)}</div>
              <div>
                <p className="eyebrow muted">
                  {product.brand
                    ? field(product.brand, "name", locale)
                    : field(product.category, "name", locale)}
                </p>
                <h1>{field(product, "name", locale)}</h1>
                <span className="money">
                  {cash(
                    variant?.sale_price ?? variant?.price ?? 0,
                    cfg.currency,
                    locale,
                  )}
                </span>
                <p className="muted">{field(product, "description", locale)}</p>
                <div className="divider" />
                <label>
                  {t.select}
                  <div className="variant-select">
                    {product.variants.map((v: any) => (
                      <button
                        className={variant?.id === v.id ? "selected" : ""}
                        key={v.id}
                        onClick={() => {
                          setVariant(v);
                          setQty(1);
                        }}
                      >
                        {Object.values(v.options)
                          .map((o: any) => field(o, "label", locale))
                          .join(" / ") || v.sku}
                      </button>
                    ))}
                  </div>
                </label>
                <p>
                  <span
                    className={"pill " + (!variant?.available ? "warn" : "")}
                  >
                    {variant?.available
                      ? `${variant.available} ${t.available}`
                      : t.out}
                  </span>{" "}
                  <small className="muted">{variant?.sku}</small>
                </p>
                <div className="row">
                  <input
                    aria-label={t.quantity}
                    type="number"
                    min={1}
                    max={Math.min(50, variant?.available || 1)}
                    value={qty}
                    onChange={(e) => setQty(Number(e.target.value))}
                    style={{ width: 80 }}
                  />
                  <button
                    className="btn"
                    style={{ flex: 1 }}
                    disabled={
                      !variant?.available ||
                      busy ||
                      !Number.isInteger(qty) ||
                      qty < 1 ||
                      qty > Math.min(50, variant?.available || 0)
                    }
                    onClick={() => add(variant, qty)}
                  >
                    <Icon name="bag" size={18} />
                    {t.add}
                  </button>
                  <button
                    className="btn secondary"
                    aria-label={t.save}
                    onClick={() => save(product)}
                  >
                    <Icon name="heart" />
                  </button>
                </div>
                {cfg.whatsapp && (
                  <a
                    className="btn secondary"
                    style={{ width: "100%", marginTop: 15 }}
                    href={`https://wa.me/${cfg.whatsapp}?text=${encodeURIComponent(`Hi, I am interested in ${field(product, "name", locale)}.\nProduct: ${typeof window !== "undefined" ? window.location.origin : ""}${url("products/" + product.code)}`)}`}
                    target="_blank"
                    rel="noreferrer"
                  >
                    {t.whatsapp}
                  </a>
                )}
              </div>
            </div>
            <div className="spec-table">
              <h2>{t.specifications}</h2>
              <table>
                <tbody>
                  {product.attributes.map((a: any) => (
                    <tr key={a.code}>
                      <td>{field(a, "name", locale)}</td>
                      <td>
                        {Array.isArray(a.value)
                          ? a.value.join(", ")
                          : String(a.value)}{" "}
                        {a.unit}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Reviews
              productId={product.id}
              locale={locale}
              user={user}
              run={run}
              busy={busy}
            />
          </>
        )}
        {page === "cart" && (
          <>
            <div className="page-heading">
              <h1>{t.cart}</h1>
            </div>
            {bag.items.length || bag.bundles?.length ? (
              <div className="checkout-layout">
                <div>
                  {bag.items.map((i: any) => (
                    <div className="cart-line" key={i.id}>
                      <div className="product-glyph">
                        <Icon name="box" />
                      </div>
                      <div>
                        <strong>{field(i, "name", locale)}</strong>
                        <p
                          className="muted"
                          style={{ fontSize: 12, margin: "6px 0" }}
                        >
                          {i.sku}
                        </p>
                        <button
                          className="link"
                          onClick={() =>
                            run(async () =>
                              setBag(
                                await api("/cart", {
                                  method: "DELETE",
                                  body: JSON.stringify({ item_id: i.id }),
                                }),
                              ),
                            )
                          }
                        >
                          {t.remove}
                        </button>
                      </div>
                      <QuantityInput
                        label={t.quantity}
                        value={i.quantity}
                        disabled={busy}
                        onCommit={(quantity) =>
                          run(async () =>
                            setBag(
                              await api("/cart", {
                                method: "PATCH",
                                body: JSON.stringify({
                                  variant_id: i.variant_id,
                                  quantity,
                                }),
                              }),
                            ),
                          )
                        }
                      />
                      <span className="money">
                        {cash(
                          Number(i.price) * i.quantity,
                          cfg.currency,
                          locale,
                        )}
                      </span>
                    </div>
                  ))}
                  {bag.bundles?.map((b: any) => (
                    <div className="cart-line" key={b.id}>
                      <strong>
                        {locale === "ar" ? "باقة مختارة" : "Selected bundle"} ×{" "}
                        {b.quantity}
                      </strong>
                      <button
                        className="link"
                        onClick={() =>
                          run(async () => {
                            await api("/cart/bundles", {
                              method: "DELETE",
                              body: JSON.stringify({ bundle_id: b.id }),
                            });
                            setBag(await api("/cart"));
                          })
                        }
                      >
                        {t.remove}
                      </button>
                    </div>
                  ))}
                </div>
                <div className="card summary">
                  <h3>{t.subtotal}</h3>
                  <div className="between">
                    <span>{t.subtotal}</span>
                    <span className="money">
                      {bag.bundles?.length
                        ? locale === "ar"
                          ? "يُحسب عند الدفع"
                          : "Calculated at checkout"
                        : cash(total, cfg.currency, locale)}
                    </span>
                  </div>
                  <p className="muted" style={{ fontSize: 12 }}>
                    {locale === "ar"
                      ? "يتم حساب الخصومات والتوصيل عند الدفع."
                      : "Promotions and delivery are calculated at checkout."}
                  </p>
                  <Link
                    className="btn"
                    style={{ width: "100%" }}
                    href={url("checkout")}
                  >
                    {t.checkout}
                    <Icon name="arrow" size={17} />
                  </Link>
                </div>
              </div>
            ) : (
              <div className="empty">
                <h2>{t.empty}</h2>
                <Link className="btn" href={url("shop")}>
                  {t.explore}
                </Link>
              </div>
            )}
          </>
        )}
        {page === "checkout" && (
          <Checkout
            cfg={cfg}
            locale={locale}
            bag={bag}
            setBag={setBag}
            run={run}
            busy={busy}
            user={user}
          />
        )}
        {page === "reset-password" && (
          <PasswordReset locale={locale} run={run} busy={busy} />
        )}
        {page === "login" && (
          <Auth
            locale={locale}
            run={run}
            busy={busy}
            setUser={setUser}
            done={() => router.push(url("account"))}
          />
        )}
        {["account", "orders"].includes(page) && (
          <>
            <div className="between page-heading">
              <div>
                <h1>{user?.name || t.account}</h1>
                <p className="muted">{user?.email}</p>
              </div>
              {user ? (
                <button
                  className="btn secondary"
                  onClick={() =>
                    run(async () => {
                      await post("/auth/logout", {});
                      setUser(null);
                      router.push(url("login"));
                    })
                  }
                >
                  {t.logout}
                </button>
              ) : (
                <Link className="btn" href={url("login")}>
                  {t.login}
                </Link>
              )}
            </div>
            <h2>{t.orders}</h2>
            {orders.map((o) => (
              <div className="card" style={{ marginBottom: 15 }} key={o.id}>
                <div className="between">
                  <div>
                    <strong>{o.number}</strong>
                    <p className="muted">
                      {new Date(o.created_at).toLocaleDateString(locale)}
                    </p>
                  </div>
                  <span className="pill">{o.state.replaceAll("_", " ")}</span>
                  <span className="money">
                    {cash(o.total, o.currency, locale)}
                  </span>
                  <a
                    className="link"
                    href={"/api/v1/orders/" + o.id + "/invoice"}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    {t.invoice}
                  </a>
                </div>
                {o.items.map((i: any) => (
                  <p key={i.id} style={{ fontSize: 12 }}>
                    {field(i, "name", locale)} × {i.quantity}
                  </p>
                ))}
              </div>
            ))}
            {page === "account" && user && (
              <AccountTools locale={locale} run={run} busy={busy} />
            )}
            <button
              className="link"
              onClick={() =>
                run(async () => setOrders(await api("/account/orders")))
              }
            >
              {locale === "ar" ? "تحديث الطلبات" : "Refresh orders"}
            </button>
            {!orders.length && (
              <p className="muted">
                {locale === "ar" ? "لا توجد طلبات بعد." : "No orders yet."}
              </p>
            )}
          </>
        )}
        {page === "wishlist" && (
          <>
            <h1 style={{ fontSize: 34 }}>{t.wishlist}</h1>
            {cards(saved)}
          </>
        )}
        {page === "compare" && (
          <>
            <h1 style={{ fontSize: 34 }}>{t.compare}</h1>
            <div className="scroll">
              <table className="compare-table">
                <thead>
                  <tr>
                    <th>{t.specifications}</th>
                    {compareProducts.map((p) => (
                      <th key={p.id}>
                        {field(p, "name", locale)}{" "}
                        <button
                          className="link"
                          onClick={() => toggleCompare(p.code)}
                        >
                          {t.remove}
                        </button>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {Array.from(
                    new Set(
                      compareProducts.flatMap((p) =>
                        p.attributes.map((a: any) => a.code),
                      ),
                    ),
                  ).map((code: any) => (
                    <tr key={code}>
                      <td>{code}</td>
                      {compareProducts.map((p) => (
                        <td key={p.id}>
                          {String(
                            p.attributes.find((a: any) => a.code === code)
                              ?.value ?? "—",
                          )}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {!compare.length && <p className="muted">{t.select}</p>}
          </>
        )}
        {page === "pages" && content && (
          <article className="page-copy">
            <h1 style={{ fontSize: 38 }}>{field(content, "title", locale)}</h1>
            <p>{field(content, "body", locale)}</p>
          </article>
        )}
      </main>
      <footer className="footer">
        <div className="footer-grid">
          <div>
            <Link href={url()} className="wordmark">
              {title}
            </Link>
            <p>{field(cfg, "tagline", locale) || t.details}</p>
            <p>{cfg.address}</p>
          </div>
          <div>
            <h4>{t.policies}</h4>
            {cms.pages
              .filter((p: any) => p.kind === "page")
              .slice(0, 7)
              .map((p: any) => (
                <Link key={p.slug} href={url("pages/" + p.slug)}>
                  {field(p, "title", locale)}
                </Link>
              ))}
          </div>
          <div>
            <h4>{t.support}</h4>
            {cfg.email && <a href={"mailto:" + cfg.email}>{cfg.email}</a>}
            {cfg.phone && <a href={"tel:" + cfg.phone}>{cfg.phone}</a>}
            <Link href={url("account")}>{t.orders}</Link>
          </div>
        </div>
        <div className="footer-bottom">
          <span>
            © {new Date().getFullYear()} {title}
          </span>
          <span>{cfg.currency} · English / العربية</span>
        </div>
      </footer>
      <Consent
        locale={locale}
        productId={page === "products" ? product?.id : null}
      />
      {toast && (
        <div className="toast" role="status">
          {toast}
        </div>
      )}
    </div>
  );
}

function Auth({ locale, run, busy, setUser, done }: any) {
  const t = messages[locale as Locale];
  const [mode, setMode] = useState("login"),
    [email, setEmail] = useState(""),
    [password, setPassword] = useState(""),
    [name, setName] = useState(""),
    [code, setCode] = useState(""),
    [sent, setSent] = useState(false);
  return (
    <div className="card auth-card">
      <h1>{mode === "register" ? t.register : t.login}</h1>
      <div className="auth-tabs">
        {[
          ["login", t.login],
          ["register", t.register],
          ["otp", t.otp],
        ].map(([m, label]) => (
          <button
            key={m}
            className={mode === m ? "active" : ""}
            onClick={() => {
              setMode(m);
              setSent(false);
              setCode("");
            }}
          >
            {label}
          </button>
        ))}
      </div>
      <form
        className="stack"
        onSubmit={(e) => {
          e.preventDefault();
          run(async () => {
            if (mode === "otp" && !sent) {
              await post("/auth/otp/request", { email });
              setSent(true);
              return;
            }
            const u = await post(
              mode === "otp"
                ? "/auth/otp/verify"
                : mode === "register"
                  ? "/auth/register"
                  : "/auth/login",
              { email, password, name, code },
            );
            setUser(u);
            done();
          });
        }}
      >
        {mode === "register" && (
          <label>
            {t.name}
            <input
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </label>
        )}
        <label>
          {t.email}
          <input
            required
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </label>
        {mode !== "otp" ? (
          <label>
            {t.password}
            <input
              required
              minLength={mode === "register" ? 12 : 1}
              type="password"
              autoComplete={
                mode === "register" ? "new-password" : "current-password"
              }
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </label>
        ) : (
          sent && (
            <label>
              {t.otp}
              <input
                required
                inputMode="numeric"
                maxLength={6}
                value={code}
                onChange={(e) => setCode(e.target.value)}
              />
            </label>
          )
        )}
        <button className="btn" disabled={busy}>
          {mode === "otp"
            ? sent
              ? t.verify
              : t.sendCode
            : mode === "register"
              ? t.register
              : t.login}
        </button>
      </form>
      <Link className="link" href={`/${locale}/reset-password`}>
        {locale === "ar" ? "نسيت كلمة المرور؟" : "Forgot password?"}
      </Link>
    </div>
  );
}
