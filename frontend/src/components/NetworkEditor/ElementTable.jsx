import { Button, Table, TableHead, TableBody, TableRow, TableHeader, TableCell } from '../ui';

const COLUMNS = {
  busbars: [
    { key: 'id', label: 'ID' },
    { key: 'name', label: 'Názov' },
    { key: 'Un', label: 'Un [kV]' },
    { key: 'is_reference', label: 'Referenčný', format: (v) => (v ? 'Áno' : 'Nie') },
  ],
  external_grids: [
    { key: 'id', label: 'ID' },
    { key: 'name', label: 'Názov' },
    { key: 'bus_id', label: 'Uzol' },
    { key: 'Sk_max', label: 'Sk max [MVA]' },
    { key: 'Sk_min', label: 'Sk min [MVA]' },
    { key: 'rx_ratio', label: 'R/X' },
  ],
  lines: [
    { key: 'id', label: 'ID' },
    { key: 'name', label: 'Názov' },
    { key: 'bus_from', label: 'Z uzla' },
    { key: 'bus_to', label: 'Do uzla' },
    { key: 'length', label: 'Dĺžka [km]' },
    { key: 'r1_per_km', label: 'R1 [Ω/km]' },
    { key: 'x1_per_km', label: 'X1 [Ω/km]' },
  ],
  transformers_2w: [
    { key: 'id', label: 'ID' },
    { key: 'name', label: 'Názov' },
    { key: 'bus_hv', label: 'VN uzol' },
    { key: 'bus_lv', label: 'NN uzol' },
    { key: 'Sn', label: 'Sn [MVA]' },
    { key: 'Un_hv', label: 'Un VN [kV]' },
    { key: 'Un_lv', label: 'Un NN [kV]' },
    { key: 'uk_percent', label: 'uk [%]' },
    { key: 'vector_group', label: 'Zapojenie' },
  ],
  transformers_3w: [
    { key: 'id', label: 'ID' },
    { key: 'bus_hv', label: 'VN' },
    { key: 'bus_mv', label: 'SN' },
    { key: 'bus_lv', label: 'NN' },
    { key: 'Sn_hv', label: 'Sn [MVA]' },
    { key: 'uk_hv_mv_percent', label: 'uk VN-SN [%]' },
  ],
  autotransformers: [
    { key: 'id', label: 'ID' },
    { key: 'name', label: 'Názov' },
    { key: 'bus_hv', label: 'VN uzol' },
    { key: 'bus_lv', label: 'SN uzol' },
    { key: 'Sn', label: 'Sn [MVA]' },
    { key: 'uk_percent', label: 'uk [%]' },
    { key: 'neutral_grounding', label: 'Uzemnenie' },
  ],
  generators: [
    { key: 'id', label: 'ID' },
    { key: 'name', label: 'Názov' },
    { key: 'bus_id', label: 'Uzol' },
    { key: 'Sn', label: 'Sn [MVA]' },
    { key: 'Un', label: 'Un [kV]' },
    { key: 'Xd_pp', label: "Xd'' [%]" },
    { key: 'cos_phi', label: 'cos φ' },
  ],
  motors: [
    { key: 'id', label: 'ID' },
    { key: 'name', label: 'Názov' },
    { key: 'bus_id', label: 'Uzol' },
    { key: 'Un', label: 'Un [kV]' },
    { key: 'Pn', label: 'Pn [kW]' },
    { key: 'Ia_In', label: 'Ia/In' },
  ],
  psus: [
    { key: 'id', label: 'ID' },
    { key: 'name', label: 'Názov' },
    { key: 'generator_id', label: 'Generátor' },
    { key: 'transformer_id', label: 'Transformátor' },
    { key: 'has_oltc', label: 'OLTC', format: (v) => (v ? 'Áno' : 'Nie') },
  ],
  impedances: [
    { key: 'id', label: 'ID' },
    { key: 'name', label: 'Názov' },
    { key: 'bus_from', label: 'Z uzla' },
    { key: 'bus_to', label: 'Do uzla' },
    { key: 'R', label: 'R [Ω]' },
    { key: 'X', label: 'X [Ω]' },
  ],
  grounding_impedances: [
    { key: 'id', label: 'ID' },
    { key: 'name', label: 'Názov' },
    { key: 'R', label: 'R [Ω]' },
    { key: 'X', label: 'X [Ω]' },
  ],
};

export default function ElementTable({ type, elements, allElements, onEdit, onDelete }) {
  const columns = COLUMNS[type] || [];

  if (elements.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500">
        Žiadne prvky. Kliknite na "Pridať" pre vytvorenie nového.
      </div>
    );
  }

  const getBusName = (busId) => {
    const bus = allElements.busbars?.find((b) => b.id === busId);
    return bus ? (bus.name || busId) : busId;
  };

  const formatValue = (col, value) => {
    if (col.format) return col.format(value);
    if (col.key.includes('bus') && col.key !== 'busbars') {
      return getBusName(value);
    }
    if (value === null || value === undefined) return '-';
    if (typeof value === 'number') {
      return Number.isInteger(value) ? value : value.toFixed(3);
    }
    return String(value);
  };

  return (
    <Table>
      <TableHead>
        <TableRow>
          {columns.map((col) => (
            <TableHeader key={col.key}>{col.label}</TableHeader>
          ))}
          <TableHeader className="w-24">Akcie</TableHeader>
        </TableRow>
      </TableHead>
      <TableBody>
        {elements.map((element) => (
          <TableRow key={element.id}>
            {columns.map((col) => (
              <TableCell key={col.key}>
                {formatValue(col, element[col.key])}
              </TableCell>
            ))}
            <TableCell>
              <div className="flex space-x-1">
                <Button variant="ghost" size="sm" onClick={() => onEdit(element)}>
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                  </svg>
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => onDelete(element.id)}
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
  );
}
