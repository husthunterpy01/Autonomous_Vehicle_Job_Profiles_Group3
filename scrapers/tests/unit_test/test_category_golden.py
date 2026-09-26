from scrapers.service.llm.job_enricher import ALLOWED_CATEGORIES
from scrapers.utils.eval_category_golden import NO_CATEGORY, is_correct, load_golden


def test_golden_set_is_well_formed():
    golden = load_golden()
    assert len(golden) >= 30
    keys = [(job["company"], job["title"]) for job in golden]
    assert len(keys) == len(set(keys))
    for job in golden:
        assert job["expected"] in ALLOWED_CATEGORIES | {NO_CATEGORY}
        assert job["why"].strip()
        assert len(job["description"]) > 200


def test_golden_set_covers_dropping_and_the_infrastructure_boundary():
    expected = [job["expected"] for job in load_golden()]
    assert expected.count(NO_CATEGORY) >= 5
    assert expected.count("Infrastructure") >= 5
    assert expected.count("System and Safety") >= 5


def test_is_correct_treats_no_category_as_its_own_answer():
    assert is_correct(NO_CATEGORY, ())
    assert not is_correct(NO_CATEGORY, ("Infrastructure",))
    assert not is_correct("Perception", ())
    assert is_correct("Perception", ("Sensing", "Perception"))
