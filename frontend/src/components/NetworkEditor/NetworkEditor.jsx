import { useState } from 'react';
import { Button, Modal } from '../ui';
import ElementTable from './ElementTable';
import ElementForm from './ElementForm';

const ELEMENT_TYPES = [
  { key: 'busbars', label: 'Uzly (Busbars)', icon: 'M4 6h16M4 12h16M4 18h16' },
  { key: 'external_grids', label: 'Externé siete', icon: 'M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z' },
  { key: 'lines', label: 'Vedenia / Káble', icon: 'M13 17h8m0 0V9m0 8l-8-8-4 4-6-6' },
  { key: 'impedances', label: 'Impedancie', icon: 'M4 12h5m6 0h5M9 9l3 3-3 3m6-6l-3 3 3 3' },
  { key: 'transformers_2w', label: 'Transformátory 2W', icon: 'M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15' },
  { key: 'transformers_3w', label: 'Transformátory 3W', icon: 'M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15' },
  { key: 'autotransformers', label: 'Autotransformátory', icon: 'M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15' },
  { key: 'generators', label: 'Generátory', icon: 'M13 10V3L4 14h7v7l9-11h-7z' },
  { key: 'motors', label: 'Motory', icon: 'M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z' },
];

export default function NetworkEditor({ elements, onChange }) {
  const [activeTab, setActiveTab] = useState('busbars');
  const [showForm, setShowForm] = useState(false);
  const [editingElement, setEditingElement] = useState(null);

  const handleAdd = () => {
    setEditingElement(null);
    setShowForm(true);
  };

  const handleEdit = (element) => {
    setEditingElement(element);
    setShowForm(true);
  };

  const handleDelete = (elementId) => {
    if (!confirm('Naozaj chcete zmazať tento prvok?')) return;
    const newElements = {
      ...elements,
      [activeTab]: elements[activeTab].filter((e) => e.id !== elementId),
    };
    onChange(newElements);
  };

  const handleSaveElement = (element) => {
    let newList;
    if (editingElement) {
      newList = elements[activeTab].map((e) =>
        e.id === editingElement.id ? element : e
      );
    } else {
      newList = [...(elements[activeTab] || []), element];
    }
    onChange({ ...elements, [activeTab]: newList });
    setShowForm(false);
    setEditingElement(null);
  };

  const currentType = ELEMENT_TYPES.find((t) => t.key === activeTab);

  return (
    <div className="h-[600px] flex flex-col">
      <div className="flex overflow-x-auto border-b bg-gray-50">
        {ELEMENT_TYPES.map((type) => (
          <button
            key={type.key}
            onClick={() => setActiveTab(type.key)}
            className={`px-4 py-3 text-sm font-medium whitespace-nowrap border-b-2 transition-colors ${
              activeTab === type.key
                ? 'border-blue-500 text-blue-600 bg-white'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            {type.label}
            {elements[type.key]?.length > 0 && (
              <span className="ml-2 px-2 py-0.5 text-xs rounded-full bg-gray-200">
                {elements[type.key].length}
              </span>
            )}
          </button>
        ))}
      </div>

      <div className="flex justify-between items-center px-4 py-3 border-b bg-white">
        <h3 className="font-medium text-gray-900">{currentType?.label}</h3>
        <Button size="sm" onClick={handleAdd}>
          <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Pridať
        </Button>
      </div>

      <div className="flex-1 overflow-auto">
        <ElementTable
          type={activeTab}
          elements={elements[activeTab] || []}
          allElements={elements}
          onEdit={handleEdit}
          onDelete={handleDelete}
        />
      </div>

      <Modal
        isOpen={showForm}
        onClose={() => {
          setShowForm(false);
          setEditingElement(null);
        }}
        title={editingElement ? 'Upraviť prvok' : 'Nový prvok'}
        size="lg"
      >
        <ElementForm
          type={activeTab}
          element={editingElement}
          allElements={elements}
          onSave={handleSaveElement}
          onCancel={() => {
            setShowForm(false);
            setEditingElement(null);
          }}
        />
      </Modal>
    </div>
  );
}
