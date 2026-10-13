"use client";
import { useEffect, useState, useRef } from "react";
import Link from "next/link";
import { api, post, cash, field } from "@shared/api";
import { MarketplaceHero, CategoryTiles } from "./Marketplace";
import { Icon } from "@shared/Icon";
export function Consent({ locale, productId }: any) {
  const [choice, setChoice] = useState<string | null>(null),
    [open, setOpen] = useState(false),
    [error, setError] = useState("");
  const pageId = useRef("");
  useEffect(() => {
    let active = true;
    const stored = localStorage.getItem("shopping-consent");
    if (stored) {
      post("/analytics/consent", { consent: stored === "yes" })
        .then(() => {
          if (active) setChoice(stored);
        })
        .catch(() => {
          if (active) setOpen(true);
        });
    } else setOpen(true);
    return () => {
      active = false;
    };
  }, []);
  useEffect(() => {
    pageId.current = crypto.randomUUID();
  }, [productId]);
  useEffect(() => {
    if (choice === "yes" && productId)
      post("/analytics/product-view", {
        product_id: productId,
        page_view_id: pageId.current,
      }).catch(() => {});
  }, [choice, productId]);
  async function choose(value: boolean) {
    try {
      await post("/analytics/consent", { consent: value });
      localStorage.setItem("shopping-consent", value ? "yes" : "no");
      setChoice(value ? "yes" : "no");
      setOpen(false);
      setError("");
    } catch {
      setError(
        locale === "ar"
          ? "تعذر حفظ الاختيار. أعد المحاولة."
          : "Could not save your choice. Please retry.",
      );
    }
  }
  return (
    <>
      <button className="privacy-link" onClick={() => setOpen(true)}>
        {locale === "ar" ? "تفضيلات الخصوصية" : "Privacy preferences"}
      </button>
      {open && (
        <section
          className="consent card"
          aria-label={
            locale === "ar" ? "تفضيلات الخصوصية" : "Privacy preferences"
          }
        >
          <strong>
            {locale === "ar"
              ? "هل تسمح بتحليلات التسوق الاختيارية؟"
              : "Allow optional shopping analytics?"}
          </strong>
          <p>
            {locale === "ar"
              ? "نستخدم جلسات التسوق لفهم زيارات المنتجات وعمليات الشراء. يمكنك الرفض ومواصلة التسوق."
              : "We use shopping sessions to understand product visits and purchases. You can decline and continue shopping."}
          </p>
          <div className="row">
            <button
              className="btn secondary small"
              onClick={() => choose(false)}
            >
              {locale === "ar" ? "رفض" : "Decline"}
            </button>
            <button className="btn small" onClick={() => choose(true)}>
              {locale === "ar" ? "سماح" : "Allow"}
            </button>
          </div>
          {error && <p role="alert">{error}</p>}
        </section>
      )}
    </>
  );
}
export function Reviews({ productId, locale, user, run, busy }: any) {
  const [rows, setRows] = useState<any[]>([]),
    [body, setBody] = useState(""),
    [rating, setRating] = useState(5),
    [sent, setSent] = useState(false);
  useEffect(() => {
    api("/store/products/" + productId + "/reviews")
      .then(setRows)
      .catch(() => {});
  }, [productId]);
  return (
    <section className="card stack">
      <h2>{locale === "ar" ? "آراء العملاء" : "Customer reviews"}</h2>
      {rows.map((r, i) => (
        <article key={i}>
          <strong>
            {r.name || (locale === "ar" ? "عميل" : "Customer")} · {r.rating}/5
          </strong>
          <p>{r.body}</p>
        </article>
      ))}
      {!rows.length && (
        <p className="muted">
          {locale === "ar"
            ? "لا توجد تقييمات منشورة بعد."
            : "No published reviews yet."}
        </p>
      )}
      {user && !sent && (
        <form
          className="stack"
          onSubmit={(e) => {
            e.preventDefault();
            run(async () => {
              await post("/store/products/" + productId + "/reviews", {
                rating,
                body,
              });
              setSent(true);
            });
          }}
        >
          <p className="field-help">
            {locale === "ar"
              ? "يمكن للعملاء الذين استلموا طلباتهم تقديم تقييم للمراجعة."
              : "Customers with a completed purchase can submit a review for moderation."}
          </p>
          <label>
            {locale === "ar" ? "التقييم" : "Rating"}
            <select
              value={rating}
              onChange={(e) => setRating(Number(e.target.value))}
            >
              {[5, 4, 3, 2, 1].map((n) => (
                <option key={n} value={n}>
                  {n}/5
                </option>
              ))}
            </select>
          </label>
          <label>
            {locale === "ar" ? "رأيك" : "Your review"}
            <textarea
              required
              maxLength={5000}
              value={body}
              onChange={(e) => setBody(e.target.value)}
            />
          </label>
          <button className="btn secondary" disabled={busy}>
            {locale === "ar" ? "إرسال التقييم" : "Submit review"}
          </button>
        </form>
      )}
      {sent && (
        <p role="status">
          {locale === "ar"
            ? "تم إرسال تقييمك للمراجعة."
            : "Your review is awaiting moderation."}
        </p>
      )}
    </section>
  );
}
export function Bundles({ locale, currency, run, busy, refresh }: any) {
  const [rows, setRows] = useState<any[]>([]);
  useEffect(() => {
    api("/store/bundles")
      .then(setRows)
      .catch(() => {});
  }, []);
  if (!rows.length) return null;
  return (
    <section className="bundle-section">
      <h2>{locale === "ar" ? "باقات مختارة" : "Better together"}</h2>
      <div className="product-grid">
        {rows.map((b) => (
          <article className="card stack" key={b.id}>
            <span className="eyebrow">
              {locale === "ar" ? "باقة" : "Bundle"}
            </span>
            <h3>{b.name}</h3>
            <span>
              {Object.values(b.components).reduce(
                (n: number, q: any) => n + Number(q),
                0,
              )}{" "}
              {locale === "ar" ? "منتجات في الباقة" : "items in this bundle"}
            </span>
            <strong>{cash(b.price, currency, locale)}</strong>
            <button
              disabled={busy}
              className="btn"
              onClick={() =>
                run(async () => {
                  await post("/cart/bundles", {
                    promotion_id: b.id,
                    quantity: 1,
                  });
                  await refresh();
                })
              }
            >
              {locale === "ar" ? "أضف الباقة" : "Add bundle"}
            </button>
          </article>
        ))}
      </div>
    </section>
  );
}
export function HomeSections({
  sections,
  products,
  categories,
  brands,
  locale,
  cards,
}: any) {
  return (
    <div className="homepage-sections">
      {sections.map((s: any, index: number) => {
        const title = field(s, "title", locale),
          body = field(s, "body", locale);
        if (s.kind === "hero")
          return <MarketplaceHero key={index} section={s} products={products} locale={locale} />;
        if (s.kind === "featured_products") {
          const ids = s.properties?.product_ids;
          return (
            <section className="home-section" key={index}>
              <div className="section-heading"><h2>{title}</h2>
                <Link className="view-all" href={`/${locale}/shop`}>{locale === "ar" ? "عرض الكل" : "View all"}</Link>
              </div>
              {body && <p className="section-description">{body}</p>}
              {cards(
                Array.isArray(ids)
                  ? products.filter((p: any) => ids.includes(p.id))
                  : products.slice(0, 8),
              )}
            </section>
          );
        }
        if (s.kind === "categories" || s.kind === "brands")
          return (
            <section className="home-section" key={index}>
              <h2>{title}</h2>
              <CategoryTiles rows={s.kind === "categories" ? categories : brands} locale={locale} kind={s.kind} icons={s.properties?.icons || {}} />
            </section>
          );
        return (
          <section className={s.kind === "promotion" || s.properties?.layout === "compact" ? "promotion-section" : "card home-section"} key={index}>
            <h2>{title}</h2>
            <p style={{ whiteSpace: "pre-wrap" }}>{body}</p>
            {s.kind === "text" && s.properties?.layout === "compact" && (
              <Link className="btn secondary" href={`/${locale}/shop`}>
                {locale === "ar" ? "تسوق الآن" : "Explore the collection"}<Icon name="arrow" size={17} />
              </Link>
            )}
            {s.kind === "promotion" && (
              <Link className="btn secondary" href={`/${locale}/offers`}>
                {locale === "ar" ? "استكشف العروض" : "Explore offers"}<Icon name="arrow" size={17} />
              </Link>
            )}
          </section>
        );
      })}
    </div>
  );
}
