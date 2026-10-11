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
  getJobSeniorityLevels: vi.fn(),
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
  getJobSeniorityLevels: mocks.getJobSeniorityLevels,
  SENIORITY_LEVEL_LABELS: {
    1: "Junior",
    2: "Mid-level",
    3: "Senior",
    6: "Manager",
  } as Record<number, string>,
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
  mocks.getJobSeniorityLevels.mockResolvedValue([
    { seniority_level: 3, job_count: 12 },
    { seniority_level: 1, job_count: 4 },
    { seniority_level: 2, job_count: 30 },
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

describe("salary filter", () => {
  it("strips non-digit characters as the user types, before Apply", () => {
    render(<SearchClient />);

    fireEvent.change(screen.getByLabelText("Min salary (USD/yr)"), {
      target: { value: "$60,000.50" },
    });

    expect(screen.getByLabelText("Min salary (USD/yr)")).toHaveProperty(
      "value",
      "6000050",
    );
  });

  it("only takes effect on Apply, same as category and country", async () => {
    render(<SearchClient />);
    const apply = screen.getByRole("button", { name: "Apply" });
    expect(apply).toHaveProperty("disabled", true);

    fireEvent.change(screen.getByLabelText("Min salary (USD/yr)"), {
      target: { value: "60000" },
    });
    fireEvent.change(screen.getByLabelText("Max salary (USD/yr)"), {
      target: { value: "100000" },
    });
    expect(apply).toHaveProperty("disabled", false);
    expect(mocks.getJobs).not.toHaveBeenCalledWith(
      expect.objectContaining({ salary_min: 60000 }),
      expect.any(AbortSignal),
    );

    fireEvent.click(apply);

    await waitFor(() => {
      expect(mocks.getJobs).toHaveBeenCalledWith(
        expect.objectContaining({ salary_min: 60000, salary_max: 100000 }),
        expect.any(AbortSignal),
      );
    });
    expect(mocks.replace).toHaveBeenCalledWith(
      "/search?salary_min=60000&salary_max=100000",
    );
  });

  it("shows an inline error and disables Apply when min > max, before it's ever submitted", () => {
    render(<SearchClient />);
    mocks.getJobs.mockClear();

    fireEvent.change(screen.getByLabelText("Min salary (USD/yr)"), {
      target: { value: "100000" },
    });
    fireEvent.change(screen.getByLabelText("Max salary (USD/yr)"), {
      target: { value: "60000" },
    });

    screen.getByText("Minimum salary must not be greater than the maximum.");
    expect(screen.getByRole("button", { name: "Apply" })).toHaveProperty(
      "disabled",
      true,
    );
    expect(mocks.getJobs).not.toHaveBeenCalled();
  });

  it("Clear in the filter row resets the salary draft too", async () => {
    mocks.search = "salary_min=60000&salary_max=100000";

    render(<SearchClient />);
    await screen.findByRole("option", { name: "Japan (5)" });
    fireEvent.click(screen.getByRole("button", { name: "Clear" }));

    expect(screen.getByLabelText("Min salary (USD/yr)")).toHaveProperty(
      "value",
      "",
    );
    expect(screen.getByLabelText("Max salary (USD/yr)")).toHaveProperty(
      "value",
      "",
    );
    expect(mocks.replace).toHaveBeenLastCalledWith("/search");
  });

  it("shows a removable chip for an active salary filter, which clears it", () => {
    mocks.search = "salary_min=60000&salary_max=100000";

    render(<SearchClient />);

    // Throws if the chip text isn't rendered.
    screen.getByText("Salary: US$60,000 - US$100,000");

    fireEvent.click(
      screen.getByRole("button", { name: "Remove salary filter" }),
    );

    expect(screen.getByLabelText("Min salary (USD/yr)")).toHaveProperty(
      "value",
      "",
    );
    expect(screen.getByLabelText("Max salary (USD/yr)")).toHaveProperty(
      "value",
      "",
    );
    expect(mocks.replace).toHaveBeenCalledWith("/search");
  });

  it("shows a salary-specific empty state when the filter excludes every job", async () => {
    mocks.search = "salary_min=500000";

    render(<SearchClient />);

    // Throws if the empty-state text isn't rendered.
    await screen.findByText("No jobs match your salary range");
  });
});

describe("seniority filter", () => {
  const seniorityOptionsShown = () =>
    screen
      .getAllByRole<HTMLOptionElement>("option")
      .filter((option) => option.closest("#seniority-filter"))
      .map((option) => [option.value, option.textContent]);

  it("lists the levels that have jobs, lowest first, and says mid-level also holds unstated ones", async () => {
    render(<SearchClient />);

    const seniority = screen.getByLabelText("Seniority");
    expect(seniority.tagName).toBe("SELECT");
    await screen.findByRole("option", { name: "Senior (12)" });
    expect(seniorityOptionsShown()).toEqual([
      ["", "All levels"],
      ["1", "Junior (4)"],
      ["2", "Mid-level or not stated (30)"],
      ["3", "Senior (12)"],
    ]);
    expect(seniority).toHaveProperty("value", "");
  });

  it("uses the level in the URL and fetches only that level", async () => {
    mocks.search = "seniority=3";

    render(<SearchClient />);

    await screen.findByRole("option", { name: "Senior (12)" });
    expect(screen.getByLabelText("Seniority")).toHaveProperty("value", "3");
    await waitFor(() => {
      expect(mocks.getJobs).toHaveBeenCalledWith(
        expect.objectContaining({ seniority_level: 3 }),
        expect.any(AbortSignal),
      );
    });
  });

  it("drops a URL level that has no jobs", async () => {
    mocks.search = "seniority=7";

    render(<SearchClient />);

    await screen.findByRole("option", { name: "Senior (12)" });
    expect(screen.getByLabelText("Seniority")).toHaveProperty("value", "");
    await waitFor(() => {
      expect(mocks.getJobs).toHaveBeenLastCalledWith(
        expect.objectContaining({ seniority_level: undefined }),
        expect.any(AbortSignal),
      );
    });
  });

  it("a picked level only takes effect on Apply, then goes into the URL", async () => {
    render(<SearchClient />);
    await screen.findByRole("option", { name: "Senior (12)" });
    const apply = screen.getByRole("button", { name: "Apply" });
    expect(apply).toHaveProperty("disabled", true);

    fireEvent.change(screen.getByLabelText("Seniority"), {
      target: { value: "3" },
    });
    expect(apply).toHaveProperty("disabled", false);
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(mocks.getJobs).not.toHaveBeenCalledWith(
      expect.objectContaining({ seniority_level: 3 }),
      expect.any(AbortSignal),
    );

    fireEvent.click(apply);
    await waitFor(() => {
      expect(mocks.getJobs).toHaveBeenCalledWith(
        expect.objectContaining({ seniority_level: 3 }),
        expect.any(AbortSignal),
      );
    });
    expect(mocks.replace).toHaveBeenLastCalledWith("/search?seniority=3");
    expect(apply).toHaveProperty("disabled", true);
  });

  it("combines with the other filters and keeps them when applied", async () => {
    mocks.search = "q=lidar&country=Germany";

    render(<SearchClient />);
    await screen.findByRole("option", { name: "Senior (12)" });
    fireEvent.change(screen.getByLabelText("Seniority"), {
      target: { value: "1" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Apply" }));

    expect(mocks.replace).toHaveBeenLastCalledWith(
      "/search?q=lidar&country=Germany&seniority=1",
    );
    await waitFor(() => {
      expect(mocks.getJobs).toHaveBeenCalledWith(
        expect.objectContaining({
          q: "lidar",
          country: "Germany",
          seniority_level: 1,
        }),
        expect.any(AbortSignal),
      );
    });
  });

  it("Clear resets the level but keeps the keyword", async () => {
    mocks.search = "q=lidar&seniority=3";

    render(<SearchClient />);
    await screen.findByRole("option", { name: "Senior (12)" });
    fireEvent.click(screen.getByRole("button", { name: "Clear" }));

    expect(screen.getByLabelText("Seniority")).toHaveProperty("value", "");
    expect(mocks.replace).toHaveBeenLastCalledWith("/search?q=lidar");
  });

  it("still shows the page when the levels cannot be loaded", async () => {
    mocks.getJobSeniorityLevels.mockRejectedValue(new Error("offline"));

    render(<SearchClient />);

    expect(await screen.findByLabelText("Seniority")).toBeTruthy();
    expect(seniorityOptionsShown()).toEqual([["", "All levels"]]);
  });
});
