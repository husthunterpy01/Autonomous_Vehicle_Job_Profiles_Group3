from unittest.mock import patch

from scrapers.pipeline_main import main


@patch("scrapers.pipeline_main.PipelineRunner")
def test_main_delegates_to_pipeline_runner(mock_pipeline_runner):
    mock_pipeline_runner.run.return_value = 0

    status = main(["--company", "stack_av"])

    assert status == 0
    mock_pipeline_runner.run.assert_called_once_with(["--company", "stack_av"])
