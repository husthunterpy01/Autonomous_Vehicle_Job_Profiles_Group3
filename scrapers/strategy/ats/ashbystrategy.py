from datetime import datetime

from scrapers.models.bronze.bronze_payload import BronzePayload
from scrapers.strategy.ats.atsbasestrategy import ATSBaseStrategy


class AshbyStrategy(ATSBaseStrategy):
    def map_response_to_bronze_payload(self,company_name, headquarter, json_raw_response):
        job_list_information: list[BronzePayload] = []
        for job in json_raw_response["jobs"]:
            job_list_information.append(
                BronzePayload(
                    ats_name=self.source_system,
                    company_name=company_name,
                    headquarter=headquarter,
                    job_name=job["title"],
                    job_description=job.get("descriptionPlain") or "",
                    location=self._locations(job),
                    job_uploaded_at=job.get("publishedAt"),
                    job_url=job.get("jobUrl"),
                    employment_type=job.get("employmentType"),
                )
            )
        return job_list_information

    # Ashby provides multiple locations for a job, so we would extract all of these locations
    @staticmethod
    def _locations(job: dict) -> str | None:
        locations: list[str] = []
        seen: set[str] = set()

        def add(value: object) -> None:
            if not isinstance(value, str):
                return
            text = value.strip()
            if not text or text in seen:
                return
            seen.add(text)
            locations.append(text)

        add(job.get("location"))
        for secondary in job.get("secondaryLocations") or []:
            if isinstance(secondary, dict):
                add(secondary.get("location"))
            else:
                add(secondary)

        if not locations:
            return None
        return " | ".join(locations)
