"""Manual command: python -m app.validate_handoff handoff.json."""
from app.core.database import engine
from app.services.silver_pipeline import SilverPipeline
from app.utils.cli import input_parser, read_json, run_command


def main():
    parser = input_parser("Validate external job identities without writing data")
    run_command(parser, lambda args: SilverPipeline(engine).validate(read_json(args.input)))


if __name__ == "__main__":
    main()
