"""
RS-274X Gerber & Excellon Drill File Parser
Extracts copper pad coordinates and flash targets for camera-less Flying Probe Testing.
"""
import re
from typing import List, Dict, Any, Tuple, Optional
from .models import Board, Component, Pad, Net

class GerberParser:
    def __init__(self):
        self.scale_factor = 1.0       # Converts to mm (inch -> 25.4, mm -> 1.0)
        self.x_digits_int = 2
        self.x_digits_dec = 4
        self.y_digits_int = 2
        self.y_digits_dec = 4

    def parse_file(self, gerber_path: str) -> Board:
        with open(gerber_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        return self.parse_string(content, board_name=gerber_path)

    def parse_string(self, content: str, board_name: str = "Gerber_Board") -> Board:
        lines = content.splitlines()
        apertures: Dict[str, Dict[str, Any]] = {}
        current_aperture = ""
        pads: List[Pad] = []
        cur_x = 0.0
        cur_y = 0.0
        pad_counter = 1

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 1. Unit Format (%MOIN*% or %MOMM*%)
            if '%MOIN*%' in line or 'INCH' in line:
                self.scale_factor = 25.4
            elif '%MOMM*%' in line or 'METRIC' in line:
                self.scale_factor = 1.0

            # 2. Format Specifier (%FSLAX24Y24*%)
            fs_match = re.search(r'%FSLAX(\d)(\d)Y(\d)(\d)\*%', line)
            if fs_match:
                self.x_digits_int = int(fs_match.group(1))
                self.x_digits_dec = int(fs_match.group(2))
                self.y_digits_int = int(fs_match.group(3))
                self.y_digits_dec = int(fs_match.group(4))

            # 3. Aperture Definition (%ADD10C,0.5000*%)
            ap_match = re.search(r'%ADD(\d+)([C,R,O,P])(?:,([\d\.]+)(?:X([\d\.]+))?)?\*%', line)
            if ap_match:
                ap_code = f"D{ap_match.group(1)}"
                ap_type = ap_match.group(2)
                dim1 = float(ap_match.group(3)) if ap_match.group(3) else 1.0
                dim2 = float(ap_match.group(4)) if ap_match.group(4) else dim1
                apertures[ap_code] = {
                    "type": ap_type,
                    "width": dim1 * self.scale_factor,
                    "height": dim2 * self.scale_factor
                }

            # 4. Aperture Select (D10*)
            ap_sel = re.match(r'^(D\d+)\*$', line)
            if ap_sel:
                current_aperture = ap_sel.group(1)

            # 5. Coordinate movement & Flash command (X1000Y2000D03*)
            coord_match = re.search(r'(?:X(-?\d+))?(?:Y(-?\d+))?(D0[123])?\*?', line)
            if coord_match:
                x_raw = coord_match.group(1)
                y_raw = coord_match.group(2)
                d_code = coord_match.group(3)

                if x_raw:
                    cur_x = self._parse_coord(x_raw, self.x_digits_dec) * self.scale_factor
                if y_raw:
                    cur_y = self._parse_coord(y_raw, self.y_digits_dec) * self.scale_factor

                # D03 = Flash (place pad at current location)
                if d_code == 'D03':
                    ap_info = apertures.get(current_aperture, {"type": "C", "width": 1.0, "height": 1.0})
                    pad = Pad(
                        pad_id=f"GERBER_PAD_{pad_counter}",
                        component_ref=f"P{pad_counter}",
                        pad_number="1",
                        x=cur_x,
                        y=cur_y,
                        width=ap_info["width"],
                        height=ap_info["height"],
                        shape="circle" if ap_info["type"] == "C" else "rect",
                        net_id=0,
                        net_name=f"GERBER_NET_{pad_counter}"
                    )
                    pads.append(pad)
                    pad_counter += 1

        board = Board(name=board_name, pads=pads)
        if pads:
            min_x = min(p.x for p in pads)
            max_x = max(p.x for p in pads)
            min_y = min(p.y for p in pads)
            max_y = max(p.y for p in pads)
            board.width = max_x - min_x
            board.height = max_y - min_y

            center_x = (min_x + max_x) / 2.0
            center_y = (min_y + max_y) / 2.0

            # Center board at (X=0.0, Y=57.5)
            for p in pads:
                p.x = p.x - center_x
                p.y = (p.y - center_y) + 57.5

        return board

    def _parse_coord(self, raw_str: str, decimal_digits: int) -> float:
        if not raw_str:
            return 0.0
        val = int(raw_str)
        return val / (10 ** decimal_digits)
