"""GeneFi Configuration - Gene + DeFi Evolution Engine"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # OKX OnchainOS
    OKX_API_KEY = os.getenv("OKX_API_KEY", "")
    OKX_SECRET_KEY = os.getenv("OKX_SECRET_KEY", "")
    OKX_PASSPHRASE = os.getenv("OKX_PASSPHRASE", "")
    OKX_BASE_URL = os.getenv("OKX_BASE_URL", "https://www.okx.com")

    # Claw Model
    CLAW_API_KEY = os.getenv("CLAW_API_KEY", "")
    CLAW_OPUS_MODEL = os.getenv("CLAW_OPUS_MODEL", "claw-opus-latest")
    CLAW_SONNET_MODEL = os.getenv("CLAW_SONNET_MODEL", "claw-sonnet-latest")

    # Evolution Parameters
    DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"
    POPULATION_SIZE = int(os.getenv("EVOLUTION_POPULATION_SIZE", "20"))
    MAX_GENERATIONS = int(os.getenv("EVOLUTION_GENERATIONS", "10"))
    MUTATION_RATE = float(os.getenv("MUTATION_RATE", "0.15"))
    SELECTION_PRESSURE = float(os.getenv("SELECTION_PRESSURE", "0.3"))

    # Execution Mode: "simulation" (local) | "demo_api" (OKX Demo Trading)
    EXECUTION_MODE = os.getenv("EXECUTION_MODE", "simulation")

    # Risk Controls
    MAX_POSITION_SIZE = float(os.getenv("MAX_POSITION_SIZE", "100"))  # USDT
    MAX_LEVERAGE_LIMIT = int(os.getenv("MAX_LEVERAGE_LIMIT", "20"))
    API_RATE_LIMIT_PER_SEC = int(os.getenv("API_RATE_LIMIT_PER_SEC", "5"))

    # Fitness Weights
    PNL_WEIGHT = 0.5
    FUNDING_WEIGHT = 0.3
    DRAWDOWN_WEIGHT = 0.2

    # Paths
    LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")

    @property
    def has_api_keys(self) -> bool:
        return bool(self.OKX_API_KEY and self.OKX_SECRET_KEY and self.OKX_PASSPHRASE)

    @property
    def can_trade(self) -> bool:
        return self.has_api_keys and self.EXECUTION_MODE == "demo_api"
