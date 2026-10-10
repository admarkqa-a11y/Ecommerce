import { api } from "./api";
/** Follow pages by local page number, never a server-provided foreign URL. */
export async function allResources(resource: string) {
  const rows: any[] = [];
  for (let page = 1; page <= 1000; page++) {
    const result = await api("/admin/" + resource + "?page=" + page);
    rows.push(...result.results);
    if (!result.next) return rows;
  }
  throw new Error(
    "Too many choices to load. Use the API or narrow the catalog.",
  );
}
