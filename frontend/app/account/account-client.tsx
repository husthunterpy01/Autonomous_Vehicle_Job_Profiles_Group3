"use client";

import { useEffect, useState } from "react";
import { getCurrentUser } from "@/lib/services/auth";
import AccountView, { type AccountState } from "./account-view";
import PasswordForm from "./password-form";
import ProfileForm from "./profile-form";

export default function AccountClient() {
  const [state, setState] = useState<AccountState>({ status: "loading" });
  const [editing, setEditing] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

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

  return (
    <AccountView
      state={state}
      notice={notice}
      onEdit={() => {
        setNotice(null);
        setEditing(true);
      }}
      editor={
        editing && state.status === "success" ? (
          <ProfileForm
            user={state.user}
            onCancel={() => setEditing(false)}
            onSaved={(user) => {
              setState({ status: "success", user });
              setEditing(false);
              setNotice("Your information has been saved.");
            }}
          />
        ) : undefined
      }
    >
      <PasswordForm />
    </AccountView>
  );
}
