"""Software-only, two-tier local ECG service-loop prototype.

All results produced by this package are software simulation/runtime evidence;
physical hardware deployment is outside the current study scope.
"""

from .contracts import Acknowledgement, ActionRecord, ECGPacket, GatewayEvent

__all__ = ["Acknowledgement", "ActionRecord", "ECGPacket", "GatewayEvent"]
