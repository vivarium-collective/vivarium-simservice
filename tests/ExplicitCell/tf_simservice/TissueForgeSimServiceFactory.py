from simservice.managers import ServiceManagerLocal
from simservice.service_wraps import TypeProcessWrap
from simservice.service_factory import process_factory
from .TissueForgeSimService import TissueForgeSimService

SERVICE_NAME = "TissueForgeSubcellularSimService"


class TissueForgeSimServiceWrap(TypeProcessWrap):
    _process_cls = TissueForgeSimService


ServiceManagerLocal.register_service(SERVICE_NAME, TissueForgeSimServiceWrap)


def tissue_forge_simservice(*args, **kwargs):
    return process_factory(SERVICE_NAME, *args, **kwargs)
