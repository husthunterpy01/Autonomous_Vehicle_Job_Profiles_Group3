import assert from "node:assert/strict";
import { test } from "node:test";
import {
  buildProfileUpdate,
  emailChanged,
  profileValuesFrom,
  validatePasswordChange,
  validateProfile,
} from "./account-validation.ts";

const user = {
  full_name: "Alex Driver",
  username: "alex.driver",
  email: "alex@example.com",
  phone: "+61 412 345 678",
  address: "Perth, WA",
};
const values = () => profileValuesFrom(user);

test("untouched values produce no update and no errors", () => {
  assert.equal(buildProfileUpdate(user, values(), ""), null);
  assert.deepEqual(validateProfile(user, values(), ""), {});
});

test("only changed fields are sent", () => {
  const next = { ...values(), full_name: "Alex  Q Driver", address: "Sydney" };
  assert.deepEqual(buildProfileUpdate(user, next, ""), {
    full_name: "Alex Q Driver",
    address: "Sydney",
  });
});

test("case and spacing differences alone are not changes", () => {
  const next = {
    ...values(),
    username: "  ALEX.DRIVER ",
    email: " Alex@Example.com ",
    phone: "+61  412 345 678",
  };
  assert.equal(buildProfileUpdate(user, next, ""), null);
  assert.equal(emailChanged(user, next), false);
});

test("clearing phone or address sends null", () => {
  const next = { ...values(), phone: "  ", address: "" };
  assert.deepEqual(buildProfileUpdate(user, next, ""), {
    phone: null,
    address: null,
  });
});

test("a missing phone and address stay unchanged when left empty", () => {
  const bare = { full_name: "A B", username: "ab1", email: "a@b.co" };
  assert.equal(buildProfileUpdate(bare, profileValuesFrom(bare), ""), null);
});

test("changing the email needs the current password and sends it", () => {
  const next = { ...values(), email: "new@example.com" };
  assert.equal(
    validateProfile(user, next, "").current_password,
    "Enter your current password to change your email.",
  );
  assert.deepEqual(validateProfile(user, next, "Secret!Pass123"), {});
  assert.deepEqual(buildProfileUpdate(user, next, "Secret!Pass123"), {
    email: "new@example.com",
    current_password: "Secret!Pass123",
  });
});

test("the current password is not sent when the email is unchanged", () => {
  const next = { ...values(), full_name: "Alex D" };
  const update = buildProfileUpdate(user, next, "Secret!Pass123");
  assert.equal(update && "current_password" in update, false);
});

test("profile fields are validated like the backend does", () => {
  const errors = validateProfile(
    user,
    {
      full_name: " ",
      username: "a b",
      email: "not-an-email",
      phone: "letters",
      address: "x".repeat(501),
    },
    "",
  );
  assert.deepEqual(Object.keys(errors).sort(), [
    "address",
    "email",
    "full_name",
    "phone",
    "username",
  ]);
});

test("an invalid email reports the format, not the missing password", () => {
  const errors = validateProfile(user, { ...values(), email: "nope" }, "");
  assert.ok(errors.email);
  assert.equal(errors.current_password, undefined);
});

test("a new password must be strong, different and confirmed", () => {
  assert.deepEqual(
    validatePasswordChange(
      "Old!Password123",
      "New!Password456",
      "New!Password456",
    ),
    {},
  );
  assert.ok(
    validatePasswordChange("", "New!Password456", "New!Password456")
      .current_password,
  );
  assert.ok(
    validatePasswordChange("Old!Password123", "short", "short").new_password,
  );
  assert.ok(
    validatePasswordChange(
      "Old!Password123",
      "alllowercase1234",
      "alllowercase1234",
    ).new_password,
  );
  assert.equal(
    validatePasswordChange(
      "Same!Password123",
      "Same!Password123",
      "Same!Password123",
    ).new_password,
    "Choose a password different from the current one.",
  );
  assert.equal(
    validatePasswordChange(
      "Old!Password123",
      "New!Password456",
      "Other!Password789",
    ).confirm_password,
    "The passwords do not match.",
  );
  assert.ok(
    validatePasswordChange("Old!Password123", "New!Password456", "")
      .confirm_password,
  );
});
