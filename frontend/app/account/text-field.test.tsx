import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import TextField from "./text-field";
import AccountClient from "./account-client";

vi.mock("@/lib/services/auth", () => ({
  getCurrentUser: vi.fn().mockResolvedValue({
    user_id: "u1",
    full_name: "Alex Driver",
    username: "alex.driver",
    email: "alex@example.com",
    created_at: "2025-06-15T12:30:00Z",
  }),
  updateProfile: vi.fn(),
  changePassword: vi.fn(),
  AuthApiError: class AuthApiError extends Error {},
}));

afterEach(cleanup);

function password(label = "New password") {
  return render(
    <TextField
      id="pw"
      label={label}
      type="password"
      value="Secret!Pass123"
      onChange={() => {}}
    />,
  );
}

describe("password visibility", () => {
  it("hides the text by default and shows it when the eye is pressed", () => {
    password();
    const input = screen.getByLabelText(/^New password/) as HTMLInputElement;
    const eye = screen.getByRole("button", { name: "Show new password" });

    expect(input.type).toBe("password");
    expect(eye.getAttribute("aria-pressed")).toBeNull();

    fireEvent.click(eye);

    expect(input.type).toBe("text");
    // The name flips instead of a pressed state, so it is announced once.
    const hide = screen.getByRole("button", { name: "Hide new password" });
    expect(hide.getAttribute("aria-pressed")).toBeNull();
  });

  it("hides it again on the second press and keeps what was typed", () => {
    password();
    const input = screen.getByLabelText(/^New password/) as HTMLInputElement;

    fireEvent.click(screen.getByRole("button", { name: "Show new password" }));
    fireEvent.click(screen.getByRole("button", { name: "Hide new password" }));

    expect(input.type).toBe("password");
    expect(input.value).toBe("Secret!Pass123");
  });

  it("does not read the required marker aloud", () => {
    render(
      <TextField
        id="n"
        label="Full name"
        required
        value=""
        onChange={() => {}}
      />,
    );

    expect(screen.getByLabelText(/^Full name/).hasAttribute("required")).toBe(
      true,
    );
    expect(screen.getByText("*").getAttribute("aria-hidden")).toBe("true");
  });

  it("is named after its own field", () => {
    password("Confirm new password");

    expect(
      screen.getByRole("button", { name: "Show confirm new password" }),
    ).toBeTruthy();
  });

  it("is not added to ordinary fields", () => {
    render(
      <TextField id="name" label="Full name" value="A" onChange={() => {}} />,
    );

    expect(screen.queryByRole("button")).toBeNull();
  });
});

describe("the account page", () => {
  it("gives each password field its own independent eye", async () => {
    render(<AccountClient />);
    await screen.findByRole("heading", { name: "Change password" });

    const eyes = screen.getAllByRole("button", { name: /^Show .*password$/ });
    expect(eyes).toHaveLength(3);

    fireEvent.click(screen.getByRole("button", { name: "Show new password" }));

    expect(
      (screen.getByLabelText(/^New password/) as HTMLInputElement).type,
    ).toBe("text");
    expect(
      (screen.getByLabelText(/^Current password/) as HTMLInputElement).type,
    ).toBe("password");
    expect(
      (screen.getByLabelText(/^Confirm new password/) as HTMLInputElement).type,
    ).toBe("password");
  });
});
