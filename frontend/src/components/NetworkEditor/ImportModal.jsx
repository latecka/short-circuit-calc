import { useState, useRef } from 'react';
import { Button, Modal } from '../ui';

const API_URL = import.meta.env.VITE_API_URL || '';

export default function ImportModal({ isOpen, onClose, projectId, onImportSuccess }) {
  const [file, setFile] = useState(null);
  const [validating, setValidating] = useState(false);
  const [importing, setImporting] = useState(false);
  const [validationResult, setValidationResult] = useState(null);
  const [error, setError] = useState(null);
  const fileInputRef = useRef(null);

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    setFile(selectedFile);
    setValidationResult(null);
    setError(null);

    if (selectedFile) {
      validateFile(selectedFile);
    }
  };

  const getFileType = (filename) => {
    if (filename.endsWith('.json')) return 'json';
    if (filename.endsWith('.xlsx') || filename.endsWith('.xls')) return 'xlsx';
    return null;
  };

  const validateFile = async (fileToValidate) => {
    const fileType = getFileType(fileToValidate.name);
    if (!fileType) {
      setError('Nepodporovaný formát súboru. Použite JSON alebo XLSX.');
      return;
    }

    setValidating(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('file', fileToValidate);

      const token = localStorage.getItem('token');
      const response = await fetch(`${API_URL}/api/v1/import/validate/${fileType}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });

      const result = await response.json();
      setValidationResult(result);

      if (!result.valid) {
        setError(result.message);
      }
    } catch (err) {
      setError('Validácia zlyhala: ' + err.message);
    } finally {
      setValidating(false);
    }
  };

  const handleImport = async () => {
    if (!file || !validationResult?.valid) return;

    const fileType = getFileType(file.name);
    setImporting(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const token = localStorage.getItem('token');
      const response = await fetch(`${API_URL}/api/v1/import/${fileType}/${projectId}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail?.message || errData.detail || 'Import zlyhal');
      }

      const result = await response.json();
      onImportSuccess(result);
      handleClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setImporting(false);
    }
  };

  const handleDownloadTemplate = async (format = 'xlsx') => {
    try {
      const token = localStorage.getItem('token');
      const endpoint = format === 'json'
        ? `${API_URL}/api/v1/import/template/json`
        : `${API_URL}/api/v1/import/template`;

      const response = await fetch(endpoint, {
        headers: { Authorization: `Bearer ${token}` },
      });

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = format === 'json' ? 'network_template.json' : 'network_template.xlsx';
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      a.remove();
    } catch (err) {
      console.error('Template download failed:', err);
    }
  };

  const handleClose = () => {
    setFile(null);
    setValidationResult(null);
    setError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
    onClose();
  };

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title="Importovať sieť" size="lg">
      <div className="space-y-4">
        {/* File input */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Vyberte súbor (JSON alebo XLSX)
          </label>
          <div className="flex items-center space-x-3">
            <input
              ref={fileInputRef}
              type="file"
              accept=".json,.xlsx,.xls"
              onChange={handleFileChange}
              className="block w-full text-sm text-gray-500
                file:mr-4 file:py-2 file:px-4
                file:rounded-lg file:border-0
                file:text-sm file:font-medium
                file:bg-blue-50 file:text-blue-700
                hover:file:bg-blue-100
                cursor-pointer"
            />
          </div>
          <p className="mt-1 text-xs text-gray-500">
            Podporované formáty: JSON, XLSX
          </p>
        </div>

        {/* Template download */}
        <div className="p-3 bg-gray-50 rounded-lg">
          <div className="text-sm text-gray-600 mb-2">
            Stiahnite si vzorovú šablónu:
          </div>
          <div className="flex flex-wrap gap-2">
            <Button variant="ghost" size="sm" onClick={() => handleDownloadTemplate('xlsx')}>
              <svg className="w-4 h-4 mr-1 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              Vzor XLSX
            </Button>
            <Button variant="ghost" size="sm" onClick={() => handleDownloadTemplate('json')}>
              <svg className="w-4 h-4 mr-1 text-yellow-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              Vzor JSON
            </Button>
          </div>
        </div>

        {/* Validation status */}
        {validating && (
          <div className="flex items-center space-x-2 text-blue-600">
            <svg className="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            <span>Validujem súbor...</span>
          </div>
        )}

        {/* Validation result */}
        {validationResult && (
          <div className={`p-4 rounded-lg ${validationResult.valid ? 'bg-green-50' : 'bg-red-50'}`}>
            {validationResult.valid ? (
              <div>
                <div className="flex items-center text-green-700 mb-2">
                  <svg className="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  <span className="font-medium">Súbor je validný</span>
                </div>
                <div className="text-sm text-green-600">
                  Celkovo prvkov: {validationResult.element_count}
                </div>
                {validationResult.summary && (
                  <div className="mt-2 text-sm text-green-600">
                    {Object.entries(validationResult.summary).map(([key, count]) => (
                      <span key={key} className="mr-3">
                        {key}: {count}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <div>
                <div className="flex items-center text-red-700 mb-2">
                  <svg className="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                  <span className="font-medium">Validácia zlyhala</span>
                </div>
                {validationResult.errors && validationResult.errors.length > 0 && (
                  <ul className="text-sm text-red-600 space-y-1 max-h-40 overflow-y-auto">
                    {validationResult.errors.slice(0, 10).map((err, i) => (
                      <li key={i}>
                        • {err.type}[{err.index}] {err.id}: {err.field ? `${err.field} - ` : ''}{err.error}
                      </li>
                    ))}
                    {validationResult.errors.length > 10 && (
                      <li className="text-gray-500">
                        ... a {validationResult.errors.length - 10} ďalších chýb
                      </li>
                    )}
                  </ul>
                )}
              </div>
            )}
          </div>
        )}

        {/* Error message */}
        {error && !validationResult && (
          <div className="p-4 bg-red-50 text-red-700 rounded-lg text-sm">
            {error}
          </div>
        )}

        {/* Actions */}
        <div className="flex justify-end space-x-3 pt-4 border-t">
          <Button variant="secondary" onClick={handleClose}>
            Zrušiť
          </Button>
          <Button
            onClick={handleImport}
            disabled={!file || !validationResult?.valid || importing}
            loading={importing}
          >
            Importovať
          </Button>
        </div>
      </div>
    </Modal>
  );
}
