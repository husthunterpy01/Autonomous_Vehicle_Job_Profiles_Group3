"""Manual command: python -m app.import_salary handoff.json."""
from app.core.database import engine
from app.services.silver_pipeline import SilverPipeline
from app.utils.cli import input_parser, read_json, run_command


def main():
    parser = input_parser("Import salary data into backend jobposting salary_* columns")
    run_command(parser, lambda args: SilverPipeline(engine).import_salary(read_json(args.input)))


if __name__ == "__main__":
    main()
