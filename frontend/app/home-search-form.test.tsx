import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import HomeSearchForm from "./home-search-form";

const mocks = vi.hoisted(() => ({ getJobCountries: vi.fn() }));

vi.mock("@/lib/services/job", () => ({
  getJobCountries: mocks.getJobCountries,
}));

beforeEach(() => {
  mocks.getJobCountries.mockResolvedValue([
    { country: "Germany", job_count: 7 },
    { country: "United States", job_count: 770 },
  ]);
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

function submittedSearch(form: HTMLFormElement) {
  const params = new URLSearchParams();
  for (const [key, value] of new FormData(form)) {
    params.append(key, String(value));
  }
  const query = params.toString();
  return query ? `${form.getAttribute("action")}?${query}` : "/search";
}

async function chooseGermany() {
  await screen.findByRole("option", { name: "Germany (7)" });
  fireEvent.change(screen.getByLabelText("Country"), {
    target: { value: "Germany" },
  });
}

describe("home-page job search", () => {
  it("lists the countries that have jobs in an accessible select", async () => {
    render(<HomeSearchForm />);

    const country = screen.getByLabelText("Country");
    expect(country.tagName).toBe("SELECT");
    expect(country.id).toBe("home-country-filter");
    expect(country).toHaveProperty("value", "");
    expect(screen.queryByPlaceholderText("Country")).toBeNull();

    await screen.findByRole("option", { name: "Germany (7)" });
    expect(
      screen
        .getAllByRole<HTMLOptionElement>("option")
        .map(({ value, textContent }) => [value, textContent]),
    ).toEqual([
      ["", "All Countries"],
      ["United States", "United States (770)"],
      ["Germany", "Germany (7)"],
    ]);
  });

  it("keeps working with only All Countries when the list fails to load", async () => {
    mocks.getJobCountries.mockRejectedValue(new Error("offline"));
    render(<HomeSearchForm />);

    await Promise.resolve();
    expect(
      screen.getAllByRole("option").map((option) => option.textContent),
    ).toEqual(["All Countries"]);
  });

  it("submits keyword and selected country to the search page", async () => {
    render(<HomeSearchForm />);

    fireEvent.change(
      screen.getByPlaceholderText("Job title, skill or keyword"),
      {
        target: { value: "engineer" },
      },
    );
    await chooseGermany();

    const form = screen.getByRole<HTMLFormElement>("form", {
      name: "Search jobs",
    });
    expect(form.method).toBe("get");
    expect(submittedSearch(form)).toBe("/search?q=engineer&country=Germany");
  });

  it("omits the country parameter when All Countries is selected", async () => {
    render(<HomeSearchForm />);

    fireEvent.change(
      screen.getByPlaceholderText("Job title, skill or keyword"),
      {
        target: { value: "engineer" },
      },
    );
    await chooseGermany();
    fireEvent.change(screen.getByLabelText("Country"), {
      target: { value: "" },
    });

    const form = screen.getByRole<HTMLFormElement>("form", {
      name: "Search jobs",
    });
    expect(submittedSearch(form)).toBe("/search?q=engineer");
    expect(new FormData(form).has("country")).toBe(false);
  });
});
