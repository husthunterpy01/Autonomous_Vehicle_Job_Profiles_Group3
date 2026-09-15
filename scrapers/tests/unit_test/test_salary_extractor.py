from scrapers.service.silver_cleaning.salary_extractor import (
    SalaryEstimate,
    extract_salary_from_text,
)


def test_extracts_dollar_range_with_per_year():
    # Real text from a live Aurora/Ashby posting fetched this session.
    text = (
        "For roles based in San Francisco, CA, Mountain View, CA, and Seattle, WA: "
        "The salary range for this position is $139,000 - $223,000 per year."
    )
    assert extract_salary_from_text(text) == SalaryEstimate(139000.0, 223000.0, "USD", "yearly")


def test_extracts_range_with_capitalized_year():
    # Real text from a live Aurora/Ashby posting fetched this session.
    text = "The base salary range for this position is  $162,000 - $260,000 per Year."
    assert extract_salary_from_text(text) == SalaryEstimate(162000.0, 260000.0, "USD", "yearly")


def test_extracts_euro_range_per_annum():
    text = "The salary range is €50,000 - €70,000 per annum."
    assert extract_salary_from_text(text) == SalaryEstimate(50000.0, 70000.0, "EUR", "yearly")


def test_returns_none_when_no_salary_mentioned():
    text = "We are hiring 5-10 engineers this quarter to join the team."
    assert extract_salary_from_text(text) is None


def test_returns_none_for_single_value_up_to_amount():
    # A lone "up to $X" has no second number to pair with - correctly skipped
    # rather than guessing a min.
    text = "Compensation: up to $200,000 per year."
    assert extract_salary_from_text(text) is None


def test_returns_none_when_range_has_no_period_indicator():
    # Real text from a live NVIDIA/Workday posting fetched this session -
    # states a currency-coded range but never says "per year" anywhere near
    # it, so the extractor correctly declines rather than assuming annual.
    text = (
        "Your base salary will be determined based on your location, experience, and the "
        "pay of employees in similar positions. The base salary range is 116,000 USD - "
        "178,250 USD for Level 3, and 140,000 USD - 224,250 USD for Level 4."
    )
    assert extract_salary_from_text(text) is None


def test_returns_none_for_unrelated_numeric_range():
    text = "Posting dates: 2024-01-01 - 2024-02-15 for this role."
    assert extract_salary_from_text(text) is None


def test_returns_none_for_empty_description():
    assert extract_salary_from_text("") is None


def test_handles_european_thousands_separator_and_leading_annual_period():
    # Real, unmodified text from a live Bosch/SmartRecruiters posting
    # (av_jobs.jsonl, dedup key 0531b5ae510b89f862653c708d8012fb). Regression
    # test for three real bugs found there: (1) "50.000" is fifty-thousand
    # (European "." thousands grouping), not 50.0 - a naive float() parse
    # silently produced a wildly wrong magnitude; (2) the period is stated
    # *before* the range ("gross annual salary"), and "40-hour work week"
    # right after it was being misread as a weekly/hourly rate instead; (3)
    # the raw description's "&#xa0;" entities (6 literal characters each,
    # not real whitespace) pushed "annual" outside the before-window until
    # the text was normalized first.
    text = (
        "In&#xa0;line&#xa0;with&#xa0;our&#xa0;compensation&#xa0;policies,&#xa0;the&#xa0;gross&#xa0;annual"
        "&#xa0;salary&#xa0;(RAL) for&#xa0;this&#xa0;position&#xa0;lies&#xa0;within&#xa0;the range "
        "€ 50.000 - €60.000 for a 40-hour work week.&#xa0;&#xa0; The&#xa0;remuneration&#xa0;package"
        "&#xa0;also&#xa0;includes"
    )
    assert extract_salary_from_text(text) == SalaryEstimate(50000.0, 60000.0, "EUR", "yearly")


def test_does_not_misread_hour_count_in_work_week_as_hourly_rate():
    text = "This is a 40-hour work week. Salary: $26.39 - $39.59 per hour."
    assert extract_salary_from_text(text) == SalaryEstimate(26.39, 39.59, "USD", "hourly")


def test_two_digit_decimal_is_still_read_as_cents_not_thousands():
    text = "Pay rate: $25.50 - $35.00 per hour."
    assert extract_salary_from_text(text) == SalaryEstimate(25.50, 35.00, "USD", "hourly")


def test_prefers_closer_period_word_over_farther_unrelated_one():
    # Real text (paraphrased for brevity) from a live intern posting found
    # in av_jobs.jsonl this session. Regression test for two real bugs: (1)
    # "hourly" doesn't match a bare \bhour\b word-boundary pattern (the "ly"
    # blocks the trailing boundary) - it was silently never recognized; (2)
    # a fixed yearly-before-hourly priority order let the *earlier but
    # unrelated* "year" in "your sophomore year in school" beat the
    # *closer, directly relevant* "hourly rate" right next to the numbers.
    text = "Must have completed your sophomore year in school. The hourly rate for our interns is 20 USD - 71 USD."
    assert extract_salary_from_text(text) == SalaryEstimate(20.0, 71.0, "USD", "hourly")


def test_daily_is_recognized_not_just_day():
    text = "Contractor rate: $200 - $400 daily depending on project."
    assert extract_salary_from_text(text) == SalaryEstimate(200.0, 400.0, "USD", "daily")


def test_skips_sign_on_bonus_range_in_favor_of_base_salary():
    # Regression test: the first range in the text used to win outright, so
    # a one-time bonus mentioned before the base salary - with a single
    # "annual" reachable from both ranges - was returned instead of the
    # actual base pay.
    text = (
        "This role offers a competitive annual compensation package. "
        "Sign-on bonus of $5,000 - $10,000. Base salary $180,000 - $220,000."
    )
    assert extract_salary_from_text(text) == SalaryEstimate(180000.0, 220000.0, "USD", "yearly")


def test_recognizes_k_thousands_shorthand():
    text = "Compensation $150K - $200K per year."
    assert extract_salary_from_text(text) == SalaryEstimate(150000.0, 200000.0, "USD", "yearly")


def test_recognizes_between_x_and_y_phrasing():
    text = "Salary is between $100,000 and $150,000 per year."
    assert extract_salary_from_text(text) == SalaryEstimate(100000.0, 150000.0, "USD", "yearly")


def test_years_of_experience_is_not_read_as_a_yearly_pay_period():
    # Regression test: a bare digit immediately before "year(s)" almost
    # always states required experience, not pay frequency - it must not
    # be treated as the closest period word for a nearby, unrelated range.
    text = "5+ years of experience required. $30 - $40 per hour."
    assert extract_salary_from_text(text) == SalaryEstimate(30.0, 40.0, "USD", "hourly")


def test_after_n_months_is_not_read_as_a_monthly_pay_period():
    text = "After 6 months of employment, salary becomes $100,000 - $130,000 per year."
    assert extract_salary_from_text(text) == SalaryEstimate(100000.0, 130000.0, "USD", "yearly")


def test_full_european_decimal_comma_format_is_not_collapsed():
    # Regression test: "50.000,00" (European "." thousands + "," decimal)
    # was read as if "," were a US-style thousands separator to strip,
    # silently collapsing it to 50.0 instead of 50000.0.
    text = "Gross annual salary range €50.000,00 - €60.000,00 per year."
    assert extract_salary_from_text(text) == SalaryEstimate(50000.0, 60000.0, "EUR", "yearly")
