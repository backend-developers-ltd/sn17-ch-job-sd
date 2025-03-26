import asyncio

import compute_horde_sdk.v1 as ch

import settings

prompt = "A bright yellow chanterelle mushroom with wavy edges and a firm, twisting stem."

async def main():
    client = ch.ComputeHordeClient(
        hotkey=settings.BT_WALLET.hotkey, # For authentication and authorization
        compute_horde_validator_hotkey=settings.CH_RELAY_VALIDATOR_SS58_ADDRESS,
        facilitator_url=settings.CH_FACILITATOR_URL,
    )

    job_spec = ch.ComputeHordeJobSpec(
        executor_class=ch.ExecutorClass.always_on__llm__a6000,
        job_namespace="sn17-sd15-v1",
        docker_image="kkowalskireef/sn17-ch-sd15",
        args=["image_generator.py", "--seed", "123", "--prompt", prompt],
        artifacts_dir="/out",
        input_volumes={}
    )

    created_job = await client.create_job(job_spec)
    await created_job.wait()
    print(created_job.status, created_job.result.stdout)

if __name__ == '__main__':
    asyncio.run(main())