from abc import ABC, abstractmethod
from multiprocessing.shared_memory import SharedMemory
from sys import platform


class AbstractDataClass(ABC):
    """Outlines the data structure used to store the telemetry information"""

    @abstractmethod
    def update(self, memory_map):
        pass


class TelemetryReader:
    """This class allows you to hook into ETS2's telemetry stream and start reading from it"""

    # memory_location defined by
    # https://github.com/RenCloud/scs-sdk-plugin/blob/master/scs-telemetry/inc/scs-telemetry-common.hpp#L26
    # On Windows: "Local\\SCSTelemetry"
    # On macOS: "/SCSTelemetry" (POSIX shared memory)
    
    memory_map = None
    
    def __init__(self):
        """Initialise the telemetry reader, attempting the first hook"""
        self.hook_into_telemetry()

    def hook_into_telemetry(self):
        """Try to hook into the memory and start streaming information from it"""

        if self.memory_map is not None:
            # Have already hooked into the memory map. We do not do it again
            return

        try:
            # Get the correct memory location based on platform
            if platform == "win32":
                memory_location = "Local\\SCSTelemetry"
            elif platform == "darwin":
                # macOS uses POSIX shared memory names
                memory_location = "SCSTelemetry"
            else:
                # Linux and other platforms
                memory_location = "SCSTelemetry"
            
            self.memory_map = SharedMemory(memory_location)
        except FileNotFoundError:
            if platform == "win32":
                print(
                    f"ETS2's telemetry is not to be found. Make sure:"
                    f"\n1. ETS2 is running"
                    f"\n2. SCS Telemetry SDK plugin is installed"
                    f"\n3. Telemetry is enabled in ETS2 settings"
                )
            elif platform == "darwin":
                print(
                    f"ETS2's telemetry is not to be found. Make sure:"
                    f"\n1. ETS2 is running via Proton/Wine on macOS"
                    f"\n2. SCS Telemetry SDK plugin is installed"
                    f"\n3. Telemetry is enabled in ETS2 settings"
                    f"\n4. Wine is configured with POSIX shared memory support"
                )
            else:
                print(
                    f"ETS2's telemetry is not to be found. Telemetry is not enabled"
                )
        except Exception as e:
            print(f"Error connecting to telemetry: {e}")

    def update_telemetry(self, data_class: AbstractDataClass):
        """Read the telemetry data"""
        if self.memory_map is None:
            print("Telemetry stream is not open. Can not update!")
            return

        data_class.update(self.memory_map.buf)
