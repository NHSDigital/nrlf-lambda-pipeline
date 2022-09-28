from lambda_pipeline.logging import logger


def test_logger_runs():
    logger.info("foo")
