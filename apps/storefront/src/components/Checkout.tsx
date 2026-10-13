"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api, post, cash, field } from "@shared/api";
import { messages, Locale } from "@i18n";
export default function Checkout({
  cfg,
  locale,
  bag,
  setBag,
  run,
  busy,
  user,
}: any) {
  const t = messages[locale as Locale],
    tx = (en: string, ar: string) => (locale === "ar" ? ar : en);
  const [methods, setMethods] = useState<any[]>([]),
    [areas, setAreas] = useState<any[]>([]),
    [addresses, setAddresses] = useState<any[]>([]),
    [saved, setSaved] = useState("");
  const [method, setMethod] = useState(""),
    [area, setArea] = useState(""),
    [coupon, setCoupon] = useState(bag.coupon || ""),
    [payment, setPayment] = useState(
      cfg.cod_enabled
        ? "cod"
        : cfg.bank_enabled
          ? "bank"
          : cfg.card_enabled
            ? "card"
            : "",
    );
  const [quote, setQuote] = useState<any>(null),
    [order, setOrder] = useState<any>(null),
    [tick, setTick] = useState(Date.now());
  const [contact, setContact] = useState({
    name: user?.name || "",
    email: user?.email || "",
    phone: "",
    line1: "",
  });
  useEffect(() => {
    run(async () => {
      setMethods(await api("/store/delivery-methods"));
      setAreas(await api("/store/delivery-areas"));
      if (user) setAddresses(await api("/account/addresses"));
    });
  }, []);
  useEffect(() => {
    setQuote(null);
  }, [method, area, bag.version]);
  useEffect(() => {
    const id = setInterval(() => setTick(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);
  const current = methods.find((m) => m.id === method),
    expired = quote && new Date(quote.expires_at).getTime() <= tick;
  const hasItems = bag.items.length || bag.bundles?.length;
  if (order)
    return (
      <section className="card success-card" aria-live="polite">
        <span>✓</span>
        <h1>
          {order.payment_state === "paid_exception"
            ? tx("Payment needs review", "الدفع يحتاج إلى مراجعة")
            : order.state === "cancelled"
              ? tx("This order was cancelled", "تم إلغاء هذا الطلب")
              : order.state === "pending"
                ? t.pending
                : t.success}
        </h1>
        <p>{order.number}</p>
        <p className="money">{cash(order.total, cfg.currency, locale)}</p>
        {order.payment_method === "bank" && (
          <p style={{ whiteSpace: "pre-wrap" }}>{cfg.bank_instructions}</p>
        )}
        {order.payment_method === "card" && (
          <>
            <p>
              {tx(
                "Your order is saved. Payment is confirmed only after verification by the payment provider.",
                "تم حفظ طلبك. يتم تأكيد الدفع بعد التحقق من مزود الدفع فقط.",
              )}
            </p>
            {order.state === "pending" && order.payment?.checkout_url ? (
              <a className="btn" href={order.payment.checkout_url}>
                {tx(
                  "Continue to secure card payment",
                  "المتابعة إلى الدفع الآمن بالبطاقة",
                )}
              </a>
            ) : (
              <p role="status">
                {tx(
                  "Payment is being checked. Do not place another order. Check your order status or contact the store.",
                  "جارٍ التحقق من الدفع. لا تنشئ طلباً آخر. راجع حالة طلبك أو تواصل مع المتجر.",
                )}
              </p>
            )}
          </>
        )}
        <div
          className="row"
          style={{ justifyContent: "center", marginTop: 22 }}
        >
          <Link className="btn secondary" href={`/${locale}/orders`}>
            {t.orders}
          </Link>
          <Link className="btn secondary" href={`/${locale}/shop`}>
            {t.continue}
          </Link>
        </div>
      </section>
    );
  if (!hasItems)
    return (
      <div className="empty">
        <h1>{t.empty}</h1>
        <Link className="btn" href={`/${locale}/shop`}>
          {t.explore}
        </Link>
      </div>
    );
  return (
    <>
      <div className="page-heading">
        <span className="eyebrow">{tx("One last step", "الخطوة الأخيرة")}</span>
        <h1>{t.checkout}</h1>
      </div>
      <form
        className="checkout-layout"
        onSubmit={(e) => {
          e.preventDefault();
          if (!quote || expired) return;
          run(async () => {
            const result = await post(
              "/checkout/orders",
              {
                quote_id: quote.id,
                payment_method: payment,
                contact: {
                  name: contact.name,
                  email: contact.email,
                  phone: contact.phone,
                },
                ...(saved
                  ? { address_id: saved }
                  : { address: { line1: contact.line1 } }),
              },
              { "Idempotency-Key": quote.id },
            );
            setOrder(result);
            setBag({ items: [], bundles: [] });
          });
        }}
      >
        <div className="stack">
          <section className="card">
            <h2>{t.contact}</h2>
            <div className="form-grid">
              {["name", "email", "phone"].map((k) => (
                <label key={k}>
                  {(t as any)[k]}
                  <input
                    required
                    autoComplete={
                      k === "name" ? "name" : k === "email" ? "email" : "tel"
                    }
                    type={
                      k === "email" ? "email" : k === "phone" ? "tel" : "text"
                    }
                    value={(contact as any)[k]}
                    onChange={(e) =>
                      setContact({ ...contact, [k]: e.target.value })
                    }
                  />
                </label>
              ))}
            </div>
          </section>
          <section className="card stack">
            <h2>{t.delivery}</h2>
            <label>
              {t.select}
              <select
                required
                value={method}
                onChange={(e) => setMethod(e.target.value)}
              >
                <option value="">—</option>
                {methods.map((m) => (
                  <option key={m.id} value={m.id}>
                    {field(m, "name", locale)}
                  </option>
                ))}
              </select>
            </label>
            {current?.kind === "pickup" ? (
              <p>{current.pickup_address}</p>
            ) : (
              <>
                {addresses.length > 0 && (
                  <label>
                    {tx("Saved address", "عنوان محفوظ")}
                    <select
                      value={saved}
                      onChange={(e) => {
                        setSaved(e.target.value);
                        const a = addresses.find(
                          (a) => a.id === e.target.value,
                        );
                        if (a) {
                          setArea(a.data.area_id || "");
                          setContact((c) => ({
                            ...c,
                            line1: a.data.line1,
                            phone: c.phone || a.data.phone || "",
                          }));
                        }
                      }}
                    >
                      <option value="">
                        {tx("Use another address", "استخدام عنوان آخر")}
                      </option>
                      {addresses.map((a) => (
                        <option key={a.id} value={a.id}>
                          {a.label} — {a.data.line1}
                        </option>
                      ))}
                    </select>
                  </label>
                )}
                <label>
                  {tx("Delivery area", "منطقة التوصيل")}
                  <select
                    required
                    value={area}
                    disabled={!!saved}
                    onChange={(e) => setArea(e.target.value)}
                  >
                    <option value="">—</option>
                    {areas.map((a) => (
                      <option key={a.id} value={a.id}>
                        {field(a, "name", locale)}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  {t.address}
                  <input
                    required
                    disabled={!!saved}
                    autoComplete="street-address"
                    value={contact.line1}
                    onChange={(e) =>
                      setContact({ ...contact, line1: e.target.value })
                    }
                  />
                </label>
              </>
            )}
            <p className="field-help">
              {tx(
                "Availability, cutoffs and delivery fees are checked when calculating your total.",
                "يتم التحقق من التوفر ومواعيد الطلب ورسوم التوصيل عند حساب الإجمالي.",
              )}
            </p>
          </section>
          <section className="card stack">
            <h2>{tx("Payment method", "طريقة الدفع")}</h2>
            <select
              aria-label={tx("Payment method", "طريقة الدفع")}
              required
              value={payment}
              onChange={(e) => setPayment(e.target.value)}
            >
              <option value="">—</option>
              {cfg.cod_enabled && <option value="cod">{t.cod}</option>}
              {cfg.bank_enabled && <option value="bank">{t.bank}</option>}
              {cfg.card_enabled && (
                <option value="card">
                  {tx("Credit / debit card", "بطاقة ائتمان / خصم")}
                </option>
              )}
            </select>
            {payment === "bank" && (
              <p style={{ whiteSpace: "pre-wrap" }}>{cfg.bank_instructions}</p>
            )}
            {payment === "card" && (
              <p>
                {tx(
                  "Card details are entered securely on the payment provider’s page.",
                  "يتم إدخال تفاصيل البطاقة بأمان على صفحة مزود الدفع.",
                )}
              </p>
            )}
          </section>
        </div>
        <aside className="card summary stack">
          <h2>{t.cart}</h2>
          {bag.items.map((i: any) => (
            <div className="between" key={i.id}>
              <span>
                {field(i, "name", locale)} × {i.quantity}
              </span>
              <small>
                {cash(Number(i.price) * i.quantity, cfg.currency, locale)}
              </small>
            </div>
          ))}
          {bag.bundles?.map((b: any) => (
            <p key={b.id}>
              {tx("Selected bundle", "باقة مختارة")} × {b.quantity}
            </p>
          ))}
          <div className="row">
            <input
              placeholder={t.coupon}
              aria-label={t.coupon}
              value={coupon}
              onChange={(e) => setCoupon(e.target.value)}
            />
            <button
              type="button"
              className="btn secondary small"
              disabled={busy}
              onClick={() =>
                run(async () =>
                  setBag(
                    await api("/cart", {
                      method: "PATCH",
                      body: JSON.stringify({ coupon }),
                    }),
                  ),
                )
              }
            >
              {t.apply}
            </button>
          </div>
          {quote && (
            <>
              {[
                ["subtotal", quote.gross],
                ["discount", quote.discount],
                ["delivery", quote.delivery_fee],
                ["total", quote.total],
              ].map(([label, value]) => (
                <div className="between" key={label}>
                  <span>{(t as any)[label]}</span>
                  <strong>{cash(value, cfg.currency, locale)}</strong>
                </div>
              ))}
              <p role="status" className={expired ? "error" : "field-help"}>
                {expired
                  ? tx(
                      "Your quote has expired. Calculate again.",
                      "انتهت صلاحية عرض السعر. أعد الحساب.",
                    )
                  : tx(
                      "Prices and availability are reserved when you place your order.",
                      "يتم حجز الأسعار والتوفر عند تأكيد الطلب.",
                    )}
              </p>
            </>
          )}
          <button
            type="button"
            className="btn secondary"
            disabled={!method || busy || (current?.kind !== "pickup" && !area)}
            onClick={() =>
              run(async () =>
                setQuote(
                  await post("/checkout/quote", {
                    method_id: method,
                    area_id: current?.kind === "pickup" ? null : area,
                  }),
                ),
              )
            }
          >
            {t.quote}
          </button>
          <button
            className="btn"
            disabled={!quote || expired || busy || !payment}
          >
            {busy ? tx("Please wait…", "يرجى الانتظار…") : t.place}
          </button>
        </aside>
      </form>
    </>
  );
}
