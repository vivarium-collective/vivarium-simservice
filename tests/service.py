from vivarium_simservice.simservice_process import SimserviceProcess
from tests.RandomWalker.RandomWalkerFactory import ServiceManagerLocal


def test_simservice():
    process = SimserviceProcess({
        'service_name': 'RandomWalkerService',
        'args': [1.0],
        'kwargs': {}})

    pos = process.service.get_pos()

    assert pos == 1.0


if __name__ == '__main__':
    test_simservice()
