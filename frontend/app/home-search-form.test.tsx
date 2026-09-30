import { afterEach, describe, expect, it } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { COUNTRY_OPTIONS } from "@/lib/country-filter";
import HomeSearchForm from "./home-search-form";

afterEach(cleanup);

function submittedSearch(form: HTMLFormElement) {
  const params = new URLSearchParams();
  for (const [key, value] of new FormData(form)) {
    params.append(key, String(value));
  }
  const query = params.toString();
  return query ? `${form.getAttribute("action")}?${query}` : "/search";
}

describe("home-page job search", () => {
  it("renders the centralized country options in an accessible select", () => {
    render(<HomeSearchForm />);

    const country = screen.getByLabelText("Country");
    const options = screen.getAllByRole<HTMLOptionElement>("option");

    expect(country.tagName).toBe("SELECT");
    expect(country.id).toBe("home-country-filter");
    expect(country).toHaveProperty("value", "");
    expect(screen.queryByPlaceholderText("Country")).toBeNull();
    expect(
      options.map(({ value, textContent }) => ({
        value,
        label: textContent,
      })),
    ).toEqual(COUNTRY_OPTIONS.map((option) => ({ ...option })));
  });

  it("submits keyword and selected country to the search page", () => {
    render(<HomeSearchForm />);

    fireEvent.change(
      screen.getByPlaceholderText("Job title, skill or keyword"),
      {
        target: { value: "engineer" },
      },
    );
    fireEvent.change(screen.getByLabelText("Country"), {
      target: { value: "Germany" },
    });

    const form = screen.getByRole<HTMLFormElement>("form", {
      name: "Search jobs",
    });
    expect(form.method).toBe("get");
    expect(submittedSearch(form)).toBe("/search?q=engineer&country=Germany");
  });

  it("omits the country parameter when All Countries is selected", () => {
    render(<HomeSearchForm />);

    fireEvent.change(
      screen.getByPlaceholderText("Job title, skill or keyword"),
      {
        target: { value: "engineer" },
      },
    );
    fireEvent.change(screen.getByLabelText("Country"), {
      target: { value: "Germany" },
    });
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
