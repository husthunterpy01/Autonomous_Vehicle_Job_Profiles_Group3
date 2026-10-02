import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import SearchClient from "./search-client";

const mocks = vi.hoisted(() => ({
  getJobs: vi.fn(),
  getJobCountries: vi.fn(),
  getCategoryStatsRaw: vi.fn(),
  replace: vi.fn(),
  push: vi.fn(),
  search: "",
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: mocks.replace, push: mocks.push }),
  useSearchParams: () => new URLSearchParams(mocks.search),
}));

vi.mock("@/lib/services/home", () => ({
  getCategoryStatsRaw: mocks.getCategoryStatsRaw,
}));

vi.mock("@/lib/services/job", () => ({
  getJobs: mocks.getJobs,
  getJobCountries: mocks.getJobCountries,
}));

vi.mock("@/lib/services/favorite", () => ({
  addFavoriteJob: vi.fn(),
  removeFavoriteJob: vi.fn(),
}));

const emptyJobsResponse = {
  items: [],
  total: 0,
  page: 1,
  page_size: 6,
  total_pages: 0,
};

beforeEach(() => {
  mocks.search = "";
  mocks.getJobs.mockResolvedValue(emptyJobsResponse);
  mocks.getJobCountries.mockResolvedValue([
    { country: "Japan", job_count: 5 },
    { country: "Germany", job_count: 7 },
  ]);
  mocks.getCategoryStatsRaw.mockResolvedValue([
    {
      category_id: "category-id",
      sub_type: "Planning",
      main_type: "Planning & Decision-Making",
      job_count: 3,
    },
  ]);
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("country filter", () => {
  it("lists countries with jobs, most first, and fetches the URL country exactly", async () => {
    mocks.search = "country=Germany";

    render(<SearchClient />);

    const country = screen.getByLabelText("Country");
    expect(country.tagName).toBe("SELECT");
    expect(country.id).toBe("country-filter");
    await screen.findByRole("option", { name: "Germany (7)" });
    expect(
      screen
        .getAllByRole<HTMLOptionElement>("option")
        .filter((option) => option.closest("#country-filter"))
        .map((option) => [option.value, option.textContent]),
    ).toEqual([
      ["", "All Countries"],
      ["Germany", "Germany (7)"],
      ["Japan", "Japan (5)"],
    ]);
    expect(country).toHaveProperty("value", "Germany");
    await waitFor(() => {
      expect(mocks.getJobs).toHaveBeenCalledWith(
        expect.objectContaining({ country: "Germany" }),
        expect.any(AbortSignal),
      );
    });
  });

  it("drops a URL country that no longer has jobs", async () => {
    mocks.search = "country=Atlantis";

    render(<SearchClient />);

    await screen.findByRole("option", { name: "Germany (7)" });
    expect(screen.getByLabelText("Country")).toHaveProperty("value", "");
    await waitFor(() => {
      expect(mocks.getJobs).toHaveBeenLastCalledWith(
        expect.objectContaining({ country: undefined }),
        expect.any(AbortSignal),
      );
    });
  });

  it("keeps the search bar for the keyword only, with the filters in their own row", () => {
    render(<SearchClient />);

    const filters = screen.getByRole("group", { name: "Filters" });
    expect(filters.contains(screen.getByLabelText("Category"))).toBe(true);
    expect(filters.contains(screen.getByLabelText("Country"))).toBe(true);
    const searchBar = screen
      .getByPlaceholderText("Job title, skill or keyword")
      .closest("form")!;
    expect(searchBar.contains(screen.getByLabelText("Category"))).toBe(false);
  });

  it("a picked country only takes effect on Apply", async () => {
    render(<SearchClient />);
    await screen.findByRole("option", { name: "Japan (5)" });
    const apply = screen.getByRole("button", { name: "Apply" });
    expect(apply).toHaveProperty("disabled", true);

    fireEvent.change(screen.getByLabelText("Country"), {
      target: { value: "Japan" },
    });
    expect(apply).toHaveProperty("disabled", false);
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(mocks.getJobs).not.toHaveBeenCalledWith(
      expect.objectContaining({ country: "Japan" }),
      expect.any(AbortSignal),
    );

    fireEvent.click(apply);
    await waitFor(() => {
      expect(mocks.getJobs).toHaveBeenCalledWith(
        expect.objectContaining({ country: "Japan" }),
        expect.any(AbortSignal),
      );
    });
    expect(apply).toHaveProperty("disabled", true);
  });

  it("Clear in the filter row resets category and country but keeps the keyword", async () => {
    mocks.search = "q=lidar&category=category-id&country=Germany";

    render(<SearchClient />);
    await screen.findByRole("option", { name: "Germany (7)" });
    fireEvent.click(screen.getByRole("button", { name: "Clear" }));

    expect(screen.getByLabelText("Country")).toHaveProperty("value", "");
    expect(mocks.replace).toHaveBeenLastCalledWith("/search?q=lidar");
    expect(screen.getByRole("button", { name: "Clear" })).toHaveProperty(
      "disabled",
      true,
    );
  });

  it("Apply updates the URL, preserves other filters, and fetches the selected country", async () => {
    mocks.search =
      "q=autonomy&category=category-id&country=Germany&sort=company&direction=desc";

    render(<SearchClient />);
    await screen.findByRole("option", { name: "Japan (5)" });
    fireEvent.change(screen.getByLabelText("Country"), {
      target: { value: "Japan" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Apply" }));

    expect(mocks.replace).toHaveBeenCalledWith(
      "/search?q=autonomy&category=category-id&country=Japan&sort=company&direction=desc",
    );
    await waitFor(
      () => {
        expect(mocks.getJobs).toHaveBeenCalledWith(
          expect.objectContaining({
            q: "autonomy",
            category_id: "category-id",
            country: "Japan",
            sort: { field: "company", direction: "desc" },
          }),
          expect.any(AbortSignal),
        );
      },
      { timeout: 1000 },
    );
  });

  it("Clear filters resets Country and removes all browser filters", async () => {
    mocks.search = "country=Germany";

    render(<SearchClient />);
    const clearFilters = await screen.findByRole("button", {
      name: "Clear filters",
    });
    fireEvent.click(clearFilters);

    expect(screen.getByLabelText("Country")).toHaveProperty("value", "");
    expect(mocks.replace).toHaveBeenCalledWith("/search");
    await waitFor(() => {
      expect(mocks.getJobs).toHaveBeenCalledWith(
        expect.objectContaining({ country: undefined }),
        expect.any(AbortSignal),
      );
    });
  });
});
