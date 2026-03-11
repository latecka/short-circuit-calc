import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { projectsApi } from '../api/client';
import Layout from '../components/Layout';
import { Button, Input, Card, CardBody, Modal, Select, Table, TableHead, TableBody, TableRow, TableHeader, TableCell } from '../components/ui';

export default function Projects() {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState('');
  const [newDesc, setNewDesc] = useState('');
  const [creating, setCreating] = useState(false);
  const [editingProject, setEditingProject] = useState(null);
  const [editName, setEditName] = useState('');
  const [editDesc, setEditDesc] = useState('');
  const [saving, setSaving] = useState(false);
  const navigate = useNavigate();

  // Search and sort state
  const [searchQuery, setSearchQuery] = useState('');
  const [sortOption, setSortOption] = useState('updated_desc');

  // Versions modal state
  const [versionsProject, setVersionsProject] = useState(null);
  const [versions, setVersions] = useState([]);
  const [loadingVersions, setLoadingVersions] = useState(false);

  useEffect(() => {
    loadProjects();
  }, []);

  // Filter and sort projects
  const filteredProjects = useMemo(() => {
    let result = [...projects];

    // Filter by search query
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      result = result.filter(p =>
        p.name.toLowerCase().includes(query) ||
        (p.description && p.description.toLowerCase().includes(query))
      );
    }

    // Sort
    result.sort((a, b) => {
      switch (sortOption) {
        case 'updated_desc':
          return new Date(b.updated_at) - new Date(a.updated_at);
        case 'updated_asc':
          return new Date(a.updated_at) - new Date(b.updated_at);
        case 'name_asc':
          return a.name.localeCompare(b.name, 'sk');
        case 'name_desc':
          return b.name.localeCompare(a.name, 'sk');
        default:
          return 0;
      }
    });

    return result;
  }, [projects, searchQuery, sortOption]);

  const loadProjects = async () => {
    try {
      const data = await projectsApi.list();
      setProjects(data.items);
    } catch (err) {
      console.error('Failed to load projects:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    setCreating(true);
    try {
      const project = await projectsApi.create(newName, newDesc);
      setShowCreate(false);
      setNewName('');
      setNewDesc('');
      navigate(`/projects/${project.id}`);
    } catch (err) {
      console.error('Failed to create project:', err);
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (e, id) => {
    e.stopPropagation();
    if (!confirm('Naozaj chcete zmazať tento projekt?')) return;
    try {
      await projectsApi.delete(id);
      setProjects(projects.filter((p) => p.id !== id));
    } catch (err) {
      console.error('Failed to delete project:', err);
    }
  };

  const handleEdit = (e, project) => {
    e.stopPropagation();
    setEditingProject(project);
    setEditName(project.name);
    setEditDesc(project.description || '');
  };

  const handleUpdate = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const updated = await projectsApi.update(editingProject.id, {
        name: editName,
        description: editDesc,
      });
      setProjects(projects.map((p) => (p.id === updated.id ? updated : p)));
      setEditingProject(null);
    } catch (err) {
      console.error('Failed to update project:', err);
    } finally {
      setSaving(false);
    }
  };

  const formatDate = (dateStr) => {
    return new Date(dateStr).toLocaleDateString('sk-SK', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const handleShowVersions = async (e, project) => {
    e.stopPropagation();
    setVersionsProject(project);
    setLoadingVersions(true);
    try {
      const versionsData = await projectsApi.listVersions(project.id);
      setVersions(versionsData);
    } catch (err) {
      console.error('Failed to load versions:', err);
      setVersions([]);
    } finally {
      setLoadingVersions(false);
    }
  };

  const handleCloseVersions = () => {
    setVersionsProject(null);
    setVersions([]);
  };

  return (
    <Layout>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Projekty</h1>
        <Button onClick={() => setShowCreate(true)}>
          <svg className="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Nový projekt
        </Button>
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-500">Načítavam...</div>
      ) : projects.length === 0 ? (
        <Card>
          <CardBody className="text-center py-12">
            <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 13h6m-3-3v6m-9 1V7a2 2 0 012-2h6l2 2h6a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z" />
            </svg>
            <h3 className="mt-4 text-lg font-medium text-gray-900">Žiadne projekty</h3>
            <p className="mt-2 text-gray-500">Vytvorte svoj prvý projekt.</p>
            <Button className="mt-4" onClick={() => setShowCreate(true)}>
              Vytvoriť projekt
            </Button>
          </CardBody>
        </Card>
      ) : (
        <>
          {/* Search and Sort Controls */}
          <div className="flex flex-col sm:flex-row gap-3 mb-4">
            <div className="relative flex-1 min-w-0">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <svg className="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Hľadať projekt..."
                className="block w-full min-w-[200px] pl-10 pr-10 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery('')}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600"
                >
                  <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              )}
            </div>
            <Select
              value={sortOption}
              onChange={(e) => setSortOption(e.target.value)}
              options={[
                { value: 'updated_desc', label: 'Dátum úpravy ↓' },
                { value: 'updated_asc', label: 'Dátum úpravy ↑' },
                { value: 'name_asc', label: 'Názov A→Z' },
                { value: 'name_desc', label: 'Názov Z→A' },
              ]}
              className="w-full sm:w-auto sm:min-w-[180px] shrink-0"
            />
          </div>

          <Card>
            <Table>
              <TableHead>
                <TableRow>
                  <TableHeader>Názov</TableHeader>
                  <TableHeader>Popis</TableHeader>
                  <TableHeader>Upravené</TableHeader>
                  <TableHeader className="w-24"></TableHeader>
                </TableRow>
              </TableHead>
              <TableBody>
                {filteredProjects.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={4} className="text-center text-gray-500 py-8">
                      Žiadne projekty nezodpovedajú vyhľadávaniu
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredProjects.map((project) => (
                    <TableRow
                      key={project.id}
                      onClick={() => navigate(`/projects/${project.id}`)}
                    >
                      <TableCell className="font-medium">{project.name}</TableCell>
                      <TableCell className="text-gray-500 max-w-xs truncate">
                        {project.description || '-'}
                      </TableCell>
                      <TableCell className="text-gray-500">
                        {formatDate(project.updated_at)}
                      </TableCell>
                      <TableCell>
                        <div className="flex space-x-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={(e) => handleShowVersions(e, project)}
                            className="text-gray-600 hover:text-blue-600 hover:bg-blue-50"
                            title="Zobraziť verzie"
                          >
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={(e) => handleEdit(e, project)}
                            className="text-gray-600 hover:text-blue-600 hover:bg-blue-50"
                            title="Upraviť projekt"
                          >
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                            </svg>
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={(e) => handleDelete(e, project.id)}
                            className="text-red-600 hover:text-red-700 hover:bg-red-50"
                            title="Zmazať projekt"
                          >
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                            </svg>
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </Card>
        </>
      )}

      <Modal isOpen={showCreate} onClose={() => setShowCreate(false)} title="Nový projekt">
        <form onSubmit={handleCreate} className="space-y-4">
          <Input
            label="Názov projektu"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            required
            autoFocus
          />
          <Input
            label="Popis"
            value={newDesc}
            onChange={(e) => setNewDesc(e.target.value)}
          />
          <div className="flex justify-end space-x-3 pt-4">
            <Button variant="secondary" onClick={() => setShowCreate(false)}>
              Zrušiť
            </Button>
            <Button type="submit" loading={creating}>
              Vytvoriť
            </Button>
          </div>
        </form>
      </Modal>

      <Modal isOpen={!!editingProject} onClose={() => setEditingProject(null)} title="Upraviť projekt">
        <form onSubmit={handleUpdate} className="space-y-4">
          <Input
            label="Názov projektu"
            value={editName}
            onChange={(e) => setEditName(e.target.value)}
            required
            autoFocus
          />
          <Input
            label="Popis"
            value={editDesc}
            onChange={(e) => setEditDesc(e.target.value)}
          />
          <div className="flex justify-end space-x-3 pt-4">
            <Button variant="secondary" onClick={() => setEditingProject(null)}>
              Zrušiť
            </Button>
            <Button type="submit" loading={saving}>
              Uložiť
            </Button>
          </div>
        </form>
      </Modal>

      {/* Versions Modal */}
      <Modal isOpen={!!versionsProject} onClose={handleCloseVersions} title={`Verzie projektu: ${versionsProject?.name || ''}`} size="lg">
        <div className="space-y-4">
          {loadingVersions ? (
            <div className="text-center py-8 text-gray-500">Načítavam verzie...</div>
          ) : versions.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <svg className="mx-auto h-12 w-12 text-gray-400 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <p>Projekt zatiaľ nemá žiadne uložené verzie.</p>
              <p className="text-sm mt-1">Verzie sa vytvárajú pri uložení zmien v editore siete.</p>
            </div>
          ) : (
            <div className="max-h-96 overflow-y-auto">
              <Table>
                <TableHead>
                  <TableRow>
                    <TableHeader>Verzia</TableHeader>
                    <TableHeader>Dátum</TableHeader>
                    <TableHeader>Komentár</TableHeader>
                    <TableHeader>Prvkov</TableHeader>
                    <TableHeader className="w-24"></TableHeader>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {versions.slice().reverse().map((version) => (
                    <TableRow key={version.id}>
                      <TableCell className="font-medium">v{version.version_number}</TableCell>
                      <TableCell className="text-gray-500 text-sm">
                        {formatDate(version.created_at)}
                      </TableCell>
                      <TableCell className="text-gray-500 text-sm max-w-xs truncate">
                        {version.comment || '-'}
                      </TableCell>
                      <TableCell className="text-gray-500">
                        {version.element_count || 0}
                      </TableCell>
                      <TableCell>
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => {
                            handleCloseVersions();
                            navigate(`/projects/${versionsProject.id}?version=${version.id}`);
                          }}
                        >
                          Otvoriť
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
          <div className="flex justify-end pt-4 border-t">
            <Button variant="secondary" onClick={handleCloseVersions}>
              Zavrieť
            </Button>
          </div>
        </div>
      </Modal>
    </Layout>
  );
}
