import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { projectsApi } from '../api/client';
import Layout from '../components/Layout';
import { Button, Input, Card, CardBody, Modal, Table, TableHead, TableBody, TableRow, TableHeader, TableCell } from '../components/ui';

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

  useEffect(() => {
    loadProjects();
  }, []);

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
        <Card>
          <Table>
            <TableHead>
              <TableRow>
                <TableHeader>Názov</TableHeader>
                <TableHeader>Popis</TableHeader>
                <TableHeader>Verzií</TableHeader>
                <TableHeader>Upravené</TableHeader>
                <TableHeader className="w-24"></TableHeader>
              </TableRow>
            </TableHead>
            <TableBody>
              {projects.map((project) => (
                <TableRow
                  key={project.id}
                  onClick={() => navigate(`/projects/${project.id}`)}
                >
                  <TableCell className="font-medium">{project.name}</TableCell>
                  <TableCell className="text-gray-500 max-w-xs truncate">
                    {project.description || '-'}
                  </TableCell>
                  <TableCell>{project.version_count}</TableCell>
                  <TableCell className="text-gray-500">
                    {formatDate(project.updated_at)}
                  </TableCell>
                  <TableCell>
                    <div className="flex space-x-1">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={(e) => handleEdit(e, project)}
                        className="text-gray-600 hover:text-blue-600 hover:bg-blue-50"
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
                      >
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
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
    </Layout>
  );
}
