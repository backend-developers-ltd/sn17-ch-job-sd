import asyncio
import glob
import hashlib
import random
from datetime import datetime
from pathlib import Path
from typing import Callable

import compute_horde_sdk.v1 as ch

from util import (
    Batch,
    ValidationData,
    get_ch_client,
    download_and_unpack_zip,
)

concurrent_job_limiter = asyncio.Semaphore(2)


async def main() -> None:
    common_seed = random.randint(0, 500000)
    logger = _timed_logger("main")

    # Build batches from batches/* - one batch directory will be submitted as one job
    batches = [
        Batch(
            seed=common_seed,
            data_location=Path(batch_data_location),
            output_location=Path("outputs") / Path(batch_data_location).name,
        )
        for batch_data_location in glob.glob("batches/*")
        if Path(batch_data_location).is_dir() and (Path(batch_data_location) / "prompts.txt").is_file()
    ]
    logger("Found", len(batches), "batches:", ", ".join((str(b) for b in batches)))

    # Start job driver tasks in the background
    tasks = [asyncio.create_task(drive_batch_job(batch)) for batch in batches]

    # In the meantime, submit a trusted validation job using random samples
    logger("Submitting validation job")
    validation_data = ValidationData(batches)
    validation_job_spec = validation_data.as_ch_job_spec()
    validation_job = await get_ch_client().run_until_complete(
        validation_job_spec,
        on_trusted_miner=True,
        max_attempts=30,
        job_attempt_callback=_attempt_logger(validation_data, logger=_timed_logger("validation batch")),
    )
    try:
        await validation_job.wait(timeout=120)
        logger(f"Validation job {validation_job.status}")
    except Exception as e:
        logger(f"Validation job failed with exception: {e}")

    # Wait for jobs to finish
    results = await asyncio.gather(*tasks, return_exceptions=True)
    all_batch_results: dict[Batch, ch.ComputeHordeJob | BaseException] = dict(zip(batches, results))
    successful_batch_results: dict[Batch, ch.ComputeHordeJob] = {
        batch: result
        for batch, result in all_batch_results.items()
        if not isinstance(result, BaseException) and result.status == ch.ComputeHordeJobStatus.COMPLETED
    }

    if validation_job.status != ch.ComputeHordeJobStatus.COMPLETED:
        logger(f"(!) Validation job failed. Results will not be validated. ({validation_job.status})")
        return

    logger("Validating results against trusted job results")
    if not successful_batch_results:
        logger("No successful batch jobs found. Nothing to validate.")
    for batch, job in successful_batch_results.items():
        logger(f"Validating batch job {batch}")
        validation_idx = validation_data.batches.index(batch)
        test_file = batch.output_location / f"{batch.sample_prompt_idx}.png"
        miner_reported_hash = job.result.artifacts.get(f"/artifacts/{batch.sample_prompt_idx}.png.sha256")
        trusted_hash = validation_job.result.artifacts.get(f"/artifacts/{validation_idx}.png.sha256")
        calculated_hash = hashlib.sha256(test_file.read_bytes()).hexdigest().encode()

        logger("Test file:", test_file)
        logger("Miner reported hash:", miner_reported_hash)
        logger("Trusted hash:", trusted_hash)
        logger("Calculated hash:", calculated_hash)
        if miner_reported_hash == trusted_hash == calculated_hash:
            logger(f"Batch job {batch} validation passed.")
        else:
            logger(f"(!) Batch job {batch} validation failed.")
            logger(f"Reporting cheated job back to ComputeHorde: {job.uuid}")
            await get_ch_client().report_cheated_job(job.uuid)


async def drive_batch_job(batch: Batch) -> ch.ComputeHordeJob:
    """
    Submits a ComputeHorde job based on given batch data.
    Returns the successful ComputeHorde job.
    Throws an exception if the job is not successful for any reason.
    """

    async with concurrent_job_limiter:
        await asyncio.sleep(3)  # Short pause allows a recently used miner to pick up the job
        logger = _timed_logger(batch)
        try:
            spec = batch.as_ch_job_spec()
            logger("submitting")
            logger(f"upload URL: {batch.upload_url}")
            logger(f"download URL: {batch.download_url}")
            job = await get_ch_client().run_until_complete(
                spec,
                max_attempts=30,
                timeout=1800,
                job_attempt_callback=_attempt_logger(batch, logger),
            )
            if job.status != ch.ComputeHordeJobStatus.COMPLETED:
                raise Exception(f"last known status: {job.status}")
            logger("CH job successful, downloading results")
            await download_and_unpack_zip(batch.download_url, into=batch.output_location)
            logger(f"downloaded output to {batch.output_location}")
        except BaseException as e:
            logger(f"(!) failed: {e}")
            raise e

        return job


def _attempt_logger(batch: Batch | ValidationData, logger: Callable[[...], None]) -> Callable[[ch.ComputeHordeJob], None]:
    attempt_count = 0

    def _callback(ch_job: ch.ComputeHordeJob):
        nonlocal attempt_count
        attempt_count += 1
        logger(f"attempt {attempt_count} submitted as CH job {ch_job.uuid}")
        logger(f"expected time to complete: {sum((
            batch.expected_input_download_time,
            batch.expected_execution_time,
            batch.expected_results_upload_time
        ))}s")

    return _callback

def _timed_logger(*prefixes: object) -> Callable[[...], None]:
    def _log(*msgs: object):
        print(
            *(f"[{prefix}]" for prefix in (
                datetime.now().isoformat(),
                *prefixes,
            )),
            *msgs,
        )
    return _log

if __name__ == "__main__":
    asyncio.run(main())
