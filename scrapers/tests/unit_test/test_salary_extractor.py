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


def test_infers_yearly_when_a_large_range_states_no_period_at_all():
    # Real text from a live NVIDIA/Workday posting - states a currency-coded
    # range but never says "per year" anywhere near it. No real hourly,
    # daily, or weekly rate reaches five figures, so a five-figure-or-larger
    # unstated-period range can only be annual.
    text = (
        "Your base salary will be determined based on your location, experience, and the "
        "pay of employees in similar positions. The base salary range is 116,000 USD - "
        "178,250 USD for Level 3, and 140,000 USD - 224,250 USD for Level 4."
    )
    assert extract_salary_from_text(text) == SalaryEstimate(
        min=116000.0, max=178250.0, currency="USD", period="yearly"
    )


def test_does_not_infer_yearly_for_a_small_unstated_period_range():
    # Below the floor, the numbers are too ambiguous to guess a period for
    # (could be a headcount, an ID range, a small one-off payment, ...).
    assert extract_salary_from_text("We have 5,000 - 6,000 $ widgets in stock.") is None


def test_an_explicit_period_still_wins_over_yearly_inference():
    text = "$5,000 - $10,000 per month for this contract role."
    assert extract_salary_from_text(text) == SalaryEstimate(min=5000.0, max=10000.0, currency="USD", period="monthly")


def test_wayve_style_range_plus_equity_package_with_no_period_still_extracts():
    text = "The reasonably estimated salary for this role ranges from $311,850–$370,000, plus a competitive equity package."
    assert extract_salary_from_text(text) == SalaryEstimate(
        min=311850.0, max=370000.0, currency="USD", period="yearly"
    )


def test_in_addition_to_bonus_is_treated_as_extra_pay_not_a_label_on_the_range():
    # Real text from a live XPENG posting - "in addition to bonus" is the
    # same shape as "+ Annual Bonus" (#135) but doesn't contain "+"/"plus".
    text = "The salary range for this role is $174,720 - $295,680, in addition to bonus, equity and benefits."
    assert extract_salary_from_text(text) == SalaryEstimate(
        min=174720.0, max=295680.0, currency="USD", period="yearly"
    )


def test_a_range_actually_labeled_as_a_bonus_before_in_addition_to_is_still_skipped():
    text = "Sign-on bonus of $5,000 - $10,000, in addition to your base salary."
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


def test_keeps_base_range_when_a_bonus_is_listed_as_extra_pay_after_it():
    # Regression test (real Stack AV posting): "+ Annual Bonus" after the
    # range is extra pay on top of it, not a label on it, but the trailing
    # bonus check used to discard this hourly base rate entirely.
    text = (
        "Benefits & Perks to joining Stack AV: Compensation: $32.00 – $37.00/hr "
        "+ Annual Bonus + Long Term Incentive $0 Healthcare Premiums"
    )
    assert extract_salary_from_text(text) == SalaryEstimate(32.0, 37.0, "USD", "hourly")

    text = "Base pay $150,000 - $180,000 per year plus annual bonus and equity."
    assert extract_salary_from_text(text) == SalaryEstimate(150000.0, 180000.0, "USD", "yearly")


def test_still_skips_a_range_labelled_as_a_bonus_right_after_it():
    text = "Up to $5,000 - $10,000 signing bonus. Salary $120,000 - $140,000 per year."
    assert extract_salary_from_text(text) == SalaryEstimate(120000.0, 140000.0, "USD", "yearly")


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
