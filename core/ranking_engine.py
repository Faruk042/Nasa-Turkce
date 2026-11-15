# -*- coding: utf-8 -*-
"""
ALTAR-NASA v6.3 Deney Sıralama (Ranking), Çapraz Dilli Semantik Vektör Arama (RAG),
Donanım Raf Filtresi (CIR/MDCA • MSG/SPICE • Cygnus • Kabin/DAFT) ve Karşılaştırma Motoru.
Gerçek TF-IDF + Karakter Dörtlüsü (4-gram) + TR<->EN Bilimsel Eş Anlamlı Genişletmeli
Kosinüs Benzerliği (NumPy) ve Fiziksel Parametre Yakınlık Puanlaması kullanır.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any, Dict, List, Optional

import numpy as np

from core.nasa_datasets import NASA_EXPERIMENTS_CATALOG
from core.physics_engine import simulate_combustion_state

# Türkçe <-> İngilizce Bilimsel Terim Köprüsü (Çapraz Dilli Semantik Eşleşme İçin)
BILINGUAL_SCIENTIFIC_SYNONYMS: Dict[str, str] = {
    "soğuk alev": "cool flame ntc low temperature radiative extinction heptane flex cfi cfi-g",
    "soguk alev": "cool flame ntc low temperature radiative extinction heptane flex cfi cfi-g",
    "serin alev": "cool flame cfi cfi-g ntc spherical burner propane heptane",
    "damlacık": "droplet spherical liquid heptane methanol decane flex cfi mdca",
    "damlacik": "droplet spherical liquid heptane methanol decane flex cfi mdca",
    "havalandırma": "ventilation airflow forced flow fan bass spice slice moc",
    "havalandirma": "ventilation airflow forced flow fan bass spice slice moc",
    "fan": "ventilation airflow low velocity opposed flow msg spice duct",
    "oksijen": "oxygen o2 moc concentration exploration atmosphere cfi-g",
    "uzay giysisi": "spacesuit eva 4.3 psia 100% o2 pure oxygen nomex pre-breathe",
    "gezgin": "pressurized rover lunar base 10.2 psia 30% o2 sofie saffire-v",
    "rover": "pressurized rover lunar base 10.2 psia 30% o2 sofie",
    "artemis": "exploration atmosphere 34% o2 8.2 psia 10.2 psia lunar habitat saffire-v sofie",
    "ay": "lunar exploration atmosphere 8.2 psia 10.2 psia 34% o2 luci fm2 daft",
    "mars": "martian exploration habitat low pressure partial gravity",
    "kısmi yerçekimi": "partial gravity lunar-g luci fm2 acme e-field ionic wind",
    "kismi yercekimi": "partial gravity lunar-g luci fm2 acme e-field ionic wind",
    "kumaş": "fabric textile sibal cotton fiberglass nomex bass-ii saffire",
    "kumas": "fabric textile sibal cotton fiberglass nomex bass-ii saffire",
    "akrilik": "pmma polymer solid acrylic bass sofie saffire-iv",
    "polimer": "pmma polymer solid fuel sofie bass bre",
    "su sisi": "water mist suppression pfe sofie-mist flex-2",
    "söndürme": "suppression extinguish quenching blowoff water mist",
    "sondurme": "suppression extinguish quenching blowoff water mist",
    "kurum": "soot radiation yellow shell acme spice smoke point",
    "duman noktası": "smoke point co-flow spice soot msg",
    "kalkış": "liftoff blowout triple flame slice msg",
    "elektrik": "electric field ionic wind e-field partial gravity acme",
    "büyük ölçek": "large scale cygnus spacecraft saffire",
    "duman": "smoke co carbon monoxide scrubber saffire-iv same daft",
    "toz": "dust aerosol measurement feasibility daft daft-2 same lunar dust smoke detector",
    "sensör": "sensor radiometer thermocouple optical uv laser co anomaly daft",
    "brülör": "burner porous spherical bre cfi-g acme spice",
}


def _expand_bilingual_text(text: str) -> str:
    lower = text.lower()
    extras: List[str] = []
    for tr_term, en_expansion in BILINGUAL_SCIENTIFIC_SYNONYMS.items():
        if tr_term in lower:
            extras.append(en_expansion)
    return f"{lower} {' '.join(extras)}"


def _tokenize_features(text: str) -> Counter:
    """Kelime ve 4-karakterli kök n-gram özniteliklerini çıkarır (hem TR eklerine hem EN terimlerine dayanıklıdır)."""
    expanded = _expand_bilingual_text(text)
    words = re.findall(r"[a-z0-9çğıöşü]{2,}", expanded)
    counts: Counter = Counter()
    for w in words:
        counts[f"w:{w}"] += 2.0
        if len(w) >= 4:
            for i in range(len(w) - 3):
                counts[f"g:{w[i:i+4]}"] += 0.5
    return counts


class SemanticKnowledgeIndex:
    """
    Hafif, hızlı ve %100 taşınabilir NumPy TF-IDF Kosinüs Benzerliği Vektör Hafızası.
    Hem yerleşik 15 NASA PSI deney kataloğunu hem de kullanıcının yüklediği PDF/NTRS belgelerini indeksler.
    """

    def __init__(self) -> None:
        self.documents: List[Dict[str, Any]] = []
        self.vocab: Dict[str, int] = {}
        self.idf: Optional[np.ndarray] = None
        self.matrix: Optional[np.ndarray] = None
        self._seed_catalog()

    def _seed_catalog(self) -> None:
        for exp in NASA_EXPERIMENTS_CATALOG:
            runs_txt = " ".join(
                f"{r.get('run_code', '')} {r.get('diff_tr', '')} {r.get('diff_en', '')} {r.get('result_tr', '')}"
                for r in exp.get("intra_runs", [])
            )
            combined = (
                f"{exp['exp_id']} {exp['program']} {exp.get('hardware_group', '')} {exp['facility']} "
                f"{exp['title']} {exp['title_tr']} {exp['material']} "
                f"{exp.get('sample_geometry_tr', '')} {exp.get('sample_geometry_en', '')} "
                f"{exp.get('sensors_tr', '')} {exp.get('sensors_en', '')} "
                f"{exp['key_finding_tr']} {exp['key_finding_en']} "
                f"{exp['safety_insight_tr']} {exp['safety_insight_en']} "
                f"{runs_txt} {' '.join(exp['tags'])}"
            )
            self.documents.append({
                "doc_id": exp["exp_id"],
                "doc_type": "nasa_experiment",
                "title": exp["title_tr"],
                "title_tr": exp["title_tr"],
                "title_en": exp["title"],
                "source": f"{exp['program']} • NTRS {exp['ntrs_id']}",
                "url": exp["ntrs_url"],
                "text": combined,
                "text_tr": f"{exp['key_finding_tr']} {exp['safety_insight_tr']}",
                "text_en": f"{exp['key_finding_en']} {exp['safety_insight_en']}",
                "metadata": exp,
            })
        self._rebuild_matrix()

    def add_custom_document(self, title: str, content: str, source: str = "User Upload", url: str = "") -> int:
        """Yeni bir PDF/Web/NTRS belgesini parçalara (chunk) ayırarak semantik vektör indeksine ekler."""
        clean = (content or "").strip()
        if not clean:
            return 0
        chunk_size = 1200
        overlap = 150
        chunks: List[str] = []
        idx = 0
        while idx < len(clean) and len(chunks) < 40:
            chunks.append(clean[idx:idx + chunk_size])
            idx += (chunk_size - overlap)

        base_num = len(self.documents)
        for i, ch in enumerate(chunks, 1):
            self.documents.append({
                "doc_id": f"DOC-{base_num + i}",
                "doc_type": "ingested_doc",
                "title": f"{title} (Part {i}/{len(chunks)})",
                "title_tr": f"{title} (Bölüm {i}/{len(chunks)})",
                "title_en": f"{title} (Part {i}/{len(chunks)})",
                "source": source,
                "url": url,
                "text": f"{title}\n{ch}",
                "text_tr": f"{title}\n{ch}",
                "text_en": f"{title}\n{ch}",
                "metadata": {"snippet": ch[:450]},
            })
        self._rebuild_matrix()
        return len(chunks)

    def _rebuild_matrix(self) -> None:
        if not self.documents:
            return
        tokenized_docs = [_tokenize_features(d["text"]) for d in self.documents]
        df: Counter = Counter()
        for tdoc in tokenized_docs:
            for feat in tdoc.keys():
                df[feat] += 1

        most_common = [feat for feat, _ in df.most_common(4096)]
        self.vocab = {feat: idx for idx, feat in enumerate(most_common)}
        n_docs = len(self.documents)
        n_vocab = len(self.vocab)

        idf_arr = np.zeros(n_vocab, dtype=np.float32)
        for feat, idx in self.vocab.items():
            idf_arr[idx] = math.log((1.0 + n_docs) / (1.0 + df[feat])) + 1.0
        self.idf = idf_arr

        mat = np.zeros((n_docs, n_vocab), dtype=np.float32)
        for d_idx, tdoc in enumerate(tokenized_docs):
            for feat, cnt in tdoc.items():
                v_idx = self.vocab.get(feat)
                if v_idx is not None:
                    mat[d_idx, v_idx] = (1.0 + math.log(cnt)) * idf_arr[v_idx]
            norm = np.linalg.norm(mat[d_idx])
            if norm > 1e-8:
                mat[d_idx] /= norm
        self.matrix = mat

    def search(self, query: str, top_k: int = 5, doc_type: Optional[str] = None) -> List[Dict[str, Any]]:
        if self.matrix is None or self.idf is None or not self.vocab:
            return []
        q_feats = _tokenize_features(query or "microgravity combustion")
        q_vec = np.zeros(len(self.vocab), dtype=np.float32)
        for feat, cnt in q_feats.items():
            v_idx = self.vocab.get(feat)
            if v_idx is not None:
                q_vec[v_idx] = (1.0 + math.log(cnt)) * self.idf[v_idx]
        q_norm = np.linalg.norm(q_vec)
        if q_norm > 1e-8:
            q_vec /= q_norm

        scores = self.matrix @ q_vec
        ranked_indices = np.argsort(-scores)

        results: List[Dict[str, Any]] = []
        for idx in ranked_indices:
            doc = self.documents[int(idx)]
            if doc_type and doc["doc_type"] != doc_type:
                continue
            sim = float(scores[int(idx)])
            results.append({
                "doc_id": doc["doc_id"],
                "doc_type": doc["doc_type"],
                "title": doc["title"],
                "title_tr": doc.get("title_tr", doc["title"]),
                "title_en": doc.get("title_en", doc["title"]),
                "source": doc["source"],
                "url": doc["url"],
                "similarity": round(max(0.0, sim), 4),
                "text": doc["text"][:800],
                "text_tr": (doc.get("text_tr") or doc["text"])[:800],
                "text_en": (doc.get("text_en") or doc["text"])[:800],
                "metadata": doc["metadata"],
            })
            if len(results) >= top_k:
                break
        return results


class ExperimentRankingEngine:
    """
    Yarışmanın ana hedefi olan 'Summarize, Rank, Compare & Interpret' işlevini yürütür.
    Kullanıcının görev atmosferi, donanım raf filtresi (CIR / MSG / CYGNUS / CABIN) ve sorgusuna göre NASA deneylerini:
    1) Fiziksel Parametre Uyumu (O2 %, Basınç psia, Akış hızı cm/s, Yakıt sınıfı)
    2) Semantik Sorgu Benzerliği
    3) Yangın Güvenliği Kritiklik / Risk Skoru
    kriterleriyle puanlayıp sıralar.
    """

    def __init__(self, knowledge_index: SemanticKnowledgeIndex) -> None:
        self.index = knowledge_index
        self.dynamic_experiments: List[Dict[str, Any]] = []

    def _all_experiments(self) -> List[Dict[str, Any]]:
        return list(self.dynamic_experiments) + list(NASA_EXPERIMENTS_CATALOG)

    def register_dynamic_experiment(
        self,
        filename: str,
        sim_params: Dict[str, Any],
        sim_state: Dict[str, Any],
        summary_tr: str = "",
        summary_en: str = "",
    ) -> Dict[str, Any]:
        """Kullanıcının yüklediği yeni NASA PSI / laboratuvar veri setini dinamik olarak sıralama kataloğuna kaydeder."""
        inp = sim_state.get("inputs", {})
        tel = sim_state.get("telemetry", {})
        clean_name = re.sub(r"\.[a-zA-Z0-9]{1,5}$", "", filename or "Yeni_Deney").strip() or "Yeni_Deney"
        existing = next((x for x in self.dynamic_experiments if x.get("source_filename") == filename), None)
        exp_id = existing["exp_id"] if existing else f"PSI-USR-{len(self.dynamic_experiments) + 1:02d}"

        flow_val = float(inp.get("airflow_cms", 0.0))
        flow_dir = str(inp.get("flow_direction", "opposed"))
        flow_regime = "quiescent" if flow_val < 1.0 else flow_dir
        spread_val = float(tel.get("flame_spread_mm_s", 0.0))
        k_val = float(tel.get("burning_rate_k_mm2_s", 0.0))
        rate_str = (
            f"Spread = {spread_val:.2f} mm/s"
            if spread_val > 0.05
            else f"K = {k_val:.3f} mm²/s"
        )
        short_sum_tr = (summary_tr or "").splitlines()[0][:200] if summary_tr else f"Yüklenen veri dosyasından ({filename}) çıkarılan deney kaydı."
        short_sum_en = (summary_en or "").splitlines()[0][:200] if summary_en else f"Experiment record extracted from uploaded dataset ({filename})."

        record: Dict[str, Any] = {
            "exp_id": exp_id,
            "source_filename": filename,
            "is_dynamic_upload": True,
            "program": f"Yeni Veri ({clean_name[:18]})",
            "program_tr": f"Yeni Veri ({clean_name[:18]})",
            "program_en": f"Uploaded ({clean_name[:18]})",
            "hardware_group": "CIR" if inp.get("fuel_phase") != "solid" else "MSG",
            "title": f"Uploaded Dataset — {clean_name}",
            "title_tr": f"Yüklenen Deney Verisi — {clean_name}",
            "title_en": f"Uploaded Dataset — {clean_name}",
            "facility": "Kullanıcı Veri Yüklemesi / PSI Tablosu",
            "facility_tr": "Kullanıcı Veri Yüklemesi / PSI Tablosu",
            "facility_en": "User Dataset Upload / PSI Table",
            "year": 2026,
            "fuel_id": str(inp.get("fuel_id", "n_heptane")),
            "custom_material_name": str(inp.get("custom_material_name", "")),
            "material": str(inp.get("fuel_name_en", inp.get("fuel_id", "Sample"))),
            "sample_geometry_tr": f"Yüklenen veri kaydı (D₀ = {inp.get('droplet_d0_mm', 3.2)} mm)",
            "sample_geometry_en": f"Uploaded dataset geometry (D₀ = {inp.get('droplet_d0_mm', 3.2)} mm)",
            "sensors_tr": "Yüklenen dosya telemetrisi (Sıcaklık, O₂, Basınç, Radyometre / CO)",
            "sensors_en": "Uploaded file telemetry (Temperature, O₂, Pressure, Radiometer / CO)",
            "gravity_g": float(inp.get("gravity_g", 0.0)),
            "oxygen_pct": float(inp.get("oxygen_pct", 21.0)),
            "pressure_psia": float(inp.get("pressure_psia", 14.7)),
            "airflow_cms": flow_val,
            "moc_measured_pct": float(tel.get("moc_pct", 15.0)),
            "scale_class_tr": "Yeni Yüklenen Veri",
            "scale_class_en": "Uploaded Dataset",
            "hrrpua_kw_m2": float(tel.get("hrrpua_kw_m2", 120.0)),
            "flow_regime": flow_regime,
            "burning_rate_or_spread": rate_str,
            "cool_flame_observed": bool(tel.get("cool_flame_active", False)),
            "ntrs_id": "USER-DATA",
            "ntrs_url": "https://psi.nasa.gov/",
            "psi_id": exp_id,
            "psi_url": "https://psi.nasa.gov/",
            "key_finding_tr": short_sum_tr.replace("**", ""),
            "key_finding_en": short_sum_en.replace("**", ""),
            "safety_insight_tr": "Yüklenen deney parametreleri mevcut kabin atmosferiyle otomatik karşılaştırıldı.",
            "safety_insight_en": "Uploaded test parameters were automatically benchmarked against target cabin conditions.",
            "intra_runs": [
                {
                    "run_code": f"{exp_id}-R1",
                    "same_tr": f"Dosya: {filename}, Basınç: {inp.get('pressure_psia', 14.7)} psia",
                    "same_en": f"File: {filename}, Pressure: {inp.get('pressure_psia', 14.7)} psia",
                    "diff_tr": f"O₂: %{inp.get('oxygen_pct', 21.0)}, Akış: {flow_val} cm/s ({flow_dir})",
                    "diff_en": f"O₂: {inp.get('oxygen_pct', 21.0)}%, Flow: {flow_val} cm/s ({flow_dir})",
                    "result_tr": f"Hesaplanan T_f = {tel.get('flame_temp_k', 0)} K, MOC = %{tel.get('moc_pct', 0)}, {rate_str}.",
                    "result_en": f"Evaluated T_f = {tel.get('flame_temp_k', 0)} K, MOC = {tel.get('moc_pct', 0)}%, {rate_str}.",
                }
            ],
            "tags": ["user upload", "dynamic", clean_name.lower(), str(inp.get("fuel_id", ""))],
        }
        if existing:
            idx = self.dynamic_experiments.index(existing)
            self.dynamic_experiments[idx] = record
        else:
            self.dynamic_experiments.insert(0, record)
            self.index.documents.append({
                "doc_id": exp_id,
                "doc_type": "nasa_experiment",
                "title": record["title_tr"],
                "title_tr": record["title_tr"],
                "title_en": record["title_en"],
                "source": f"{record['program']} • {filename}",
                "url": record["ntrs_url"],
                "text": f"{exp_id} {clean_name} {record['material']} {record['key_finding_tr']} {record['key_finding_en']}",
                "text_tr": f"{record['key_finding_tr']} {record['safety_insight_tr']}",
                "text_en": f"{record['key_finding_en']} {record['safety_insight_en']}",
                "metadata": record,
            })
            self.index._rebuild_matrix()
        return record

    def rank_experiments(
        self,
        mission_params: Dict[str, Any],
        query: str = "",
        hardware_filter: str = "ALL",
    ) -> Dict[str, Any]:
        if not isinstance(mission_params, dict):
            mission_params = {}

        def _rfloat(val: Any, default: float, lo: float, hi: float) -> float:
            if val is None or isinstance(val, bool):
                return default
            try:
                fv = float(val)
            except (TypeError, ValueError):
                return default
            if not math.isfinite(fv):
                return default
            return max(lo, min(hi, fv))

        target_o2 = _rfloat(mission_params.get("oxygen_pct"), 21.0, 5.0, 100.0)
        target_p = _rfloat(mission_params.get("pressure_psia"), 14.7, 2.0, 30.0)
        target_flow = _rfloat(mission_params.get("airflow_cms"), 3.5, 0.0, 100.0)
        target_flow_dir = "concurrent" if str(mission_params.get("flow_direction", "opposed")).lower() == "concurrent" else "opposed"
        target_fuel = str(mission_params.get("fuel_id", "n_heptane"))
        if target_fuel == "custom_material":
            from core.physics_engine import resolve_analog_material
            target_fuel = resolve_analog_material(mission_params)["base_fuel_id"]
        target_g = _rfloat(mission_params.get("gravity_g"), 0.0, 0.0, 2.0)
        hw_norm = (hardware_filter or "ALL").strip().upper()

        all_exps = self._all_experiments()
        sem_map: Dict[str, float] = {}
        if query and query.strip():
            sem_hits = self.index.search(query.strip(), top_k=len(all_exps), doc_type="nasa_experiment")
            for h in sem_hits:
                sem_map[h["doc_id"]] = h["similarity"]

        ranked: List[Dict[str, Any]] = []
        for exp in all_exps:
            if hw_norm not in ("", "ALL") and exp.get("hardware_group", "").upper() != hw_norm:
                continue

            # 1) Atmosfer, Akış Yönü ve Ölçek Yakınlık Skoru (0 - 100)
            o2_diff = abs(target_o2 - float(exp["oxygen_pct"]))
            p_diff = abs(target_p - float(exp["pressure_psia"]))
            flow_diff = abs(target_flow - float(exp["airflow_cms"]))
            exp_fuel = exp["fuel_id"]
            fuel_bonus = 22.0 if exp_fuel == target_fuel else 0.0
            partial_g_bonus = 14.0 if (0.04 <= target_g <= 0.85 and exp["exp_id"] in ("PSI-ACME-09", "PSI-SOFIE-08", "PSI-SAFFIRE5-07", "PSI-DAFT-15")) else 0.0

            exp_freg = str(exp.get("flow_regime", "opposed")).lower()
            if target_flow < 1.0 and exp_freg == "quiescent":
                flow_dir_bonus = 8.0
            elif target_flow >= 1.0 and (exp_freg == target_flow_dir or exp_freg == "both"):
                flow_dir_bonus = 7.5
            else:
                flow_dir_bonus = 0.0
            dyn_bonus = 10.0 if exp.get("is_dynamic_upload") else 0.0

            param_affinity = max(
                10.0,
                100.0 - (min(42.0, o2_diff * 1.6) + p_diff * 2.6 + flow_diff * 1.3) + fuel_bonus + partial_g_bonus + flow_dir_bonus + dyn_bonus,
            )
            param_affinity = min(100.0, param_affinity)

            # 2) Bu deneydeki malzemenin hedef görev atmosferindeki gerçek fiziksel riski
            sim_eval = simulate_combustion_state({
                "fuel_id": exp["fuel_id"],
                "custom_material_name": exp.get("custom_material_name", ""),
                "gravity_g": target_g,
                "oxygen_pct": target_o2,
                "pressure_psia": target_p,
                "airflow_cms": target_flow,
                "flow_direction": target_flow_dir,
                "droplet_d0_mm": 3.5,
                "diluent": mission_params.get("diluent", "N2"),
            })
            hazard_score = float(sim_eval["telemetry"]["risk_score"])

            # 3) Semantik alaka
            sem_score = sem_map.get(exp["exp_id"], 0.0) * 100.0

            if query and query.strip():
                composite = 0.44 * sem_score + 0.32 * param_affinity + 0.24 * hazard_score
            else:
                composite = 0.56 * param_affinity + 0.44 * hazard_score

            ranked.append({
                **exp,
                "priority_score": round(min(99.9, composite), 1),
                "param_affinity": round(param_affinity, 1),
                "mission_hazard_score": int(hazard_score),
                "predicted_regime_in_mission": sim_eval["telemetry"]["regime"],
                "predicted_moc_in_mission": sim_eval["telemetry"]["moc_pct"],
                "predicted_hrrpua_kw_m2": sim_eval["telemetry"].get("hrrpua_kw_m2", exp.get("hrrpua_kw_m2", 120.0)),
            })

        ranked.sort(key=lambda x: x["priority_score"], reverse=True)
        for rank_no, item in enumerate(ranked, 1):
            item["rank"] = rank_no

        return {
            "count": len(ranked),
            "hardware_filter": hw_norm,
            "mission_evaluated": {
                "oxygen_pct": target_o2,
                "pressure_psia": target_p,
                "airflow_cms": target_flow,
                "flow_direction": target_flow_dir,
                "gravity_g": target_g,
                "fuel_id": target_fuel,
            },
            "ranked_experiments": ranked,
        }

    def compare_experiments(self, exp_ids: List[str], mission_params: Dict[str, Any]) -> Dict[str, Any]:
        """Seçilen 2 ila 4 NASA deneyini donanım, ölçek (HRRPUA), sensör, MOC ve çelişkili test sınırları (Worst-Case Bounding) açısından karşılaştırır."""
        all_exps = self._all_experiments()
        selected = [e for e in all_exps if e["exp_id"] in exp_ids]
        if len(selected) < 2:
            selected = all_exps[:3]

        lowest_moc_exp = min(selected, key=lambda x: x["moc_measured_pct"])
        highest_moc_exp = max(selected, key=lambda x: x["moc_measured_pct"])
        highest_o2_exp = max(selected, key=lambda x: x["oxygen_pct"])
        max_hrrpua_exp = max(selected, key=lambda x: float(x.get("hrrpua_kw_m2", 0.0)))
        cool_flame_exps = [x["program"] for x in selected if x["cool_flame_observed"]]
        facilities = sorted(list({x.get("hardware_group", "CIR") for x in selected}))
        scales_tr = sorted(list({str(x.get("scale_class_tr", "Orta Ölçek")).split("(")[0].strip() for x in selected}))
        scales_en = sorted(list({str(x.get("scale_class_en", "Medium Scale")).split("(")[0].strip() for x in selected}))

        # Veri Tutarsızlığı ve İhtiyatlı Üst Sınır (Worst-Case Bounding — Jüri Soru 8)
        conflict_reasons_tr: List[str] = []
        conflict_reasons_en: List[str] = []
        sel_ids = {x["exp_id"] for x in selected}
        moc_span = round(float(highest_moc_exp["moc_measured_pct"]) - float(lowest_moc_exp["moc_measured_pct"]), 2)

        if "PSI-BASS-03" in sel_ids or "PSI-BASS2-04" in sel_ids:
            conflict_reasons_tr.append("durgun 0G testlerinde sönümlenen katı numunelerin düşük hızlı fan akışında (3–8 cm/s) kararlı yanması")
            conflict_reasons_en.append("samples self-extinguishing in quiescent 0G yet burning steadily under gentle 3–8 cm/s ventilation")
        if "PSI-SAFFIRE4-06" in sel_ids or "PSI-SAFFIRE1-05" in sel_ids:
            conflict_reasons_tr.append("kalın/düz numune sönümlenirken ince veya oluklu (ribbed) geometrinin +%45 hızlı yayılması")
            conflict_reasons_en.append("thick/flat slabs quenching while thin or ribbed geometries accelerate flame spread by +45%")
        if len(scales_tr) >= 2:
            conflict_reasons_tr.append(f"farklı deney ölçekleri ({' vs. '.join(scales_tr)}) arasında kabin sınır ve ısı kaybı farkı")
            conflict_reasons_en.append(f"scale divergence across facilities ({' vs. '.join(scales_en)})")
        if moc_span >= 2.2:
            conflict_reasons_tr.append(f"test kayıtları arasında %{moc_span:.1f} O₂ genişliğinde MOC eşik farkı")
            conflict_reasons_en.append(f"a {moc_span:.1f}% O₂ spread in measured MOC thresholds")

        has_conflict = len(conflict_reasons_tr) > 0
        worst_moc = float(lowest_moc_exp["moc_measured_pct"])
        worst_hrrpua = float(max_hrrpua_exp.get("hrrpua_kw_m2", 180.0))
        conflict_warning_tr = (
            f"Veri Tutarsızlığı ve İhtiyatlı Sınır (Worst-Case Bounding): Seçili deneylerde {'; '.join(conflict_reasons_tr)} saptandı. "
            f"Mürettebat güvenliği için ortalama almak yerine en ihtiyatlı sınır uygulanır: Kritik MOC Tavanı = %{worst_moc:.1f} O₂ ({lowest_moc_exp['program']}) "
            f"ve Tepe Birim Isı Gücü (HRRPUA) = {worst_hrrpua:.0f} kW/m² ({max_hrrpua_exp['program']})."
            if has_conflict else ""
        )
        conflict_warning_en = (
            f"Data Discrepancy & Worst-Case Bounding: Detected {'; '.join(conflict_reasons_en)}. "
            f"Instead of averaging conflicting outcomes, conservative safety bounding enforces MOC Ceiling = {worst_moc:.1f}% O₂ ({lowest_moc_exp['program']}) "
            f"and Peak HRRPUA = {worst_hrrpua:.0f} kW/m² ({max_hrrpua_exp['program']})."
            if has_conflict else ""
        )

        hw_note_tr = (
            f"Donanım mimarisi olarak tümü aynı **{facilities[0]}** platformunu paylaşmaktadır. "
            if len(facilities) == 1
            else f"Farklı uzay donanım mimarilerini (**{' vs. '.join(facilities)}**) kapsayarak ölçek-bağımsız birim alan ısı gücü (`HRRPUA`) üzerinden normalize edilmiştir. "
        )
        hw_note_en = (
            f"All selected investigations share the **{facilities[0]}** orbital hardware facility. "
            if len(facilities) == 1
            else f"Spans distinct orbital facilities (**{' vs. '.join(facilities)}**), normalized via scale-independent Heat Release Rate Per Unit Area (`HRRPUA`). "
        )

        synthesis_tr = (
            f"**Deneyler Arası Karşılaştırma Özeti ({len(selected)} NASA PSI Kaydı):** {hw_note_tr}"
            f"En düşük oksijen sınırına sahip (en kolay tutuşan) deney **%{lowest_moc_exp['moc_measured_pct']} MOC** ile "
            f"**{lowest_moc_exp['program']}** ({lowest_moc_exp['material']}); en yüksek birim ısı gücüne ulaşan ise "
            f"**{worst_hrrpua:.0f} kW/m² HRRPUA** ile **{max_hrrpua_exp['program']}** (Test O₂: `%{highest_o2_exp['oxygen_pct']}`) kaydıdır. "
        )
        if cool_flame_exps:
            synthesis_tr += (
                f"Ayrıca **{', '.join(cool_flame_exps)}** soruşturmalarında 550–750 K görünmez Soğuk Alev gözlemlendiğinden "
                f"yalnızca optik kamera yerine CIR UV/IR radyometre, CSA-CP / ANITA-2 (CO/CH₂O) gaz analizi ve DAFT/SAME toz-ayrımlı lazer duman algılama zorunludur."
            )
        else:
            synthesis_tr += "Havalandırma fanlarının (HVAC) anında kapatılması ve ince su sisi (SoFIE-MIST) tüm seçili rejimlerde ortak birincil bastırma adımıdır."

        synthesis_en = (
            f"**Cross-Experiment Comparison Summary ({len(selected)} NASA PSI Records):** {hw_note_en}"
            f"**{lowest_moc_exp['program']}** ({lowest_moc_exp['material']}) exhibits the lowest Minimum Oxygen Concentration "
            f"(**{lowest_moc_exp['moc_measured_pct']}% O₂**), while **{max_hrrpua_exp['program']}** reaches **{worst_hrrpua:.0f} kW/m² HRRPUA** (Max O₂: **{highest_o2_exp['oxygen_pct']}%**). "
        )
        if cool_flame_exps:
            synthesis_en += (
                f"Invisible NTC Cool Flame persistence in **{', '.join(cool_flame_exps)}** mandates CIR UV/IR radiometry and CSA-CP/ANITA-2 CO/CH₂O gas monitoring alongside DAFT/SAME dust-immune smoke detection."
            )
        else:
            synthesis_en += "Immediate cabin HVAC shutoff and fine water mist (SoFIE-MIST) remain the universal non-Halon countermeasures."

        return {
            "compared_count": len(selected),
            "experiments": selected,
            "lowest_moc_program": lowest_moc_exp["program"],
            "synthesis_tr": synthesis_tr,
            "synthesis_en": synthesis_en,
            "conflict_bounding": {
                "has_conflict": has_conflict,
                "worst_case_moc_pct": worst_moc,
                "worst_case_hrrpua_kw_m2": worst_hrrpua,
                "warning_tr": conflict_warning_tr,
                "warning_en": conflict_warning_en,
            },
        }
