import base64
import dataclasses
import random
import shutil
import tempfile
import uuid
from functools import cache, cached_property
from io import BytesIO
from pathlib import Path
from typing import cast
from zipfile import ZipFile

import aiohttp
import boto3
from compute_horde_sdk import v1 as ch

import settings


@dataclasses.dataclass(frozen=True)
class Batch:
    seed: int
    data_location: Path
    output_location: Path

    @cached_property
    def prompts(self) -> list[str]:
        return (self.data_location / "prompts.txt").read_text().splitlines()

    @cached_property
    def sample_prompt_idx(self) -> int:
        return random.randint(0, len(self.prompts) - 1)

    @cached_property
    def sample_prompt(self) -> str:
        return self.prompts[self.sample_prompt_idx]

    @cached_property
    def download_url(self) -> str:
        return generate_s3_download_url(self.s3_key)

    @cached_property
    def upload_url(self) -> str:
        return generate_s3_upload_url(self.s3_key)

    @cached_property
    def s3_key(self) -> str:
        # Has to be unique between jobs
        return uuid.uuid4().hex

    def as_ch_job_spec(
        self,
        expected_input_download_time: int,
        expected_execution_time: int,
        expected_results_upload_time: int,
    ) -> ch.ComputeHordeJobSpec:
        return ch.ComputeHordeJobSpec(
            executor_class=ch.ExecutorClass.always_on__llm__a6000,
            job_namespace=settings.JOB_NAMESPACE,
            docker_image=settings.JOB_DOCKER_IMAGE,
            input_volumes={
                "/volume/batch": directory_to_volume(self.data_location),
            },
            output_volumes={
                "/output/images.zip": ch.HTTPOutputVolume(
                    http_method="PUT",
                    url=self.upload_url,
                )
            },
            artifacts_dir="/artifacts",
            args=[
                "batch_generator.py",
                "--seed",
                str(self.seed),
                "--prompts-file",
                "/volume/batch/prompts.txt",
                "--output-file",
                "/output/images.zip",
                "--artifacts-directory",
                "/artifacts",
            ],
            download_time_limit_sec=expected_input_download_time,
            execution_time_limit_sec=expected_execution_time,
            upload_time_limit_sec=expected_results_upload_time,
        )

    def __str__(self) -> str:
        return str(self.data_location.name)


@dataclasses.dataclass(frozen=True)
class ValidationData:
    batches: list[Batch]

    def as_ch_job_spec(
        self,
        expected_input_download_time: int,
        expected_execution_time: int,
        expected_results_upload_time: int,
    ) -> ch.ComputeHordeJobSpec:
        return ch.ComputeHordeJobSpec(
            executor_class=ch.ExecutorClass.always_on__llm__a6000,
            job_namespace=settings.JOB_NAMESPACE,
            docker_image=settings.JOB_DOCKER_IMAGE,
            input_volumes={"/volume/batch": self.build_input_volume()},
            output_volumes={},
            artifacts_dir="/artifacts",
            args=[
                "batch_generator.py",
                "--seed",
                str(self.batches[0].seed),  # assume all batches share the same seed
                "--prompts-file",
                "/volume/batch/prompts.txt",
                "--output-file",
                "/output/images.zip",
                "--artifacts-directory",
                "/artifacts",
            ],
            download_time_limit_sec=expected_input_download_time,
            execution_time_limit_sec=expected_execution_time,
            upload_time_limit_sec=expected_results_upload_time,
        )

    def build_input_volume(self) -> ch.InputVolume:
        contents = "\n".join(batch.sample_prompt for batch in self.batches)
        return ch.InlineInputVolume.from_file_contents(
            "prompts.txt",
            contents=contents,
            compress=True,
        )


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


@cache
def get_ch_client() -> ch.ComputeHordeClient:
    return ch.ComputeHordeClient(
        hotkey=settings.BT_WALLET.hotkey,  # For authentication and authorization
        compute_horde_validator_hotkey=settings.CH_RELAY_VALIDATOR_SS58_ADDRESS,
        facilitator_url=settings.CH_FACILITATOR_URL,
    )


def generate_s3_upload_url(key: str) -> str:
    s3 = get_s3_client()
    url = s3.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": settings.AWS_S3_BUCKET_NAME,
            "Key": f"images/{key}",
        },
        ExpiresIn=600,
    )
    return cast(str, url)


def generate_s3_download_url(key: str, ttl_seconds: int = 60 * 60 * 2) -> str:
    s3 = get_s3_client()
    url = s3.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": settings.AWS_S3_BUCKET_NAME,
            "Key": f"images/{key}",
        },
        ExpiresIn=ttl_seconds,
    )
    return cast(str, url)


def directory_to_volume(directory: Path) -> ch.InlineInputVolume:
    directory = directory.absolute()

    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = Path(tmpdir) / "volume.zip"
        shutil.make_archive(str(zip_path.with_suffix("")), "zip", directory)
        with open(zip_path, "rb") as zip_file:
            return ch.InlineInputVolume(
                contents=base64.b64encode(zip_file.read()).decode(),
            )


async def download_and_unpack_zip(url: str, into: Path) -> None:
    into.mkdir(parents=True, exist_ok=True)
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            buf = BytesIO(await response.read())
            with ZipFile(buf, "r") as zf:
                zf.extractall(into)
