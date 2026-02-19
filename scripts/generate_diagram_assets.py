"""
Generate diagram assets from docs/diagrams/diagram_definitions.json.

Outputs:
- docs/diagrams/*.svg
- docs/diagrams/system_architecture.drawio
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from xml.sax.saxutils import escape


ROOT = Path(__file__).resolve().parents[1]
DEFS_PATH = ROOT / "docs" / "diagrams" / "diagram_definitions.json"
OUT_DIR = ROOT / "docs" / "diagrams"
DRAWIO_PATH = OUT_DIR / "system_architecture.drawio"


def _node_center(node: dict) -> tuple[float, float]:
    return (float(node["x"]) + float(node["w"]) / 2.0, float(node["y"]) + float(node["h"]) / 2.0)


def _svg_for_diagram(diagram: dict) -> str:
    width = int(diagram["width"])
    height = int(diagram["height"])
    nodes = {n["id"]: n for n in diagram["nodes"]}

    parts: list[str] = []
    parts.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">')
    parts.append(
        "<defs>"
        "<marker id='arrow' markerWidth='10' markerHeight='10' refX='9' refY='3' orient='auto' markerUnits='strokeWidth'>"
        "<path d='M0,0 L10,3 L0,6 z' fill='#444'/>"
        "</marker>"
        "<style>"
        "text{font-family:Segoe UI,Arial,sans-serif; fill:#222; font-size:14px;}"
        ".title{font-size:26px; font-weight:700;}"
        ".edge{stroke:#444; stroke-width:2; fill:none; marker-end:url(#arrow);}"
        ".edgeLabel{font-size:12px; fill:#333;}"
        ".node{stroke:#2f2f2f; stroke-width:1.2; rx:10; ry:10;}"
        ".nodeLabel{font-size:13px; font-weight:600;}"
        "</style>"
        "</defs>"
    )
    parts.append("<rect x='0' y='0' width='100%' height='100%' fill='#ffffff'/>")
    parts.append(f"<text class='title' x='30' y='48'>{escape(diagram['title'])}</text>")

    # Edges first
    for edge in diagram["edges"]:
        source = nodes[edge["source"]]
        target = nodes[edge["target"]]
        sx, sy = _node_center(source)
        tx, ty = _node_center(target)
        parts.append(f"<line class='edge' x1='{sx:.1f}' y1='{sy:.1f}' x2='{tx:.1f}' y2='{ty:.1f}'/>")
        label = edge.get("label", "")
        if label:
            mx = (sx + tx) / 2.0
            my = (sy + ty) / 2.0 - 6.0
            parts.append(f"<text class='edgeLabel' x='{mx:.1f}' y='{my:.1f}' text-anchor='middle'>{escape(label)}</text>")

    # Nodes
    for node in diagram["nodes"]:
        x = int(node["x"])
        y = int(node["y"])
        w = int(node["w"])
        h = int(node["h"])
        fill = node.get("fill", "#f4f4f4")
        parts.append(f"<rect class='node' x='{x}' y='{y}' width='{w}' height='{h}' fill='{fill}'/>")
        # center text (single line for consistency)
        cx = x + w / 2.0
        cy = y + h / 2.0 + 5
        parts.append(f"<text class='nodeLabel' x='{cx:.1f}' y='{cy:.1f}' text-anchor='middle'>{escape(node['label'])}</text>")

    parts.append("</svg>")
    return "".join(parts)


def _drawio_style(fill: str) -> str:
    return (
        "rounded=1;whiteSpace=wrap;html=1;arcSize=8;"
        f"fillColor={fill};strokeColor=#2f2f2f;fontSize=12;fontStyle=1;"
    )


def _drawio_diagram_xml(diagram: dict) -> str:
    cell_lines: list[str] = []
    cell_lines.append("<mxCell id='0'/>")
    cell_lines.append("<mxCell id='1' parent='0'/>")

    node_cell_id: dict[str, str] = {}
    next_id = 2

    for node in diagram["nodes"]:
        cid = str(next_id)
        next_id += 1
        node_cell_id[node["id"]] = cid
        style = _drawio_style(node.get("fill", "#f4f4f4"))
        val = escape(node["label"])
        x = int(node["x"])
        y = int(node["y"])
        w = int(node["w"])
        h = int(node["h"])
        cell_lines.append(
            f"<mxCell id='{cid}' value='{val}' style='{style}' vertex='1' parent='1'>"
            f"<mxGeometry x='{x}' y='{y}' width='{w}' height='{h}' as='geometry'/>"
            "</mxCell>"
        )

    edge_style = "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;endArrow=block;endFill=1;"
    for edge in diagram["edges"]:
        cid = str(next_id)
        next_id += 1
        src = node_cell_id[edge["source"]]
        tgt = node_cell_id[edge["target"]]
        val = escape(edge.get("label", ""))
        cell_lines.append(
            f"<mxCell id='{cid}' value='{val}' style='{edge_style}' edge='1' parent='1' source='{src}' target='{tgt}'>"
            "<mxGeometry relative='1' as='geometry'/>"
            "</mxCell>"
        )

    # Title node
    title_id = str(next_id)
    title_style = "text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;fontSize=20;fontStyle=1;"
    title = escape(diagram["title"])
    cell_lines.append(
        f"<mxCell id='{title_id}' value='{title}' style='{title_style}' vertex='1' parent='1'>"
        "<mxGeometry x='20' y='16' width='900' height='32' as='geometry'/>"
        "</mxCell>"
    )

    root = "".join(cell_lines)
    return (
        "<mxGraphModel dx='1320' dy='740' grid='1' gridSize='10' guides='1' tooltips='1' connect='1' arrows='1' fold='1' "
        "page='1' pageScale='1' pageWidth='1920' pageHeight='1080' math='0' shadow='0'>"
        f"<root>{root}</root>"
        "</mxGraphModel>"
    )


def _write_drawio(diagrams: list[dict]) -> None:
    diagram_xml_parts: list[str] = []
    for i, d in enumerate(diagrams, start=1):
        did = f"{i}-{uuid.uuid4().hex[:10]}"
        model_xml = _drawio_diagram_xml(d)
        diagram_xml_parts.append(f"<diagram id='{did}' name='{escape(d['id'])}'>{model_xml}</diagram>")

    mxfile = (
        "<mxfile host='app.diagrams.net' modified='2026-02-19T00:00:00.000Z' agent='Codex' version='24.7.0' editor='draw.io'>"
        + "".join(diagram_xml_parts)
        + "</mxfile>"
    )
    DRAWIO_PATH.write_text(mxfile, encoding="utf-8")


def main() -> None:
    data = json.loads(DEFS_PATH.read_text(encoding="utf-8"))
    diagrams = data["diagrams"]
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    for d in diagrams:
        svg = _svg_for_diagram(d)
        out_path = OUT_DIR / f"{d['id']}.svg"
        out_path.write_text(svg, encoding="utf-8")

    _write_drawio(diagrams)
    print(f"Generated {len(diagrams)} SVG files and {DRAWIO_PATH.name}")


if __name__ == "__main__":
    main()
