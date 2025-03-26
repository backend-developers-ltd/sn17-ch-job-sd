import bittensor
from decouple import config as _conf

CH_FACILITATOR_URL: str = _conf("CH_FACILITATOR_URL")
CH_FACILITATOR_TOKEN: str = _conf("CH_FACILITATOR_TOKEN")

# This validator will route and manage the job on ComputeHorde side
CH_RELAY_VALIDATOR_SS58_ADDRESS: str = _conf("CH_RELAY_VALIDATOR_SS58_ADDRESS")

# User for signing job requests
BT_WALLET: bittensor.Wallet = bittensor.wallet(
    name=_conf("BT_WALLET_NAME"),
    hotkey=_conf("BT_HOTKEY_NAME"),
)
