from scrapers.models.bronze.bronze_payload import BronzePayload
from scrapers.strategy.ats.atsbasestrategy import ATSBaseStrategy


class SmartRecruiterStrategy(ATSBaseStrategy):
    def map_response_to_bronze_payload(self, company_name, headquarter, json_raw_response):
        job_list_information: list[BronzePayload] = []
        for job in json_raw_response["content"]:
            location = job.get("location") or {}
            employment = job.get("typeOfEmployment") or {}
            job_list_information.append(
                BronzePayload(
                    ats_name=self.source_system,
                    company_name=company_name,
                    headquarter=headquarter,
                    job_name=job["name"],
                    job_description=self._job_description(job),
                    location=location.get("fullLocation"),
                    job_uploaded_at=job.get("releasedDate"),
                    job_url=job.get("postingUrl") or job.get("absolute_url"),
                    employment_type=employment.get("label"),
                )
            )
        return job_list_information

    @staticmethod
    def _job_description(job: dict) -> str:
        sections = (job.get("jobAd") or {}).get("sections") or {}
        parts: list[str] = []
        for key in (
            "companyDescription",
            "jobDescription",
            "qualifications",
            "additionalInformation",
        ):
            section = sections.get(key) or {}
            text = section.get("text")
            if isinstance(text, str) and text.strip():
                parts.append(text.strip())
        if parts:
            return "\n".join(parts)
        content = job.get("content")
        return content if isinstance(content, str) else ""
