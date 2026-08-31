from scrapers.strategy.ats.atsbasestrategy import ATSBaseStrategy
from scrapers.models.bronze.bronze_payload import BronzePayload
class LeverStrategy(ATSBaseStrategy):
    def map_response_to_bronze_payload(self, company_name, headquarter, json_raw_response):
        job_list_information : list[BronzePayload] = []
        # Extract data information
        for job in json_raw_response:
            job_list_information.append(
                BronzePayload(
                    ats_name=self.source_system,
                    company_name = company_name,
                    headquarter = headquarter,
                    job_name = job["text"],
                    job_description = job["descriptionPlain"],
                    location = job["categories"]["location"],
                    job_uploaded_at = job["createdAt"],
                    job_url = job["hostedUrl"],
                    employment_type = job["workplaceType"],
                )
            )

        return job_list_information