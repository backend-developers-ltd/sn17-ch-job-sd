import asyncio
import base64
import shutil
import tempfile
import uuid
from functools import cache
from pathlib import Path

import boto3

import compute_horde_sdk.v1 as ch

import settings

# TODO: Explain this
docker_image = "kkowalskireef/sn17-job-sd15:latest"
job_namespace = "kkowalskireef/sn17-job-sd15:latest"

@cache
def get_s3_client():
    s3_client_opts: dict[str, str] = {}
    if settings.AWS_S3_ENDPOINT:
        s3_client_opts["endpoint_url"] = settings.AWS_S3_ENDPOINT
    if settings.AWS_ACCESS_KEY_ID:
        s3_client_opts["aws_access_key_id"] = settings.AWS_ACCESS_KEY_ID
    if settings.AWS_SECRET_ACCESS_KEY:
        s3_client_opts["aws_secret_access_key"] = settings.AWS_SECRET_ACCESS_KEY
    if settings.AWS_REGION_NAME:
        s3_client_opts["region_name"] = settings.AWS_REGION_NAME
    s3 = boto3.client("s3", **s3_client_opts)
    return s3


def generate_upload_url(key: str):
    s3 = get_s3_client()
    return s3.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": settings.AWS_S3_BUCKET_NAME,
            "Key": f"images/{key}",
        },
        ExpiresIn=1200,
    )

def generate_download_url(key: str):
    s3 = get_s3_client()
    return s3.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": settings.AWS_S3_BUCKET_NAME,
            "Key": f"images/{key}",
        },
        ExpiresIn=7200,
    )

def directory_to_volume(directory: Path) -> ch.InlineInputVolume:
    directory = directory.absolute()

    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = Path(tmpdir) / "archive.zip"
        shutil.make_archive(str(zip_path.with_suffix('')), 'zip', directory)
        with open(zip_path, "rb") as zip_file:
            encoded_bytes = base64.b64encode(zip_file.read())

    return ch.InlineInputVolume(contents=encoded_bytes.decode())


async def main():
    uid = str(uuid.uuid4())

    client = ch.ComputeHordeClient(
        hotkey=settings.BT_WALLET.hotkey, # For authentication and authorization
        compute_horde_validator_hotkey=settings.CH_RELAY_VALIDATOR_SS58_ADDRESS,
        facilitator_url=settings.CH_FACILITATOR_URL,
    )

    job_spec = ch.ComputeHordeJobSpec(
        executor_class=ch.ExecutorClass.always_on__llm__a6000,
        job_namespace=job_namespace,
        docker_image=docker_image,
        input_volumes={
            "/volume/prompts": directory_to_volume(Path("./prompts")),
        },
        output_volumes={
            "/output/images.zip": ch.HTTPOutputVolume(
                http_method="PUT",
                url=generate_upload_url(uid),
            )
        },
        artifacts_dir="/artifacts",
        args=[
            "batch_generator.py",
            "--seed", "123",
            "--prompts-file", "/volume/prompts/prompts-batch-01.txt",
            "--output-file", "/output/images.zip",
        ],
    )

    created_job = await client.create_job(job_spec)

    while created_job.status not in {ch.ComputeHordeJobStatus.COMPLETED, ch.ComputeHordeJobStatus.FAILED, ch.ComputeHordeJobStatus.REJECTED}:
        await created_job.refresh_from_facilitator()
        print("Job status:", created_job.status)
        await asyncio.sleep(1)

    if created_job.status != ch.ComputeHordeJobStatus.COMPLETED:
        print("Job failed:", created_job.status)
        return

    download_url = generate_download_url(uid)
    print("Job finished!")
    print("Results available at:", download_url)
    print("URL will expire in 2 hours.")


if __name__ == '__main__':
    asyncio.run(main())