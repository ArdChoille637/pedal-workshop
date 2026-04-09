from api.suppliers.base import SupplierAdapter

_ADAPTERS: dict[str, type[SupplierAdapter]] = {}


def register_adapter(slug: str, adapter_cls: type[SupplierAdapter]):
    _ADAPTERS[slug] = adapter_cls


def get_adapter(slug: str) -> SupplierAdapter | None:
    cls = _ADAPTERS.get(slug)
    if cls:
        return cls()
    return None


# Register available adapters
from api.suppliers.tayda import TaydaAdapter  # noqa: E402
from api.suppliers.mouser import MouserAdapter  # noqa: E402
from api.suppliers.digikey import DigiKeyAdapter  # noqa: E402
from api.suppliers.smallbear import SmallBearAdapter  # noqa: E402
from api.suppliers.lovemyswitches import LoveMySwitchesAdapter  # noqa: E402
from api.suppliers.mammoth import MammothAdapter  # noqa: E402
from api.suppliers.pcbway import PCBWayAdapter  # noqa: E402

register_adapter("tayda", TaydaAdapter)
register_adapter("mouser", MouserAdapter)
register_adapter("digikey", DigiKeyAdapter)
register_adapter("smallbear", SmallBearAdapter)
register_adapter("lovemyswitches", LoveMySwitchesAdapter)
register_adapter("mammoth", MammothAdapter)
register_adapter("pcbway", PCBWayAdapter)
