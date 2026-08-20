"""
Workspace Validator & Coordinate Frame Transformer
Computes local arm reference frames and checks reachability limits for 5-bar linkage arms.
"""
import math
from typing import Tuple, Dict, Any
from .models import Pad

class WorkspaceValidator:
    def __init__(
        self,
        l0: float = 80.0,
        l1: float = 35.0,
        l2: float = 70.0,
        arm_spacing_d: float = 115.0
    ):
        self.l0 = l0
        self.l1 = l1
        self.l2 = l2
        self.max_reach = l1 + l2
        self.min_reach = abs(l1 - l2)
        self.d = arm_spacing_d

    def global_to_local(self, arm_id: int, global_x: float, global_y: float) -> Tuple[float, float]:
        """
        Transforms global PCB coordinate (mm) to local arm reference frame.
        Arm 0: (x, y) = (global_x, global_y)
        Arm 1: (x, y) = (-global_x, D - global_y)
        """
        if arm_id == 0:
            return global_x, global_y
        elif arm_id == 1:
            return -global_x, self.d - global_y
        else:
            raise ValueError(f"Invalid arm_id: {arm_id}. Must be 0 or 1.")

    def is_reachable(self, arm_id: int, global_x: float, global_y: float) -> bool:
        """
        Validates if target global point is reachable by the specified 5-bar linkage arm.
        """
        local_x, local_y = self.global_to_local(arm_id, global_x, global_y)

        # Distance to Base Motor A (-L0/2, 0)
        d1_sq = (self.l0 / 2.0 + local_x)**2 + local_y**2
        d1 = math.sqrt(d1_sq)

        # Distance to Base Motor B (+L0/2, 0)
        d2_sq = (self.l0 / 2.0 - local_x)**2 + local_y**2
        d2 = math.sqrt(d2_sq)

        # Triangle inequality & singularity check
        if d1 > self.max_reach or d1 < self.min_reach:
            return False
        if d2 > self.max_reach or d2 < self.min_reach:
            return False

        # Y must be positive (above motor base line)
        if local_y <= 5.0:  # 5mm safety boundary from base line
            return False

        return True

    def validate_pad_pair(self, pad_a: Pad, pad_b: Pad) -> Tuple[bool, str]:
        """
        Validates if Pad A can be probed by Arm 0 and Pad B can be probed by Arm 1.
        """
        arm0_ok = self.is_reachable(0, pad_a.x, pad_a.y)
        if not arm0_ok:
            return False, f"Pad A ({pad_a.pad_id} at {pad_a.x:.1f},{pad_a.y:.1f}) is out of reach for Arm 0."

        arm1_ok = self.is_reachable(1, pad_b.x, pad_b.y)
        if not arm1_ok:
            return False, f"Pad B ({pad_b.pad_id} at {pad_b.x:.1f},{pad_b.y:.1f}) is out of reach for Arm 1."

        return True, "Reachable"
