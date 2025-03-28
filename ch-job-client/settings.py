import bittensor
from decouple import config as _conf

CH_FACILITATOR_URL: str = _conf("CH_FACILITATOR_URL")
CH_FACILITATOR_TOKEN: str = _conf("CH_FACILITATOR_TOKEN")

JOB_NAMESPACE: str = _conf("JOB_NAMESPACE")
JOB_DOCKER_IMAGE: str = _conf("JOB_DOCKER_IMAGE")

CH_RELAY_VALIDATOR_SS58_ADDRESS: str = _conf("CH_RELAY_VALIDATOR_SS58_ADDRESS")

BT_WALLET: bittensor.Wallet = bittensor.wallet(
    name=_conf("BT_WALLET_NAME"),
    hotkey=_conf("BT_HOTKEY_NAME"),
)

AWS_S3_BUCKET_NAME: str = _conf("AWS_S3_BUCKET_NAME")

AWS_REGION_NAME: str | None = _conf("AWS_REGION_NAME", default=None)
AWS_ACCESS_KEY_ID: str | None = _conf("AWS_ACCESS_KEY_ID", default=None)
AWS_SECRET_ACCESS_KEY: str | None = _conf("AWS_SECRET_ACCESS_KEY", default=None)
AWS_S3_ENDPOINT: str | None = _conf("AWS_S3_ENDPOINT", default=None)
