import type { Metadata } from "next";
import FavoritesClient from "./favorites-client";

export const metadata: Metadata = { title: "Favorites | AV Job Finder" };

export default function FavoritesPage() {
  return <FavoritesClient />;
}
