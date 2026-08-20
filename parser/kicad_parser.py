"""
KiCad PCB S-Expression Parser
Extracts components, pad coordinates (using 2D rotation matrix math), and net assignments.
Supports KiCad v5, v6, v7, and v8 formats.
"""
import math
import re
from typing import List, Dict, Any, Tuple, Optional
from .models import Board, Component, Pad, Net

class SExpParser:
    """Simple robust S-expression tokenizer and parser for KiCad PCB files."""
    @staticmethod
    def parse(sexp_str: str) -> List[Any]:
        tokens = SExpParser._tokenize(sexp_str)
        if not tokens:
            return []
        parsed, _ = SExpParser._parse_tokens(tokens)
        if parsed and isinstance(parsed, list) and isinstance(parsed[0], list):
            return parsed[0]
        return parsed

    @staticmethod
    def _tokenize(s: str) -> List[str]:
        # Strip comments
        s = re.sub(r';.*$', '', s, flags=re.MULTILINE)
        token_pattern = re.compile(r'[()]|"(?:\\.|[^"\\])*"|[^\s()]+')
        return token_pattern.findall(s)

    @staticmethod
    def _parse_tokens(tokens: List[str], index: int = 0) -> Tuple[Any, int]:
        parsed = []
        i = index
        while i < len(tokens):
            token = tokens[i]
            if token == '(':
                sub, i = SExpParser._parse_tokens(tokens, i + 1)
                parsed.append(sub)
            elif token == ')':
                return parsed, i + 1
            else:
                # Unquote string if needed
                if token.startswith('"') and token.endswith('"'):
                    token = token[1:-1]
                parsed.append(token)
                i += 1
        return parsed, i


class KiCadPCBParser:
    def __init__(self):
        pass

    def parse_file(self, file_path: str) -> Board:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        return self.parse_string(content, board_name=file_path)

    def parse_string(self, content: str, board_name: str = "KiCad_Board") -> Board:
        sexp = SExpParser.parse(content)
        if not sexp or not isinstance(sexp, list) or sexp[0] != 'kicad_pcb':
            raise ValueError("Invalid KiCad PCB file format (missing 'kicad_pcb' root element).")

        board = Board(name=board_name)
        net_map: Dict[int, str] = {}
        components: List[Component] = []
        all_pads: List[Pad] = []

        # Step 1: Extract Nets
        for item in sexp:
            if isinstance(item, list) and len(item) >= 3 and item[0] == 'net':
                try:
                    net_id = int(item[1])
                    net_name = str(item[2])
                    net_map[net_id] = net_name
                    board.nets[net_name] = Net(net_id=net_id, name=net_name)
                except Exception:
                    continue

        # Step 2: Extract Footprints (Modules in v5, Footprints in v6+)
        for item in sexp:
            if isinstance(item, list) and (item[0] in ('footprint', 'module')):
                comp = self._parse_footprint(item, net_map)
                if comp:
                    components.append(comp)
                    all_pads.extend(comp.pads)
                    # Assign pads to nets
                    for pad in comp.pads:
                        if pad.net_name in board.nets:
                            board.nets[pad.net_name].pads.append(pad)

        board.components = components
        board.pads = all_pads

        # Step 3: Extract Board Edge.Cuts Outline Boundaries if available
        edge_coords_x = []
        edge_coords_y = []
        for item in sexp:
            if isinstance(item, list) and item and item[0] in ('gr_line', 'gr_rect', 'gr_arc', 'gr_circle', 'segment'):
                has_edge_layer = any(isinstance(sub, list) and len(sub) >= 2 and sub[0] == 'layer' and sub[1] in ('Edge.Cuts', 'Board.Outline') for sub in item)
                if has_edge_layer:
                    for sub in item:
                        if isinstance(sub, list) and len(sub) >= 3 and sub[0] in ('start', 'end', 'at'):
                            try:
                                edge_coords_x.append(float(sub[1]))
                                edge_coords_y.append(float(sub[2]))
                            except Exception:
                                pass

        # Calculate bounding box & normalize to self-centering vise centerpoint (0.0, 57.5)
        if edge_coords_x and edge_coords_y:
            min_x = min(edge_coords_x)
            max_x = max(edge_coords_x)
            min_y = min(edge_coords_y)
            max_y = max(edge_coords_y)
            board.width = max_x - min_x
            board.height = max_y - min_y
        elif all_pads:
            min_x = min(p.x for p in all_pads)
            max_x = max(p.x for p in all_pads)
            min_y = min(p.y for p in all_pads)
            max_y = max(p.y for p in all_pads)
            board.width = max_x - min_x
            board.height = max_y - min_y

        if all_pads:
            center_x = (min_x + max_x) / 2.0
            center_y = (min_y + max_y) / 2.0

            # Center board at (X=0.0, Y=57.5)
            for p in all_pads:
                p.x = p.x - center_x
                p.y = (p.y - center_y) + 57.5

        return board

    def _parse_footprint(self, fp_sexp: List[Any], net_map: Dict[int, str]) -> Optional[Component]:
        fp_name = fp_sexp[1] if len(fp_sexp) > 1 and isinstance(fp_sexp[1], str) else "Unknown"
        ref = "REF?"
        val = ""
        fp_x, fp_y, fp_rot = 0.0, 0.0, 0.0
        pads: List[Pad] = []

        for node in fp_sexp:
            if not isinstance(node, list) or not node:
                continue

            tag = node[0]
            if tag == 'at':
                fp_x = float(node[1]) if len(node) > 1 else 0.0
                fp_y = float(node[2]) if len(node) > 2 else 0.0
                fp_rot = float(node[3]) if len(node) > 3 else 0.0

            elif tag == 'property' and len(node) >= 3:
                prop_name = str(node[1])
                prop_val = str(node[2])
                if prop_name == "Reference":
                    ref = prop_val
                elif prop_name == "Value":
                    val = prop_val

            elif tag == 'fp_text':
                if len(node) >= 3:
                    text_type = node[1]
                    text_val = node[2]
                    if text_type == 'reference':
                        ref = str(text_val)
                    elif text_type == 'value':
                        val = str(text_val)

        # Parse pads
        for node in fp_sexp:
            if isinstance(node, list) and node and node[0] == 'pad':
                pad = self._parse_pad(node, ref, fp_x, fp_y, fp_rot, net_map)
                if pad:
                    pads.append(pad)

        comp_type = self._classify_component(ref, val)
        return Component(
            ref=ref,
            value=val,
            footprint=fp_name,
            x=fp_x,
            y=fp_y,
            rotation=fp_rot,
            comp_type=comp_type,
            pads=pads
        )

    def _parse_pad(
        self,
        pad_sexp: List[Any],
        comp_ref: str,
        fp_x: float,
        fp_y: float,
        fp_rot: float,
        net_map: Dict[int, str]
    ) -> Optional[Pad]:
        pad_num = str(pad_sexp[1]) if len(pad_sexp) > 1 else "1"
        pad_shape = str(pad_sexp[3]) if len(pad_sexp) > 3 else "rect"
        
        rel_x, rel_y, pad_rot = 0.0, 0.0, 0.0
        width, height = 1.0, 1.0
        layer = "F.Cu"
        net_id = 0
        net_name = ""

        for sub in pad_sexp[4:]:
            if not isinstance(sub, list) or not sub:
                continue
            
            tag = sub[0]
            if tag == 'at':
                rel_x = float(sub[1]) if len(sub) > 1 else 0.0
                rel_y = float(sub[2]) if len(sub) > 2 else 0.0
                pad_rot = float(sub[3]) if len(sub) > 3 else 0.0

            elif tag == 'size':
                width = float(sub[1]) if len(sub) > 1 else 1.0
                height = float(sub[2]) if len(sub) > 2 else 1.0

            elif tag == 'layers':
                layer = str(sub[1]) if len(sub) > 1 else "F.Cu"

            elif tag == 'net':
                if len(sub) >= 3:
                    net_id = int(sub[1])
                    net_name = str(sub[2])
                elif len(sub) >= 2:
                    net_id = int(sub[1])
                    net_name = net_map.get(net_id, f"Net-({comp_ref}-Pad{pad_num})")

        # Apply 2D Rotation Transformation Matrix
        # KiCad angle is in degrees (counter-clockwise or clockwise depending on convention)
        rad = math.radians(fp_rot)
        cos_a = math.cos(rad)
        sin_a = math.sin(rad)

        abs_x = fp_x + (rel_x * cos_a - rel_y * sin_a)
        abs_y = fp_y + (rel_x * sin_a + rel_y * cos_a)

        pad_id = f"{comp_ref}-{pad_num}"
        return Pad(
            pad_id=pad_id,
            component_ref=comp_ref,
            pad_number=pad_num,
            x=abs_x,
            y=abs_y,
            width=width,
            height=height,
            shape=pad_shape,
            layer=layer,
            net_id=net_id,
            net_name=net_name
        )

    def _classify_component(self, ref: str, val: str) -> str:
        ref_upper = ref.upper()
        if ref_upper.startswith('R'):
            return "resistor"
        elif ref_upper.startswith('C'):
            return "capacitor"
        elif ref_upper.startswith('D') or 'LED' in ref_upper:
            return "diode"
        elif ref_upper.startswith('U') or ref_upper.startswith('IC'):
            return "ic"
        elif ref_upper.startswith('J') or ref_upper.startswith('P') or ref_upper.startswith('CONN'):
            return "connector"
        elif ref_upper.startswith('TP'):
            return "testpoint"
        return "passive"
