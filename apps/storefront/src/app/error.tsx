"use client";
export default function ErrorPage({ reset }: { reset: () => void }) {
  return (
    <main className="empty" role="alert">
      <h1>
        Something went wrong
        <br />
        حدث خطأ
      </h1>
      <button className="btn" onClick={reset}>
        Try again · أعد المحاولة
      </button>
    </main>
  );
}
