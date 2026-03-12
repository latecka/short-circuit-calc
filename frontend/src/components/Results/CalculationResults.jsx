import { useState } from 'react';
import { Table, TableHead, TableBody, TableRow, TableHeader, TableCell, Button } from '../ui';

const API_URL = import.meta.env.VITE_API_URL || '';

export default function CalculationResults({ result }) {
  const [selectedFaultType, setSelectedFaultType] = useState('all');
  const [exporting, setExporting] = useState(null);

  if (!result) {
    return (
      <div className="text-center py-8 text-gray-500">
        Žiadne výsledky
      </div>
    );
  }

  // Show error message if calculation failed
  if (result.status === 'failed' || result.error_message) {
    return (
      <div className="space-y-4">
        <div className="flex items-center space-x-2">
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
            Zlyhal
          </span>
        </div>
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <h4 className="text-sm font-medium text-red-800 mb-2">Chyba výpočtu:</h4>
          <p className="text-sm text-red-700 font-mono whitespace-pre-wrap">
            {result.error_message || 'Neznáma chyba'}
          </p>
        </div>
      </div>
    );
  }

  if (!result.results || result.results.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        Žiadne výsledky
      </div>
    );
  }

  const faultTypes = [...new Set(result.results.map((r) => r.fault_type))];
  const filteredResults = selectedFaultType === 'all'
    ? result.results
    : result.results.filter((r) => r.fault_type === selectedFaultType);

  // Group results by bus
  const resultsByBus = {};
  result.results.forEach((r) => {
    if (!resultsByBus[r.bus_id]) {
      resultsByBus[r.bus_id] = {};
    }
    resultsByBus[r.bus_id][r.fault_type] = r;
  });

  const formatNumber = (num, decimals = 3) => {
    if (num === null || num === undefined) return '-';
    return Number(num).toFixed(decimals);
  };

  const handleExport = async (format) => {
    setExporting(format);
    try {
      const token = localStorage.getItem('token');
      let response;

      if (format === 'pdf' && result.onCaptureSchema) {
        // Capture schema image from React Flow and send as POST
        const schemaImage = await result.onCaptureSchema();
        response = await fetch(`${API_URL}/api/v1/export/${format}/${result.id}`, {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ schema_image: schemaImage }),
        });
      } else {
        response = await fetch(`${API_URL}/api/v1/export/${format}/${result.id}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
      }

      if (!response.ok) throw new Error('Export failed');

      const blob = await response.blob();
      const filename = response.headers.get('Content-Disposition')?.match(/filename="(.+)"/)?.[1]
        || `export.${format}`;

      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      a.remove();
    } catch (err) {
      console.error('Export failed:', err);
      alert('Export zlyhal');
    } finally {
      setExporting(null);
    }
  };

  return (
    <div className="space-y-4">
      {/* Status and Export */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
            result.status === 'completed'
              ? 'bg-green-100 text-green-800'
              : result.status === 'failed'
              ? 'bg-red-100 text-red-800'
              : 'bg-yellow-100 text-yellow-800'
          }`}>
            {result.status === 'completed' ? 'Dokončený' :
             result.status === 'failed' ? 'Zlyhal' : 'Prebieha'}
          </span>
          <span className="text-sm text-gray-500">
            {result.calculation_mode === 'max' ? 'Ik max' : 'Ik min'}
          </span>
        </div>
        <div className="flex items-center space-x-2">
          <Button
            size="sm"
            variant="secondary"
            onClick={() => handleExport('pdf')}
            disabled={exporting !== null}
          >
            {exporting === 'pdf' ? (
              <svg className="animate-spin h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            ) : (
              <svg className="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            )}
            PDF
          </Button>
          <Button
            size="sm"
            variant="secondary"
            onClick={() => handleExport('xlsx')}
            disabled={exporting !== null}
          >
            {exporting === 'xlsx' ? (
              <svg className="animate-spin h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            ) : (
              <svg className="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            )}
            XLSX
          </Button>
          <span className="text-sm text-gray-500">
            {new Date(result.completed_at || result.started_at).toLocaleString('sk-SK')}
          </span>
        </div>
      </div>

      {result.error_message && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-700">
          {result.error_message}
        </div>
      )}

      {/* Filter */}
      <div className="flex space-x-2">
        <Button
          size="sm"
          variant={selectedFaultType === 'all' ? 'primary' : 'secondary'}
          onClick={() => setSelectedFaultType('all')}
        >
          Všetky
        </Button>
        {faultTypes.map((ft) => (
          <Button
            key={ft}
            size="sm"
            variant={selectedFaultType === ft ? 'primary' : 'secondary'}
            onClick={() => setSelectedFaultType(ft)}
          >
            {ft}
          </Button>
        ))}
      </div>

      {/* Summary Table */}
      {selectedFaultType === 'all' ? (
        <Table>
          <TableHead>
            <TableRow>
              <TableHeader>Uzol</TableHeader>
              <TableHeader className="text-right">Ik3 [kA]</TableHeader>
              <TableHeader className="text-right">ip3 [kA]</TableHeader>
              <TableHeader className="text-right">Ik2 [kA]</TableHeader>
              <TableHeader className="text-right">Ik1 [kA]</TableHeader>
            </TableRow>
          </TableHead>
          <TableBody>
            {Object.entries(resultsByBus).map(([busId, faults]) => (
              <TableRow key={busId}>
                <TableCell className="font-medium">{busId}</TableCell>
                <TableCell className="text-right font-mono">
                  {formatNumber(faults.Ik3?.Ik)}
                </TableCell>
                <TableCell className="text-right font-mono">
                  {formatNumber(faults.Ik3?.ip)}
                </TableCell>
                <TableCell className="text-right font-mono">
                  {formatNumber(faults.Ik2?.Ik)}
                </TableCell>
                <TableCell className="text-right font-mono">
                  {formatNumber(faults.Ik1?.Ik)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      ) : (
        <Table>
          <TableHead>
            <TableRow>
              <TableHeader>Uzol</TableHeader>
              <TableHeader className="text-right">Ik [kA]</TableHeader>
              <TableHeader className="text-right">ip [kA]</TableHeader>
              <TableHeader className="text-right">R/X</TableHeader>
              <TableHeader className="text-right">c</TableHeader>
              <TableHeader className="text-right">Z1 [Ω]</TableHeader>
            </TableRow>
          </TableHead>
          <TableBody>
            {filteredResults.map((r) => (
              <TableRow key={`${r.bus_id}-${r.fault_type}`}>
                <TableCell className="font-medium">{r.bus_id}</TableCell>
                <TableCell className="text-right font-mono">{formatNumber(r.Ik)}</TableCell>
                <TableCell className="text-right font-mono">{formatNumber(r.ip)}</TableCell>
                <TableCell className="text-right font-mono">{formatNumber(r.R_X_ratio)}</TableCell>
                <TableCell className="text-right font-mono">{formatNumber(r.c_factor, 2)}</TableCell>
                <TableCell className="text-right font-mono text-xs">
                  {formatNumber(r.Z1?.r, 4)} + j{formatNumber(r.Z1?.x, 4)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      {/* Warnings */}
      {filteredResults.some((r) => r.warnings?.length > 0) && (
        <div className="mt-4">
          <h4 className="text-sm font-medium text-gray-700 mb-2">Varovania:</h4>
          <ul className="text-sm text-yellow-700 bg-yellow-50 rounded-lg p-3 space-y-1">
            {filteredResults.flatMap((r) =>
              (r.warnings || []).map((w, i) => (
                <li key={`${r.bus_id}-${i}`}>• {r.bus_id}: {w}</li>
              ))
            )}
          </ul>
        </div>
      )}
    </div>
  );
}
