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
  it("associates the Country label with the native select and fetches the URL country", async () => {
    mocks.search = "country=Germany";

    render(<SearchClient />);

    const country = screen.getByLabelText("Country");
    expect(country.tagName).toBe("SELECT");
    expect(country.id).toBe("country-filter");
    expect(country).toHaveProperty("value", "Germany");
    expect(
      screen.getByRole("option", { name: "All Countries" }),
    ).toHaveProperty("value", "");
    await waitFor(() => {
      expect(mocks.getJobs).toHaveBeenCalledWith(
        expect.objectContaining({ location: "Germany" }),
      );
    });
  });

  it("updates the URL, preserves other filters, and fetches the selected country", async () => {
    mocks.search =
      "q=autonomy&category=category-id&country=Germany&sort=company&direction=desc";

    render(<SearchClient />);
    fireEvent.change(screen.getByLabelText("Country"), {
      target: { value: "Japan" },
    });

    expect(mocks.replace).toHaveBeenCalledWith(
      "/search?q=autonomy&category=category-id&country=Japan&sort=company&direction=desc",
    );
    await waitFor(
      () => {
        expect(mocks.getJobs).toHaveBeenCalledWith(
          expect.objectContaining({
            q: "autonomy",
            category_id: "category-id",
            location: "Japan",
            sort: { field: "company", direction: "desc" },
          }),
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
        expect.objectContaining({ location: undefined }),
      );
    });
  });
});
