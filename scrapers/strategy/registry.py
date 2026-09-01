from scrapers.strategy.ats.ashbystrategy import AshbyStrategy
from scrapers.strategy.ats.greenhousestrategy import GreenhouseStrategy
from scrapers.strategy.ats.leverstrategy import LeverStrategy
from scrapers.strategy.ats.smartrecruiter import SmartRecruiterStrategy

ATS_ADAPTERS = {
    "greenhouse": GreenhouseStrategy,
    "ashby": AshbyStrategy,
    "lever": LeverStrategy,
    "smartrecruiters": SmartRecruiterStrategy,
    "smartrecruiter": SmartRecruiterStrategy,
}


def get_ats_adapter(source_system: str):
    adapter_cls = ATS_ADAPTERS.get(source_system)
    if adapter_cls is None:
        raise ValueError(f"Unknown source system: {source_system}")
    return adapter_cls(source_system)
