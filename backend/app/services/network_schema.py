"""Network schema generator - creates SVG diagram from network topology."""

import io
import math
from typing import Any

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, Circle, Rectangle, FancyArrowPatch
import networkx as nx


def generate_network_schema(
    elements: dict[str, Any],
    results: list[dict] | None = None,
    width: float = 12,
    height: float = 8,
    format: str = "svg"
) -> bytes:
    """
    Generate network single-line diagram from topology.

    Args:
        elements: Network elements dictionary
        results: Optional calculation results to display on nodes
        width: Figure width in inches
        height: Figure height in inches
        format: Output format ('svg' or 'png')

    Returns:
        Image bytes (SVG or PNG)
    """
    # Build networkx graph
    G = nx.Graph()

    # Extract busbars and their voltage levels
    busbars = {bus['id']: bus for bus in elements.get('busbars', [])}

    # Group buses by voltage level for hierarchical layout
    voltage_levels = {}
    for bus_id, bus in busbars.items():
        un = bus.get('Un', 0)
        if un not in voltage_levels:
            voltage_levels[un] = []
        voltage_levels[un].append(bus_id)
        G.add_node(bus_id, type='busbar', Un=un, name=bus.get('name', bus_id))

    # Add edges for lines
    for line in elements.get('lines', []):
        G.add_edge(
            line['bus_from'], line['bus_to'],
            type='line', id=line['id'],
            name=line.get('name', line['id'])
        )

    # Add edges for transformers
    for tr in elements.get('transformers_2w', []):
        G.add_edge(
            tr['bus_hv'], tr['bus_lv'],
            type='transformer', id=tr['id'],
            name=tr.get('name', tr['id'])
        )

    for tr in elements.get('transformers_3w', []):
        # Create virtual node for 3W transformer center
        center_id = f"_tr3w_{tr['id']}"
        G.add_node(center_id, type='transformer_3w_center')
        G.add_edge(tr['bus_hv'], center_id, type='transformer_3w', id=tr['id'])
        G.add_edge(tr['bus_mv'], center_id, type='transformer_3w', id=tr['id'])
        G.add_edge(tr['bus_lv'], center_id, type='transformer_3w', id=tr['id'])

    for at in elements.get('autotransformers', []):
        G.add_edge(
            at['bus_hv'], at['bus_lv'],
            type='autotransformer', id=at['id'],
            name=at.get('name', at['id'])
        )

    # Track attached elements for display
    attached = {bus_id: [] for bus_id in busbars}

    for grid in elements.get('external_grids', []):
        if grid['bus_id'] in attached:
            attached[grid['bus_id']].append(('grid', grid))

    for gen in elements.get('generators', []):
        if gen['bus_id'] in attached:
            attached[gen['bus_id']].append(('generator', gen))

    for motor in elements.get('motors', []):
        if motor['bus_id'] in attached:
            attached[motor['bus_id']].append(('motor', motor))

    # Create results lookup
    results_lookup = {}
    if results:
        for r in results:
            bus_id = r.get('bus_id')
            fault_type = r.get('fault_type')
            if bus_id not in results_lookup:
                results_lookup[bus_id] = {}
            results_lookup[bus_id][fault_type] = r

    # Calculate hierarchical layout based on voltage levels
    sorted_voltages = sorted(voltage_levels.keys(), reverse=True)
    pos = {}
    y_step = height / (len(sorted_voltages) + 1)

    for i, voltage in enumerate(sorted_voltages):
        buses_at_level = voltage_levels[voltage]
        x_step = width / (len(buses_at_level) + 1)
        y = height - (i + 1) * y_step

        for j, bus_id in enumerate(buses_at_level):
            x = (j + 1) * x_step
            pos[bus_id] = (x, y)

    # Position virtual nodes for 3W transformers
    for node in G.nodes():
        if G.nodes[node].get('type') == 'transformer_3w_center':
            neighbors = list(G.neighbors(node))
            if neighbors:
                avg_x = sum(pos.get(n, (width/2, height/2))[0] for n in neighbors if n in pos) / len([n for n in neighbors if n in pos])
                avg_y = sum(pos.get(n, (width/2, height/2))[1] for n in neighbors if n in pos) / len([n for n in neighbors if n in pos])
                pos[node] = (avg_x, avg_y)

    # Create figure
    fig, ax = plt.subplots(1, 1, figsize=(width, height))
    ax.set_xlim(-0.5, width + 0.5)
    ax.set_ylim(-0.5, height + 0.5)
    ax.set_aspect('equal')
    ax.axis('off')

    # Draw edges (lines, transformers)
    for u, v, data in G.edges(data=True):
        if u not in pos or v not in pos:
            continue

        x1, y1 = pos[u]
        x2, y2 = pos[v]

        edge_type = data.get('type', 'line')

        if edge_type == 'line':
            ax.plot([x1, x2], [y1, y2], 'k-', linewidth=1.5, zorder=1)
        elif edge_type in ('transformer', 'autotransformer'):
            # Draw transformer symbol (two circles)
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            r = 0.15

            # Calculate direction
            dx, dy = x2 - x1, y2 - y1
            length = math.sqrt(dx*dx + dy*dy)
            if length > 0:
                dx, dy = dx/length, dy/length

            # Draw lines to transformer
            ax.plot([x1, mx - dx*r*1.5], [y1, my - dy*r*1.5], 'k-', linewidth=1.5, zorder=1)
            ax.plot([mx + dx*r*1.5, x2], [my + dy*r*1.5, y2], 'k-', linewidth=1.5, zorder=1)

            # Draw circles
            circle1 = Circle((mx - dx*r*0.7, my - dy*r*0.7), r, fill=False,
                            edgecolor='black', linewidth=1.5, zorder=2)
            circle2 = Circle((mx + dx*r*0.7, my + dy*r*0.7), r, fill=False,
                            edgecolor='black', linewidth=1.5, zorder=2)
            ax.add_patch(circle1)
            ax.add_patch(circle2)
        elif edge_type == 'transformer_3w':
            ax.plot([x1, x2], [y1, y2], 'k-', linewidth=1.5, zorder=1)

    # Draw busbars
    for bus_id, bus in busbars.items():
        if bus_id not in pos:
            continue

        x, y = pos[bus_id]
        un = bus.get('Un', 0)
        name = bus.get('name', bus_id)

        # Draw busbar as thick horizontal line
        bar_width = 0.8
        ax.plot([x - bar_width/2, x + bar_width/2], [y, y],
               'k-', linewidth=6, solid_capstyle='butt', zorder=3)

        # Label with name and voltage
        label = f"{name}\n{un} kV"

        # Add results if available
        if bus_id in results_lookup:
            ik3 = results_lookup[bus_id].get('Ik3', {}).get('Ik')
            ip3 = results_lookup[bus_id].get('Ik3', {}).get('ip')
            if ik3:
                label += f"\nIk3={ik3:.2f} kA"
            if ip3:
                label += f"\nip={ip3:.2f} kA"

        ax.text(x, y + 0.3, label, ha='center', va='bottom', fontsize=8,
               fontweight='bold', zorder=5)

    # Draw attached elements (grids, generators, motors)
    for bus_id, items in attached.items():
        if bus_id not in pos or not items:
            continue

        x, y = pos[bus_id]

        for i, (item_type, item) in enumerate(items):
            # Offset below busbar
            offset_y = -0.4 - i * 0.5

            if item_type == 'grid':
                # External grid: square with arrow
                rect = Rectangle((x - 0.15, y + offset_y - 0.15), 0.3, 0.3,
                                fill=True, facecolor='lightgray',
                                edgecolor='black', linewidth=1.5, zorder=4)
                ax.add_patch(rect)
                ax.annotate('', xy=(x, y + offset_y + 0.25),
                           xytext=(x, y + offset_y + 0.05),
                           arrowprops=dict(arrowstyle='->', color='black', lw=1.5),
                           zorder=5)
                ax.plot([x, x], [y, y + offset_y + 0.15], 'k-', linewidth=1.5, zorder=1)

            elif item_type == 'generator':
                # Generator: circle with G
                ax.plot([x, x], [y, y + offset_y + 0.15], 'k-', linewidth=1.5, zorder=1)
                circle = Circle((x, y + offset_y), 0.15, fill=True,
                               facecolor='white', edgecolor='black',
                               linewidth=1.5, zorder=4)
                ax.add_patch(circle)
                ax.text(x, y + offset_y, 'G', ha='center', va='center',
                       fontsize=10, fontweight='bold', zorder=5)

            elif item_type == 'motor':
                # Motor: circle with M
                ax.plot([x, x], [y, y + offset_y + 0.15], 'k-', linewidth=1.5, zorder=1)
                circle = Circle((x, y + offset_y), 0.15, fill=True,
                               facecolor='white', edgecolor='black',
                               linewidth=1.5, zorder=4)
                ax.add_patch(circle)
                ax.text(x, y + offset_y, 'M', ha='center', va='center',
                       fontsize=10, fontweight='bold', zorder=5)

    # Add title
    ax.text(width / 2, height + 0.3, 'Jednopólová schéma siete',
           ha='center', va='bottom', fontsize=12, fontweight='bold')

    # Save to bytes
    buf = io.BytesIO()
    plt.savefig(buf, format=format, bbox_inches='tight', dpi=150,
               facecolor='white', edgecolor='none')
    plt.close(fig)
    buf.seek(0)

    return buf.getvalue()
