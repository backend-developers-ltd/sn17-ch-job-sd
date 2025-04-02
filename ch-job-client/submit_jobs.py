import asyncio
import glob
import hashlib
import random
import uuid
from pathlib import Path

import compute_horde_sdk.v1 as ch

from util import ImageGenerationBatchData, download_and_unpack_zip, ValidationJobData, get_ch_client


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
        and (Path(batch_data_location) / "prompts.txt").is_file()
    ]
    print("Found", len(batches), "batches:", [str(b.data_location) for b in batches])

    # Submit jobs
    tasks = [
        asyncio.create_task(drive_batch_job(batch))
        for batch in batches
    ]

    # In the meantime, submit a trusted validation job using random samples
    # One **random** prompt per batch is good enough
    print("Submitting validation job")
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
    validation_ch_job = await get_ch_client().create_job(
        job_spec=validation_job_data.as_ch_job_spec(),
        on_trusted_miner=True,
    )
    try:
        await validation_ch_job.wait(timeout=120)
        print(f"Validation job {validation_ch_job.status}")
    except Exception:
        #
        pass

    # Wait for jobs to finish
    results: list[tuple[ImageGenerationBatchData, ch.ComputeHordeJob] | Exception] = await asyncio.gather(*tasks, return_exceptions=True)

    for result in results:
        if isinstance(result, Exception):
            print(f"Batch job failed: {result}")

    # Download results
    batch_output_locations: dict[ImageGenerationBatchData, Path] = {}
    for batch_data, batch_ch_job in (result for result in results if not isinstance(result, Exception)):
        batch_output_location = Path("outputs") / batch_data.internal_id
        await download_and_unpack_zip(batch_data.get_download_url(), into=batch_output_location)
        batch_output_locations[batch_data] = batch_output_location
        print(f"Downloaded output of batch job {batch_data} to {batch_output_location}")

    if validation_ch_job.status != ch.ComputeHordeJobStatus.COMPLETED:
        print(f"(!) Validation job failed. Results will not be validated.")
        return

    print(f"Validating results against trusted job results")
    for validation_idx, sample in enumerate(validation_samples):
        batch_data, prompt, sample_idx = sample
        if batch_data not in batch_output_locations:
            print(f"Skipping validation of {batch_data.data_location} - job didn't finish")
            continue

        print(f"Validating job {batch_data.data_location}")
        batch_ch_job = results[validation_idx][1]
        batch_output_location = batch_output_locations[batch_data]
        test_file = batch_output_location / f"{sample_idx}.png"
        reported_hash = batch_ch_job.result.artifacts.get(f"/artifacts/{sample_idx}.png.sha256")
        trusted_hash = validation_ch_job.result.artifacts.get(f"/artifacts/{validation_idx}.png.sha256")

        print("Test file:", test_file)
        print("Reported hash:", reported_hash)
        print("Trusted hash:", trusted_hash)
        if reported_hash == trusted_hash:
            print(f"Batch job {batch_data.data_location} validation passed.")
        else:
            related_ch_job = results[validation_idx][1]
            print(f"(!) Batch job {batch_data.data_location} validation failed.")
            print(f"Reporting cheated job back to ComputeHorde: {related_ch_job.uuid}")
            await get_ch_client().report_cheated_job(related_ch_job.uuid)

semaphore = asyncio.Semaphore(2)
async def drive_batch_job(job_data: ImageGenerationBatchData) -> tuple[ImageGenerationBatchData, ch.ComputeHordeJob]:
    async with semaphore:
        await asyncio.sleep(3)
        spec = job_data.as_ch_job_spec()

        print("Submitting batch job:", job_data)

        try:
            job = await get_ch_client().run_until_complete(spec, max_attempts=3, timeout=120)
            print(f"Batch job {job.status}: {job_data}")
        except ch.ComputeHordeJobTimeoutError:
            print("Batch job timed out:", job_data)

        if job.status != ch.ComputeHordeJobStatus.COMPLETED:
            raise Exception(f"Batch job {job_data} failed with status {job.status}")

        return job_data, job


if __name__ == "__main__":
    asyncio.run(main())
