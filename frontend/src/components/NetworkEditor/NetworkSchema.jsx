import { useMemo, useState, useCallback, useEffect } from 'react';
import ReactFlow, { Background, Controls, MiniMap, useNodesState, useEdgesState } from 'reactflow';
import BreakerEdge from './BreakerEdge';
import { Button } from '../ui';

const edgeTypes = { breaker: BreakerEdge };
const EMPTY_BREAKERS = {};

function flattenBreakers(elements) {
  const breakers = {};
  const add = (key) => {
    if (key) breakers[key] = true;
  };

  (elements.external_grids || []).forEach((e) => add(e.id));
  (elements.generators || []).forEach((e) => add(e.id));
  (elements.motors || []).forEach((e) => add(e.id));
  (elements.psus || []).forEach((e) => add(e.id));
  (elements.impedances || []).forEach((e) => add(e.id));
  (elements.grounding_impedances || []).forEach((e) => add(e.id));
  (elements.lines || []).forEach((e) => add(e.id));
  (elements.transformers_2w || []).forEach((e) => {
    add(`${e.id}_HV`);
    add(`${e.id}_LV`);
  });
  (elements.transformers_3w || []).forEach((e) => {
    add(`${e.id}_HV`);
    add(`${e.id}_MV`);
    add(`${e.id}_LV`);
  });
  (elements.autotransformers || []).forEach((e) => {
    add(`${e.id}_HV`);
    add(`${e.id}_LV`);
  });

  return breakers;
}

function isEquipmentActive(keys, breakerStates) {
  if (!keys?.length) return true;
  return keys.every((k) => breakerStates[k] !== false);
}

export default function NetworkSchema({
  elements,
  mode = 'edit',
  breakerStates,
  onToggleBreaker,
  onSave,
  layoutPositions,
  onLayoutChange,
}) {
  const [selected, setSelected] = useState(null);
  const [layoutSeed, setLayoutSeed] = useState(0);

  const graph = useMemo(() => {
    const busbars = elements.busbars || [];
    const breakersBase = flattenBreakers(elements);
    const safeBreakerStates = breakerStates || EMPTY_BREAKERS;
    const mergedBreakers = { ...breakersBase, ...safeBreakerStates };

    const busesByVoltage = new Map();
    busbars.forEach((b) => {
      const k = Number(b.Un || 0);
      if (!busesByVoltage.has(k)) busesByVoltage.set(k, []);
      busesByVoltage.get(k).push(b);
    });

    const voltageLevels = [...busesByVoltage.keys()].sort((a, b) => b - a);
    const busPositions = new Map();
    const nodes = [];

    voltageLevels.forEach((level, idx) => {
      const row = busesByVoltage.get(level) || [];
      row.forEach((bus, j) => {
        const x = 150 + j * 280 + layoutSeed * 0;
        const y = 80 + idx * 170;
        busPositions.set(bus.id, { x, y, Un: bus.Un });
        const nodeId = `bus:${bus.id}`;
        const overriddenPos = layoutPositions?.[nodeId];
        nodes.push({
          id: nodeId,
          type: 'default',
          position: overriddenPos || { x, y },
          data: { label: `${bus.name || bus.id} (${bus.Un} kV)` },
          draggable: mode === 'edit',
          style: { border: '2px solid #1d4ed8', borderRadius: 10, background: '#eff6ff' },
        });
      });
    });

    const edges = [];
    const makeEquipmentNode = (type, item, busId, index, keys = [item.id]) => {
      const busPos = busPositions.get(busId);
      if (!busPos) return;
      const id = `eq:${type}:${item.id}`;
      const active = isEquipmentActive(keys, mergedBreakers);
      const defaultPos = { x: busPos.x + 180 + (index % 3) * 45, y: busPos.y - 90 + Math.floor(index / 3) * 55 };
      nodes.push({
        id,
        position: layoutPositions?.[id] || defaultPos,
        data: { label: item.name || item.id, raw: item, type },
        draggable: mode === 'edit',
        style: {
          background: '#ffffff',
          border: '1px solid #94a3b8',
          borderRadius: 8,
          opacity: active ? 1 : 0.25,
          filter: active ? 'none' : 'grayscale(1)',
          fontSize: 12,
        },
      });
      edges.push({
        id: `ed:${id}:${busId}`,
        source: `bus:${busId}`,
        target: id,
        type: 'breaker',
        data: {
          breakerKey: keys[0],
          isClosed: mergedBreakers[keys[0]] !== false,
          interactive: mode === 'scenario',
          onToggle: onToggleBreaker,
        },
      });
    };

    const singleBusTypes = ['external_grids', 'generators', 'motors', 'psus', 'impedances', 'grounding_impedances'];
    singleBusTypes.forEach((type) => {
      (elements[type] || []).forEach((item, i) => {
        const busId = item.bus_id || item.bus || item.busbar_id;
        makeEquipmentNode(type, item, busId, i, [item.id]);
      });
    });

    (elements.lines || []).forEach((line) => {
      const from = line.bus_from;
      const to = line.bus_to;
      const p1 = busPositions.get(from);
      const p2 = busPositions.get(to);
      if (!p1 || !p2) return;
      const nodeId = `eq:line:${line.id}`;
      const active = mergedBreakers[line.id] !== false;
      const defaultPos = { x: (p1.x + p2.x) / 2, y: (p1.y + p2.y) / 2 - 45 };
      nodes.push({
        id: nodeId,
        position: layoutPositions?.[nodeId] || defaultPos,
        data: { label: line.name || line.id, raw: line, type: 'lines' },
        draggable: mode === 'edit',
        style: { border: '1px solid #94a3b8', borderRadius: 8, background: '#fff', opacity: active ? 1 : 0.25, filter: active ? 'none' : 'grayscale(1)' },
      });
      edges.push({ id: `ed:l1:${line.id}`, source: `bus:${from}`, target: nodeId, type: 'breaker', data: { breakerKey: line.id, isClosed: active, interactive: mode === 'scenario', onToggle: onToggleBreaker } });
      edges.push({ id: `ed:l2:${line.id}`, source: nodeId, target: `bus:${to}`, type: 'breaker', data: { breakerKey: line.id, isClosed: active, interactive: mode === 'scenario', onToggle: onToggleBreaker } });
    });

    const twoW = [...(elements.transformers_2w || []), ...(elements.autotransformers || [])];
    twoW.forEach((tr) => {
      const hv = tr.bus_hv;
      const lv = tr.bus_lv;
      const p1 = busPositions.get(hv);
      const p2 = busPositions.get(lv);
      if (!p1 || !p2) return;
      const nodeId = `eq:tr:${tr.id}`;
      const keys = [`${tr.id}_HV`, `${tr.id}_LV`];
      const active = isEquipmentActive(keys, mergedBreakers);
      const defaultPos = { x: (p1.x + p2.x) / 2 + 30, y: (p1.y + p2.y) / 2 };
      nodes.push({
        id: nodeId,
        position: layoutPositions?.[nodeId] || defaultPos,
        data: { label: tr.name || tr.id, raw: tr, type: 'transformer' },
        draggable: mode === 'edit',
        style: { border: '1px solid #94a3b8', borderRadius: 8, background: '#fff', opacity: active ? 1 : 0.25, filter: active ? 'none' : 'grayscale(1)' },
      });
      edges.push({ id: `ed:t1:${tr.id}`, source: `bus:${hv}`, target: nodeId, type: 'breaker', data: { breakerKey: keys[0], isClosed: mergedBreakers[keys[0]] !== false, interactive: mode === 'scenario', onToggle: onToggleBreaker } });
      edges.push({ id: `ed:t2:${tr.id}`, source: nodeId, target: `bus:${lv}`, type: 'breaker', data: { breakerKey: keys[1], isClosed: mergedBreakers[keys[1]] !== false, interactive: mode === 'scenario', onToggle: onToggleBreaker } });
    });

    return { nodes, edges, breakersBase };
  }, [elements, breakerStates, mode, onToggleBreaker, layoutSeed, layoutPositions]);

  const [nodes, setNodes, onNodesChange] = useNodesState(graph.nodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(graph.edges);

  useEffect(() => {
    setNodes(graph.nodes);
  }, [graph.nodes, setNodes]);

  useEffect(() => {
    setEdges(graph.edges);
  }, [graph.edges, setEdges]);

  const handleNodeClick = useCallback((_, node) => {
    setSelected(node);
  }, []);

  const persistLayout = useCallback((sourceNodes) => {
    if (!onLayoutChange) return;
    const next = {};
    (sourceNodes || []).forEach((n) => {
      next[n.id] = { x: n.position.x, y: n.position.y };
    });
    onLayoutChange(next);
  }, [onLayoutChange]);


  return (
    <div className="space-y-3">
      <div className={`rounded-lg border px-3 py-2 flex items-center justify-between ${mode === 'scenario' ? 'bg-amber-50 border-amber-200' : 'bg-blue-50 border-blue-200'}`}>
        <div className="text-sm font-medium text-gray-700">
          {mode === 'scenario'
            ? 'Scenario mód — klikni na vypínač pre zapnutie/vypnutie'
            : 'Edit mód — vypínače sú len indikátor stavu'}
        </div>
        {mode === 'edit' && (
          <div className="flex gap-2">
            <Button size="sm" variant="secondary" onClick={() => { setLayoutSeed((s) => s + 1); onLayoutChange?.({}); }}>Auto rozloženie</Button>
            <Button size="sm" variant="secondary" onClick={onSave}>Uložiť</Button>
            <Button size="sm" variant="secondary" onClick={() => window.print()}>Exportovať PNG</Button>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-3">
        <div className="lg:col-span-3 h-[560px] border rounded-lg overflow-hidden bg-white">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            edgeTypes={edgeTypes}
            fitView
            nodesDraggable={mode === 'edit'}
            nodesConnectable={false}
            elementsSelectable
            onNodeClick={handleNodeClick}
            onNodeDragStop={(_, __, currentNodes) => persistLayout(currentNodes)}
            proOptions={{ hideAttribution: true }}
          >
            <MiniMap zoomable pannable />
            <Controls />
            <Background gap={18} color="#e2e8f0" />
          </ReactFlow>
        </div>
        <div className="lg:col-span-1 border rounded-lg p-3 bg-gray-50">
          <h4 className="font-semibold text-sm mb-2">Detail prvku</h4>
          {selected ? (
            <div className="text-xs space-y-1">
              <div><span className="font-semibold">ID:</span> {selected.id}</div>
              <div><span className="font-semibold">Názov:</span> {selected.data?.label}</div>
              {selected.data?.raw && <pre className="mt-2 p-2 bg-white rounded border overflow-auto max-h-64">{JSON.stringify(selected.data.raw, null, 2)}</pre>}
            </div>
          ) : (
            <div className="text-sm text-gray-500">Kliknite na prvok v schéme.</div>
          )}
        </div>
      </div>
    </div>
  );
}
