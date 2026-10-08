import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import AccountClient from "./account-client";

const { getCurrentUserMock, updateProfileMock, changePasswordMock } =
  vi.hoisted(() => ({
    getCurrentUserMock: vi.fn(),
    updateProfileMock: vi.fn(),
    changePasswordMock: vi.fn(),
  }));

vi.mock("@/lib/services/auth", () => ({
  getCurrentUser: getCurrentUserMock,
  updateProfile: updateProfileMock,
  changePassword: changePasswordMock,
  AuthApiError: class AuthApiError extends Error {
    constructor(
      message: string,
      public readonly status: number,
    ) {
      super(message);
    }
  },
}));

import { AuthApiError } from "@/lib/services/auth";

const user = {
  user_id: "u1",
  full_name: "Alex Driver",
  username: "alex.driver",
  email: "alex@example.com",
  created_at: "2025-06-15T12:30:00Z",
  phone: null,
  address: null,
};

async function openEditor() {
  render(<AccountClient />);
  fireEvent.click(
    await screen.findByRole("button", { name: "Edit information" }),
  );
}

const profileForm = () =>
  within(screen.getByRole("form", { name: "Edit personal information" }));
const passwordForm = () =>
  within(screen.getByRole("form", { name: "Change password" }));
const field = (label: string) =>
  profileForm().getByLabelText(new RegExp(`^${label}`));

beforeEach(() => {
  getCurrentUserMock.mockResolvedValue(user);
});
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("editing personal information", () => {
  it("shows the saved details until Edit is pressed, and Cancel goes back", async () => {
    await openEditor();

    expect(field("Full name")).toHaveProperty("value", "Alex Driver");
    expect(profileForm().queryByLabelText(/^Current password/)).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(
      screen.getByRole("button", { name: "Edit information" }),
    ).toBeTruthy();
    expect(updateProfileMock).not.toHaveBeenCalled();
  });

  it("saves only what changed, shows the new details and confirms", async () => {
    updateProfileMock.mockResolvedValue({
      ...user,
      full_name: "Alex Q Driver",
      phone: "+61 412 345 678",
    });
    await openEditor();

    fireEvent.change(field("Full name"), {
      target: { value: "Alex Q Driver" },
    });
    fireEvent.change(field("Phone"), { target: { value: "+61 412 345 678" } });
    fireEvent.click(screen.getByRole("button", { name: "Save changes" }));

    await waitFor(() =>
      expect(updateProfileMock).toHaveBeenCalledWith({
        full_name: "Alex Q Driver",
        phone: "+61 412 345 678",
      }),
    );
    expect(
      await screen.findByText("Your information has been saved."),
    ).toBeTruthy();
    expect(screen.getByText("Alex Q Driver")).toBeTruthy();
    expect(screen.getByText("+61 412 345 678")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Save changes" })).toBeNull();
  });

  it("does not send a request when nothing changed", async () => {
    await openEditor();

    fireEvent.click(screen.getByRole("button", { name: "Save changes" }));

    expect(
      await screen.findByText("You haven't changed anything."),
    ).toBeTruthy();
    expect(updateProfileMock).not.toHaveBeenCalled();
  });

  it("shows field errors without calling the API", async () => {
    await openEditor();

    fireEvent.change(field("Full name"), { target: { value: " " } });
    fireEvent.change(field("Email"), { target: { value: "nope" } });
    fireEvent.click(screen.getByRole("button", { name: "Save changes" }));

    expect(await screen.findByText("Full name is required.")).toBeTruthy();
    expect(screen.getByText("Enter a valid email address.")).toBeTruthy();
    expect(field("Full name").getAttribute("aria-invalid")).toBe("true");
    expect(updateProfileMock).not.toHaveBeenCalled();
  });

  it("asks for the current password when the email changes and sends it", async () => {
    updateProfileMock.mockResolvedValue({ ...user, email: "new@example.com" });
    await openEditor();

    fireEvent.change(field("Email"), { target: { value: "new@example.com" } });
    expect(field("Current password")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Save changes" }));
    expect(
      await screen.findByText(
        "Enter your current password to change your email.",
      ),
    ).toBeTruthy();
    expect(updateProfileMock).not.toHaveBeenCalled();

    fireEvent.change(field("Current password"), {
      target: { value: "Secret!Pass123" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save changes" }));

    await waitFor(() =>
      expect(updateProfileMock).toHaveBeenCalledWith({
        email: "new@example.com",
        current_password: "Secret!Pass123",
      }),
    );
  });

  it("puts a wrong current password on that field", async () => {
    updateProfileMock.mockRejectedValue(
      new AuthApiError(
        "Current password is incorrect or required to change email",
        400,
      ),
    );
    await openEditor();

    fireEvent.change(field("Email"), { target: { value: "new@example.com" } });
    fireEvent.change(field("Current password"), { target: { value: "wrong" } });
    fireEvent.click(screen.getByRole("button", { name: "Save changes" }));

    const message = await screen.findByText(/Current password is incorrect/);
    expect(message.id).toBe("profile-current-password-error");
    expect(
      field("Current password").getAttribute("aria-describedby"),
    ).toContain("profile-current-password-error");
  });

  it("shows a taken email or username as a form error and keeps the form open", async () => {
    updateProfileMock.mockRejectedValue(
      new AuthApiError(
        "An account with that email or username already exists",
        409,
      ),
    );
    await openEditor();

    fireEvent.change(field("Username"), { target: { value: "taken.name" } });
    fireEvent.click(screen.getByRole("button", { name: "Save changes" }));

    expect((await screen.findByRole("alert")).textContent).toContain(
      "already exists",
    );
    expect(screen.getByRole("button", { name: "Save changes" })).toBeTruthy();
  });
});

describe("changing the password", () => {
  const fill = (current: string, next: string, confirm: string) => {
    const form = passwordForm();
    fireEvent.change(form.getByLabelText(/^Current password/), {
      target: { value: current },
    });
    fireEvent.change(form.getByLabelText(/^New password/), {
      target: { value: next },
    });
    fireEvent.change(form.getByLabelText(/^Confirm new password/), {
      target: { value: confirm },
    });
    fireEvent.click(screen.getByRole("button", { name: "Update password" }));
  };

  async function open() {
    render(<AccountClient />);
    await screen.findByRole("heading", { name: "Change password" });
  }

  it("validates before calling the API", async () => {
    await open();

    fill("Old!Password123", "short", "other");

    expect(
      await screen.findByText(/Password must be at least 12/),
    ).toBeTruthy();
    expect(screen.getByText("The passwords do not match.")).toBeTruthy();
    expect(changePasswordMock).not.toHaveBeenCalled();
  });

  it("changes the password, confirms and clears the fields", async () => {
    changePasswordMock.mockResolvedValue(undefined);
    await open();

    fill("Old!Password123", "New!Password456", "New!Password456");

    await waitFor(() =>
      expect(changePasswordMock).toHaveBeenCalledWith(
        "Old!Password123",
        "New!Password456",
      ),
    );
    expect(
      await screen.findByText("Your password has been updated."),
    ).toBeTruthy();
    expect(passwordForm().getByLabelText(/^Current password/)).toHaveProperty(
      "value",
      "",
    );
    expect(passwordForm().getByLabelText(/^New password/)).toHaveProperty(
      "value",
      "",
    );
  });

  it("shows a wrong current password on its field", async () => {
    changePasswordMock.mockRejectedValue(
      new AuthApiError("Current password is incorrect", 400),
    );
    await open();

    fill("Wrong!Password1", "New!Password456", "New!Password456");

    const message = await screen.findByText("Current password is incorrect");
    expect(message.id).toBe("password-current-error");
  });

  it("shows the too-many-attempts message", async () => {
    changePasswordMock.mockRejectedValue(
      new AuthApiError(
        "Too many incorrect passwords. Please try again later",
        429,
      ),
    );
    await open();

    fill("Wrong!Password1", "New!Password456", "New!Password456");

    expect((await screen.findByRole("alert")).textContent).toContain(
      "Too many incorrect passwords",
    );
  });
});
