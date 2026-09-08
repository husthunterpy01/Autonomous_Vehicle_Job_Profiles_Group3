from scrapers.service.bronze_storage.html_extractor import HTMLExtractor

CONFIG = {
    "strategy": "css_list",
    "item": "div.careers-item",
    "job_name": "h3",
    "location": "[fs-cmsfilter-field='Regions']",
    "employment_type": "[fs-cmsfilter-field='Jobtypes']",
    "link": "a[href*='/careers/']",
    "job_id_pattern": r"/careers/(jd\d+)",
}

PAGE = """
<html><body>
  <div class="careers-grid">
    <div class="careers-item">
      <h3>FP&amp;A Manager</h3>
      <div fs-cmsfilter-field="Jobtypes">Full-Time</div>
      <div fs-cmsfilter-field="Regions">San Jose, California, US</div>
      <a class="link-10" href="/careers/jd203">Details</a>
    </div>
    <div class="careers-item">
      <h3>AI Agent R&amp;D Engineer</h3>
      <div fs-cmsfilter-field="Jobtypes">Full-Time</div>
      <div fs-cmsfilter-field="Regions">Remote</div>
      <a class="link-10" href="/careers/jd66">Details</a>
    </div>
  </div>
</body></html>
"""


def test_css_list_maps_rows_to_bronze_fields():
    jobs = HTMLExtractor(PAGE, CONFIG, page_url="https://www.tensor.auto/careers").extract_jobs()

    assert jobs == [
        {
            "source_job_id": "jd203",
            "job_name": "FP&A Manager",
            "job_url": "https://www.tensor.auto/careers/jd203",
            "job_description": None,
            "location": "San Jose, California, US",
            "employment_type": "Full-Time",
            "job_uploaded_at": None,
        },
        {
            "source_job_id": "jd66",
            "job_name": "AI Agent R&D Engineer",
            "job_url": "https://www.tensor.auto/careers/jd66",
            "job_description": None,
            "location": "Remote",
            "employment_type": "Full-Time",
            "job_uploaded_at": None,
        },
    ]


def test_job_id_falls_back_to_url_when_pattern_misses():
    config = {**CONFIG, "job_id_pattern": r"/nomatch/(\d+)"}
    (job, _) = HTMLExtractor(PAGE, config, page_url="https://x.test/careers").extract_jobs()
    assert job["source_job_id"] == "https://x.test/careers/jd203"


def test_relative_links_kept_when_no_page_url():
    (job, _) = HTMLExtractor(PAGE, CONFIG).extract_jobs()
    assert job["job_url"] == "/careers/jd203"


def test_headless_strategy_is_a_stub():
    assert HTMLExtractor("<html></html>", {"strategy": "headless"}).extract_jobs() == []


JOBYLON_PAGE = """
<html><body><script>
JBL.embed_v2['jobs'] = [
    {
        id: '380347',
        url: '/jobs/380347-einride-ehs-manager/',
        title: 'Environmental Health \\u0026 Safety Manager',
        klass: { 'job-id-380347': true },
        'layers_1': [ 'Full\\u002Dtime', ],
        locations: [ 'Dallas', 'Houston', ],
        locations_text: 'Dallas +1 more',
    },
    {
        id: '380393',
        url: '/jobs/380393-einride-office-manager/',
        title: 'Office Manager',
        'layers_1': [ 'Part-time', ],
        locations_text: 'Gothenburg',
    },
];
</script></body></html>
"""


def test_jobylon_strategy_parses_js_job_array():
    jobs = HTMLExtractor(JOBYLON_PAGE, {"strategy": "jobylon"}).extract_jobs()

    assert jobs == [
        {
            "source_job_id": "380347",
            "job_name": "Environmental Health & Safety Manager",
            "job_description": None,
            "location": "Dallas +1 more",
            "employment_type": "Full-time",
            "job_uploaded_at": None,
            "job_url": "https://emp.jobylon.com/jobs/380347-einride-ehs-manager/",
        },
        {
            "source_job_id": "380393",
            "job_name": "Office Manager",
            "job_description": None,
            "location": "Gothenburg",
            "employment_type": "Part-time",
            "job_uploaded_at": None,
            "job_url": "https://emp.jobylon.com/jobs/380393-einride-office-manager/",
        },
    ]


def test_jobylon_strategy_without_array_returns_empty():
    assert HTMLExtractor("<html></html>", {"strategy": "jobylon"}).extract_jobs() == []


def test_css_list_fills_description_from_detail_script():
    page = (
        '<ul><li class="c"><a href="/careers/jd1">Role A</a></li>'
        '<li class="c"><a href="/careers/jd2">Role B</a></li></ul>'
        '<script type="application/x-bronze-detail">'
        '{"jd1": "<p>full A</p>", "https://x.test/careers/jd2": "<p>full B</p>"}'
        "</script>"
    )
    cfg = {
        "strategy": "css_list",
        "item": "li.c",
        "job_name": "a",
        "link": "a",
        "job_id_pattern": r"/careers/(jd\d+)",
    }
    jobs = HTMLExtractor(page, cfg, page_url="https://x.test/careers").extract_jobs()
    assert [j["job_description"] for j in jobs] == ["<p>full A</p>", "<p>full B</p>"]


def test_unknown_strategy_returns_empty():
    assert HTMLExtractor("<html></html>", {"strategy": "nope"}).extract_jobs() == []


def test_missing_item_selector_returns_empty():
    assert HTMLExtractor(PAGE, {"strategy": "css_list"}).extract_jobs() == []


def test_accepts_bytes():
    jobs = HTMLExtractor(PAGE.encode("utf-8"), CONFIG, page_url="https://x.test/c").extract_jobs()
    assert len(jobs) == 2


def test_selector_at_attr_reads_attribute():
    page = (
        '<div class="c"><a href="/careers/jd1">x</a>'
        '<time class="d" datetime="2026-08-24">1 week ago</time></div>'
    )
    cfg = {
        "strategy": "css_list",
        "item": "div.c",
        "job_name": "a",
        "job_uploaded_at": "time.d@datetime",
        "link": "a",
        "job_id_pattern": r"/careers/(jd\d+)",
    }
    (job,) = HTMLExtractor(page, cfg, page_url="https://x.test/careers").extract_jobs()
    assert job["job_uploaded_at"] == "2026-08-24"


def test_paginated_snapshots_are_deduplicated():
    snapshot = (
        '<ul><li class="c"><a href="/careers/jd1">Role A</a></li>'
        '<li class="c"><a href="/careers/jd2">Role B</a></li></ul>'
    )
    combined = snapshot + "\n" + snapshot  # two page snapshots concatenated
    cfg = {
        "strategy": "css_list",
        "item": "li.c",
        "job_name": "a",
        "link": "a",
        "job_id_pattern": r"/careers/(jd\d+)",
    }
    jobs = HTMLExtractor(combined, cfg, page_url="https://x.test/careers").extract_jobs()
    assert [j["source_job_id"] for j in jobs] == ["jd1", "jd2"]
