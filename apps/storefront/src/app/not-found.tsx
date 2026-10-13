import Link from "next/link";
export default function NotFound() {
  return (
    <main className="empty">
      <h1>404</h1>
      <p>Page not found · الصفحة غير موجودة</p>
      <Link className="btn" href="/en">
        Back to store · العودة للمتجر
      </Link>
    </main>
  );
}
