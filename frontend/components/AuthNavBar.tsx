"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import NavBar from "@/components/NavBar";
import { getCurrentUser, signOut, type AuthUser } from "@/lib/services/auth";

export default function AuthNavBar() {
  const router = useRouter();
  const [user, setUser] = useState<AuthUser | null>(null);

  useEffect(() => {
    let active = true;
    const refreshUser = () => {
      void getCurrentUser()
        .then((currentUser) => {
          if (active) setUser(currentUser);
        })
        .catch(() => {
          if (active) setUser(null);
        });
    };

    refreshUser();
    window.addEventListener("auth-changed", refreshUser);
    return () => {
      active = false;
      window.removeEventListener("auth-changed", refreshUser);
    };
  }, []);

  async function handleLogout() {
    try {
      await signOut();
    } finally {
      setUser(null);
      router.push("/");
      router.refresh();
    }
  }

  if (!user) {
    return <NavBar />;
  }

  return (
    <NavBar
      user={{ displayName: user.full_name }}
      changeInformationHref="/account"
      favoriteListHref="/favorites"
      onLogout={handleLogout}
    />
  );
}
