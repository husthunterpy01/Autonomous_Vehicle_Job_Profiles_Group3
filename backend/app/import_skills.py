"""Manual command: python -m app.import_skills handoff.json."""
from app.core.database import engine
from app.services.silver_pipeline import SilverPipeline
from app.utils.cli import input_parser, read_json, run_command
from scripts.sync_to_supabase import sync_if_configured


def main():
    parser = input_parser("Import extracted skills into backend skill/job_skill tables")
    run_command(parser, lambda args: SilverPipeline(engine).import_skills(read_json(args.input)))
    sync_if_configured()


if __name__ == "__main__":
    main()
