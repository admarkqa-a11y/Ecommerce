"use client";
import { useEffect, useState } from "react";
import { api, post, field } from "@shared/api";
export function AccountTools({ locale, run, busy }: any) {
  const tx = (en: string, ar: string) => (locale === "ar" ? ar : en);
  const [rows, setRows] = useState<any[]>([]),
    [areas, setAreas] = useState<any[]>([]),
    [editing, setEditing] = useState(""),
    [label, setLabel] = useState(""),
    [line1, setLine1] = useState(""),
    [area, setArea] = useState(""),
    [password, setPassword] = useState(""),
    [current, setCurrent] = useState(""),
    [message, setMessage] = useState("");
  const refresh = async () => setRows(await api("/account/addresses"));
  useEffect(() => {
    run(async () => {
      await refresh();
      setAreas(await api("/store/delivery-areas"));
    });
  }, []);
  return (
    <div className="account-tools">
      <section className="card stack">
        <h2>{tx("Your addresses", "عناوينك")}</h2>
        {rows.map((a) => (
          <div className="between" key={a.id}>
            <span>
              <strong>{a.label}</strong>
              <br />
              {a.data.line1}
            </span>
            <div className="row">
              <button
                className="link"
                onClick={() => {
                  setEditing(a.id);
                  setLabel(a.label);
                  setLine1(a.data.line1);
                  setArea(a.data.area_id || "");
                }}
              >
                {tx("Edit", "تعديل")}
              </button>
              <button
                className="link"
                disabled={busy}
                onClick={() =>
                  run(async () => {
                    await api("/account/addresses/" + a.id, {
                      method: "DELETE",
                    });
                    await refresh();
                  })
                }
              >
                {tx("Delete", "حذف")}
              </button>
            </div>
          </div>
        ))}
        <form
          className="stack"
          onSubmit={(e) => {
            e.preventDefault();
            run(async () => {
              await api("/account/addresses" + (editing ? "/" + editing : ""), {
                method: editing ? "PATCH" : "POST",
                body: JSON.stringify({ label, data: { line1, area_id: area } }),
              });
              setEditing("");
              setLabel("");
              setLine1("");
              setArea("");
              await refresh();
            });
          }}
        >
          <label>
            {tx("Address label", "اسم العنوان")}
            <input
              required
              maxLength={60}
              value={label}
              onChange={(e) => setLabel(e.target.value)}
            />
          </label>
          <label>
            {tx("Street address", "عنوان الشارع")}
            <input
              required
              value={line1}
              onChange={(e) => setLine1(e.target.value)}
            />
          </label>
          <label>
            {tx("Delivery area", "منطقة التوصيل")}
            <select
              required
              value={area}
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
          <button disabled={busy} className="btn secondary">
            {editing
              ? tx("Save address", "حفظ العنوان")
              : tx("Add address", "إضافة عنوان")}
          </button>
          {editing && (
            <button
              type="button"
              className="link"
              onClick={() => {
                setEditing("");
                setLabel("");
                setLine1("");
                setArea("");
              }}
            >
              {tx("Cancel edit", "إلغاء التعديل")}
            </button>
          )}
        </form>
      </section>
      <section className="card">
        <h2>{tx("Change password", "تغيير كلمة المرور")}</h2>
        <form
          className="stack"
          onSubmit={(e) => {
            e.preventDefault();
            run(async () => {
              await post("/auth/password/change", {
                current_password: current,
                password,
              });
              setCurrent("");
              setPassword("");
              setMessage(tx("Password updated.", "تم تحديث كلمة المرور."));
            });
          }}
        >
          <label>
            {tx("Current password", "كلمة المرور الحالية")}
            <input
              required
              type="password"
              autoComplete="current-password"
              value={current}
              onChange={(e) => setCurrent(e.target.value)}
            />
          </label>
          <label>
            {tx("New password", "كلمة المرور الجديدة")}
            <input
              required
              minLength={12}
              type="password"
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </label>
          <button disabled={busy} className="btn secondary">
            {tx("Update password", "تحديث كلمة المرور")}
          </button>
          <p role="status">{message}</p>
        </form>
      </section>
    </div>
  );
}
export function PasswordReset({ locale, run, busy }: any) {
  const tx = (en: string, ar: string) => (locale === "ar" ? ar : en);
  const [email, setEmail] = useState(""),
    [password, setPassword] = useState(""),
    [params, setParams] = useState<URLSearchParams | null>(null),
    [sent, setSent] = useState(false);
  useEffect(() => setParams(new URLSearchParams(window.location.search)), []);
  const confirming = params?.has("uid") && params.has("token");
  return (
    <section className="auth-card card">
      <h1>{tx("Reset password", "إعادة تعيين كلمة المرور")}</h1>
      {sent ? (
        <p role="status">
          {confirming
            ? tx(
                "Your password was changed. You can sign in now.",
                "تم تغيير كلمة المرور. يمكنك تسجيل الدخول الآن.",
              )
            : tx(
                "If the address is eligible, a reset link will arrive shortly.",
                "إذا كان العنوان مؤهلاً، فسيصلك رابط إعادة التعيين قريباً.",
              )}
        </p>
      ) : (
        <form
          className="stack"
          onSubmit={(e) => {
            e.preventDefault();
            run(async () => {
              await post(
                confirming
                  ? "/auth/password/reset-confirm"
                  : "/auth/password/reset-request",
                confirming
                  ? {
                      uid: params?.get("uid"),
                      token: params?.get("token"),
                      password,
                    }
                  : { email },
              );
              setSent(true);
            });
          }}
        >
          <label>
            {confirming
              ? tx("New password", "كلمة المرور الجديدة")
              : tx("Email address", "البريد الإلكتروني")}
            <input
              required
              type={confirming ? "password" : "email"}
              autoComplete={confirming ? "new-password" : "email"}
              minLength={confirming ? 12 : undefined}
              value={confirming ? password : email}
              onChange={(e) =>
                confirming
                  ? setPassword(e.target.value)
                  : setEmail(e.target.value)
              }
            />
          </label>
          <button className="btn" disabled={busy}>
            {tx("Continue", "متابعة")}
          </button>
        </form>
      )}
      <a className="link" href={`/${locale}/login`}>
        {tx("Sign in", "تسجيل الدخول")}
      </a>
    </section>
  );
}
