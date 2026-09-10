"""Manual command: python -m app.import_categories handoff.json."""
from app.core.database import engine
from app.services.silver_pipeline import SilverPipeline
from app.utils.cli import input_parser, read_json, run_command


def main():
    parser = input_parser("Import functional_area labels into backend categories")
    run_command(parser, lambda args: SilverPipeline(engine).import_categories(read_json(args.input)))


if __name__ == "__main__":
    main()
