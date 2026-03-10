# Data Dictionary

Short-Circuit Calculator - IEC 60909-0 V1

## Spoločné konvencie

- **id**: Unikátny identifikátor prvku (string, UUID alebo user-defined)
- **type**: Diskriminátor typu prvku (const string)
- **name**: Voliteľný popisný názov
- **validation_status**: `pending` | `valid` | `error`

### Jednotky

| Veličina | Jednotka | Poznámka |
|----------|----------|----------|
| Napätie | kV | Menovité napätie |
| Výkon | MVA / MW / kW | Podľa kontextu |
| Impedancia | Ω | Absolútna hodnota |
| Prúd | kA / A | Podľa kontextu |
| Dĺžka | km | Vedenia, káble |
| Percentuálne hodnoty | % | uk%, straty |

---

## 1. Busbar (Node)

Uzol siete - zbernica, prípojnica.

| Pole | Typ | Povinné | Default | Validácia | Popis |
|------|-----|---------|---------|-----------|-------|
| id | string | áno | - | unique | Unikátny identifikátor |
| type | const | áno | "busbar" | - | Typ prvku |
| name | string | nie | null | - | Popisný názov |
| Un | float [kV] | áno | - | > 0 | Menovité napätie |
| is_reference | boolean | nie | false | - | Referenčný uzol siete |

---

## 2. External Grid (Napájacia sústava)

Externá napájacia sieť - modelovaná ako ekvivalentný zdroj.

| Pole | Typ | Povinné | Default | Validácia | Popis |
|------|-----|---------|---------|-----------|-------|
| id | string | áno | - | unique | Unikátny identifikátor |
| type | const | áno | "external_grid" | - | Typ prvku |
| name | string | nie | null | - | Popisný názov |
| bus_id | ref | áno | - | exists | Pripojovací uzol |
| Sk_max | float [MVA] | áno | - | > 0 | Skratový výkon max |
| Sk_min | float [MVA] | áno | - | > 0, ≤ Sk_max | Skratový výkon min |
| rx_ratio | float | áno | - | > 0 | Pomer R/X |
| c_max | float | nie | 1.1 | > 0 | Napäťový faktor c (max) |
| c_min | float | nie | 1.0 | > 0 | Napäťový faktor c (min) |
| Z0_Z1_ratio | float | nie | 1.0 | ≥ 0 | Pomer Z0/Z1 |
| X0_X1_ratio | float | nie | 1.0 | ≥ 0 | Pomer X0/X1 |
| R0_X0_ratio | float | nie | null | ≥ 0 | Pomer R0/X0 (ak null, použije rx_ratio) |

### Odvodzovanie impedancií

```
Z1 = c * Un² / Sk
R1 = Z1 / sqrt(1 + (1/rx_ratio)²)
X1 = R1 / rx_ratio
Z2 = Z1 (predpoklad)
Z0 = Z1 * Z0_Z1_ratio
```

---

## 3. Overhead Line (Vzdušné vedenie)

| Pole | Typ | Povinné | Default | Validácia | Popis |
|------|-----|---------|---------|-----------|-------|
| id | string | áno | - | unique | Unikátny identifikátor |
| type | const | áno | "overhead_line" | - | Typ prvku |
| name | string | nie | null | - | Popisný názov |
| bus_from | ref | áno | - | exists | Počiatočný uzol |
| bus_to | ref | áno | - | exists | Koncový uzol |
| length | float [km] | áno | - | > 0 | Dĺžka vedenia |
| r1_per_km | float [Ω/km] | áno | - | ≥ 0 | Činný odpor súslednej zložky |
| x1_per_km | float [Ω/km] | áno | - | > 0 | Reaktancia súslednej zložky |
| r0_per_km | float [Ω/km] | áno | - | ≥ 0 | Činný odpor nulovej zložky |
| x0_per_km | float [Ω/km] | áno | - | > 0 | Reaktancia nulovej zložky |
| b1_per_km | float [µS/km] | nie | 0 | ≥ 0 | Susceptancia súslednej zložky |
| parallel_lines | int | nie | 1 | ≥ 1 | Počet paralelných vedení |
| in_service | boolean | nie | true | - | V prevádzke |

### Výpočet celkových impedancií

```
R1 = r1_per_km * length / parallel_lines
X1 = x1_per_km * length / parallel_lines
R0 = r0_per_km * length / parallel_lines
X0 = x0_per_km * length / parallel_lines
```

---

## 4. Cable (Kábel)

| Pole | Typ | Povinné | Default | Validácia | Popis |
|------|-----|---------|---------|-----------|-------|
| id | string | áno | - | unique | Unikátny identifikátor |
| type | const | áno | "cable" | - | Typ prvku |
| name | string | nie | null | - | Popisný názov |
| bus_from | ref | áno | - | exists | Počiatočný uzol |
| bus_to | ref | áno | - | exists | Koncový uzol |
| length | float [km] | áno | - | > 0 | Dĺžka kábla |
| r1_per_km | float [Ω/km] | áno | - | ≥ 0 | Činný odpor súslednej zložky |
| x1_per_km | float [Ω/km] | áno | - | > 0 | Reaktancia súslednej zložky |
| r0_per_km | float [Ω/km] | áno | - | ≥ 0 | Činný odpor nulovej zložky |
| x0_per_km | float [Ω/km] | áno | - | > 0 | Reaktancia nulovej zložky |
| b1_per_km | float [µS/km] | nie | 0 | ≥ 0 | Susceptancia súslednej zložky |
| cable_type | string | nie | null | - | Typové označenie kábla |
| parallel_cables | int | nie | 1 | ≥ 1 | Počet paralelných káblov |
| in_service | boolean | nie | true | - | V prevádzke |

---

## 5. Transformer 2-Winding (2-vinutíový transformátor)

| Pole | Typ | Povinné | Default | Validácia | Popis |
|------|-----|---------|---------|-----------|-------|
| id | string | áno | - | unique | Unikátny identifikátor |
| type | const | áno | "transformer_2w" | - | Typ prvku |
| name | string | nie | null | - | Popisný názov |
| bus_hv | ref | áno | - | exists | Uzol VN strany |
| bus_lv | ref | áno | - | exists | Uzol NN/SN strany |
| Sn | float [MVA] | áno | - | > 0 | Menovitý zdanlivý výkon |
| Un_hv | float [kV] | áno | - | > 0 | Menovité napätie VN |
| Un_lv | float [kV] | áno | - | > 0 | Menovité napätie NN/SN |
| uk_percent | float [%] | áno | - | > 0, < 100 | Napätie nakrátko |
| Pkr | float [kW] | áno | - | ≥ 0 | Straty nakrátko |
| vector_group | string | áno | - | valid_vg | Zapojenie vinutí (Dyn11, YNyn0, ...) |
| tap_position | float [%] | nie | 0 | -20..+20 | Poloha odbočky |
| tap_side | enum | nie | "hv" | hv/lv | Strana s odbočkou |
| neutral_grounding_hv | enum | nie | "isolated" | grounded/isolated/impedance | Uzemnenie neutrála VN |
| neutral_grounding_lv | enum | nie | "isolated" | grounded/isolated/impedance | Uzemnenie neutrála NN |
| grounding_impedance_hv_id | ref | podm. | null | exists | Ref na zemniaci prvok VN |
| grounding_impedance_lv_id | ref | podm. | null | exists | Ref na zemniaci prvok NN |
| in_service | boolean | nie | true | - | V prevádzke |

### Vector group pravidlá pre Z0

| VN vinutie | NN vinutie | Z0 prenos |
|------------|------------|-----------|
| D | yn (uzemnené) | Z0 blokované na VN strane |
| Yn (uzemnené) | yn (uzemnené) | Z0 prechádza |
| Y (izolované) | yn | Z0 blokované |
| D | d | Z0 blokované obidve strany |

---

## 6. Transformer 3-Winding (3-vinutíový transformátor)

| Pole | Typ | Povinné | Default | Validácia | Popis |
|------|-----|---------|---------|-----------|-------|
| id | string | áno | - | unique | Unikátny identifikátor |
| type | const | áno | "transformer_3w" | - | Typ prvku |
| name | string | nie | null | - | Popisný názov |
| bus_hv | ref | áno | - | exists | Uzol VN strany |
| bus_mv | ref | áno | - | exists | Uzol SN strany |
| bus_lv | ref | áno | - | exists | Uzol NN strany |
| Sn_hv | float [MVA] | áno | - | > 0 | Menovitý výkon VN |
| Sn_mv | float [MVA] | áno | - | > 0 | Menovitý výkon SN |
| Sn_lv | float [MVA] | áno | - | > 0 | Menovitý výkon NN |
| Un_hv | float [kV] | áno | - | > 0 | Menovité napätie VN |
| Un_mv | float [kV] | áno | - | > 0 | Menovité napätie SN |
| Un_lv | float [kV] | áno | - | > 0 | Menovité napätie NN |
| uk_hv_mv_percent | float [%] | áno | - | > 0 | uk% medzi VN-SN |
| uk_hv_lv_percent | float [%] | áno | - | > 0 | uk% medzi VN-NN |
| uk_mv_lv_percent | float [%] | áno | - | > 0 | uk% medzi SN-NN |
| Pkr_hv_mv | float [kW] | áno | - | ≥ 0 | Straty nakrátko VN-SN |
| Pkr_hv_lv | float [kW] | áno | - | ≥ 0 | Straty nakrátko VN-NN |
| Pkr_mv_lv | float [kW] | áno | - | ≥ 0 | Straty nakrátko SN-NN |
| vector_group_hv_mv | string | áno | - | valid_vg | Zapojenie VN-SN |
| vector_group_hv_lv | string | áno | - | valid_vg | Zapojenie VN-NN |
| tap_position | float [%] | nie | 0 | - | Poloha odbočky |
| tap_side | enum | nie | "hv" | hv/mv/lv | Strana s odbočkou |
| in_service | boolean | nie | true | - | V prevádzke |

### Validácia konzistencie uk%

Engine musí overiť konzistenciu trojice uk% hodnôt:
```
uk_hv + uk_mv ≥ uk_hv_mv
uk_hv + uk_lv ≥ uk_hv_lv
uk_mv + uk_lv ≥ uk_mv_lv
```

---

## 7. Autotransformer

Autotransformátor s galvanickým prepojením vinutí.

| Pole | Typ | Povinné | Default | Validácia | Popis |
|------|-----|---------|---------|-----------|-------|
| id | string | áno | - | unique | Unikátny identifikátor |
| type | const | áno | "autotransformer" | - | Typ prvku |
| name | string | nie | null | - | Popisný názov |
| bus_hv | ref | áno | - | exists | Pripojovací uzol VN |
| bus_lv | ref | áno | - | exists | Pripojovací uzol SN |
| Sn | float [MVA] | áno | - | > 0 | Menovitý zdanlivý výkon |
| Un_hv | float [kV] | áno | - | > 0 | Menovité napätie VN |
| Un_lv | float [kV] | áno | - | > 0, < Un_hv | Menovité napätie SN |
| uk_percent | float [%] | áno | - | > 0, < 100 | Napätie nakrátko |
| Pkr | float [kW] | áno | - | ≥ 0 | Straty nakrátko |
| vector_group | string | áno | - | YNa0/YNa6/... | Zapojenie (autotransformátor) |
| has_tertiary_delta | boolean | áno | - | - | Prítomnosť delta terciáru |
| tertiary_Sn | float [MVA] | podm. | null | > 0 | Výkon terciáru (povinné ak has_tertiary_delta) |
| neutral_grounding | enum | áno | - | grounded/isolated/impedance | Uzemnenie neutrála |
| grounding_impedance_id | ref | podm. | null | exists | Ref na zemniaci prvok (povinné ak impedance) |
| Z0_source | enum | áno | - | measured/derived | Zdroj Z0 dát |
| Z0_measured_r | float [Ω] | podm. | null | - | R0 (povinné ak measured) |
| Z0_measured_x | float [Ω] | podm. | null | - | X0 (povinné ak measured) |
| tap_position | float [%] | nie | 0 | -20..+20 | Poloha odbočky |
| in_service | boolean | nie | true | - | V prevádzke |

### Z0 pravidlá pre autotransformátor

| neutral_grounding | has_tertiary_delta | Z0 správanie |
|-------------------|-------------------|--------------|
| grounded | false | Galvanický Z0 prenos |
| grounded | true | Z0 cez paralelnú cestu delta terciáru |
| isolated | false | Z0 = ∞ (blokovanie) |
| isolated | true | Z0 cez delta terciár |
| impedance | * | Z0 cez zemniaci prvok |

---

## 8. Synchronous Generator

Synchrónny generátor.

| Pole | Typ | Povinné | Default | Validácia | Popis |
|------|-----|---------|---------|-----------|-------|
| id | string | áno | - | unique | Unikátny identifikátor |
| type | const | áno | "synchronous_generator" | - | Typ prvku |
| name | string | nie | null | - | Popisný názov |
| bus_id | ref | áno | - | exists | Pripojovací uzol |
| Sn | float [MVA] | áno | - | > 0 | Menovitý zdanlivý výkon |
| Un | float [kV] | áno | - | > 0 | Menovité napätie |
| Xd_pp | float [%] | áno | - | > 0 | Subtranzientná reaktancia Xd'' |
| Ra | float [%] | nie | 0 | ≥ 0 | Činný odpor statora |
| cos_phi | float | áno | - | 0..1 | Účiník |
| connection | enum | nie | "direct" | direct/via_transformer | Spôsob pripojenia |
| in_service | boolean | nie | true | - | V prevádzke |

### Korekčný faktor KG (priame pripojenie)

```
KG = Un / (UrG * (1 + Xd'' * sin(phi)))
```

Kde:
- Un = menovité napätie siete
- UrG = menovité napätie generátora
- Xd'' = subtranzientná reaktancia (p.u.)

---

## 9. Power Station Unit (PSU)

Bloková jednotka: generátor + blokový transformátor.

| Pole | Typ | Povinné | Default | Validácia | Popis |
|------|-----|---------|---------|-----------|-------|
| id | string | áno | - | unique | Unikátny identifikátor |
| type | const | áno | "power_station_unit" | - | Typ prvku |
| name | string | nie | null | - | Popisný názov |
| generator_id | ref | áno | - | exists, type=synchronous_generator | Referencia na generátor |
| transformer_id | ref | áno | - | exists, type=transformer_2w/3w | Referencia na transformátor |
| has_oltc | boolean | áno | - | - | Transformátor s OLTC |
| generator_winding | enum | podm. | null | hv/mv/lv | Vinutie pre generátor (povinné pre 3W Tr) |

### Validačné pravidlá

1. Generátor a transformátor musia byť topologicky prepojené (spoločný uzol)
2. Transformátor nesmie byť súčasťou inej PSU
3. Generátor nesmie byť súčasťou inej PSU
4. V1 podporuje len 1:1 párovanie (generátor : transformátor)

### Korekčné faktory

| has_oltc | Faktor | Referencia IEC 60909-0 |
|----------|--------|------------------------|
| true | KS | §3.7.1, rovnice 21-22 |
| false | KSO | §3.7.2, rovnice 23-24 |

---

## 10. Asynchronous Motor

Asynchrónny motor.

| Pole | Typ | Povinné | Default | Validácia | Popis |
|------|-----|---------|---------|-----------|-------|
| id | string | áno | - | unique | Unikátny identifikátor |
| type | const | áno | "asynchronous_motor" | - | Typ prvku |
| name | string | nie | null | - | Popisný názov |
| bus_id | ref | áno | - | exists | Pripojovací uzol |
| Un | float [kV] | áno | - | > 0 | Menovité napätie |
| input_mode | enum | áno | - | power/current | Režim zadania |
| Pn | float [kW] | podm. | null | > 0 | Menovitý výkon (ak power) |
| eta | float | podm. | null | 0..1 | Účinnosť (ak power) |
| cos_phi | float | podm. | null | 0..1 | Účiník (ak power) |
| In | float [A] | podm. | null | > 0 | Menovitý prúd (ak current) |
| Ia_In | float | áno | - | > 1 | Pomer záberového / menovitého prúdu |
| pole_pairs | int | nie | 1 | ≥ 1 | Počet párov pólov |
| include_in_sc | boolean | nie | true | - | Započítať do skratu |
| in_service | boolean | nie | true | - | V prevádzke |

### Validácia vstupných režimov

| input_mode | Povinné polia |
|------------|---------------|
| power | Pn, eta, cos_phi, Ia_In |
| current | In, Ia_In |

### R/X pomer podľa IEC 60909-0 §3.8

| Podmienka | R/X |
|-----------|-----|
| Un > 1 kV a Pn/p ≥ 1 MW | 0.10 |
| Un > 1 kV a Pn/p < 1 MW | 0.15 |
| Un ≤ 1 kV | 0.42 |

### Príspevok podľa typu poruchy

| Typ poruchy | Max variant | Min variant |
|-------------|-------------|-------------|
| Ik3 | Z1 | 0 (ignorované) |
| Ik2 | Z1+Z2 (Z2≈Z1) | 0 (ignorované) |
| Ik1 | 0 (Z0=∞) | 0 (Z0=∞) |

---

## 11. Impedance Element

Všeobecný impedančný prvok.

| Pole | Typ | Povinné | Default | Validácia | Popis |
|------|-----|---------|---------|-----------|-------|
| id | string | áno | - | unique | Unikátny identifikátor |
| type | const | áno | "impedance" | - | Typ prvku |
| name | string | nie | null | - | Popisný názov |
| bus_from | ref | áno | - | exists | Počiatočný uzol |
| bus_to | ref | áno | - | exists | Koncový uzol |
| R | float [Ω] | áno | - | ≥ 0 | Činný odpor |
| X | float [Ω] | áno | - | - | Reaktancia |
| R0 | float [Ω] | nie | R | ≥ 0 | R nulovej zložky |
| X0 | float [Ω] | nie | X | - | X nulovej zložky |
| in_service | boolean | nie | true | - | V prevádzke |

---

## 12. Grounding Impedance

Zemniaca impedancia neutrálneho bodu.

| Pole | Typ | Povinné | Default | Validácia | Popis |
|------|-----|---------|---------|-----------|-------|
| id | string | áno | - | unique | Unikátny identifikátor |
| type | const | áno | "grounding_impedance" | - | Typ prvku |
| name | string | nie | null | - | Popisný názov |
| R | float [Ω] | áno | - | ≥ 0 | Činný odpor |
| X | float [Ω] | áno | - | ≥ 0 | Reaktancia |

---

## 13. Project

Projektová entita.

| Pole | Typ | Povinné | Default | Validácia | Popis |
|------|-----|---------|---------|-----------|-------|
| id | string | áno | - | unique | Unikátny identifikátor |
| name | string | áno | - | - | Názov projektu |
| description | string | nie | null | - | Popis |
| created_at | datetime | áno | now() | - | Čas vytvorenia |
| updated_at | datetime | áno | now() | - | Čas poslednej úpravy |
| created_by | ref | áno | - | exists | Autor |

---

## 14. Network Version

Verzia siete v rámci projektu.

| Pole | Typ | Povinné | Default | Validácia | Popis |
|------|-----|---------|---------|-----------|-------|
| id | string | áno | - | unique | Unikátny identifikátor |
| project_id | ref | áno | - | exists | Referencia na projekt |
| version_number | int | áno | - | > 0 | Číslo verzie |
| elements | array | áno | [] | - | Pole prvkov siete |
| created_at | datetime | áno | now() | - | Čas vytvorenia |
| created_by | ref | áno | - | exists | Autor |
| comment | string | nie | null | - | Komentár k verzii |

---

## 15. Calculation Run

Výpočtový beh.

| Pole | Typ | Povinné | Default | Validácia | Popis |
|------|-----|---------|---------|-----------|-------|
| id | string | áno | - | unique | Unikátny identifikátor |
| project_id | ref | áno | - | exists | Referencia na projekt |
| network_version_id | ref | áno | - | exists | Referencia na verziu siete |
| calculation_mode | enum | áno | - | max/min | Max/min skratový stav |
| fault_types | array[enum] | áno | - | Ik3/Ik2/Ik1 | Typy porúch na výpočet |
| fault_buses | array[ref] | áno | - | exists | Uzly pre výpočet skratu |
| engine_version | string | áno | - | - | Verzia výpočtového enginu |
| input_hash | string | áno | - | - | Hash vstupných dát |
| started_at | datetime | áno | now() | - | Čas spustenia |
| completed_at | datetime | nie | null | - | Čas dokončenia |
| status | enum | áno | "running" | running/completed/failed | Stav výpočtu |
| user_id | ref | áno | - | exists | Používateľ |

---

## 16. Run Result

Výsledky výpočtu pre jeden uzol a typ poruchy.

| Pole | Typ | Povinné | Default | Validácia | Popis |
|------|-----|---------|---------|-----------|-------|
| id | string | áno | - | unique | Unikátny identifikátor |
| run_id | ref | áno | - | exists | Referencia na run |
| bus_id | ref | áno | - | exists | Uzol poruchy |
| fault_type | enum | áno | - | Ik3/Ik2/Ik1 | Typ poruchy |
| Ik | float [kA] | áno | - | - | Počiatočný skratový prúd |
| ip | float [kA] | áno | - | - | Nárazový prúd |
| Zk | complex [Ω] | áno | - | - | Ekvivalentná impedancia |
| Z1 | complex [Ω] | áno | - | - | Súsledná impedancia |
| Z2 | complex [Ω] | áno | - | - | Spätná impedancia |
| Z0 | complex [Ω] | nie | null | - | Nulová impedancia (ak relevantné) |
| R_X_ratio | float | áno | - | - | Pomer R/X |
| c_factor | float | áno | - | - | Použitý napäťový faktor c |
| correction_factors | object | nie | {} | - | Použité korekčné faktory |
| warnings | array[string] | nie | [] | - | Varovné hlásenia |
| assumptions | array[string] | nie | [] | - | Predpoklady výpočtu |

---

## 17. Korekčné faktory - prehľad

| Symbol | Názov | Typ prvku | Referencia IEC |
|--------|-------|-----------|----------------|
| c | Napäťový faktor | Globálny | Tab. 1 |
| KG | Korekčný faktor generátora | Synchrónny generátor | §3.6.1, eq. 17-18 |
| KT | Korekčný faktor transformátora | Sieťový transformátor | §3.3.3, eq. 12a |
| KS | Korekčný faktor PSU s OLTC | PowerStationUnit | §3.7.1, eq. 21-22 |
| KSO | Korekčný faktor PSU bez OLTC | PowerStationUnit | §3.7.2, eq. 23-24 |

---

## 18. Validačné stavy

| Stav | Popis | Povolené operácie |
|------|-------|-------------------|
| pending | Prvok čaká na validáciu | Úprava, import |
| valid | Prvok je validný | Výpočet, export |
| error | Validácia zlyhala | Úprava, zobrazenie chýb |

---

## 19. Chybové kódy

| Kód | Popis |
|-----|-------|
| E001 | Chýbajúce povinné pole |
| E002 | Neplatná hodnota |
| E003 | Referencia na neexistujúci prvok |
| E004 | Nepodporovaná konfigurácia |
| E005 | Topologická chyba |
| E006 | Konzistentnostná chyba (napr. uk% pre 3W Tr) |
| E007 | PSU validačná chyba |
| W001 | OLTC ignorovaný v Z0 modeli |
| W002 | Motor ignorovaný pri min variante |
