import asyncio
import glob
import hashlib
import random
from pathlib import Path

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
    print("Found", len(batches), "batches:", ", ".join((str(b) for b in batches)))

    # Start job driver tasks in the background
    tasks = [asyncio.create_task(drive_batch_job(batch)) for batch in batches]

    # In the meantime, submit a trusted validation job using random samples
    print("Submitting validation job")
    validation_data = ValidationData(batches)
    validation_job_spec = validation_data.as_ch_job_spec(
        expected_input_download_time=5,
        expected_execution_time=60,
        expected_results_upload_time=5,
    )
    validation_job = await get_ch_client().run_until_complete(
        validation_job_spec, on_trusted_miner=True, max_attempts=30
    )
    try:
        await validation_job.wait(timeout=120)
        print(f"Validation job {validation_job.status}")
    except Exception as e:
        print(f"Validation job failed with exception: {e}")

    # Wait for jobs to finish
    results = await asyncio.gather(*tasks, return_exceptions=True)
    all_batch_results: dict[Batch, ch.ComputeHordeJob | BaseException] = dict(zip(batches, results))
    successful_batch_results: dict[Batch, ch.ComputeHordeJob] = {
        batch: result
        for batch, result in all_batch_results.items()
        if not isinstance(result, BaseException) and result.status == ch.ComputeHordeJobStatus.COMPLETED
    }

    if validation_job.status != ch.ComputeHordeJobStatus.COMPLETED:
        print(f"(!) Validation job failed. Results will not be validated. ({validation_job.status})")
        return

    print("Validating results against trusted job results")
    for batch, job in successful_batch_results.items():
        print(f"Validating batch job {batch}")
        validation_idx = validation_data.batches.index(batch)
        test_file = batch.output_location / f"{batch.sample_prompt_idx}.png"
        miner_reported_hash = job.result.artifacts.get(f"/artifacts/{batch.sample_prompt_idx}.png.sha256")
        trusted_hash = validation_job.result.artifacts.get(f"/artifacts/{validation_idx}.png.sha256")
        calculated_hash = hashlib.sha256(test_file.read_bytes()).hexdigest().encode()

        print("Test file:", test_file)
        print("Miner reported hash:", miner_reported_hash)
        print("Trusted hash:", trusted_hash)
        print("Calculated hash:", calculated_hash)
        if miner_reported_hash == trusted_hash == calculated_hash:
            print(f"Batch job {batch} validation passed.")
        else:
            print(f"(!) Batch job {batch} validation failed.")
            print(f"Reporting cheated job back to ComputeHorde: {job.uuid}")
            await get_ch_client().report_cheated_job(job.uuid)


async def drive_batch_job(batch: Batch) -> ch.ComputeHordeJob:
    """
    Submits a ComputeHorde job based on given batch data.
    Returns the successful ComputeHorde job.
    Throws an exception if the job is not successful for any reason.
    """
    async with concurrent_job_limiter:
        await asyncio.sleep(3)  # Short pause allows a recently used miner to pick up the job
        try:
            print("Submitting batch job:", batch)
            spec = batch.as_ch_job_spec(
                expected_input_download_time=5,
                expected_execution_time=60,
                expected_results_upload_time=5,
            )
            job = await get_ch_client().run_until_complete(spec, max_attempts=30, timeout=300)
            print(f"Batch job {job.status}: {batch}")
            if job.status != ch.ComputeHordeJobStatus.COMPLETED:
                raise Exception(f"Batch job {batch} failed with status {job.status}")
            await download_and_unpack_zip(batch.download_url, into=batch.output_location)
            print(f"Downloaded output of batch job {batch} to {batch.output_location}")
        except BaseException as e:
            print(f"Batch job {batch} failed: {e}")
            raise e

        return job


if __name__ == "__main__":
    asyncio.run(main())
