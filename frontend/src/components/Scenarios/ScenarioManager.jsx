import { useState, useEffect } from 'react';
import { scenariosApi, calculationsApi } from '../../api/client';
import { Button, Modal, Input, Select, Card, CardHeader, CardBody, Table, TableHead, TableBody, TableRow, TableHeader, TableCell } from '../ui';

// Element type labels
const ELEMENT_TYPE_LABELS = {
  busbars: 'Uzly',
  external_grids: 'Externé siete',
  lines: 'Vedenia',
  transformers_2w: 'Transformátory 2W',
  transformers_3w: 'Transformátory 3W',
  autotransformers: 'Autotransformátory',
  generators: 'Generátory',
  motors: 'Motory',
  psus: 'PSU',
  impedances: 'Impedancie',
  grounding_impedances: 'Zemniace impedancie',
};

export default function ScenarioManager({ projectId, elements, onCalculationComplete }) {
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
      if (data.items.length > 0 && !selectedScenario) {
        setSelectedScenario(data.items[0]);
      }
    } catch (err) {
      console.error('Failed to load scenarios:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    if (!newScenarioName.trim()) return;
    setCreating(true);
    try {
      const scenario = await scenariosApi.create(projectId, {
        name: newScenarioName,
        description: newScenarioDesc,
        calculation_mode: 'max',
        element_states: {},
        copy_from: copyFrom || null,
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

  const handleDelete = async (scenarioId) => {
    if (!confirm('Naozaj chcete zmazať tento scenár?')) return;
    try {
      await scenariosApi.delete(projectId, scenarioId);
      const newScenarios = scenarios.filter(s => s.id !== scenarioId);
      setScenarios(newScenarios);
      if (selectedScenario?.id === scenarioId) {
        setSelectedScenario(newScenarios[0] || null);
      }
    } catch (err) {
      console.error('Failed to delete scenario:', err);
    }
  };

  const handleToggleElement = async (elementType, elementId) => {
    if (!selectedScenario) return;

    const currentStates = selectedScenario.element_states || {};
    const typeStates = currentStates[elementType] || {};
    const currentValue = typeStates[elementId] ?? true;

    const newStates = {
      ...currentStates,
      [elementType]: {
        ...typeStates,
        [elementId]: !currentValue,
      },
    };

    setSaving(true);
    try {
      const updated = await scenariosApi.update(projectId, selectedScenario.id, {
        element_states: newStates,
      });
      setSelectedScenario(updated);
      setScenarios(scenarios.map(s => s.id === updated.id ? updated : s));
    } catch (err) {
      console.error('Failed to update scenario:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleModeChange = async (mode) => {
    if (!selectedScenario) return;
    setSaving(true);
    try {
      const updated = await scenariosApi.update(projectId, selectedScenario.id, {
        calculation_mode: mode,
      });
      setSelectedScenario(updated);
      setScenarios(scenarios.map(s => s.id === updated.id ? updated : s));
    } catch (err) {
      console.error('Failed to update scenario:', err);
    } finally {
      setSaving(false);
    }
  };

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
        // Load full results
        const fullResult = await calculationsApi.get(result.run_id);
        onCalculationComplete?.(fullResult);
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

  const toggleFaultType = (type) => {
    if (faultTypes.includes(type)) {
      setFaultTypes(faultTypes.filter(t => t !== type));
    } else {
      setFaultTypes([...faultTypes, type]);
    }
  };

  const isElementActive = (elementType, elementId) => {
    if (!selectedScenario) return true;
    const typeStates = selectedScenario.element_states?.[elementType] || {};
    return typeStates[elementId] ?? true;
  };

  const getActiveElementCount = () => {
    if (!selectedScenario || !elements) return 0;
    let count = 0;
    for (const [type, items] of Object.entries(elements)) {
      if (!Array.isArray(items)) continue;
      for (const item of items) {
        if (isElementActive(type, item.id)) count++;
      }
    }
    return count;
  };

  const getTotalElementCount = () => {
    if (!elements) return 0;
    let count = 0;
    for (const items of Object.values(elements)) {
      if (Array.isArray(items)) count += items.length;
    }
    return count;
  };

  if (loading) {
    return <div className="text-center py-8 text-gray-500">Načítavam scenáre...</div>;
  }

  return (
    <div className="space-y-4">
      {/* Scenario selector and actions */}
      <div className="flex flex-wrap items-center gap-3">
        <Select
          value={selectedScenario?.id || ''}
          onChange={(e) => {
            const scenario = scenarios.find(s => s.id === e.target.value);
            setSelectedScenario(scenario);
          }}
          options={scenarios.map(s => ({ value: s.id, label: s.name }))}
          className="flex-1 min-w-[200px]"
        />
        <Button variant="secondary" size="sm" onClick={() => setShowCreateModal(true)}>
          + Nový
        </Button>
        {selectedScenario && (
          <>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => {
                setNewScenarioName(selectedScenario.name + ' (kópia)');
                setCopyFrom(selectedScenario.id);
                setShowCreateModal(true);
              }}
            >
              Kopírovať
            </Button>
            <Button
              variant="danger"
              size="sm"
              onClick={() => handleDelete(selectedScenario.id)}
            >
              Zmazať
            </Button>
          </>
        )}
      </div>

      {scenarios.length === 0 ? (
        <Card>
          <CardBody className="text-center py-8">
            <p className="text-gray-500 mb-4">Žiadne scenáre. Vytvorte prvý scenár.</p>
            <Button onClick={() => setShowCreateModal(true)}>Vytvoriť scenár</Button>
          </CardBody>
        </Card>
      ) : selectedScenario && (
        <>
          {/* Scenario settings */}
          <Card>
            <CardHeader>
              <div className="flex justify-between items-center">
                <div>
                  <h3 className="font-semibold">{selectedScenario.name}</h3>
                  {selectedScenario.description && (
                    <p className="text-sm text-gray-500">{selectedScenario.description}</p>
                  )}
                </div>
                <div className="flex items-center gap-4">
                  <div className="text-sm text-gray-600">
                    Aktívnych prvkov: {getActiveElementCount()} / {getTotalElementCount()}
                  </div>
                  <Select
                    value={selectedScenario.calculation_mode}
                    onChange={(e) => handleModeChange(e.target.value)}
                    options={[
                      { value: 'max', label: 'Maximum (Ik max)' },
                      { value: 'min', label: 'Minimum (Ik min)' },
                    ]}
                    className="w-40"
                  />
                  <Button onClick={() => setShowRunModal(true)} disabled={saving}>
                    Spustiť výpočet
                  </Button>
                </div>
              </div>
            </CardHeader>
          </Card>

          {/* Element toggles */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {Object.entries(ELEMENT_TYPE_LABELS).map(([type, label]) => {
              const items = elements?.[type] || [];
              if (items.length === 0) return null;

              return (
                <Card key={type}>
                  <CardHeader>
                    <h4 className="font-medium">{label}</h4>
                  </CardHeader>
                  <CardBody className="p-0">
                    <div className="divide-y divide-gray-100 max-h-60 overflow-y-auto">
                      {items.map((item) => {
                        const isActive = isElementActive(type, item.id);
                        return (
                          <div
                            key={item.id}
                            className={`flex items-center justify-between px-4 py-2 ${
                              isActive ? '' : 'bg-gray-50'
                            }`}
                          >
                            <div className={isActive ? '' : 'text-gray-400 line-through'}>
                              <span className="font-medium">{item.id}</span>
                              {item.name && item.name !== item.id && (
                                <span className="text-gray-500 ml-2">{item.name}</span>
                              )}
                            </div>
                            <button
                              onClick={() => handleToggleElement(type, item.id)}
                              disabled={saving}
                              className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
                                isActive ? 'bg-green-500' : 'bg-gray-300'
                              }`}
                            >
                              <span
                                className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                                  isActive ? 'translate-x-5' : 'translate-x-0'
                                }`}
                              />
                            </button>
                          </div>
                        );
                      })}
                    </div>
                  </CardBody>
                </Card>
              );
            })}
          </div>
        </>
      )}

      {/* Create Modal */}
      <Modal isOpen={showCreateModal} onClose={() => setShowCreateModal(false)} title="Nový scenár">
        <div className="space-y-4">
          <Input
            label="Názov scenára"
            value={newScenarioName}
            onChange={(e) => setNewScenarioName(e.target.value)}
            placeholder="napr. Bez generátora G1"
            autoFocus
          />
          <Input
            label="Popis (voliteľný)"
            value={newScenarioDesc}
            onChange={(e) => setNewScenarioDesc(e.target.value)}
            placeholder="Voliteľný popis scenára"
          />
          {scenarios.length > 0 && copyFrom && (
            <div className="p-3 bg-blue-50 rounded-lg text-sm text-blue-700">
              Kopírujem nastavenia zo scenára: {scenarios.find(s => s.id === copyFrom)?.name}
            </div>
          )}
          <div className="flex justify-end gap-3 pt-4">
            <Button variant="secondary" onClick={() => {
              setShowCreateModal(false);
              setNewScenarioName('');
              setNewScenarioDesc('');
              setCopyFrom('');
            }}>
              Zrušiť
            </Button>
            <Button onClick={handleCreate} loading={creating} disabled={!newScenarioName.trim()}>
              Vytvoriť
            </Button>
          </div>
        </div>
      </Modal>

      {/* Run Calculation Modal */}
      <Modal isOpen={showRunModal} onClose={() => setShowRunModal(false)} title="Spustiť výpočet">
        <div className="space-y-4">
          <div className="p-3 bg-gray-50 rounded-lg">
            <div className="text-sm font-medium">Scenár: {selectedScenario?.name}</div>
            <div className="text-sm text-gray-500">
              Režim: {selectedScenario?.calculation_mode === 'max' ? 'Maximum' : 'Minimum'}
            </div>
            <div className="text-sm text-gray-500">
              Aktívnych prvkov: {getActiveElementCount()} / {getTotalElementCount()}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Typy porúch
            </label>
            <div className="flex gap-4">
              {['Ik3', 'Ik2', 'Ik1'].map((type) => (
                <label key={type} className="flex items-center">
                  <input
                    type="checkbox"
                    checked={faultTypes.includes(type)}
                    onChange={() => toggleFaultType(type)}
                    className="h-4 w-4 text-blue-600 rounded border-gray-300"
                  />
                  <span className="ml-2 text-sm text-gray-700">{type}</span>
                </label>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Uzly poruchy
            </label>
            <p className="text-sm text-gray-500 mb-2">
              Vyberte uzly alebo nechajte prázdne pre výpočet na všetkých aktívnych
            </p>
            <div className="max-h-40 overflow-y-auto border rounded-lg p-2">
              {(elements?.busbars || [])
                .filter(bus => isElementActive('busbars', bus.id))
                .map((bus) => (
                  <label key={bus.id} className="flex items-center py-1">
                    <input
                      type="checkbox"
                      checked={faultBuses.includes(bus.id)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setFaultBuses([...faultBuses, bus.id]);
                        } else {
                          setFaultBuses(faultBuses.filter(id => id !== bus.id));
                        }
                      }}
                      className="h-4 w-4 text-blue-600 rounded border-gray-300"
                    />
                    <span className="ml-2 text-sm text-gray-700">
                      {bus.name || bus.id} ({bus.Un} kV)
                    </span>
                  </label>
                ))}
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t">
            <Button variant="secondary" onClick={() => setShowRunModal(false)}>
              Zrušiť
            </Button>
            <Button
              onClick={handleRunCalculation}
              loading={running}
              disabled={faultTypes.length === 0}
            >
              Spustiť
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
