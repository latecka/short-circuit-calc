import { useState, useEffect, useMemo } from 'react';
import { scenariosApi, calculationsApi } from '../../api/client';
import { Button, Modal, Input, Select } from '../ui';
import NetworkSchema from '../NetworkEditor/NetworkSchema';

export default function ScenarioManager({ projectId, elements, layoutPositions, onCalculationComplete }) {
  const [scenarios, setScenarios] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedScenario, setSelectedScenario] = useState(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showRunModal, setShowRunModal] = useState(false);
  const [newScenarioName, setNewScenarioName] = useState('');
  const [newScenarioDesc, setNewScenarioDesc] = useState('');
  const [copyFrom, setCopyFrom] = useState('');
  const [creating, setCreating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [running, setRunning] = useState(false);
  const [faultTypes, setFaultTypes] = useState(['Ik3', 'Ik2', 'Ik1']);
  const [faultBuses, setFaultBuses] = useState([]);

  useEffect(() => {
    loadScenarios();
  }, [projectId]);

  const loadScenarios = async () => {
    try {
      const data = await scenariosApi.list(projectId);
      setScenarios(data.items);
      if (data.items.length > 0) {
        setSelectedScenario((prev) => prev || data.items[0]);
      }
    } catch (err) {
      console.error('Failed to load scenarios:', err);
    } finally {
      setLoading(false);
    }
  };

  const normalizedBreakerStates = useMemo(() => {
    const current = selectedScenario?.element_states?.breakers || {};
    return current;
  }, [selectedScenario]);

  const handleCreate = async () => {
    if (!newScenarioName.trim()) return;
    setCreating(true);
    try {
      const scenario = await scenariosApi.create(projectId, {
        name: newScenarioName,
        description: newScenarioDesc,
        calculation_mode: 'max',
        element_states: {
          breakers: copyFrom
            ? (scenarios.find((s) => s.id === copyFrom)?.element_states?.breakers || {})
            : (selectedScenario?.element_states?.breakers || {}),
        },
        copy_from: null,
      });
      setScenarios([...scenarios, scenario]);
      setSelectedScenario(scenario);
      setShowCreateModal(false);
      setNewScenarioName('');
      setNewScenarioDesc('');
      setCopyFrom('');
    } catch (err) {
      console.error('Failed to create scenario:', err);
      alert('Vytvorenie scenára zlyhalo');
    } finally {
      setCreating(false);
    }
  };

  const handleDuplicate = async () => {
    if (!selectedScenario) return;
    setNewScenarioName(`${selectedScenario.name} (kópia)`);
    setNewScenarioDesc(selectedScenario.description || '');
    setCopyFrom(selectedScenario.id);
    setShowCreateModal(true);
  };

  const handleToggleBreaker = async (breakerKey) => {
    if (!selectedScenario || !breakerKey) return;
    const currentStates = selectedScenario.element_states || {};
    const currentBreakers = currentStates.breakers || {};
    const nextBreakers = {
      ...currentBreakers,
      [breakerKey]: !(currentBreakers[breakerKey] ?? true),
    };

    setSaving(true);
    try {
      const updated = await scenariosApi.update(projectId, selectedScenario.id, {
        element_states: {
          ...currentStates,
          breakers: nextBreakers,
        },
      });
      setSelectedScenario(updated);
      setScenarios((prev) => prev.map((s) => (s.id === updated.id ? updated : s)));
    } catch (err) {
      console.error('Failed to toggle breaker:', err);
    } finally {
      setSaving(false);
    }
    return null;
  }, []);

  const handleRunCalculation = async () => {
    if (!selectedScenario) return;
    setRunning(true);
    try {
      const result = await scenariosApi.run(
        projectId,
        selectedScenario.id,
        faultTypes,
        faultBuses.length > 0 ? faultBuses : null
      );

      if (result.status === 'completed') {
        const fullResult = await calculationsApi.get(result.run_id);
        onCalculationComplete?.({
          ...fullResult,
          onCaptureSchema: handleCaptureSchema,
        });
        setShowRunModal(false);
      } else {
        alert('Výpočet zlyhal: ' + result.message);
      }
    } catch (err) {
      console.error('Calculation failed:', err);
      alert('Výpočet zlyhal: ' + (err.response?.data?.detail || err.message));
    } finally {
      setRunning(false);
    }
  };

  if (loading) return <div className="py-12 text-center text-gray-500">Načítavam scenáre...</div>;

  return (
    <div className="grid grid-cols-1 xl:grid-cols-12 gap-4">
      <div className="xl:col-span-3 border rounded-lg p-3 bg-white">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold">Správa scenárov</h3>
          <Button size="sm" onClick={() => setShowCreateModal(true)}>+ Nový</Button>
        </div>
        <div className="space-y-2">
          {scenarios.map((scenario) => (
            <button
              key={scenario.id}
              onClick={() => setSelectedScenario(scenario)}
              className={`w-full text-left px-3 py-2 rounded-md text-sm ${selectedScenario?.id === scenario.id ? 'bg-blue-100 text-blue-700' : 'hover:bg-gray-100 text-gray-700'}`}
            >
              {selectedScenario?.id === scenario.id ? '● ' : ''}
              {scenario.name}
            </button>
          ))}
        </div>
      </div>

      <div className="xl:col-span-9 border rounded-lg p-3 bg-white">
        <div className="flex items-center justify-between gap-3 mb-3">
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-500">Scenár:</span>
            <Select
              value={selectedScenario?.id || ''}
              onChange={(e) => {
                const scenario = scenarios.find((s) => s.id === e.target.value);
                setSelectedScenario(scenario || null);
              }}
              options={scenarios.map((s) => ({ value: s.id, label: s.name }))}
            />
          </div>
          <div className="flex items-center gap-2">
            <Button size="sm" variant="secondary" onClick={handleDuplicate} disabled={!selectedScenario}>Duplikovať</Button>
            <Button size="sm" onClick={() => setShowRunModal(true)} disabled={!selectedScenario}>⚡ Spustiť výpočet</Button>
          </div>
        </div>

        <NetworkSchema
          elements={elements}
          mode="scenario"
          breakerStates={normalizedBreakerStates}
          layoutPositions={layoutPositions}
          onToggleBreaker={handleToggleBreaker}
        />

        {saving && <p className="text-xs text-gray-500 mt-2">Ukladám stav vypínačov...</p>}
      </div>

      <Modal isOpen={showCreateModal} onClose={() => setShowCreateModal(false)} title="Nový scenár">
        <div className="space-y-4">
          <Input label="Názov scenára" value={newScenarioName} onChange={(e) => setNewScenarioName(e.target.value)} />
          <Input label="Popis" value={newScenarioDesc} onChange={(e) => setNewScenarioDesc(e.target.value)} />
          <div className="flex justify-end gap-3">
            <Button variant="secondary" onClick={() => setShowCreateModal(false)}>Zrušiť</Button>
            <Button onClick={handleCreate} loading={creating} disabled={!newScenarioName.trim()}>Vytvoriť</Button>
          </div>
        </div>
      </Modal>

      <Modal isOpen={showRunModal} onClose={() => setShowRunModal(false)} title="Spustiť výpočet scenára">
        <div className="space-y-4">
          <div className="text-sm text-gray-600">Scenár: <span className="font-semibold">{selectedScenario?.name}</span></div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Typy porúch</label>
            <div className="flex gap-4">
              {['Ik3', 'Ik2', 'Ik1'].map((type) => (
                <label key={type} className="flex items-center">
                  <input
                    type="checkbox"
                    checked={faultTypes.includes(type)}
                    onChange={() => setFaultTypes((prev) => (prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type]))}
                    className="h-4 w-4 text-blue-600 rounded border-gray-300"
                  />
                  <span className="ml-2 text-sm text-gray-700">{type}</span>
                </label>
              ))}
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Uzly poruchy</label>
            <div className="max-h-36 overflow-y-auto border rounded-lg p-2">
              {(elements?.busbars || []).map((bus) => (
                <label key={bus.id} className="flex items-center py-1">
                  <input
                    type="checkbox"
                    checked={faultBuses.includes(bus.id)}
                    onChange={(e) => {
                      if (e.target.checked) setFaultBuses([...faultBuses, bus.id]);
                      else setFaultBuses(faultBuses.filter((id) => id !== bus.id));
                    }}
                    className="h-4 w-4 text-blue-600 rounded border-gray-300"
                  />
                  <span className="ml-2 text-sm text-gray-700">{bus.name || bus.id}</span>
                </label>
              ))}
            </div>
          </div>
          <div className="flex justify-end gap-3">
            <Button variant="secondary" onClick={() => setShowRunModal(false)}>Zrušiť</Button>
            <Button onClick={handleRunCalculation} loading={running} disabled={faultTypes.length === 0}>Spustiť</Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
