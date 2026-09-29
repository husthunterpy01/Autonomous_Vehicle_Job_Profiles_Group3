from app.services.salary_stats import SalaryStatsService
from app.services.salary_sync import import_salary
from app.services.silver_sync import SilverSync


def seed(db, deduplication_key="one", job_name="Engineer", company_name="AV"):
    SilverSync(db).run([{
        "deduplication_key": deduplication_key,
        "company_name": company_name,
        "job_name": job_name,
        "job_description": "Autonomy",
    }])
    db.commit()


def _salary_row(**overrides):
    row = {
        "deduplication_key": "one",
        "salary_min": 150000,
        "salary_max": 200000,
        "salary_currency": "USD",
        "salary_period": "yearly",
        "salary_source": "api",
    }
    row.update(overrides)
    return row


def test_returns_empty_list_when_no_jobs_have_salary(db_session):
    seed(db_session)

    assert SalaryStatsService(db_session).get_top_paid_jobs() == []


def test_ranks_a_single_yearly_usd_job_by_its_max(db_session):
    seed(db_session)
    import_salary(db_session, [_salary_row()])

    stats = SalaryStatsService(db_session).get_top_paid_jobs()

    assert len(stats) == 1
    assert stats[0].salary_max == 200000
    assert stats[0].estimated_annual_usd_max == 200000
    assert stats[0].estimated_annual_usd_min == 150000


def test_orders_by_estimated_annual_usd_descending(db_session):
    seed(db_session, "one", "Lower Paid")
    seed(db_session, "two", "Higher Paid")
    import_salary(db_session, [
        _salary_row(deduplication_key="one", salary_min=100000, salary_max=120000),
        _salary_row(deduplication_key="two", salary_min=300000, salary_max=350000),
    ])

    stats = SalaryStatsService(db_session).get_top_paid_jobs()

    assert [s.title for s in stats] == ["Higher Paid", "Lower Paid"]


def test_annualizes_an_hourly_rate_before_ranking(db_session):
    # $80/hour * 2080 hours = $166,400/year - well above a $150,000 yearly
    # role, so the hourly job should rank first despite its raw number
    # looking smaller.
    seed(db_session, "one", "Yearly Role")
    seed(db_session, "two", "Hourly Role")
    import_salary(db_session, [
        _salary_row(deduplication_key="one", salary_min=140000, salary_max=150000, salary_period="yearly"),
        _salary_row(deduplication_key="two", salary_min=75, salary_max=80, salary_period="hourly"),
    ])

    stats = SalaryStatsService(db_session).get_top_paid_jobs()

    assert [s.title for s in stats] == ["Hourly Role", "Yearly Role"]
    hourly = next(s for s in stats if s.title == "Hourly Role")
    assert hourly.estimated_annual_usd_max == 80 * 2080
    assert hourly.estimated_annual_usd_min == 75 * 2080
    # The displayed figure is untouched - still the raw hourly rate.
    assert hourly.salary_max == 80
    assert hourly.salary_period == "hourly"


def test_converts_currency_before_ranking(db_session):
    # 100,000 EUR at the service's fixed 1.08 rate (~108,000 USD) should
    # rank below a 150,000 USD role, even though 100,000 < 150,000 only
    # because EUR wasn't converted - the raw numbers alone would say the
    # opposite is true (100,000 < 150,000, same conclusion here, so this
    # also exercises that conversion doesn't accidentally invert order for
    # unrelated reasons); the real check is the exact converted value below.
    seed(db_session, "one", "USD Role")
    seed(db_session, "two", "EUR Role")
    import_salary(db_session, [
        _salary_row(deduplication_key="one", salary_min=140000, salary_max=150000, salary_currency="USD"),
        _salary_row(deduplication_key="two", salary_min=95000, salary_max=100000, salary_currency="EUR"),
    ])

    stats = {s.title: s for s in SalaryStatsService(db_session).get_top_paid_jobs()}

    assert stats["EUR Role"].estimated_annual_usd_max == 100000 * 1.08
    assert stats["EUR Role"].estimated_annual_usd_min == 95000 * 1.08
    assert stats["EUR Role"].salary_max == 100000
    assert stats["EUR Role"].salary_currency == "EUR"
    assert [s.title for s in SalaryStatsService(db_session).get_top_paid_jobs()] == ["USD Role", "EUR Role"]


def test_uses_the_levels_fyi_average_when_there_is_no_disclosed_range(db_session):
    seed(db_session)
    row = {
        "deduplication_key": "one",
        "salary_average": 180000,
        "salary_currency": "USD",
        "salary_period": "yearly",
        "salary_source": "levels_fyi_average",
    }
    import_salary(db_session, [row])

    stats = SalaryStatsService(db_session).get_top_paid_jobs()

    assert len(stats) == 1
    assert stats[0].salary_average == 180000
    # No disclosed range to show, so min and max collapse to the same point
    # rather than fabricating a span.
    assert stats[0].estimated_annual_usd_max == 180000
    assert stats[0].estimated_annual_usd_min == 180000


def test_excludes_a_job_with_an_unrecognized_currency(db_session):
    # salary_sync only requires a non-empty currency string, not one of the
    # 9 the FX table knows - a currency the extractor never produces but an
    # ATS API could (e.g. a real but unmapped ISO code) must not crash the
    # ranking or silently get treated as USD; it's simply left out.
    seed(db_session)
    import_salary(db_session, [_salary_row(salary_currency="XYZ")])

    assert SalaryStatsService(db_session).get_top_paid_jobs() == []


def test_caps_levels_fyi_estimates_to_one_per_company(db_session):
    # Regression test for the exact bug Weishan reported: a levels.fyi
    # estimate is company-wide (salary_sync.py), so every job at a company
    # with no disclosed range shares the identical figure. Without a cap,
    # one such company (Stack AV in the real report) filled the entire top
    # N with duplicates of itself instead of a genuine spread of companies.
    for i in range(3):
        seed(db_session, f"stack-{i}", f"Stack Role {i}", company_name="Stack AV")
    seed(db_session, "real-1", "Real Role 1", company_name="RealCo1")
    seed(db_session, "real-2", "Real Role 2", company_name="RealCo2")
    import_salary(db_session, [
        {
            "deduplication_key": f"stack-{i}",
            "salary_average": 500000,
            "salary_currency": "USD",
            "salary_period": "yearly",
            "salary_source": "levels_fyi_average",
        }
        for i in range(3)
    ] + [
        _salary_row(deduplication_key="real-1", salary_min=300000, salary_max=350000),
        _salary_row(deduplication_key="real-2", salary_min=200000, salary_max=250000),
    ])

    stats = SalaryStatsService(db_session).get_top_paid_jobs()

    stack_av_entries = [s for s in stats if s.company_name == "Stack AV"]
    assert len(stack_av_entries) == 1
    assert [s.company_name for s in stats] == ["Stack AV", "RealCo1", "RealCo2"]


def test_does_not_cap_real_disclosed_ranges_from_the_same_company(db_session):
    # The cap only applies to levels.fyi estimates, which are company-wide
    # and therefore redundant when repeated - a real disclosed range is
    # genuinely per-job, so two different real ranges at the same company
    # are both legitimate results and must not be capped.
    seed(db_session, "one", "Role One", company_name="SameCo")
    seed(db_session, "two", "Role Two", company_name="SameCo")
    import_salary(db_session, [
        _salary_row(deduplication_key="one", salary_min=300000, salary_max=350000),
        _salary_row(deduplication_key="two", salary_min=200000, salary_max=250000),
    ])

    stats = SalaryStatsService(db_session).get_top_paid_jobs()

    assert len(stats) == 2
    assert {s.title for s in stats} == {"Role One", "Role Two"}


def test_still_respects_the_limit_after_capping_estimates(db_session):
    for i in range(5):
        seed(db_session, f"stack-{i}", f"Stack Role {i}", company_name="Stack AV")
    seed(db_session, "real-1", "Real Role 1", company_name="RealCo1")
    import_salary(db_session, [
        {
            "deduplication_key": f"stack-{i}",
            "salary_average": 500000,
            "salary_currency": "USD",
            "salary_period": "yearly",
            "salary_source": "levels_fyi_average",
        }
        for i in range(5)
    ] + [_salary_row(deduplication_key="real-1", salary_min=300000, salary_max=350000)])

    stats = SalaryStatsService(db_session).get_top_paid_jobs(limit=1)

    assert len(stats) == 1


def test_still_returns_the_full_limit_when_one_company_dwarfs_the_others(db_session):
    # Regression test for Weishan's PR #147 follow-up report: the previous
    # implementation over-fetched limit*10 rows in SQL and capped
    # per-company duplicates in Python afterward, so a single company with
    # more estimate-only jobs than that window could hold (his real-world
    # numbers: Waymo ~300, NVIDIA ~700) filled the entire window with its
    # own duplicates before any other company's rows were even fetched -
    # capping afterward then returned far fewer than `limit` results (his
    # repro below: 60 duplicates + 5 real ranges, limit=5, returned just 1).
    for i in range(60):
        seed(db_session, f"stack-{i}", f"Stack Role {i}", company_name="Stack AV")
    for i in range(5):
        seed(db_session, f"real-{i}", f"Real Role {i}", company_name=f"RealCo{i}")
    import_salary(db_session, [
        {
            "deduplication_key": f"stack-{i}",
            "salary_average": 500000,
            "salary_currency": "USD",
            "salary_period": "yearly",
            "salary_source": "levels_fyi_average",
        }
        for i in range(60)
    ] + [
        _salary_row(
            deduplication_key=f"real-{i}",
            salary_min=200000 + i * 1000,
            salary_max=250000 + i * 1000,
        )
        for i in range(5)
    ])

    stats = SalaryStatsService(db_session).get_top_paid_jobs(limit=5)

    assert len(stats) == 5
    assert len([s for s in stats if s.company_name == "Stack AV"]) == 1


def test_respects_the_limit(db_session):
    for i in range(3):
        seed(db_session, str(i), f"Role {i}")
    import_salary(db_session, [
        _salary_row(deduplication_key=str(i), salary_min=100000 + i, salary_max=100000 + i)
        for i in range(3)
    ])

    stats = SalaryStatsService(db_session).get_top_paid_jobs(limit=2)

    assert len(stats) == 2
