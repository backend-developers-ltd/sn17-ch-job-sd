import bittensor_wallet
from decouple import config as _conf

CH_FACILITATOR_URL: str = _conf("CH_FACILITATOR_URL")

JOB_NAMESPACE: str = _conf("JOB_NAMESPACE")
JOB_DOCKER_IMAGE: str = _conf("JOB_DOCKER_IMAGE")

CH_RELAY_VALIDATOR_SS58_ADDRESS: str = _conf("CH_RELAY_VALIDATOR_SS58_ADDRESS")

BT_WALLET = bittensor_wallet.Wallet(
    name=_conf("BT_WALLET_NAME"),
    hotkey=_conf("BT_HOTKEY_NAME"),
)

R2_BUCKET_NAME: str = _conf("R2_BUCKET_NAME")
R2_ACCESS_KEY_ID: str | None = _conf("R2_ACCESS_KEY_ID", default=None)
R2_SECRET_ACCESS_KEY: str | None = _conf("R2_SECRET_ACCESS_KEY", default=None)
R2_ENDPOINT: str | None = _conf("R2_ENDPOINT", default=None)
