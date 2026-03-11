import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { projectsApi } from '../api/client';
import Layout from '../components/Layout';
import NetworkEditor from '../components/NetworkEditor/NetworkEditor';
import NetworkSchema from '../components/NetworkEditor/NetworkSchema';
import ImportModal from '../components/NetworkEditor/ImportModal';
import CalculationResults from '../components/Results/CalculationResults';
import ScenarioManager from '../components/Scenarios/ScenarioManager';
import { Button, Card, CardHeader, CardBody, Input } from '../components/ui';

const API_URL = import.meta.env.VITE_API_URL || '';

export default function ProjectDetail() {
  const { projectId } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [project, setProject] = useState(null);
  const [versions, setVersions] = useState([]);
  const [currentVersion, setCurrentVersion] = useState(null);
  const [showExportMenu, setShowExportMenu] = useState(false);
  const exportMenuRef = useRef(null);
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
  const [calcResult, setCalcResult] = useState(null);
  const [hasChanges, setHasChanges] = useState(false);
  const [showImportModal, setShowImportModal] = useState(false);
  const [showMetadata, setShowMetadata] = useState(false);
  const [activeTab, setActiveTab] = useState('elements'); // 'elements' | 'scenarios'
  const [metadata, setMetadata] = useState({
    client_name: '',
    client_address: '',
    contractor_name: '',
    contractor_address: '',
    author: '',
    checker: '',
    project_number: '',
    project_location: '',
    revision: '',
    notes: '',
  });
  const [savingMetadata, setSavingMetadata] = useState(false);

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

      // Load metadata from project
      setMetadata({
        client_name: projectData.client_name || '',
        client_address: projectData.client_address || '',
        contractor_name: projectData.contractor_name || '',
        contractor_address: projectData.contractor_address || '',
        author: projectData.author || '',
        checker: projectData.checker || '',
        project_number: projectData.project_number || '',
        project_location: projectData.project_location || '',
        revision: projectData.revision || '',
        notes: projectData.notes || '',
      });

      if (versionsData.length > 0) {
        // Check if specific version requested via URL param
        const requestedVersionId = searchParams.get('version');
        if (requestedVersionId) {
          const requestedVersion = versionsData.find(v => v.id === requestedVersionId);
          if (requestedVersion) {
            await loadVersion(requestedVersion.id);
          } else {
            // Version not found, load latest
            const latestVersion = versionsData[versionsData.length - 1];
            await loadVersion(latestVersion.id);
          }
        } else {
          const latestVersion = versionsData[versionsData.length - 1];
          await loadVersion(latestVersion.id);
        }
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

  const handleImportSuccess = async (result) => {
    // Reload versions and load the new one
    const versionsData = await projectsApi.listVersions(projectId);
    setVersions(versionsData);
    await loadVersion(result.version_id);
  };

  const handleMetadataChange = (field, value) => {
    setMetadata(prev => ({ ...prev, [field]: value }));
  };

  const handleSaveMetadata = async () => {
    setSavingMetadata(true);
    try {
      const updatedProject = await projectsApi.update(projectId, metadata);
      setProject(updatedProject);
      alert('Metadata boli uložené');
    } catch (err) {
      console.error('Failed to save metadata:', err);
      alert('Uloženie metadát zlyhalo');
    } finally {
      setSavingMetadata(false);
    }
  };

  // Close export menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (exportMenuRef.current && !exportMenuRef.current.contains(event.target)) {
        setShowExportMenu(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const getExportFilename = (extension) => {
    const date = new Date().toISOString().split('T')[0];
    const safeName = (project?.name || 'projekt').replace(/[^a-zA-Z0-9_-]/g, '_');
    return `${safeName}_backup_${date}.${extension}`;
  };

  const handleExportJSON = () => {
    const exportData = {
      export_version: '1.0',
      exported_at: new Date().toISOString(),
      project: {
        name: project?.name || '',
        description: project?.description || '',
        created_at: project?.created_at || '',
        updated_at: project?.updated_at || '',
      },
      network_elements: elements,
    };

    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = getExportFilename('json');
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    a.remove();
    setShowExportMenu(false);
  };

  const handleExportXLSX = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API_URL}/api/v1/export/network/${projectId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!response.ok) {
        throw new Error('Export failed');
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = getExportFilename('xlsx');
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      a.remove();
    } catch (err) {
      console.error('Export failed:', err);
      alert('Export XLSX zlyhal');
    }
    setShowExportMenu(false);
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

          {/* Export Dropdown */}
          <div className="relative" ref={exportMenuRef}>
            <Button
              variant="secondary"
              onClick={() => setShowExportMenu(!showExportMenu)}
            >
              <svg className="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              Záloha
              <svg className="w-4 h-4 ml-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </Button>
            {showExportMenu && (
              <div className="absolute right-0 mt-2 w-48 rounded-md shadow-lg bg-white ring-1 ring-black ring-opacity-5 z-10">
                <div className="py-1">
                  <button
                    onClick={handleExportJSON}
                    className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 flex items-center"
                  >
                    <svg className="w-4 h-4 mr-2 text-yellow-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    Stiahnuť JSON
                  </button>
                  <button
                    onClick={handleExportXLSX}
                    className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 flex items-center"
                  >
                    <svg className="w-4 h-4 mr-2 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    Stiahnuť XLSX
                  </button>
                </div>
              </div>
            )}
          </div>

          <Button
            variant="secondary"
            onClick={handleSave}
            loading={saving}
            disabled={!hasChanges}
          >
            Uložiť
          </Button>
        </div>
      </div>

      {/* Metadata Section */}
      <Card className="mb-6">
        <CardHeader>
          <button
            onClick={() => setShowMetadata(!showMetadata)}
            className="flex items-center justify-between w-full text-left"
          >
            <h2 className="text-lg font-semibold">Metadata projektu</h2>
            <svg
              className={`w-5 h-5 transform transition-transform ${showMetadata ? 'rotate-180' : ''}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
        </CardHeader>
        {showMetadata && (
          <CardBody>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-4">
                <Input
                  label="Objednávateľ"
                  value={metadata.client_name}
                  onChange={(e) => handleMetadataChange('client_name', e.target.value)}
                  placeholder="Názov objednávateľa"
                />
                <Input
                  label="Adresa objednávateľa"
                  value={metadata.client_address}
                  onChange={(e) => handleMetadataChange('client_address', e.target.value)}
                  placeholder="Adresa"
                />
                <Input
                  label="Zhotoviteľ"
                  value={metadata.contractor_name}
                  onChange={(e) => handleMetadataChange('contractor_name', e.target.value)}
                  placeholder="Názov zhotoviteľa"
                />
                <Input
                  label="Adresa zhotoviteľa"
                  value={metadata.contractor_address}
                  onChange={(e) => handleMetadataChange('contractor_address', e.target.value)}
                  placeholder="Adresa"
                />
                <Input
                  label="Číslo projektu"
                  value={metadata.project_number}
                  onChange={(e) => handleMetadataChange('project_number', e.target.value)}
                  placeholder="napr. PRJ-2026-001"
                />
              </div>
              <div className="space-y-4">
                <Input
                  label="Miesto stavby"
                  value={metadata.project_location}
                  onChange={(e) => handleMetadataChange('project_location', e.target.value)}
                  placeholder="Lokalita projektu"
                />
                <Input
                  label="Vypracoval"
                  value={metadata.author}
                  onChange={(e) => handleMetadataChange('author', e.target.value)}
                  placeholder="Meno autora"
                />
                <Input
                  label="Kontroloval"
                  value={metadata.checker}
                  onChange={(e) => handleMetadataChange('checker', e.target.value)}
                  placeholder="Meno kontrolóra"
                />
                <Input
                  label="Revízia"
                  value={metadata.revision}
                  onChange={(e) => handleMetadataChange('revision', e.target.value)}
                  placeholder="napr. A, B, 1.0"
                />
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Poznámky
                  </label>
                  <textarea
                    value={metadata.notes}
                    onChange={(e) => handleMetadataChange('notes', e.target.value)}
                    placeholder="Dodatočné poznámky..."
                    rows={3}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>
            </div>
            <div className="mt-4 flex justify-end">
              <Button onClick={handleSaveMetadata} loading={savingMetadata}>
                Uložiť metadata
              </Button>
            </div>
          </CardBody>
        )}
      </Card>

      {/* Tabs */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('elements')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'elements'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Schéma siete
          </button>
          <button
            onClick={() => setActiveTab('scenarios')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'scenarios'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Scenáre
          </button>
        </nav>
      </div>

      {/* Main Content */}
      {activeTab === 'elements' ? (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <h2 className="text-lg font-semibold">Schéma siete</h2>
            </CardHeader>
            <CardBody>
              <NetworkSchema
                elements={elements}
                mode="edit"
                onSave={handleSave}
              />
            </CardBody>
          </Card>

          <Card>
            <CardHeader>
              <h2 className="text-lg font-semibold">Editor parametrov prvkov</h2>
            </CardHeader>
            <CardBody className="p-0">
              <NetworkEditor elements={elements} onChange={handleElementsChange} />
            </CardBody>
          </Card>
        </div>
      ) : (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <h2 className="text-lg font-semibold">Scenáre</h2>
            </CardHeader>
            <CardBody>
              <ScenarioManager
                projectId={projectId}
                elements={elements}
                onCalculationComplete={(result) => setCalcResult(result)}
              />
            </CardBody>
          </Card>

          <Card>
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
      )}

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
