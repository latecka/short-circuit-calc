"""Network schema generator - creates professional single-line diagram from network topology."""

import io
import math
from typing import Any, Optional
from collections import defaultdict

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle, FancyBboxPatch
from matplotlib.font_manager import FontProperties

# Configure DejaVu font for diacritics support
try:
    FONT_PATH = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    FONT_BOLD_PATH = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
    FONT_PROP = FontProperties(fname=FONT_PATH)
    FONT_BOLD_PROP = FontProperties(fname=FONT_BOLD_PATH)
except Exception:
    FONT_PROP = FontProperties()
    FONT_BOLD_PROP = FontProperties(weight='bold')


# Colors for active/inactive elements
COLOR_ACTIVE = 'black'
COLOR_INACTIVE = '#999999'  # Gray for disabled elements
LINESTYLE_INACTIVE = (0, (5, 3))  # Dashed line for inactive


# Type alias for element activity checker function
from typing import Callable
ElementActiveChecker = Callable[[str, str], bool] | None


def _is_element_active(
    is_active_fn: ElementActiveChecker,
    element_type: str,
    element_id: str
) -> bool:
    """Check if element is active using the provided checker function."""
    if is_active_fn is None:
        return True
    return is_active_fn(element_type, element_id)


def generate_network_schema(
    elements: dict[str, Any],
    results: list[dict] | None = None,
    width: float = 12,
    height: float = 8,
    format: str = "svg",
    is_element_active_fn: ElementActiveChecker = None
) -> bytes:
    """
    Generate network single-line diagram from topology.

    Args:
        elements: Network elements dictionary
        results: Optional calculation results to display on nodes
        width: Base figure width in inches (auto-adjusted)
        height: Base figure height in inches (auto-adjusted)
        format: Output format ('svg' or 'png')
        is_element_active_fn: Optional function (element_type, element_id) -> bool
                              Elements where function returns False are drawn grayed out

    Returns:
        Image bytes (SVG or PNG)
    """
    # Extract busbars
    busbars = {bus['id']: bus for bus in elements.get('busbars', [])}

    if not busbars:
        # Return empty diagram
        fig, ax = plt.subplots(figsize=(width, height))
        ax.text(0.5, 0.5, 'Žiadne uzly v sieti', ha='center', va='center',
                fontproperties=FONT_PROP, fontsize=14)
        ax.axis('off')
        buf = io.BytesIO()
        plt.savefig(buf, format=format, bbox_inches='tight', dpi=150)
        plt.close(fig)
        buf.seek(0)
        return buf.getvalue()

    # ========== STEP 1: Group buses by voltage level ==========
    voltage_levels = defaultdict(list)
    for bus_id, bus in busbars.items():
        un = bus.get('Un', 0)
        voltage_levels[un].append(bus_id)

    # Sort voltage levels descending (highest at top)
    sorted_voltages = sorted(voltage_levels.keys(), reverse=True)
    n_levels = len(sorted_voltages)

    # Assign Y coordinate to each voltage level
    level_y = {}
    for i, voltage in enumerate(sorted_voltages):
        # Y ranges from 1.0 (top) to 0.0 (bottom)
        level_y[voltage] = 1.0 - (i / max(n_levels - 1, 1)) if n_levels > 1 else 0.5

    # ========== STEP 2: Build connection graph ==========
    # Find connections between buses
    connections = defaultdict(set)  # bus_id -> set of connected bus_ids
    transformers = []  # List of (bus_hv, bus_lv, tr_data)
    lines = []  # List of (bus_from, bus_to, line_data)

    for tr in elements.get('transformers_2w', []):
        bus_hv = tr['bus_hv']
        bus_lv = tr['bus_lv']
        if bus_hv in busbars and bus_lv in busbars:
            connections[bus_hv].add(bus_lv)
            connections[bus_lv].add(bus_hv)
            transformers.append((bus_hv, bus_lv, tr))

    for at in elements.get('autotransformers', []):
        bus_hv = at['bus_hv']
        bus_lv = at['bus_lv']
        if bus_hv in busbars and bus_lv in busbars:
            connections[bus_hv].add(bus_lv)
            connections[bus_lv].add(bus_hv)
            transformers.append((bus_hv, bus_lv, at))

    for line in elements.get('lines', []):
        bus_from = line['bus_from']
        bus_to = line['bus_to']
        if bus_from in busbars and bus_to in busbars:
            connections[bus_from].add(bus_to)
            connections[bus_to].add(bus_from)
            lines.append((bus_from, bus_to, line))

    # Track attached elements
    attached = defaultdict(list)  # bus_id -> [(type, element), ...]

    for grid in elements.get('external_grids', []):
        if grid['bus_id'] in busbars:
            attached[grid['bus_id']].append(('grid', grid))

    for gen in elements.get('generators', []):
        if gen['bus_id'] in busbars:
            attached[gen['bus_id']].append(('generator', gen))

    for motor in elements.get('motors', []):
        if motor['bus_id'] in busbars:
            attached[motor['bus_id']].append(('motor', motor))

    # ========== STEP 3: Horizontal ordering within each level ==========
    bus_positions = {}  # bus_id -> (x, y) in normalized [0, 1] coordinates

    # Find buses connected to external grid (these go leftmost)
    grid_buses = set(grid['bus_id'] for grid in elements.get('external_grids', [])
                     if grid['bus_id'] in busbars)

    for voltage in sorted_voltages:
        buses_at_level = voltage_levels[voltage]
        y = level_y[voltage]

        # Sort buses: grid-connected first, then by name
        def sort_key(bus_id):
            priority = 0 if bus_id in grid_buses else 1
            return (priority, bus_id)

        sorted_buses = sorted(buses_at_level, key=sort_key)
        n_buses = len(sorted_buses)

        for j, bus_id in enumerate(sorted_buses):
            # X ranges from 0.1 to 0.9 evenly distributed
            if n_buses == 1:
                x = 0.5
            else:
                x = 0.1 + 0.8 * (j / (n_buses - 1))
            bus_positions[bus_id] = (x, y)

    # ========== STEP 4: Calculate figure size ==========
    n_buses_total = len(busbars)
    max_buses_per_level = max(len(v) for v in voltage_levels.values())

    # Dynamic sizing
    fig_width = max(10, max_buses_per_level * 3)  # inches
    fig_height = max(8, n_levels * 3)  # inches

    # Create results lookup
    results_lookup = {}
    if results:
        for r in results:
            bus_id = r.get('bus_id')
            fault_type = r.get('fault_type')
            if bus_id not in results_lookup:
                results_lookup[bus_id] = {}
            results_lookup[bus_id][fault_type] = r

    # ========== STEP 5: Create figure ==========
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))

    # Set coordinate system
    margin = 0.15
    ax.set_xlim(-margin, 1 + margin)
    ax.set_ylim(-margin, 1 + margin)
    ax.set_aspect('equal')
    ax.axis('off')

    # Drawing constants (in normalized coordinates)
    BUSBAR_WIDTH = 0.12
    BUSBAR_LW = 5
    TR_RADIUS = 0.03
    SYMBOL_RADIUS = 0.025
    SYMBOL_OFFSET = 0.08  # Vertical offset for attached elements
    LABEL_OFFSET = 0.04

    # ========== STEP 6: Draw transformers ==========
    for bus_hv, bus_lv, tr_data in transformers:
        if bus_hv not in bus_positions or bus_lv not in bus_positions:
            continue

        x1, y1 = bus_positions[bus_hv]
        x2, y2 = bus_positions[bus_lv]

        # Check if transformer is active
        tr_type = 'transformers_2w' if 'uk_percent' in tr_data else 'autotransformers'
        tr_active = _is_element_active(is_element_active_fn, tr_type, tr_data['id'])
        line_color = COLOR_ACTIVE if tr_active else COLOR_INACTIVE
        line_style = '-' if tr_active else LINESTYLE_INACTIVE

        # Calculate midpoint
        mx = (x1 + x2) / 2
        my = (y1 + y2) / 2

        # Direction vector (normalized)
        dx = x2 - x1
        dy = y2 - y1
        length = math.sqrt(dx*dx + dy*dy)
        if length > 0:
            dx, dy = dx/length, dy/length
        else:
            dx, dy = 0, -1  # Default downward

        # Draw connection lines from busbars to transformer circles
        gap = TR_RADIUS * 1.8
        ax.plot([x1, mx - dx*gap], [y1, my - dy*gap],
                color=line_color, linestyle=line_style, linewidth=1.5, zorder=1)
        ax.plot([mx + dx*gap, x2], [my + dy*gap, y2],
                color=line_color, linestyle=line_style, linewidth=1.5, zorder=1)

        # Draw two overlapping circles (transformer symbol)
        offset = TR_RADIUS * 0.6
        circle_hv = Circle((mx - dx*offset, my - dy*offset), TR_RADIUS,
                          fill=False, edgecolor=line_color, linewidth=1.5,
                          linestyle=line_style if not tr_active else '-', zorder=3)
        circle_lv = Circle((mx + dx*offset, my + dy*offset), TR_RADIUS,
                          fill=False, edgecolor=line_color, linewidth=1.5,
                          linestyle=line_style if not tr_active else '-', zorder=3)
        ax.add_patch(circle_hv)
        ax.add_patch(circle_lv)

    # ========== STEP 7: Draw lines (same voltage level) ==========
    for bus_from, bus_to, line_data in lines:
        if bus_from not in bus_positions or bus_to not in bus_positions:
            continue

        x1, y1 = bus_positions[bus_from]
        x2, y2 = bus_positions[bus_to]

        # Check if line is active
        line_active = _is_element_active(is_element_active_fn, 'lines', line_data['id'])
        line_color = COLOR_ACTIVE if line_active else COLOR_INACTIVE
        line_style = '-' if line_active else LINESTYLE_INACTIVE

        # Check if same voltage level
        un_from = busbars[bus_from].get('Un', 0)
        un_to = busbars[bus_to].get('Un', 0)

        if un_from == un_to:
            # Horizontal line between busbars
            ax.plot([x1, x2], [y1, y2], color=line_color, linestyle=line_style,
                    linewidth=1.5, zorder=1)
        else:
            # Different voltage - treat like transformer connection
            ax.plot([x1, x2], [y1, y2], color=line_color, linestyle=line_style,
                    linewidth=1.5, zorder=1)

    # ========== STEP 8: Draw busbars ==========
    for bus_id, bus in busbars.items():
        if bus_id not in bus_positions:
            continue

        x, y = bus_positions[bus_id]
        un = bus.get('Un', 0)
        name = bus.get('name', bus_id)

        # Draw busbar as thick horizontal line
        ax.plot([x - BUSBAR_WIDTH/2, x + BUSBAR_WIDTH/2], [y, y],
                'k-', linewidth=BUSBAR_LW, solid_capstyle='butt', zorder=5)

    # ========== STEP 9: Draw attached elements ==========
    for bus_id, items in attached.items():
        if bus_id not in bus_positions or not items:
            continue

        x, y = bus_positions[bus_id]

        # Separate items by type
        grids = [(t, e) for t, e in items if t == 'grid']
        generators = [(t, e) for t, e in items if t == 'generator']
        motors = [(t, e) for t, e in items if t == 'motor']

        # Draw external grids ABOVE the busbar
        for i, (item_type, item) in enumerate(grids):
            grid_active = _is_element_active(is_element_active_fn, 'external_grids', item['id'])
            elem_color = COLOR_ACTIVE if grid_active else COLOR_INACTIVE
            elem_linestyle = '-' if grid_active else LINESTYLE_INACTIVE

            offset_x = (i - (len(grids) - 1) / 2) * SYMBOL_RADIUS * 3
            gx = x + offset_x
            gy = y + SYMBOL_OFFSET

            # Connection line
            ax.plot([gx, gx], [y, gy - SYMBOL_RADIUS], color=elem_color,
                    linestyle=elem_linestyle, linewidth=1.5, zorder=1)

            # Square with hatch pattern
            size = SYMBOL_RADIUS * 2
            rect = Rectangle((gx - size/2, gy - size/2), size, size,
                            fill=True, facecolor='white',
                            edgecolor=elem_color, linewidth=1.5,
                            linestyle=elem_linestyle if not grid_active else '-',
                            hatch='///', zorder=4)
            ax.add_patch(rect)

        # Draw generators BELOW the busbar
        for i, (item_type, item) in enumerate(generators):
            gen_active = _is_element_active(is_element_active_fn, 'generators', item['id'])
            elem_color = COLOR_ACTIVE if gen_active else COLOR_INACTIVE
            elem_linestyle = '-' if gen_active else LINESTYLE_INACTIVE

            offset_x = (i - (len(generators) - 1) / 2) * SYMBOL_RADIUS * 4
            gx = x + offset_x
            gy = y - SYMBOL_OFFSET

            # Connection line
            ax.plot([gx, gx], [y, gy + SYMBOL_RADIUS], color=elem_color,
                    linestyle=elem_linestyle, linewidth=1.5, zorder=1)

            # Circle with "G"
            circle = Circle((gx, gy), SYMBOL_RADIUS, fill=True,
                           facecolor='white', edgecolor=elem_color,
                           linestyle=elem_linestyle if not gen_active else '-',
                           linewidth=1.5, zorder=4)
            ax.add_patch(circle)
            ax.text(gx, gy, 'G', ha='center', va='center', color=elem_color,
                   fontproperties=FONT_BOLD_PROP, fontsize=8, zorder=5)

        # Draw motors BELOW generators
        motor_base_y = y - SYMBOL_OFFSET - (SYMBOL_RADIUS * 3 if generators else 0)
        for i, (item_type, item) in enumerate(motors):
            motor_active = _is_element_active(is_element_active_fn, 'motors', item['id'])
            elem_color = COLOR_ACTIVE if motor_active else COLOR_INACTIVE
            elem_linestyle = '-' if motor_active else LINESTYLE_INACTIVE

            offset_x = (i - (len(motors) - 1) / 2) * SYMBOL_RADIUS * 4
            mx_pos = x + offset_x
            my_pos = motor_base_y

            # Connection line
            line_start_y = y - SYMBOL_OFFSET + SYMBOL_RADIUS if generators else y
            ax.plot([mx_pos, mx_pos], [line_start_y, my_pos + SYMBOL_RADIUS],
                   color=elem_color, linestyle=elem_linestyle, linewidth=1.5, zorder=1)

            # Circle with "M"
            circle = Circle((mx_pos, my_pos), SYMBOL_RADIUS, fill=True,
                           facecolor='white', edgecolor=elem_color,
                           linestyle=elem_linestyle if not motor_active else '-',
                           linewidth=1.5, zorder=4)
            ax.add_patch(circle)
            ax.text(mx_pos, my_pos, 'M', ha='center', va='center', color=elem_color,
                   fontproperties=FONT_BOLD_PROP, fontsize=8, zorder=5)

    # ========== STEP 10: Draw labels ==========
    for bus_id, bus in busbars.items():
        if bus_id not in bus_positions:
            continue

        x, y = bus_positions[bus_id]
        un = bus.get('Un', 0)
        name = bus.get('name', bus_id)

        # Check if this bus has grid attached (label goes higher)
        has_grid = any(t == 'grid' for t, e in attached.get(bus_id, []))
        label_y = y + SYMBOL_OFFSET + SYMBOL_RADIUS * 2 + LABEL_OFFSET if has_grid else y + LABEL_OFFSET

        # Build label text
        lines_text = [name, f"Un = {un} kV"]

        # Add results if available
        if bus_id in results_lookup:
            ik3_data = results_lookup[bus_id].get('Ik3')
            if ik3_data:
                ik = ik3_data.get('Ik')
                ip = ik3_data.get('ip')
                if ik is not None:
                    lines_text.append(f"Ik3 = {ik:.2f} kA")
                if ip is not None:
                    lines_text.append(f"ip = {ip:.2f} kA")

        # Draw label
        label_text = '\n'.join(lines_text)

        # Determine font size based on number of buses
        font_size = 7 if n_buses_total > 10 else 8

        ax.text(x, label_y, label_text, ha='center', va='bottom',
               fontproperties=FONT_PROP, fontsize=font_size,
               linespacing=1.2, zorder=6,
               bbox=dict(boxstyle='round,pad=0.2', facecolor='white',
                        edgecolor='none', alpha=0.8))

    # ========== STEP 11: Add title ==========
    ax.text(0.5, 1 + margin - 0.02, 'Jednopólová schéma siete',
           ha='center', va='top', fontproperties=FONT_BOLD_PROP,
           fontsize=12, zorder=10)

    # ========== STEP 12: Save to bytes ==========
    buf = io.BytesIO()
    plt.savefig(buf, format=format, bbox_inches='tight', dpi=150,
               facecolor='white', edgecolor='none')
    plt.close(fig)
    buf.seek(0)

    return buf.getvalue()
