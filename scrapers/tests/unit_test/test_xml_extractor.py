from scrapers.service.bronze_storage.xml_extractor import XMLExtractor

FEED = """<?xml version="1.0" encoding="UTF-8"?>
<workzag-jobs>
<position>
    <id>1784945</id>
    <office>Böblingen</office>
    <department>Business Development</department>
    <name>Business Development Director</name>
    <jobDescriptions>
        <jobDescription>
            <name>In this role, you will:</name>
            <value><![CDATA[<ul><li>Own BD</li></ul>]]></value>
        </jobDescription>
        <jobDescription>
            <name>We would like you to have:</name>
            <value><![CDATA[<ul><li>Experience</li></ul>]]></value>
        </jobDescription>
    </jobDescriptions>
    <employmentType>permanent</employmentType>
    <createdAt>2024-10-21T10:30:53+00:00</createdAt>
</position>
</workzag-jobs>
"""

FEED_URL = "https://momenta-europe-gmbh.jobs.personio.de/xml?language=en"


def test_extracts_only_bronze_fields():
    (job,) = XMLExtractor(FEED, feed_url=FEED_URL).extract_jobs()

    assert job == {
        "source_job_id": "1784945",
        "job_name": "Business Development Director",
        "job_description": (
            "<h3>In this role, you will:</h3>\n<ul><li>Own BD</li></ul>\n"
            "<h3>We would like you to have:</h3>\n<ul><li>Experience</li></ul>"
        ),
        "location": "Böblingen",
        "job_url": "https://momenta-europe-gmbh.jobs.personio.de/job/1784945",
        "job_uploaded_at": "2024-10-21T10:30:53+00:00",
        "employment_type": "permanent",
    }


def test_job_url_is_none_without_feed_url():
    (job,) = XMLExtractor(FEED).extract_jobs()
    assert job["job_url"] is None


def test_accepts_bytes_and_skips_empty_positions():
    feed = FEED.encode("utf-8").replace(
        b"</workzag-jobs>", b"<position></position></workzag-jobs>"
    )
    jobs = XMLExtractor(feed, feed_url=FEED_URL).extract_jobs()
    assert [job["source_job_id"] for job in jobs] == ["1784945"]


def test_malformed_feed_returns_empty_list():
    assert XMLExtractor("<not-xml").extract_jobs() == []
