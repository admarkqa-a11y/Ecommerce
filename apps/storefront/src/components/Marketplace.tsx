import Link from "next/link";
import { CSSProperties } from "react";
import { field, safeImage } from "@shared/api";
import { Icon } from "@shared/Icon";

// Keep text legible for both bright and dark merchant brand colors.
export function brandTheme(primary: string, accent: string): CSSProperties {
  const color = /^#[0-9a-f]{6}$/i.test(primary || "") ? primary : "#ffe600";
  const channels = [1, 3, 5].map((i) => {
    const c = parseInt(color.slice(i, i + 2), 16) / 255;
    return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  const luminance = channels[0] * 0.2126 + channels[1] * 0.7152 + channels[2] * 0.0722;
  const darkText = luminance > 0.179;
  return {
    "--primary": color,
    "--accent": /^#[0-9a-f]{6}$/i.test(accent || "") ? accent : "#e7e7ff",
    "--on-brand": darkText ? "#000000" : "#ffffff",
    "--action": darkText ? "#252641" : color,
  } as CSSProperties;
}

export function MarketplaceHero({ section, products = [], locale }: any) {
  const image = safeImage(section.properties?.image_url);
  return <section className="hero marketplace-hero">
    <div className="hero-copy">
      <div className="eyebrow">{locale === "ar" ? "اكتشف منتجاتك المفضلة" : "Discover your next favourite"}</div>
      <h1>{field(section, "title", locale)}</h1>
      {field(section, "body", locale) && <p>{field(section, "body", locale)}</p>}
      <Link className="btn" href={`/${locale}/shop`}>
        {locale === "ar" ? "استكشف المجموعة" : "Explore the collection"}<Icon name="arrow" size={18} />
      </Link>
    </div>
    <div className={"hero-art" + (image ? " has-image" : "")}>
      {image ? <img src={image} alt={field(section.properties, "image_alt", locale)} fetchPriority="high" /> :
        (products.length ? products.slice(0, 2) : [{ id: "empty" }]).map((p: any, i: number) =>
          <div className={`hero-product hero-product-${i}`} key={p.id}>
            {safeImage(p.image_url) ? <img src={safeImage(p.image_url)} alt={field(p, "name", locale)} /> : <Icon name="box" size={85} />}
            {p.name && <span>{field(p, "name", locale)}</span>}
          </div>)}
    </div>
  </section>;
}

export function CategoryTiles({ rows, locale, kind = "categories", icons = {} }: any) {
  return <div className="category-strip">
    {rows.map((r: any) => <Link className="category-tile" key={r.id}
      href={`/${locale}/shop?${kind === "brands" ? "brand=" + encodeURIComponent(r.id) : "category=" + encodeURIComponent(r.code)}`}>
      <span className="category-art"><Icon name={icons[r.code] || (kind === "brands" ? "tag" : "grid")} size={32} /></span>
      <span>{field(r, "name", locale)}</span>
    </Link>)}
  </div>;
}
