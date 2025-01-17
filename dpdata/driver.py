"""Driver plugin system."""
from typing import Callable, List, Union, TYPE_CHECKING
from .plugin import Plugin
from abc import ABC, abstractmethod

if TYPE_CHECKING:
    import ase

class Driver(ABC):
    """The base class for a driver plugin. A driver can
    label a pure System to generate the LabeledSystem.

    See Also
    --------
    dpdata.plugins.deepmd.DPDriver : an example of Driver
    """
    __DriverPlugin = Plugin()

    @staticmethod
    def register(key: str) -> Callable:
        """Register a driver plugin. Used as decorators.
        
        Parameter
        ---------
        key: str
            key of the plugin.
        
        Returns
        -------
        Callable
            decorator of a class

        Examples
        --------
        >>> @Driver.register("some_driver")
        ... class SomeDriver(Driver):
        ...     pass
        """
        return Driver.__DriverPlugin.register(key)

    @staticmethod
    def get_driver(key: str) -> "Driver":
        """Get a driver plugin.
        
        Parameter
        ---------
        key: str
            key of the plugin.
        
        Returns
        -------
        Driver
            the specific driver class
        
        Raises
        ------
        RuntimeError
            if the requested driver is not implemented
        """
        try:
            return Driver.__DriverPlugin.plugins[key]
        except KeyError as e:
            raise RuntimeError('Unknown driver: ' + key) from e
    
    def __init__(self, *args, **kwargs) -> None:
        """Setup the driver."""

    @abstractmethod
    def label(self, data: dict) -> dict:
        """Label a system data. Returns new data with energy, forces, and virials.
        
        Parameters
        ----------
        data : dict
            data with coordinates and atom types
        
        Returns
        -------
        dict
            labeled data with energies and forces
        """
        return NotImplemented

    @property
    def ase_calculator(self) -> "ase.calculators.calculator.Calculator":
        """Returns an ase calculator based on this driver."""
        from .ase_calculator import DPDataCalculator
        return DPDataCalculator(self)


@Driver.register("hybrid")
class HybridDriver(Driver):
    """Hybrid driver, with mixed drivers.

    Parameters
    ----------
    drivers : list[dict, Driver]
        list of drivers or drivers dict. For a dict, it should
        contain `type` as the name of the driver, and others
        are arguments of the driver.

    Raises
    ------
    TypeError
        The value of `drivers` is not a dict or `Driver`.

    Examples
    --------
    >>> driver = HybridDriver([
    ...     {"type": "sqm", "qm_theory": "DFTB3"},
    ...     {"type": "dp", "dp": "frozen_model.pb"},
    ... ])
    This driver is the hybrid of SQM and DP.
    """
    def __init__(self, drivers: List[Union[dict, Driver]]) -> None:
        self.drivers = []
        for driver in drivers:
            if isinstance(driver, Driver):
                self.drivers.append(driver)
            elif isinstance(driver, dict):
                type = driver["type"]
                del driver["type"]
                self.drivers.append(Driver.get_driver(type)(**driver))
            else:
                raise TypeError("driver should be Driver or dict")

    def label(self, data: dict) -> dict:
        """Label a system data.

        Energies and forces are the sum of those of each driver.
        
        Parameters
        ----------
        data : dict
            data with coordinates and atom types
        
        Returns
        -------
        dict
            labeled data with energies and forces
        """
        for ii, driver in enumerate(self.drivers):
            lb_data = driver.label(data.copy())
            if ii == 0:
                labeled_data = lb_data.copy()
            else:
                labeled_data['energies'] += lb_data ['energies']
                labeled_data['forces'] += lb_data ['forces']
        return labeled_data
