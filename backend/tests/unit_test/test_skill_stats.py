from app.services.silver_sync import SilverSync
from app.services.skill_stats import SkillService
from app.services.skill_sync import import_skills


def seed(db, deduplication_key="one", job_name="Engineer"):
    SilverSync(db).run([{
        "deduplication_key": deduplication_key,
        "company_name": "AV",
        "job_name": job_name,
        "job_description": "Autonomy",
    }])
    db.commit()


def test_returns_empty_list_when_no_skills_exist(db_session):
    seed(db_session)

    assert SkillService(db_session).get_skill_stat_per_job() == []


def test_counts_each_skill_once_per_job(db_session):
    seed(db_session)
    import_skills(db_session, [{
        "deduplication_key": "one",
        "skills": [
            {"name": "ROS 2", "skill_type": "framework"},
            {"name": "Python", "skill_type": "programming_language"},
        ],
    }])

    stats = {s.skill_name: s.number_of_occurence for s in SkillService(db_session).get_skill_stat_per_job()}

    assert stats == {"ROS 2": 1, "Python": 1}


def test_counts_a_skill_shared_across_multiple_jobs(db_session):
    seed(db_session, "one", "Engineer One")
    seed(db_session, "two", "Engineer Two")
    import_skills(db_session, [
        {"deduplication_key": "one", "skills": [{"name": "Python", "skill_type": "programming_language"}]},
        {"deduplication_key": "two", "skills": [{"name": "Python", "skill_type": "programming_language"}]},
    ])

    stats = SkillService(db_session).get_skill_stat_per_job()

    assert len(stats) == 1
    assert stats[0].skill_name == "Python"
    assert stats[0].number_of_occurence == 2


def test_job_with_no_skills_does_not_affect_other_counts(db_session):
    seed(db_session, "one", "Engineer One")
    seed(db_session, "two", "Engineer Two")
    import_skills(db_session, [
        {"deduplication_key": "one", "skills": [{"name": "Python", "skill_type": "programming_language"}]},
        {"deduplication_key": "two"},
    ])

    stats = SkillService(db_session).get_skill_stat_per_job()

    assert len(stats) == 1
    assert stats[0].number_of_occurence == 1
