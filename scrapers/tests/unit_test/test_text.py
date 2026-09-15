from scrapers.service.llm.text import compress_job_text, normalize_text


def test_normalize_text_strips_html_and_entities():
    assert normalize_text("<p>LiDAR &amp; Camera</p>") == "LiDAR & Camera"


def test_compress_cuts_at_boilerplate_marker_before_hard_limit():
    description = "We build perception systems for self-driving cars using LiDAR and cameras. " * 3
    description += "Benefits: health, dental, vision, and a generous 401k match with lots of extra detail here."

    title, compressed = compress_job_text("Perception Engineer", description, max_chars=1000)

    assert "Benefits" not in compressed
    assert "401k" not in compressed
    assert "LiDAR" in compressed
    assert title == "Perception Engineer"


def test_compress_applies_hard_cap_when_no_boilerplate_marker_present():
    description = "Perception engineering work with LiDAR and cameras. " * 50

    _, compressed = compress_job_text("Engineer", description, max_chars=100)

    assert len(compressed) <= 100


def test_compress_ignores_boilerplate_marker_appearing_too_early():
    # "About us" in the opening line shouldn't truncate everything that follows.
    description = "About us: we build self-driving cars. We need LiDAR and camera perception engineers."

    _, compressed = compress_job_text("Engineer", description, max_chars=1000)

    assert "LiDAR" in compressed
