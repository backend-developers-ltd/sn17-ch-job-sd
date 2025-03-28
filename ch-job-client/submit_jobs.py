import asyncio
import glob
import hashlib
import random
import uuid
from pathlib import Path
from typing import TypeAlias

import compute_horde_sdk.v1 as ch
from typing_extensions import TypeVar

from util import ImageGenerationBatchData, download_and_unpack_zip, get_nth_file_line, ValidationJobData, get_ch_client


semaphore = asyncio.Semaphore(2)

async def main():
    common_seed = random.randint(0, 500000)

    # Build job batches
    batches = [
        ImageGenerationBatchData(
            internal_id=uuid.uuid4().hex,
            seed=common_seed,
            data_location=Path(batch_data_location),
        )
        for batch_data_location in glob.glob("batches/*")
        if Path(batch_data_location).is_dir()
    ]

    # Submit jobs
    tasks = [
        asyncio.create_task(drive_batch_job(batch))
        for batch in batches
    ]

    # In the meantime, submit a trusted validation job for random samples
    # One **random** prompt per batch is good enough
    validation_samples: list[tuple[ImageGenerationBatchData, str, int]] = []
    for batch_data in batches:
        prompt_idx = random.randint(0, len(batch_data.prompts) - 1)
        prompt = batch_data.prompts[prompt_idx]
        validation_samples.append((batch_data, prompt, prompt_idx))
    validation_job_data = ValidationJobData(
        internal_id=uuid.uuid4().hex,
        seed=common_seed,
        prompts=[sample[1] for sample in validation_samples],
    )

    async with semaphore:
        await asyncio.sleep(3)
        print("Submitting validation job")
        validation_job = await get_ch_client().create_job(
            job_spec=validation_job_data.as_ch_job_spec(),
            on_trusted_miner=False,  # TODO - Change this to true after dealing with trusted executor outage
        )
        try:
            await validation_job.wait(timeout=120)
            print("Validation job finished")
        except Exception:
            # We'll handle this later
            pass

    # Wait for jobs to finish
    results: list[tuple[ImageGenerationBatchData, ch.ComputeHordeJob] | Exception] = await asyncio.gather(*tasks, return_exceptions=True)

    for result in results:
        if isinstance(result, Exception):
            print(f"Batch job failed: {result}")

    # Download results
    batch_output_locations: dict[ImageGenerationBatchData, Path] = {}
    for batch_data, ch_job in (result for result in results if not isinstance(result, Exception)):
        batch_output_location = Path("outputs") / batch_data.internal_id
        await download_and_unpack_zip(batch_data.get_download_url(), into=batch_output_location)
        batch_output_locations[batch_data] = batch_output_location
        print(f"Downloaded output of batch job {batch_data} to {batch_output_location}")

    if validation_job.status != ch.ComputeHordeJobStatus.COMPLETED:
        print(f"(!) Validation job failed. Results will not be validated.")
        return

    print(f"Validating results against trusted job results")
    validation_output_location = Path("outputs") / validation_job_data.internal_id
    await download_and_unpack_zip(validation_job_data.get_download_url(), into=validation_output_location)

    for validated_idx, sample in enumerate(validation_samples):
        batch_data, prompt, original_idx = sample
        if batch_data not in batch_output_locations:
            continue

        batch_output_location = batch_output_locations[batch_data]
        test_file = batch_output_location / f"{original_idx}.png"
        good_sample = validation_output_location / f"{validated_idx}.png"
        print(f"Validating job {batch_data.data_location}")
        test_hash = hashlib.sha256(test_file.read_bytes()).hexdigest()
        good_hash = hashlib.sha256(good_sample.read_bytes()).hexdigest()

        print(f"Test file: {test_file} (hash: {test_hash})")
        print(f"Known good result: {good_sample} (hash: {good_hash})")
        if test_hash == good_hash:
            print(f"Batch job {batch_data.data_location} validation passed.")
        else:
            related_ch_job = results[validated_idx][1]
            print(f"(!) Batch job {batch_data.data_location} validation failed.")
            print(f"Reporting cheated job back to ComputeHorde: {related_ch_job.uuid}")
            await get_ch_client().report_cheated_job(related_ch_job.uuid)

async def drive_batch_job(job_data: ImageGenerationBatchData) -> tuple[ImageGenerationBatchData, ch.ComputeHordeJob]:
    async with semaphore:
        await asyncio.sleep(3)
        spec = job_data.as_ch_job_spec()

        print("Submitting batch job:", job_data)
        job = await get_ch_client().create_job(spec, on_trusted_miner=False)

        try:
            await job.wait(timeout=120)
        except ch.ComputeHordeJobTimeoutError:
            print("Batch job timed out:", job_data)
        else:
            print(f"Batch job {job.status}: {job_data}")

        if job.status != ch.ComputeHordeJobStatus.COMPLETED:
            raise Exception(f"Batch job {job_data} failed with status {job.status}")

        return job_data, job


if __name__ == "__main__":
    asyncio.run(main())
