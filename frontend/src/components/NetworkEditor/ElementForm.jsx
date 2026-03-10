import { useState, useEffect } from 'react';
import { Button, Input, Select } from '../ui';

const FIELD_CONFIGS = {
  busbars: [
    { key: 'id', label: 'ID', type: 'text', required: true },
    { key: 'name', label: 'Názov', type: 'text' },
    { key: 'Un', label: 'Menovité napätie [kV]', type: 'number', required: true, min: 0 },
    { key: 'is_reference', label: 'Referenčný uzol', type: 'checkbox' },
  ],
  external_grids: [
    { key: 'id', label: 'ID', type: 'text', required: true },
    { key: 'name', label: 'Názov', type: 'text' },
    { key: 'bus_id', label: 'Pripojovací uzol', type: 'bus', required: true },
    { key: 'Sk_max', label: 'Sk max [MVA]', type: 'number', required: true, min: 0 },
    { key: 'Sk_min', label: 'Sk min [MVA]', type: 'number', required: true, min: 0 },
    { key: 'rx_ratio', label: 'R/X pomer', type: 'number', required: true, min: 0, step: 0.01, default: 0.1 },
    { key: 'c_max', label: 'Faktor c (max)', type: 'number', min: 0, step: 0.01, default: 1.1 },
    { key: 'c_min', label: 'Faktor c (min)', type: 'number', min: 0, step: 0.01, default: 1.0 },
    { key: 'Z0_Z1_ratio', label: 'Z0/Z1 pomer', type: 'number', min: 0, step: 0.1, default: 1.0 },
    { key: 'X0_X1_ratio', label: 'X0/X1 pomer', type: 'number', min: 0, step: 0.1, default: 1.0 },
  ],
  lines: [
    { key: 'id', label: 'ID', type: 'text', required: true },
    { key: 'name', label: 'Názov', type: 'text' },
    { key: 'type', label: 'Typ', type: 'select', options: [
      { value: 'overhead_line', label: 'Vzdušné vedenie' },
      { value: 'cable', label: 'Kábel' },
    ], default: 'overhead_line' },
    { key: 'bus_from', label: 'Z uzla', type: 'bus', required: true },
    { key: 'bus_to', label: 'Do uzla', type: 'bus', required: true },
    { key: 'length', label: 'Dĺžka [km]', type: 'number', required: true, min: 0, step: 0.001 },
    { key: 'r1_per_km', label: 'R1 [Ω/km]', type: 'number', required: true, min: 0, step: 0.0001 },
    { key: 'x1_per_km', label: 'X1 [Ω/km]', type: 'number', required: true, min: 0, step: 0.0001 },
    { key: 'r0_per_km', label: 'R0 [Ω/km]', type: 'number', required: true, min: 0, step: 0.0001 },
    { key: 'x0_per_km', label: 'X0 [Ω/km]', type: 'number', required: true, min: 0, step: 0.0001 },
    { key: 'parallel_lines', label: 'Počet paralelných', type: 'number', min: 1, default: 1 },
  ],
  transformers_2w: [
    { key: 'id', label: 'ID', type: 'text', required: true },
    { key: 'name', label: 'Názov', type: 'text' },
    { key: 'bus_hv', label: 'VN uzol', type: 'bus', required: true },
    { key: 'bus_lv', label: 'NN uzol', type: 'bus', required: true },
    { key: 'Sn', label: 'Menovitý výkon [MVA]', type: 'number', required: true, min: 0 },
    { key: 'Un_hv', label: 'Un VN [kV]', type: 'number', required: true, min: 0 },
    { key: 'Un_lv', label: 'Un NN [kV]', type: 'number', required: true, min: 0 },
    { key: 'uk_percent', label: 'uk [%]', type: 'number', required: true, min: 0, max: 100 },
    { key: 'Pkr', label: 'Straty nakrátko [kW]', type: 'number', min: 0, default: 0 },
    { key: 'vector_group', label: 'Zapojenie vinutí', type: 'select', required: true, options: [
      { value: 'Dyn11', label: 'Dyn11' },
      { value: 'Dyn5', label: 'Dyn5' },
      { value: 'YNyn0', label: 'YNyn0' },
      { value: 'YNd11', label: 'YNd11' },
      { value: 'Yyn0', label: 'Yyn0' },
      { value: 'Dd0', label: 'Dd0' },
    ] },
    { key: 'neutral_grounding_hv', label: 'Uzemnenie VN', type: 'select', options: [
      { value: 'isolated', label: 'Izolované' },
      { value: 'grounded', label: 'Uzemnené' },
    ], default: 'isolated' },
    { key: 'neutral_grounding_lv', label: 'Uzemnenie NN', type: 'select', options: [
      { value: 'isolated', label: 'Izolované' },
      { value: 'grounded', label: 'Uzemnené' },
    ], default: 'isolated' },
  ],
  transformers_3w: [
    { key: 'id', label: 'ID', type: 'text', required: true },
    { key: 'name', label: 'Názov', type: 'text' },
    { key: 'bus_hv', label: 'VN uzol', type: 'bus', required: true },
    { key: 'bus_mv', label: 'SN uzol', type: 'bus', required: true },
    { key: 'bus_lv', label: 'NN uzol', type: 'bus', required: true },
    { key: 'Sn_hv', label: 'Sn VN [MVA]', type: 'number', required: true, min: 0 },
    { key: 'Sn_mv', label: 'Sn SN [MVA]', type: 'number', min: 0 },
    { key: 'Sn_lv', label: 'Sn NN [MVA]', type: 'number', min: 0 },
    { key: 'Un_hv', label: 'Un VN [kV]', type: 'number', required: true, min: 0 },
    { key: 'Un_mv', label: 'Un SN [kV]', type: 'number', required: true, min: 0 },
    { key: 'Un_lv', label: 'Un NN [kV]', type: 'number', required: true, min: 0 },
    { key: 'uk_hv_mv_percent', label: 'uk VN-SN [%]', type: 'number', required: true, min: 0 },
    { key: 'uk_hv_lv_percent', label: 'uk VN-NN [%]', type: 'number', required: true, min: 0 },
    { key: 'uk_mv_lv_percent', label: 'uk SN-NN [%]', type: 'number', required: true, min: 0 },
  ],
  autotransformers: [
    { key: 'id', label: 'ID', type: 'text', required: true },
    { key: 'name', label: 'Názov', type: 'text' },
    { key: 'bus_hv', label: 'VN uzol', type: 'bus', required: true },
    { key: 'bus_lv', label: 'SN uzol', type: 'bus', required: true },
    { key: 'Sn', label: 'Sn [MVA]', type: 'number', required: true, min: 0 },
    { key: 'Un_hv', label: 'Un VN [kV]', type: 'number', required: true, min: 0 },
    { key: 'Un_lv', label: 'Un SN [kV]', type: 'number', required: true, min: 0 },
    { key: 'uk_percent', label: 'uk [%]', type: 'number', required: true, min: 0 },
    { key: 'Pkr', label: 'Straty nakrátko [kW]', type: 'number', min: 0, default: 0 },
    { key: 'neutral_grounding', label: 'Uzemnenie', type: 'select', required: true, options: [
      { value: 'grounded', label: 'Uzemnené' },
      { value: 'isolated', label: 'Izolované' },
    ], default: 'grounded' },
    { key: 'has_tertiary_delta', label: 'Delta terciár', type: 'checkbox', default: false },
  ],
  generators: [
    { key: 'id', label: 'ID', type: 'text', required: true },
    { key: 'name', label: 'Názov', type: 'text' },
    { key: 'bus_id', label: 'Pripojovací uzol', type: 'bus', required: true },
    { key: 'Sn', label: 'Sn [MVA]', type: 'number', required: true, min: 0 },
    { key: 'Un', label: 'Un [kV]', type: 'number', required: true, min: 0 },
    { key: 'Xd_pp', label: "Xd'' [%]", type: 'number', required: true, min: 0 },
    { key: 'Ra', label: 'Ra [%]', type: 'number', min: 0, default: 0 },
    { key: 'cos_phi', label: 'cos φ', type: 'number', required: true, min: 0, max: 1, step: 0.01, default: 0.85 },
  ],
  motors: [
    { key: 'id', label: 'ID', type: 'text', required: true },
    { key: 'name', label: 'Názov', type: 'text' },
    { key: 'bus_id', label: 'Pripojovací uzol', type: 'bus', required: true },
    { key: 'Un', label: 'Un [kV]', type: 'number', required: true, min: 0 },
    { key: 'input_mode', label: 'Režim zadania', type: 'select', options: [
      { value: 'power', label: 'Výkon' },
      { value: 'current', label: 'Prúd' },
    ], default: 'power' },
    { key: 'Pn', label: 'Pn [kW]', type: 'number', min: 0 },
    { key: 'eta', label: 'Účinnosť', type: 'number', min: 0, max: 1, step: 0.01 },
    { key: 'cos_phi', label: 'cos φ', type: 'number', min: 0, max: 1, step: 0.01 },
    { key: 'Ia_In', label: 'Ia/In', type: 'number', required: true, min: 1, step: 0.1, default: 6 },
    { key: 'pole_pairs', label: 'Počet párov pólov', type: 'number', min: 1, default: 1 },
  ],
  psus: [
    { key: 'id', label: 'ID', type: 'text', required: true },
    { key: 'name', label: 'Názov', type: 'text' },
    { key: 'generator_id', label: 'Generátor', type: 'generator', required: true },
    { key: 'transformer_id', label: 'Transformátor', type: 'transformer', required: true },
    { key: 'has_oltc', label: 'S reguláciou (OLTC)', type: 'checkbox', default: true },
  ],
  impedances: [
    { key: 'id', label: 'ID', type: 'text', required: true },
    { key: 'name', label: 'Názov', type: 'text' },
    { key: 'bus_from', label: 'Z uzla', type: 'bus', required: true },
    { key: 'bus_to', label: 'Do uzla', type: 'bus', required: true },
    { key: 'R', label: 'R [Ω]', type: 'number', required: true, min: 0, step: 0.001 },
    { key: 'X', label: 'X [Ω]', type: 'number', required: true, step: 0.001 },
    { key: 'R0', label: 'R0 [Ω]', type: 'number', min: 0, step: 0.001 },
    { key: 'X0', label: 'X0 [Ω]', type: 'number', step: 0.001 },
  ],
  grounding_impedances: [
    { key: 'id', label: 'ID', type: 'text', required: true },
    { key: 'name', label: 'Názov', type: 'text' },
    { key: 'R', label: 'R [Ω]', type: 'number', required: true, min: 0, step: 0.001 },
    { key: 'X', label: 'X [Ω]', type: 'number', required: true, min: 0, step: 0.001 },
  ],
};

export default function ElementForm({ type, element, allElements, onSave, onCancel }) {
  const fields = FIELD_CONFIGS[type] || [];
  const [formData, setFormData] = useState({});
  const [errors, setErrors] = useState({});

  useEffect(() => {
    if (element) {
      setFormData(element);
    } else {
      const defaults = {};
      fields.forEach((f) => {
        if (f.default !== undefined) defaults[f.key] = f.default;
      });
      setFormData(defaults);
    }
  }, [element, type]);

  const handleChange = (key, value) => {
    setFormData({ ...formData, [key]: value });
    if (errors[key]) {
      setErrors({ ...errors, [key]: null });
    }
  };

  const validate = () => {
    const newErrors = {};
    fields.forEach((f) => {
      if (f.required && !formData[f.key]) {
        newErrors[f.key] = 'Povinné pole';
      }
    });
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (validate()) {
      onSave(formData);
    }
  };

  const renderField = (field) => {
    const value = formData[field.key] ?? '';

    switch (field.type) {
      case 'checkbox':
        return (
          <label className="flex items-center">
            <input
              type="checkbox"
              checked={!!value}
              onChange={(e) => handleChange(field.key, e.target.checked)}
              className="h-4 w-4 text-blue-600 rounded border-gray-300"
            />
            <span className="ml-2 text-sm text-gray-700">{field.label}</span>
          </label>
        );

      case 'select':
        return (
          <Select
            label={field.label}
            value={value}
            onChange={(e) => handleChange(field.key, e.target.value)}
            options={field.options}
            error={errors[field.key]}
          />
        );

      case 'bus':
        return (
          <Select
            label={field.label}
            value={value}
            onChange={(e) => handleChange(field.key, e.target.value)}
            options={[
              { value: '', label: '-- Vyberte uzol --' },
              ...(allElements.busbars || []).map((b) => ({
                value: b.id,
                label: `${b.name || b.id} (${b.Un} kV)`,
              })),
            ]}
            error={errors[field.key]}
          />
        );

      case 'generator':
        return (
          <Select
            label={field.label}
            value={value}
            onChange={(e) => handleChange(field.key, e.target.value)}
            options={[
              { value: '', label: '-- Vyberte generátor --' },
              ...(allElements.generators || []).map((g) => ({
                value: g.id,
                label: g.name || g.id,
              })),
            ]}
            error={errors[field.key]}
          />
        );

      case 'transformer':
        return (
          <Select
            label={field.label}
            value={value}
            onChange={(e) => handleChange(field.key, e.target.value)}
            options={[
              { value: '', label: '-- Vyberte transformátor --' },
              ...(allElements.transformers_2w || []).map((t) => ({
                value: t.id,
                label: `${t.name || t.id} (2W)`,
              })),
              ...(allElements.transformers_3w || []).map((t) => ({
                value: t.id,
                label: `${t.name || t.id} (3W)`,
              })),
            ]}
            error={errors[field.key]}
          />
        );

      case 'number':
        return (
          <Input
            label={field.label}
            type="number"
            value={value}
            onChange={(e) => handleChange(field.key, parseFloat(e.target.value) || '')}
            min={field.min}
            max={field.max}
            step={field.step || 'any'}
            error={errors[field.key]}
          />
        );

      default:
        return (
          <Input
            label={field.label}
            type={field.type}
            value={value}
            onChange={(e) => handleChange(field.key, e.target.value)}
            error={errors[field.key]}
          />
        );
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <div className="grid grid-cols-2 gap-4">
        {fields.map((field) => (
          <div key={field.key} className={field.type === 'checkbox' ? 'col-span-2' : ''}>
            {renderField(field)}
          </div>
        ))}
      </div>

      <div className="flex justify-end space-x-3 mt-6 pt-4 border-t">
        <Button type="button" variant="secondary" onClick={onCancel}>
          Zrušiť
        </Button>
        <Button type="submit">
          {element ? 'Uložiť' : 'Pridať'}
        </Button>
      </div>
    </form>
  );
}
