import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { projectsApi, calculationsApi } from '../api/client';
import Layout from '../components/Layout';
import NetworkEditor from '../components/NetworkEditor/NetworkEditor';
import ImportModal from '../components/NetworkEditor/ImportModal';
import CalculationResults from '../components/Results/CalculationResults';
import { Button, Card, CardHeader, CardBody, Modal, Input, Select } from '../components/ui';

export default function ProjectDetail() {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const [project, setProject] = useState(null);
  const [versions, setVersions] = useState([]);
  const [currentVersion, setCurrentVersion] = useState(null);
  const [elements, setElements] = useState({
    busbars: [],
    external_grids: [],
    lines: [],
    transformers_2w: [],
    transformers_3w: [],
    autotransformers: [],
    generators: [],
    motors: [],
    psus: [],
    impedances: [],
    grounding_impedances: [],
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [showCalcModal, setShowCalcModal] = useState(false);
  const [calcMode, setCalcMode] = useState('max');
  const [calcFaultTypes, setCalcFaultTypes] = useState(['Ik3', 'Ik2', 'Ik1']);
  const [calcBuses, setCalcBuses] = useState([]);
  const [calculating, setCalculating] = useState(false);
  const [calcResult, setCalcResult] = useState(null);
  const [hasChanges, setHasChanges] = useState(false);
  const [showImportModal, setShowImportModal] = useState(false);

  useEffect(() => {
    loadProject();
  }, [projectId]);

  const loadProject = async () => {
    try {
      const [projectData, versionsData] = await Promise.all([
        projectsApi.get(projectId),
        projectsApi.listVersions(projectId),
      ]);
      setProject(projectData);
      setVersions(versionsData);

      if (versionsData.length > 0) {
        const latestVersion = versionsData[versionsData.length - 1];
        await loadVersion(latestVersion.id);
      }
    } catch (err) {
      console.error('Failed to load project:', err);
      navigate('/projects');
    } finally {
      setLoading(false);
    }
  };

  const loadVersion = async (versionId) => {
    const versionData = await projectsApi.getVersion(projectId, versionId);
    setCurrentVersion(versionData);
    setElements(versionData.elements || {
      busbars: [],
      external_grids: [],
      lines: [],
      transformers_2w: [],
      transformers_3w: [],
      autotransformers: [],
      generators: [],
      motors: [],
      psus: [],
      impedances: [],
      grounding_impedances: [],
    });
    setHasChanges(false);
  };

  const handleElementsChange = (newElements) => {
    setElements(newElements);
    setHasChanges(true);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const newVersion = await projectsApi.createVersion(
        projectId,
        elements,
        `Verzia ${versions.length + 1}`
      );
      setVersions([...versions, newVersion]);
      setCurrentVersion(newVersion);
      setHasChanges(false);
    } catch (err) {
      console.error('Failed to save version:', err);
      alert('Uloženie zlyhalo');
    } finally {
      setSaving(false);
    }
  };

  const handleRunCalculation = async () => {
    if (!currentVersion && !hasChanges) {
      alert('Najprv uložte zmeny');
      return;
    }

    // If there are unsaved changes, save first
    let versionId = currentVersion?.id;
    if (hasChanges) {
      setSaving(true);
      try {
        const newVersion = await projectsApi.createVersion(
          projectId,
          elements,
          `Verzia ${versions.length + 1}`
        );
        setVersions([...versions, newVersion]);
        setCurrentVersion(newVersion);
        setHasChanges(false);
        versionId = newVersion.id;
      } catch (err) {
        console.error('Failed to save version:', err);
        alert('Uloženie zlyhalo');
        setSaving(false);
        return;
      }
      setSaving(false);
    }

    setCalculating(true);
    setCalcResult(null);
    try {
      const result = await calculationsApi.run(
        versionId,
        calcMode,
        calcFaultTypes,
        calcBuses.length > 0 ? calcBuses : elements.busbars.map(b => b.id)
      );
      // Load full results
      const fullResult = await calculationsApi.get(result.id);
      setCalcResult(fullResult);
      setShowCalcModal(false);

      // Show error if calculation failed
      if (fullResult.status === 'failed' && fullResult.error_message) {
        alert('Výpočet zlyhal: ' + fullResult.error_message);
      }
    } catch (err) {
      console.error('Calculation failed:', err);
      alert('Výpočet zlyhal: ' + (err.response?.data?.detail || err.message));
    } finally {
      setCalculating(false);
    }
  };

  const toggleFaultType = (type) => {
    if (calcFaultTypes.includes(type)) {
      setCalcFaultTypes(calcFaultTypes.filter(t => t !== type));
    } else {
      setCalcFaultTypes([...calcFaultTypes, type]);
    }
  };

  const handleImportSuccess = async (result) => {
    // Reload versions and load the new one
    const versionsData = await projectsApi.listVersions(projectId);
    setVersions(versionsData);
    await loadVersion(result.version_id);
  };

  if (loading) {
    return (
      <Layout>
        <div className="text-center py-12 text-gray-500">Načítavam...</div>
      </Layout>
    );
  }

  return (
    <Layout>
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{project?.name}</h1>
          <p className="text-gray-500 text-sm mt-1">
            {currentVersion ? `Verzia ${currentVersion.version_number}` : 'Nová sieť'}
            {hasChanges && <span className="text-orange-500 ml-2">• Neuložené zmeny</span>}
          </p>
        </div>
        <div className="flex space-x-3">
          <Button variant="secondary" onClick={() => navigate('/projects')}>
            Späť
          </Button>
          <Button
            variant="secondary"
            onClick={() => setShowImportModal(true)}
          >
            <svg className="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
            </svg>
            Import
          </Button>
          <Button
            variant="secondary"
            onClick={handleSave}
            loading={saving}
            disabled={!hasChanges}
          >
            Uložiť
          </Button>
          <Button onClick={() => setShowCalcModal(true)}>
            <svg className="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            Výpočet
          </Button>
        </div>
      </div>

      {/* Editor */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <Card className="xl:col-span-1">
          <CardHeader>
            <h2 className="text-lg font-semibold">Editor siete</h2>
          </CardHeader>
          <CardBody className="p-0">
            <NetworkEditor elements={elements} onChange={handleElementsChange} />
          </CardBody>
        </Card>

        <Card className="xl:col-span-1">
          <CardHeader>
            <h2 className="text-lg font-semibold">Výsledky</h2>
          </CardHeader>
          <CardBody>
            {calcResult ? (
              <CalculationResults result={calcResult} />
            ) : (
              <div className="text-center py-12 text-gray-500">
                <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
                <p className="mt-4">Spustite výpočet pre zobrazenie výsledkov</p>
              </div>
            )}
          </CardBody>
        </Card>
      </div>

      {/* Calculation Modal */}
      <Modal isOpen={showCalcModal} onClose={() => setShowCalcModal(false)} title="Spustiť výpočet">
        <div className="space-y-4">
          <Select
            label="Režim výpočtu"
            value={calcMode}
            onChange={(e) => setCalcMode(e.target.value)}
            options={[
              { value: 'max', label: 'Maximum (Ik max)' },
              { value: 'min', label: 'Minimum (Ik min)' },
            ]}
          />

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Typy porúch
            </label>
            <div className="flex space-x-4">
              {['Ik3', 'Ik2', 'Ik1'].map((type) => (
                <label key={type} className="flex items-center">
                  <input
                    type="checkbox"
                    checked={calcFaultTypes.includes(type)}
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
              {elements.busbars.length === 0
                ? 'Pridajte najprv uzly do siete'
                : 'Vyberte uzly alebo nechajte prázdne pre výpočet na všetkých'
              }
            </p>
            <div className="max-h-40 overflow-y-auto border rounded-lg p-2">
              {elements.busbars.map((bus) => (
                <label key={bus.id} className="flex items-center py-1">
                  <input
                    type="checkbox"
                    checked={calcBuses.includes(bus.id)}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setCalcBuses([...calcBuses, bus.id]);
                      } else {
                        setCalcBuses(calcBuses.filter(id => id !== bus.id));
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

          <div className="flex justify-end space-x-3 pt-4">
            <Button variant="secondary" onClick={() => setShowCalcModal(false)}>
              Zrušiť
            </Button>
            <Button
              onClick={handleRunCalculation}
              loading={calculating}
              disabled={elements.busbars.length === 0 || calcFaultTypes.length === 0}
            >
              Spustiť
            </Button>
          </div>
        </div>
      </Modal>

      {/* Import Modal */}
      <ImportModal
        isOpen={showImportModal}
        onClose={() => setShowImportModal(false)}
        projectId={projectId}
        onImportSuccess={handleImportSuccess}
      />
    </Layout>
  );
}
