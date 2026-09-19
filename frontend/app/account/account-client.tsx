"use client";

import { useEffect, useState } from "react";
import { getCurrentUser } from "@/lib/services/auth";
import AccountView, { type AccountState } from "./account-view";

export default function AccountClient() {
  const [state, setState] = useState<AccountState>({ status: "loading" });

  useEffect(() => {
    let active = true;

    void getCurrentUser()
      .then((user) => {
        if (active) setState({ status: "success", user });
      })
      .catch(() => {
        if (active) setState({ status: "error" });
      });

    return () => {
      active = false;
    };
  }, []);

  return <AccountView state={state} />;
}
