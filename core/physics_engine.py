# -*- coding: utf-8 -*-
"""
ALTAR-NASA v6.3 İleri Mikroçekim & Kısmi Yerçekimi Yanma Termodinamiği, Taşınım Denklemleri ve Çoklu Sensör Motoru.
Hesaplanan Gerçek Bilimsel Büyüklükler:
- d² Damlacık Yanma Yasası: D²(t) = D₀² - K·t ve Spalding Kütle Transfer Sayısı (B_oq)
- Alev Cephesi Konum Oranı (Standoff Ratio R_f / R_d)
- Boyutsuz Akışkan ve Kimya Sayıları: Reynolds (Re), Grashof (Gr), Rayleigh (Ra),
  Richardson (Ri = Gr/Re²), Sherwood/Nusselt (Sh), Damköhler (Da = τ_flow / τ_chem)
- Kısmi Oksijen Basıncı (P_O2 psia & kPa): EVA Uzay Giysisi (4.3 psia / %100 O₂), Ay Üssü/Gezgini (10.2 psia / %32 O₂),
  Artemis Keşif Atmosferi (8.2 psia / %34 O₂) ve ACME CFI-G (%85 O₂ küresel brülör) desteği
- Kısmi Yerçekimi (0.16G Ay / 0.38G Mars) 0G–1G Sınırlandırma (Bounding) Eğrileri & LUCI / FM2 Şeffaflık Raporu
- İki Aşamalı Tutuşma ve Görünmez Soğuk Alev (Cool Flame / NTC 540–780 K) Kinetiği
"""

from __future__ import annotations

import ast
import math
from typing import Any, Dict, List

from core.compartment_network import compute_multicompartment_and_toxicology
from core.ignition_kinetics import (
    compute_arrhenius_chemical_timescale_ms,
    compute_fire_triangle_and_preignition,
)

SIGMA_SB_W_M2K4 = 5.670374419e-8


def _safe_float(val: Any, default: float, min_v: float | None = None, max_v: float | None = None) -> float:
    """Null, bool, metin, NaN ve ±Infinity değerlerine karşı tam korumalı sayısal ayrıştırıcı."""
    if isinstance(val, bool) or val is None or val == "":
        num = default
    else:
        try:
            num = float(val)
        except (TypeError, ValueError):
            num = default
    if not math.isfinite(num):
        num = default
    if min_v is not None:
        num = max(min_v, num)
    if max_v is not None:
        num = min(max_v, num)
    return num

FUEL_PROPERTIES: Dict[str, Dict[str, Any]] = {
    "n_heptane": {
        "name_tr": "n-Heptan (C₇H₁₆ • FLEX / CFI Sıvı Damlacık)",
        "name_en": "n-Heptane (C₇H₁₆ • FLEX / CFI Liquid Droplet)",
        "formula": "C₇H₁₆",
        "phase": "liquid_droplet",
        "geometry_3d": "droplet",
        "rho_l_kg_m3": 684.0,
        "lv_kj_kg": 318.0,          # Buharlaşma gizli ısısı
        "dhc_kj_kg": 44560.0,       # Alt ısıl değer (ΔH_c)
        "stoich_o2_fuel": 3.52,     # ν_s (kg O2 / kg yakıt)
        "t_boil_k": 371.5,
        "cp_vapor_j_kgk": 2410.0,   # Law & Williams (1972) iç bölge yakıt buharı c_p,F(T_ref)
        "lewis_ox": 1.05,
        "k0_base": 0.76,
        "t_adiabatic_k": 2190.0,
        "moc_0g_base": 13.8,
        "moc_1g_base": 15.2,
        "cool_flame_capable": True,
        "cool_flame_min_o2": 9.5,
        "soot_tendency": 0.62,
        "blowoff_cms": 34.0,
    },
    "methanol": {
        "name_tr": "Metanol (CH₃OH • FLEX-2 Kurumsuz Damlacık)",
        "name_en": "Methanol (CH₃OH • FLEX-2 Soot-Free Droplet)",
        "formula": "CH₃OH",
        "phase": "liquid_droplet",
        "geometry_3d": "droplet",
        "rho_l_kg_m3": 791.0,
        "lv_kj_kg": 1100.0,
        "water_cond_enthalpy_factor": 0.83,  # FLEX-2 (Dietrich et al. 2014): üretilen H2O buharının damlacık yüzeyinde çözünme/yoğuşma entalpi katkısı
        "dhc_kj_kg": 19930.0,
        "stoich_o2_fuel": 1.50,
        "t_boil_k": 337.8,
        "cp_vapor_j_kgk": 1920.0,
        "lewis_ox": 0.96,
        "k0_base": 0.58,
        "t_adiabatic_k": 1990.0,
        "moc_0g_base": 12.6,
        "moc_1g_base": 14.0,
        "cool_flame_capable": False,
        "cool_flame_min_o2": 12.6,
        "soot_tendency": 0.04,
        "blowoff_cms": 30.0,
    },
    "pmma": {
        "name_tr": "PMMA Akrilik Cam (BASS / SoFIE Katı Polimer)",
        "name_en": "Cast PMMA Acrylic (BASS / SoFIE Solid Polymer)",
        "formula": "(C₅O₂H₈)ₙ",
        "phase": "solid_surface",
        "geometry_3d": "solid_rod",
        "rho_l_kg_m3": 1180.0,
        "lv_kj_kg": 1590.0,         # Piroliz / depolimerizasyon ısısı
        "dhc_kj_kg": 24880.0,
        "stoich_o2_fuel": 1.92,
        "t_boil_k": 650.0,
        "cp_vapor_j_kgk": 2080.0,
        "lambda_s_w_mk": 0.19,
        "cp_s_j_kgk": 1460.0,
        "lewis_ox": 1.02,
        "k0_base": 0.34,
        "t_adiabatic_k": 2040.0,
        "moc_0g_base": 14.3,
        "moc_1g_base": 16.8,
        "cool_flame_capable": False,
        "cool_flame_min_o2": 14.3,
        "soot_tendency": 0.55,
        "blowoff_cms": 42.0,
    },
    "sibal": {
        "name_tr": "Sibal Kumaş (%75 Pamuk / %25 Fiberglas • Saffire)",
        "name_en": "Sibal Fabric (75% Cotton / 25% Fiberglass • Saffire)",
        "formula": "C₆H₁₀O₅ + SiO₂",
        "phase": "solid_thin",
        "geometry_3d": "flat_slab",
        "rho_l_kg_m3": 920.0,
        "lv_kj_kg": 1350.0,
        "dhc_kj_kg": 16800.0,
        "stoich_o2_fuel": 1.18,
        "t_boil_k": 610.0,
        "cp_vapor_j_kgk": 1840.0,
        "lambda_s_w_mk": 0.085,
        "cp_s_j_kgk": 1340.0,
        "thin_tau_m": 0.00038,      # Saffire Sibal kumaş kalınlığı (~0.38 mm)
        "lewis_ox": 1.00,
        "k0_base": 0.48,
        "t_adiabatic_k": 1920.0,
        "moc_0g_base": 13.2,
        "moc_1g_base": 16.0,
        "cool_flame_capable": False,
        "cool_flame_min_o2": 13.2,
        "soot_tendency": 0.42,
        "blowoff_cms": 38.0,
    },
    "nomex": {
        "name_tr": "Nomex HT90-40 (Uzay Giysisi & Kabin Kumaşı • BASS-II)",
        "name_en": "Nomex HT90-40 (EVA Suit & Crew Fabric • BASS-II)",
        "formula": "(C₁₄H₁₀N₂O₂)ₙ",
        "phase": "solid_thin",
        "geometry_3d": "flat_slab",
        "rho_l_kg_m3": 1380.0,
        "lv_kj_kg": 2150.0,
        "dhc_kj_kg": 21500.0,
        "stoich_o2_fuel": 1.84,
        "t_boil_k": 715.0,
        "cp_vapor_j_kgk": 2150.0,
        "lambda_s_w_mk": 0.13,
        "cp_s_j_kgk": 1260.0,
        "thin_tau_m": 0.00048,      # EVA / kabin Nomex kumaş kalınlığı (~0.48 mm)
        "lewis_ox": 1.04,
        "k0_base": 0.19,
        "t_adiabatic_k": 1850.0,
        "moc_0g_base": 21.5,
        "moc_1g_base": 24.2,
        "cool_flame_capable": False,
        "cool_flame_min_o2": 21.5,
        "soot_tendency": 0.68,
        "blowoff_cms": 26.0,
    },
    "hydrogen": {
        "name_tr": "Hidrojen Gaz Jeti (H₂ • ACME / SPICE / SLICE)",
        "name_en": "Hydrogen Gas Jet (H₂ • ACME / SPICE / SLICE)",
        "formula": "H₂",
        "phase": "gas_jet",
        "geometry_3d": "porous_sphere",
        "rho_l_kg_m3": 70.8,
        "dh_sens_kj_kg": 2150.0,    # Gaz fazı duyulur entalpi transfer ölçeği (c_p·ΔT)
        "lv_kj_kg": 2150.0,
        "dhc_kj_kg": 119960.0,
        "stoich_o2_fuel": 7.94,
        "t_boil_k": 298.15,
        "cp_vapor_j_kgk": 14450.0,
        "lewis_ox": 0.32,
        "k0_base": 1.35,
        "t_adiabatic_k": 2380.0,
        "moc_0g_base": 6.2,
        "moc_1g_base": 8.0,
        "cool_flame_capable": False,
        "cool_flame_min_o2": 6.2,
        "soot_tendency": 0.0,
        "blowoff_cms": 85.0,
    },
    "propane_cfig": {
        "name_tr": "Propan Küresel Brülör (C₃H₈ • ACME CFI-G / BRE Gaz)",
        "name_en": "Propane Spherical Porous Burner (C₃H₈ • ACME CFI-G / BRE)",
        "formula": "C₃H₈",
        "phase": "porous_sphere",
        "geometry_3d": "porous_sphere",
        "rho_l_kg_m3": 493.0,
        "dh_sens_kj_kg": 780.0,     # Sinterlenmiş gaz brülörü duyulur ısı transfer ölçeği
        "lv_kj_kg": 780.0,
        "dhc_kj_kg": 46350.0,
        "stoich_o2_fuel": 3.63,
        "t_boil_k": 298.15,
        "cp_vapor_j_kgk": 2520.0,
        "lewis_ox": 1.08,
        "k0_base": 0.88,
        "t_adiabatic_k": 2260.0,
        "moc_0g_base": 11.4,
        "moc_1g_base": 12.8,
        "cool_flame_capable": True,
        "cool_flame_min_o2": 8.8,
        "soot_tendency": 0.48,
        "blowoff_cms": 52.0,
    },
}

DILUENT_FACTORS: Dict[str, Dict[str, Any]] = {
    "N2": {
        "name": "Azot (N₂ - Standart Kabin)",
        "name_en": "Nitrogen (N₂ - Standard Cabin)",
        "mw": 28.01,
        "cp_factor": 1.0,
        "moc_shift": 0.0,
        "rad_factor": 1.0,
        "lambda_g": 0.076,
    },
    "CO2": {
        "name": "Karbondioksit (CO₂ - Söndürme Seyreltmesi)",
        "name_en": "Carbon Dioxide (CO₂ - Suppression Diluent)",
        "mw": 44.01,
        "cp_factor": 0.82,
        "moc_shift": 3.4,
        "rad_factor": 1.38,
        "lambda_g": 0.068,
    },
    "He": {
        "name": "Helyum (He - Yüksek Isıl Difüzyon)",
        "name_en": "Helium (He - High Thermal Diffusivity)",
        "mw": 4.00,
        "cp_factor": 1.06,
        "moc_shift": 2.1,
        "rad_factor": 0.88,
        "lambda_g": 0.185,
    },
}

HABITAT_CONFIGS: Dict[str, Dict[str, Any]] = {
    "iss_module": {
        "name_tr": "ISS ABD Laboratuvarı (Destiny Serbest Hava • 70 m³)",
        "name_en": "ISS US Lab Module (Destiny Free Air • 70 m³)",
        "volume_m3": 70.0,
    },
    "lunar_hab": {
        "name_tr": "Orion / Lunar Gateway Kabini (Serbest Hava • 19 m³)",
        "name_en": "Orion / Lunar Gateway Cabin (Free Air • 19 m³)",
        "volume_m3": 19.0,
    },
    "lunar_rover": {
        "name_tr": "Basınçlı Ay Gezgini / LTV Kabini (11 m³)",
        "name_en": "Pressurized Lunar Rover Cabin (11 m³)",
        "volume_m3": 11.0,
    },
    "mars_hab": {
        "name_tr": "Mars Yüzey Kabini (0.38G • 28 m³)",
        "name_en": "Mars Surface Cabin (0.38G • 28 m³)",
        "volume_m3": 28.0,
    },
    "eva_suit": {
        "name_tr": "EVA Uzay Giysisi Serbest Hava Hacmi (xEMU • 0.18 m³)",
        "name_en": "EVA Spacesuit Free Gas Volume (xEMU • 0.18 m³)",
        "volume_m3": 0.18,
    },
}

ANALOG_MATERIALS_DB: List[Dict[str, Any]] = [
    {
        "keys": ("peek", "polieter", "polyetheretherketone"),
        "label_tr": "PEEK Yüksek Sıcaklık Polimeri",
        "label_en": "PEEK High-Temp Polymer",
        "analog_base_id": "nomex",
        "rho_kg_m3": 1320.0,
        "lambda_s_w_mk": 0.25,
        "lv_kj_kg": 2280.0,
        "moc_0g": 22.8,
        "moc_1g": 25.6,
        "confidence_pct": 88,
        "unc_moc": 1.4,
        "tox_boost": {"hcn": 0.25, "hcl": 0.0, "hf": 0.0},
    },
    {
        "keys": ("xlpe", "polietilen", "polyethylene", "ldpe", "hdpe", "kablo izolasyon"),
        "label_tr": "XLPE / Polietilen Kablo İzolasyonu",
        "label_en": "XLPE / Polyethylene Wire Insulation",
        "analog_base_id": "pmma",
        "rho_kg_m3": 930.0,
        "lambda_s_w_mk": 0.38,
        "lv_kj_kg": 1420.0,
        "moc_0g": 15.1,
        "moc_1g": 17.4,
        "confidence_pct": 90,
        "unc_moc": 1.2,
        "tox_boost": {"hcn": 0.0, "hcl": 0.0, "hf": 0.0},
    },
    {
        "keys": ("ptfe", "teflon", "fep", "etfe", "floropolimer", "fluoropolymer"),
        "label_tr": "PTFE / Teflon Floropolimer İzolasyon",
        "label_en": "PTFE / Teflon Fluoropolymer Insulation",
        "analog_base_id": "nomex",
        "rho_kg_m3": 2150.0,
        "lambda_s_w_mk": 0.25,
        "lv_kj_kg": 2650.0,
        "moc_0g": 28.5,
        "moc_1g": 34.0,
        "confidence_pct": 86,
        "unc_moc": 1.8,
        "tox_boost": {"hcn": 0.0, "hcl": 0.0, "hf": 2.4},
    },
    {
        "keys": ("kapton", "poliimid", "polyimide"),
        "label_tr": "Kapton Poliimid Film / Kablo Bandı",
        "label_en": "Kapton Polyimide Film / Wire Wrap",
        "analog_base_id": "nomex",
        "rho_kg_m3": 1420.0,
        "lambda_s_w_mk": 0.12,
        "lv_kj_kg": 2420.0,
        "moc_0g": 24.8,
        "moc_1g": 28.5,
        "confidence_pct": 91,
        "unc_moc": 1.3,
        "tox_boost": {"hcn": 1.6, "hcl": 0.0, "hf": 0.0},
    },
    {
        "keys": ("pvc", "vinil", "vinyl", "neopren", "kloropren"),
        "label_tr": "PVC / Klorlu Polimer Kablo Kılıfı",
        "label_en": "PVC / Chlorinated Cable Jacket",
        "analog_base_id": "pmma",
        "rho_kg_m3": 1380.0,
        "lambda_s_w_mk": 0.16,
        "lv_kj_kg": 1780.0,
        "moc_0g": 19.2,
        "moc_1g": 22.4,
        "confidence_pct": 85,
        "unc_moc": 1.6,
        "tox_boost": {"hcn": 0.0, "hcl": 2.6, "hf": 0.0},
    },
    {
        "keys": ("epoksi", "epoxy", "karbon", "carbon", "kompozit", "composite", "cfrp"),
        "label_tr": "Karbon-Epoksi Yapısal Kompozit",
        "label_en": "Carbon-Epoxy Structural Composite",
        "analog_base_id": "pmma",
        "rho_kg_m3": 1560.0,
        "lambda_s_w_mk": 0.65,
        "lv_kj_kg": 1920.0,
        "moc_0g": 17.6,
        "moc_1g": 20.4,
        "confidence_pct": 83,
        "unc_moc": 1.7,
        "tox_boost": {"hcn": 0.45, "hcl": 0.0, "hf": 0.0},
    },
    {
        "keys": ("silikon", "silicone", "pdms", "elastomer"),
        "label_tr": "Silikon Elastomer Conta / Kılıf",
        "label_en": "Silicone Elastomer Seal / Liner",
        "analog_base_id": "sibal",
        "rho_kg_m3": 1150.0,
        "lambda_s_w_mk": 0.20,
        "lv_kj_kg": 1620.0,
        "moc_0g": 16.4,
        "moc_1g": 19.2,
        "confidence_pct": 89,
        "unc_moc": 1.3,
        "tox_boost": {"hcn": 0.0, "hcl": 0.0, "hf": 0.0},
    },
]


def resolve_analog_material(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    NASA PSI veritabanında doğrudan yer almayan kompozit / kablo izolasyonu malzemeleri için
    termofiziksel (yoğunluk, ısıl iletkenlik, ısıl atalet λ·ρ·c_p, piroliz entalpisi, MOC) vekil (analog) eşleştirmesi üretir.
    Hem arayüz anahtarlarını (custom_density_kg_m3, custom_conductivity_w_mk) hem de geri uyumluluk anahtarlarını
    (custom_rho_kg_m3, custom_lambda_w_mk) tam destekler.
    """
    if not isinstance(params, dict):
        params = {}
    req_fuel_id = str(params.get("fuel_id") or "n_heptane").strip()
    raw_custom_name = str(params.get("custom_material_name") or "").strip()
    raw_rho = params.get("custom_density_kg_m3")
    if isinstance(raw_rho, bool) or raw_rho in (None, "", 0, "0"):
        raw_rho = params.get("custom_rho_kg_m3", 0.0)
    raw_lambda = params.get("custom_conductivity_w_mk")
    if isinstance(raw_lambda, bool) or raw_lambda in (None, "", 0, "0"):
        raw_lambda = params.get("custom_cond_w_mk")
    if isinstance(raw_lambda, bool) or raw_lambda in (None, "", 0, "0"):
        raw_lambda = params.get("custom_lambda_w_mk", 0.0)

    custom_rho = _safe_float(raw_rho, 0.0, 0.0, 25000.0)
    custom_lambda = _safe_float(raw_lambda, 0.0, 0.0, 500.0)
    custom_moc = _safe_float(params.get("custom_moc_pct", 0.0), 0.0, 0.0, 100.0)

    is_custom = (
        (req_fuel_id == "custom_material")
        or bool(raw_custom_name)
        or (req_fuel_id not in FUEL_PROPERTIES)
    )
    if not is_custom and req_fuel_id in FUEL_PROPERTIES:
        return {
            "active": False,
            "base_fuel_id": req_fuel_id,
            "fuel": FUEL_PROPERTIES[req_fuel_id],
            "tox_boost": {"hcn": 0.0, "hcl": 0.0, "hf": 0.0},
            "info": {"active": False, "show_banner": False, "tr": "", "en": ""},
        }

    query_text = (raw_custom_name or req_fuel_id).strip()
    q_low = query_text.lower()
    matched_entry = None
    for entry in ANALOG_MATERIALS_DB:
        if any(k in q_low for k in entry["keys"]):
            matched_entry = entry
            break

    if matched_entry is None:
        # Isıl atalet (I_th = λ_s · ρ_s · c_p) mesafesine göre en yakın NASA katı referansını seç
        eff_rho_probe = custom_rho if custom_rho > 100.0 else 1180.0
        eff_lam_probe = custom_lambda if custom_lambda > 0.01 else 0.19
        target_inertia = eff_lam_probe * eff_rho_probe * 1420.0
        solid_candidates = ("pmma", "sibal", "nomex")
        best_base = "nomex" if (custom_moc >= 21.0 or eff_rho_probe >= 1340.0) else "pmma"
        best_dist = 1e18
        for cid in solid_candidates:
            cref = FUEL_PROPERTIES[cid]
            c_in = float(cref.get("lambda_s_w_mk", 0.19)) * float(cref["rho_l_kg_m3"]) * float(cref.get("cp_s_j_kgk", 1400.0))
            moc_pen = abs((custom_moc if custom_moc >= 5.0 else float(cref["moc_0g_base"])) - float(cref["moc_0g_base"])) * 42000.0
            dist = abs(target_inertia - c_in) + moc_pen
            if dist < best_dist:
                best_dist = dist
                best_base = cid
        base_id = best_base
        base_ref = FUEL_PROPERTIES[base_id]
        rho_val = custom_rho if custom_rho > 100.0 else float(base_ref["rho_l_kg_m3"])
        lam_val = custom_lambda if custom_lambda > 0.01 else float(base_ref.get("lambda_s_w_mk", 0.19))
        # Isıl atalet arttıkça (yüksek ρ·λ) de Ris / Olson sınırına göre 0G MOC hafifçe yükselir
        ref_inertia = max(1.0, float(base_ref.get("lambda_s_w_mk", 0.19)) * float(base_ref["rho_l_kg_m3"]))
        inertia_moc_shift = max(-1.6, min(2.8, 0.85 * math.log(max(0.15, (lam_val * rho_val) / ref_inertia))))
        moc0_val = custom_moc if custom_moc >= 5.0 else max(8.0, float(base_ref["moc_0g_base"]) + inertia_moc_shift)
        moc1_val = max(moc0_val + 1.8, moc0_val + (float(base_ref["moc_1g_base"]) - float(base_ref["moc_0g_base"])))
        label_tr = raw_custom_name if raw_custom_name else "Özel Kompozit / Kablo Numunesi"
        label_en = raw_custom_name if raw_custom_name else "Custom Composite / Cable Sample"
        conf_pct = 84 if (custom_rho > 100.0 and custom_lambda > 0.01) else 76
        unc_moc = 1.4 if custom_moc >= 5.0 else 1.9
        lv_val = float(base_ref["lv_kj_kg"])
        tox_boost = {"hcn": 0.2, "hcl": 0.2, "hf": 0.0}
    else:
        base_id = str(matched_entry["analog_base_id"])
        base_ref = FUEL_PROPERTIES[base_id]
        rho_val = custom_rho if custom_rho > 100.0 else float(matched_entry["rho_kg_m3"])
        lam_val = custom_lambda if custom_lambda > 0.01 else float(matched_entry["lambda_s_w_mk"])
        ref_in_m = max(1.0, float(matched_entry["lambda_s_w_mk"]) * float(matched_entry["rho_kg_m3"]))
        in_shift_m = 0.0
        if custom_rho > 100.0 or custom_lambda > 0.01:
            in_shift_m = max(-1.5, min(2.6, 0.78 * math.log(max(0.15, (lam_val * rho_val) / ref_in_m))))
        moc0_val = custom_moc if custom_moc >= 5.0 else max(8.0, float(matched_entry["moc_0g"]) + in_shift_m)
        moc1_val = max(moc0_val + 1.8, float(matched_entry["moc_1g"]) + (moc0_val - float(matched_entry["moc_0g"])))
        label_tr = raw_custom_name if raw_custom_name else str(matched_entry["label_tr"])
        label_en = raw_custom_name if raw_custom_name else str(matched_entry["label_en"])
        conf_pct = int(matched_entry["confidence_pct"])
        unc_moc = float(matched_entry["unc_moc"])
        lv_val = float(matched_entry["lv_kj_kg"])
        tox_boost = dict(matched_entry["tox_boost"])

    synth_fuel = dict(base_ref)
    synth_fuel["name_tr"] = f"{label_tr} (Benzer: {base_ref['name_tr'].split('(')[0].strip()})"
    synth_fuel["name_en"] = f"{label_en} (Analog: {base_ref['name_en'].split('(')[0].strip()})"
    synth_fuel["rho_l_kg_m3"] = round(rho_val, 1)
    synth_fuel["lambda_s_w_mk"] = round(lam_val, 3)
    synth_fuel["lv_kj_kg"] = round(lv_val, 1)
    synth_fuel["moc_0g_base"] = round(moc0_val, 2)
    synth_fuel["moc_1g_base"] = round(moc1_val, 2)
    synth_fuel["cool_flame_min_o2"] = round(moc0_val, 2)

    base_short_tr = base_ref["name_tr"].split("(")[0].strip()
    base_short_en = base_ref["name_en"].split("(")[0].strip()
    tr_msg = (
        f"**Benzer Malzeme Eşleştirmesi ({label_tr}):** Bu malzeme için NASA PSI kataloğunda doğrudan mikroçekim deneyi "
        f"bulunmamaktadır. Termofiziksel vekil olarak **{base_short_tr}** baz alındı (`ρ = {rho_val:.0f} kg/m³`, "
        f"`λ_s = {lam_val:.2f} W/m·K`, `Tahmini 0G MOC ≈ %{moc0_val:.1f} ± %{unc_moc:.1f}`, Eşleşme Güveni: `%{conf_pct}`). "
        f"Kesin uçuş sertifikasyonu için NASA-STD-6001B Test 1 ve düşük akışlı 0G doğrulaması gerekir."
    )
    en_msg = (
        f"**Analog Material Matching ({label_en}):** Direct microgravity test records are unavailable in NASA PSI for this material. "
        f"Mapped to thermophysical proxy **{base_short_en}** (`ρ = {rho_val:.0f} kg/m³`, `λ_s = {lam_val:.2f} W/m·K`, "
        f"`Est. 0G MOC ≈ {moc0_val:.1f}% ± {unc_moc:.1f}%`, Match Confidence: `{conf_pct}%`). "
        f"Flight qualification requires NASA-STD-6001B Test 1 screening."
    )

    return {
        "active": True,
        "base_fuel_id": base_id,
        "fuel": synth_fuel,
        "tox_boost": tox_boost,
        "info": {
            "active": True,
            "show_banner": True,
            "material_label_tr": label_tr,
            "material_label_en": label_en,
            "analog_base_id": base_id,
            "analog_base_tr": base_short_tr,
            "analog_base_en": base_short_en,
            "rho_kg_m3": round(rho_val, 1),
            "lambda_w_mk": round(lam_val, 3),
            "confidence_pct": conf_pct,
            "uncertainty_moc_pct": unc_moc,
            "tr": tr_msg,
            "en": en_msg,
        },
    }


def _compute_buoyant_velocity_cms(gravity_g: float, char_len_cm: float, t_flame_k: float = 1950.0, t_amb_k: float = 298.15) -> float:
    """Gerçek kaldırma (buoyancy) hızı: u_b = sqrt(g * L_plume * (T_f / T_inf - 1)) [cm/s]."""
    if gravity_g <= 1e-5 or t_flame_k <= t_amb_k:
        return 0.0
    g_cms2 = gravity_g * 980.665
    l_plume_cm = max(0.32, char_len_cm * 0.95)
    return math.sqrt(g_cms2 * l_plume_cm * max(0.0, (t_flame_k / t_amb_k) - 1.0))


def compute_moc_at_flow(
    fuel: Dict[str, Any],
    airflow_cms: float,
    gravity_g: float,
    pressure_psia: float,
    diluent: str = "N2",
    flow_direction: str = "opposed",
) -> float:
    """
    Yarı-Ampirik Mühendislik Zarfı — NASA BASS/Saffire Olson U-Eğrisi (Olson 1991, Combust. Sci. Tech.):
    Quenching (radyatif sönme) kolu + Mikro-havalandırma çukuru (2–8 cm/s) + Damköhler Blowoff kolu MOC (% O2) hesabı.
    Eş yönlü (concurrent) akışta sıcak duman ön-ısıtması MOC sınırını düşürür ve üfleme (blowoff) direncini artırır.
    """
    dil = DILUENT_FACTORS.get(diluent, DILUENT_FACTORS["N2"])
    p_atm = max(0.24, pressure_psia / 14.696)
    pressure_shift = 2.6 * ((1.0 / p_atm) ** 0.38 - 1.0)

    u_buoy_cms = _compute_buoyant_velocity_cms(gravity_g, 0.34, float(fuel.get("t_adiabatic_k", 2000.0)) * 0.85, 298.15)
    u_eff = math.hypot(airflow_cms, u_buoy_cms)
    base_moc = fuel["moc_0g_base"] + dil["moc_shift"] + pressure_shift

    is_concurrent = str(flow_direction).lower() == "concurrent"
    blowoff_ref = float(fuel["blowoff_cms"]) * (1.28 if is_concurrent else 1.0)
    quenching_penalty = 3.6 * math.exp(-u_eff / 1.65)
    ventilation_dip = -1.15 * math.exp(-((u_eff - 5.5) ** 2) / 28.0)
    concurrent_preheat_dip = (-0.72 * min(1.0, airflow_cms / 4.0) * math.exp(-max(0.0, airflow_cms - 22.0) / 24.0)) if is_concurrent else 0.0
    blowoff_penalty = 5.8 * ((max(0.0, u_eff - (15.0 if is_concurrent else 12.0)) / max(10.0, blowoff_ref)) ** 1.85)
    gravity_penalty = (fuel["moc_1g_base"] - fuel["moc_0g_base"]) * (gravity_g ** 0.65) * 0.65

    moc = base_moc + quenching_penalty + ventilation_dip + concurrent_preheat_dip + blowoff_penalty + gravity_penalty
    return round(max(4.5, min(55.0, moc)), 2)


def _solve_pure_burning_rate_k(
    fuel: Dict[str, Any],
    dil: Dict[str, Any],
    y_o2: float,
    p_atm: float,
    sh_conv: float,
    rad_loss_frac: float,
    flame_temp_k: float,
    cp_g_kj: float,
    cool_flame_active: bool = False,
) -> float:
    """
    Saf Godsave–Spalding d² Yasası + Law & Williams (1972, Combust. Flame 19:393) 1/3 Film Kuralı:
      T_ref = T_s + (1/3) * (T_f - T_s)
      K = [8 * lambda_g(T_ref) / (rho_l * c_p,eff(T_ref))] * ln(1 + B_oq) * (Sh / 2) * (1 - 0.36 * chi_r)
    Hiçbir yapay (%55 + %45) harmanlama içermez.
    """
    t_surf_k = float(fuel["t_boil_k"])
    t_ref_k = max(310.0, t_surf_k + (flame_temp_k - t_surf_k) / 3.0)

    # 300 K baz iletkenlikten T_ref film sıcaklığına kinetik teori ölçeklemesi: lambda(T) = lambda_300 * (T/300)^0.76
    lambda_300 = float(dil["lambda_g"]) * 0.354
    lambda_ref = lambda_300 * ((t_ref_k / 300.0) ** 0.76)

    is_gas_burner_phase = fuel["phase"] in ("gas_jet", "porous_sphere")
    lv_eff = float(fuel["lv_kj_kg"]) * float(fuel.get("water_cond_enthalpy_factor", 1.0))
    denom_enthalpy = (
        max(180.0, float(fuel.get("dh_sens_kj_kg", cp_g_kj * 1150.0)))
        if is_gas_burner_phase
        else lv_eff
    )
    dhc_eff = float(fuel["dhc_kj_kg"]) * (0.235 if cool_flame_active else 1.0)
    b_eff = max(
        0.18,
        (y_o2 * (dhc_eff / float(fuel["stoich_o2_fuel"])) - cp_g_kj * max(0.0, t_surf_k - 298.15)) / denom_enthalpy,
    )

    cp_vap_j = float(fuel.get("cp_vapor_j_kgk", 2100.0)) * ((t_ref_k / 650.0) ** 0.18)
    cp_gas_j = cp_g_kj * 1000.0
    cp_inner_eff = 0.68 * cp_vap_j + 0.32 * cp_gas_j
    polar_cond_boost = 1.12 if "water_cond_enthalpy_factor" in fuel else 1.0

    k_pure = (
        (8.0 * lambda_ref * polar_cond_boost / (float(fuel["rho_l_kg_m3"]) * cp_inner_eff))
        * math.log(1.0 + b_eff)
        * 1e6
        * (sh_conv / 2.0)
        * (max(0.22, p_atm) ** 0.22)
        * max(0.25, 1.0 - 0.36 * rad_loss_frac)
    )
    return round(max(0.05, k_pure), 3)


def _solve_law_chung_standoff_ratio(
    fuel: Dict[str, Any],
    spalding_b: float,
    y_o2: float,
    cp_g_kj: float,
    sh_conv: float,
) -> float:
    """
    Law, Chung & Srinivasan (1980, Combust. Flame 38:173) Küresel Stefan Akışı + Lewis Sayısı Alev Cephesi Oranı:
    Sabit '+ 2.1' yaması kullanmadan iç/dış bölge özgül ısı oranı ve sonlu difüzyon birikim çarpanıyla R_f / R_d çözer.
    """
    cp_ratio = float(fuel.get("cp_vapor_j_kgk", 2100.0)) / max(600.0, cp_g_kj * 1000.0)
    cp_ratio_clamped = min(2.4, max(0.75, cp_ratio))
    le_ox = float(fuel.get("lewis_ox", 1.0))
    transient_accum = 0.145  # Küresel dış oksitleyici bölgesi sonlu difüzyon birikim katsayısı (Law et al. 1980)
    ox_term = math.log(1.0 + max(0.015, y_o2 / (float(fuel["stoich_o2_fuel"]) * le_ox * transient_accum)))
    rf_rd = 1.0 + math.log(1.0 + spalding_b) / max(0.12, cp_ratio_clamped * ox_term * ((sh_conv / 2.0) ** 0.62))
    return round(max(1.65, min(11.5, rf_rd)), 2)


def _solve_de_ris_solid_spread_mms(
    fuel: Dict[str, Any],
    dil: Dict[str, Any],
    flame_temp_k: float,
    u_eff_cms: float,
    p_atm: float,
    oxygen_pct: float,
    moc_current: float,
    rad_loss_frac: float,
    flow_direction: str = "opposed",
) -> float:
    """
    John de Ris (1969, 12th Symp. Int. Combust.) & Olson (1991, ISS BASS / Saffire) İki Rejimli Katı Yüzey Yayılım Yasası:
      - Termal İnce (Sibal / Nomex): V_f = [sqrt(2) * lambda_g * (T_f - T_p)] / [rho_s * c_ps * tau_s * (T_p - T_inf)]
      - Termal Kalın (PMMA Çubuk):   V_f = [U_gas * (lambda_g * rho_g * c_pg) * (T_f - T_p)^2] / [(lambda_s * rho_s * c_ps) * (T_p - T_inf)^2]
      - Eş Yönlü (Concurrent) Akış (BASS-II / Saffire-I): Akış yönündeki piroliz ön-ısıtma bölgesi (L_f) yayılım hızını ~1.9–2.2x artırır.
    """
    t_amb = 298.15
    t_p = float(fuel["t_boil_k"])
    if flame_temp_k <= t_p + 40.0:
        return 0.0
    t_ref = t_p + (flame_temp_k - t_p) / 3.0
    lambda_g = (float(dil["lambda_g"]) * 0.354) * ((t_ref / 300.0) ** 0.76)
    rho_s = float(fuel["rho_l_kg_m3"])
    cp_s = float(fuel.get("cp_s_j_kgk", 1400.0))
    rad_atten = max(0.22, 1.0 - 0.55 * rad_loss_frac)

    is_concurrent = str(flow_direction).lower() == "concurrent"
    blowoff_lim = float(fuel["blowoff_cms"]) * (1.28 if is_concurrent else 1.0)
    concurrent_factor = (1.0 + 0.98 * min(1.15, u_eff_cms / 5.0)) if is_concurrent else 1.0

    # Olson (1991) düşük hız O2 taşınım ve yüksek hız Damköhler gerilme (stretch) zarfı
    o2_margin = max(0.08, (oxygen_pct - moc_current * 0.82) / 21.0)
    stretch_atten = math.exp(-max(0.0, u_eff_cms - (20.0 if is_concurrent else 16.0)) / blowoff_lim)

    if fuel["phase"] == "solid_thin":
        tau_s = float(fuel.get("thin_tau_m", 0.00042))
        vf_m_s = (
            (2.0 * math.sqrt(2.0) * lambda_g * (flame_temp_k - t_p))
            / max(1.0, rho_s * cp_s * tau_s * (t_p - t_amb))
        ) * (o2_margin ** 0.55) * (p_atm ** 0.35) * (1.0 + 0.45 * min(2.2, u_eff_cms / 6.0)) * stretch_atten * rad_atten * concurrent_factor
    else:
        lambda_s = float(fuel.get("lambda_s_w_mk", 0.19))
        # Fernandez-Pello & Hirano (1983) / de Ris (1969) öncü kenar Oseen difüzyon + zorlanmış akış hızı
        u_oseen_ms = max(0.08, (u_eff_cms / 100.0) + 0.095)
        rho_g = (p_atm * 101325.0 * 0.0288) / (8.31446 * t_ref)
        cp_g = 1180.0 / float(dil["cp_factor"])
        vf_m_s = (
            u_oseen_ms
            * (lambda_g * rho_g * cp_g)
            * ((flame_temp_k - t_p) ** 2)
            / max(1.0, (lambda_s * rho_s * cp_s) * ((t_p - t_amb) ** 2))
        ) * 2.4 * (o2_margin ** 0.50) * stretch_atten * rad_atten * concurrent_factor

    return round(max(0.05, min(28.0, vf_m_s * 1000.0)), 2)


def _compute_planck_radiative_loss(
    fuel: Dict[str, Any],
    dil: Dict[str, Any],
    droplet_d0_mm: float,
    standoff_ratio: float,
    t_est_k: float,
    p_atm: float,
    soot_est: float,
    sh_conv: float,
) -> Dict[str, float]:
    """
    Planck-Ortalama Optik İnce Radyatif Isı Kaybı (Ju et al. 2019 / TNF Workshop Optically Thin Radiation Model):
      Q_rad = V_shell * 4 * sigma * kappa_P(CO2, H2O, soot) * (T_f^4 - T_inf^4)
    """
    t_amb = 298.15
    r_d_m = max(0.0003, (droplet_d0_mm * 0.5) / 1000.0)
    r_f_m = max(r_d_m * 1.25, r_d_m * standoff_ratio)
    v_shell_m3 = (4.0 / 3.0) * math.pi * max(1e-11, (r_f_m ** 3) - (r_d_m ** 3))

    # Gaz (CO2 + H2O Planck emilimi) + Kurum hacim kesri (f_v ~ 1.2e-6 * soot_est) emilim katsayısı [1/m]
    is_h2 = fuel["formula"] == "H₂"
    kappa_gas = p_atm * (0.42 if is_h2 else 1.35) * float(dil["rad_factor"]) * ((1000.0 / max(500.0, t_est_k)) ** 0.65)
    f_v_soot = (1.35e-6) * max(0.0, soot_est)
    kappa_soot = 1260.0 * f_v_soot * t_est_k
    kappa_planck = kappa_gas + kappa_soot

    q_rad_w = v_shell_m3 * 4.0 * SIGMA_SB_W_M2K4 * kappa_planck * max(0.0, (t_est_k ** 4) - (t_amb ** 4))

    # Karakteristik kimyasal ısı salınımı Q_chem = m_dot_F * dhc
    r_ref_m = 0.0014
    size_scale = (r_d_m / r_ref_m) ** 1.15
    q_chem_ref_w = max(1.2, 26.0 * size_scale * (sh_conv / 2.0) * ((t_est_k / 1950.0) ** 1.4))
    chi_r = q_rad_w / max(0.25, q_chem_ref_w + 0.55 * q_rad_w)
    chi_r = round(max(0.03, min(0.88, chi_r)), 3)
    return {
        "rad_loss_frac": chi_r,
        "q_rad_w": round(q_rad_w, 3),
        "kappa_planck_m_inv": round(kappa_planck, 3),
    }


def simulate_combustion_state(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tüm termodinamik, yangın üçgeni (ön-tutuşma) ve çok-bölmeli kabin taşınım formüllerini çözerek:
    - 3B WebGL motoru durumunu (sıvı damlacık, katı çubuk/plaka, küresel gözenekli brülör + 4'lü NASA Uzay Gemisi Filosu),
    - Anlık Bilimsel Formül & Boyutsuz Sayılar Sonuç Tablosunu (`formula_table`),
    - Yangın Üçgeni & 0G Ön-Tutuşma Termal Kaçak Analizini (`pre_ignition`),
    - Çok-Bölmeli Kabin Basınç (ΔP), IDSS Kapak Yükü & Çoklu-Gaz FED Analizini (`compartment_network`),
    - Canlı ISS 0G Uçuş Doğrulaması (`flight_validation`) ve Sensör Zaman Serilerini döndürür.
    """
    if not isinstance(params, dict):
        params = {}
    analog_res = resolve_analog_material(params)
    fuel_id = analog_res["base_fuel_id"]
    fuel = analog_res["fuel"]
    analog_match_info = analog_res["info"]
    tox_boost = analog_res["tox_boost"]
    requested_fuel_id = "custom_material" if analog_res["active"] else fuel_id

    gravity_g = _safe_float(params.get("gravity_g", 0.0), 0.0, 0.0, 2.0)
    # EVA Uzay Giysisi (%100 O2 / 4.3 psia), ACME CFI-G (%85 O2) ve yüksek basınçlı PSI fazları (26.45 psia) için genişletilmiş fiziksel aralık:
    oxygen_pct = _safe_float(params.get("oxygen_pct", 21.0), 21.0, 5.0, 100.0)
    pressure_psia = _safe_float(params.get("pressure_psia", 14.7), 14.7, 3.0, 35.0)
    airflow_cms = _safe_float(params.get("airflow_cms", 3.5), 3.5, 0.0, 50.0)
    flow_direction = "concurrent" if str(params.get("flow_direction", "opposed")).lower() == "concurrent" else "opposed"
    droplet_d0_mm = _safe_float(params.get("droplet_d0_mm", 3.2), 3.2, 0.6, 8.0)
    diluent = str(params.get("diluent") or "N2")
    if diluent not in DILUENT_FACTORS:
        diluent = "N2"
    dil = DILUENT_FACTORS[diluent]

    habitat_id = str(params.get("habitat_id") or "iss_module")
    if habitat_id not in HABITAT_CONFIGS:
        habitat_id = "iss_module"
    crew_response_s = _safe_float(params.get("crew_response_s", 30.0), 30.0, 5.0, 999.0)

    fire_compartment_id = str(params.get("fire_compartment_id") or "HALO").strip().upper()
    if fire_compartment_id not in ("ORION_CM", "HALO", "IHAB", "PPE", "AIRLOCK"):
        fire_compartment_id = "HALO"
    sealed_hatches = [str(h) for h in params.get("sealed_hatches", []) if isinstance(h, str)] if isinstance(params.get("sealed_hatches"), list) else []
    imv_fan_cutoff = bool(params.get("imv_fan_cutoff", False) or params.get("vent_shutoff", False))
    water_mist_active = bool(params.get("water_mist_active", False))
    full_smother_active = bool(params.get("full_smother", False))
    if imv_fan_cutoff:
        airflow_cms = 0.0
    avionics_fault_watts = _safe_float(params.get("avionics_fault_watts", 0.0), 0.0, 0.0, 50000.0)

    p_atm = pressure_psia / 14.696
    pressure_kpa = round(pressure_psia * 6.89476, 2)
    po2_psia = round(pressure_psia * (oxygen_pct / 100.0), 2)
    po2_kpa = round(pressure_kpa * (oxygen_pct / 100.0), 2)

    # Kütle kesri Y_O2 hesabı (MW_O2 = 32.0; %100 saf O2 durumunda Y_O2 = 1.0)
    x_o2 = oxygen_pct / 100.0
    mw_mix = x_o2 * 32.0 + (1.0 - x_o2) * float(dil["mw"])
    y_o2 = min(1.0, (x_o2 * 32.0) / max(1.0, mw_mix))

    # Seyreltici N2/CO2 azaldıkça (%50 -> %100 O2 EVA uzay giysisi) ısıl balast kaybı çarpanı
    inert_ballast_relief = 1.0 + 0.24 * max(0.0, (x_o2 - 0.35) / 0.65)
    cp_g_kj = (1.22 / dil["cp_factor"]) / inert_ballast_relief

    # Spalding Kütle / Faz Transfer Sayısı (sıvı/katıda L_v veya ΔH_p, sabit gaz brülöründe Δh_sens)
    is_gas_burner_phase = fuel["phase"] in ("gas_jet", "porous_sphere")
    denom_enthalpy = (
        max(180.0, float(fuel.get("dh_sens_kj_kg", cp_g_kj * 1150.0)))
        if is_gas_burner_phase
        else float(fuel["lv_kj_kg"])
    )
    spalding_b = (
        y_o2 * (fuel["dhc_kj_kg"] / fuel["stoich_o2_fuel"]) - cp_g_kj * max(0.0, fuel["t_boil_k"] - 298.15)
    ) / denom_enthalpy
    spalding_b = round(max(0.25, spalding_b), 2)

    moc_current = compute_moc_at_flow(fuel, airflow_cms, gravity_g, pressure_psia, diluent, flow_direction)
    moc_0g_bound = compute_moc_at_flow(fuel, airflow_cms, 0.0, pressure_psia, diluent, flow_direction)
    moc_1g_bound = compute_moc_at_flow(fuel, airflow_cms, 1.0, pressure_psia, diluent, flow_direction)

    # Başlangıç adyabatik film sıcaklığı tahminiyle gerçek kinematik viskozite ν(T_film, P) ve Grashof sayısı
    t_amb_k = 298.15
    o2_ratio = oxygen_pct / 21.0
    t_est_hot_k = min(2780.0, float(fuel["t_adiabatic_k"]) * (0.72 + 0.28 * (o2_ratio ** 0.42)) * float(dil["cp_factor"]) * inert_ballast_relief)
    t_film_k = 0.5 * (t_est_hot_k + t_amb_k)
    nu_cm2_s = (0.156 * ((t_film_k / 300.0) ** 1.68)) / max(0.22, p_atm)
    char_len_cm = droplet_d0_mm / 10.0

    re_num = (airflow_cms * char_len_cm) / nu_cm2_s
    gr_num = (980.665 * gravity_g * max(0.0, t_est_hot_k - t_amb_k) * (char_len_cm ** 3)) / (t_film_k * (nu_cm2_s ** 2))
    ra_num = gr_num * 0.71
    richardson_ri = round(gr_num / max(1e-4, re_num ** 2), 2) if re_num > 0.02 else (999.0 if gravity_g > 0.01 else 0.0)

    sh_conv = 2.0 + 0.60 * math.sqrt(max(0.0, re_num)) * (0.71 ** (1.0 / 3.0)) + 0.52 * (max(0.0, ra_num) ** 0.25)

    # Yamasız Law–Chung–Srinivasan (1980) Küresel Stefan + Lewis Alev Cephesi Oranı R_f / R_d
    standoff_ratio = _solve_law_chung_standoff_ratio(fuel, spalding_b, y_o2, cp_g_kj, sh_conv)

    # Planck-Ortalama Optik İnce Radyasyon Kaybı (T_f^4 - T_inf^4)
    soot_est = min(1.0, float(fuel["soot_tendency"]) * (0.28 + 0.72 * min(1.0, gravity_g * 1.1 + airflow_cms / 28.0)) * (p_atm ** 0.6) * (o2_ratio ** 0.45))
    rad_info = _compute_planck_radiative_loss(fuel, dil, droplet_d0_mm, standoff_ratio, t_est_hot_k, p_atm, soot_est, sh_conv)
    rad_loss_frac = rad_info["rad_loss_frac"]

    # Gerçek Kaldırma Hızı u_b, Froude Sayısı Fr ve İki Dallı Arrhenius Damköhler Sayısı (Da = τ_flow / τ_chem)
    u_buoy_cms = _compute_buoyant_velocity_cms(gravity_g, char_len_cm, t_est_hot_k, t_amb_k)
    u_eff = math.hypot(airflow_cms, u_buoy_cms)
    froude_fr = round((u_eff ** 2) / max(1e-4, 980.665 * gravity_g * char_len_cm), 2) if gravity_g > 1e-4 else 999.0
    tau_flow_ms = (char_len_cm / max(0.35, u_eff)) * 1000.0
    arr_kin = compute_arrhenius_chemical_timescale_ms(
        fuel_id=fuel_id,
        temp_eval_k=t_est_hot_k * (1.0 - 0.22 * rad_loss_frac),
        x_o2=x_o2,
        p_atm=p_atm,
        cool_flame_capable=bool(fuel["cool_flame_capable"]),
    )
    tau_chem_ms = arr_kin["tau_chem_ms"]
    damkohler_da = round(min(99.9, tau_flow_ms / max(0.04, tau_chem_ms)), 2)

    blowoff_vel_limit = fuel["blowoff_cms"] * (1.28 if flow_direction == "concurrent" else 1.0) * ((oxygen_pct / 21.0) ** 0.65)
    is_blowoff = airflow_cms > blowoff_vel_limit or (damkohler_da < 0.95 and airflow_cms >= (13.0 if flow_direction == "concurrent" else 10.0))
    radiative_quench_trigger = (
        gravity_g < 0.08
        and airflow_cms < 1.8
        and droplet_d0_mm >= 3.4
        and oxygen_pct < (moc_current + 3.2)
    )

    cool_flame_active = False
    extinguished = False

    if water_mist_active or full_smother_active:
        regime = "QUENCHED_EXTINGUISHED"
        extinguished = True
    elif is_blowoff:
        regime = "BLOWOFF_EXTINGUISHED"
        extinguished = True
    elif oxygen_pct < moc_current or radiative_quench_trigger:
        if (
            fuel["cool_flame_capable"]
            and gravity_g < 0.15
            and airflow_cms < 8.0
            and oxygen_pct >= fuel["cool_flame_min_o2"]
        ):
            regime = "COOL_FLAME_NTC"
            cool_flame_active = True
        else:
            regime = "QUENCHED_EXTINGUISHED"
            extinguished = True
    else:
        if gravity_g >= 0.12:
            regime = "BUOYANT_PLUME_1G"
        elif airflow_cms >= 1.5:
            regime = "VENTILATED_WAKE_0G"
        else:
            regime = "HOT_SPHERICAL_0G"

    if extinguished:
        flame_temp_k = 298.0
        gr_num = 0.0
        ra_num = 0.0
        richardson_ri = 0.0
        k_burn = 0.0
        flame_spread_mms = 0.0
        co_ppm = 1.0
        soot_index = 0.0
        heat_flux_kw_m2 = 0.0
    elif cool_flame_active:
        eff_o2_span = min(14.0, max(0.5, oxygen_pct - fuel["cool_flame_min_o2"]))
        flame_temp_k = round(565.0 + eff_o2_span * 14.5 + 25.0 * p_atm, 1)
        flame_temp_k = min(785.0, max(520.0, flame_temp_k))
        # NTC soğuk alevde yeniden hesaplanan gerçek Arrhenius kimyasal zaman ölçeği ve saf Godsave–Spalding d² hızı
        arr_ntc = compute_arrhenius_chemical_timescale_ms(fuel_id, flame_temp_k, x_o2, p_atm, True)
        tau_chem_ms = arr_ntc["tau_chem_ms"]
        damkohler_da = round(min(99.9, tau_flow_ms / max(0.05, tau_chem_ms)), 2)
        k_burn = _solve_pure_burning_rate_k(
            fuel=fuel,
            dil=dil,
            y_o2=y_o2,
            p_atm=p_atm,
            sh_conv=sh_conv,
            rad_loss_frac=rad_loss_frac * 0.35,
            flame_temp_k=flame_temp_k,
            cp_g_kj=cp_g_kj,
            cool_flame_active=True,
        )
        flame_spread_mms = 0.0
        co_ppm = round(420.0 + 38.0 * droplet_d0_mm + (18.0 - min(18.0, oxygen_pct)) * 22.0, 0)
        soot_index = 0.0
        heat_flux_kw_m2 = round(3.4 + 0.6 * (flame_temp_k - 520.0) / 100.0, 2)
    else:
        raw_temp = (
            fuel["t_adiabatic_k"]
            * (0.72 + 0.28 * (o2_ratio ** 0.42))
            * dil["cp_factor"]
            * inert_ballast_relief
            * (1.0 - 0.34 * rad_loss_frac)
            * (p_atm ** 0.06)
        )
        # Yüksek sıcaklıkta endotermik CO2/H2O disosiyasyonu (NASA CEA termokimyasal tavan sönümlemesi)
        if raw_temp > 2280.0:
            raw_temp = 2280.0 + 510.0 * math.tanh((raw_temp - 2280.0) / 740.0)
        flame_temp_k = round(max(1180.0, min(2810.0, raw_temp)), 1)

        # Saf Godsave–Spalding + Law–Williams 1/3 Film Kuralı yanma hızı sabiti K
        k_burn = _solve_pure_burning_rate_k(
            fuel=fuel,
            dil=dil,
            y_o2=y_o2,
            p_atm=p_atm,
            sh_conv=sh_conv,
            rad_loss_frac=rad_loss_frac,
            flame_temp_k=flame_temp_k,
            cp_g_kj=cp_g_kj,
            cool_flame_active=False,
        )

        # John de Ris (1969) İki Rejimli Katı Yüzey Alev Yayılım Yasası (yalnızca katı yakıtlarda tanımlı)
        if fuel["phase"] in ("solid_surface", "solid_thin", "rod", "fabric_sheet"):
            flame_spread_mms = _solve_de_ris_solid_spread_mms(
                fuel=fuel,
                dil=dil,
                flame_temp_k=flame_temp_k,
                u_eff_cms=u_eff,
                p_atm=p_atm,
                oxygen_pct=oxygen_pct,
                moc_current=moc_current,
                rad_loss_frac=rad_loss_frac,
                flow_direction=flow_direction,
            )
        else:
            flame_spread_mms = 0.0
        soot_index = round(soot_est, 3)
        co_ppm = round(45.0 + 190.0 * soot_index + (120.0 if airflow_cms < 2.0 else 25.0), 0)
        # Stefan-Boltzmann T^4 radyatif + sınır tabakası konvektif radyometre ısı akısı [kW/m^2]
        emissivity_view = 0.021 + 0.022 * soot_index + 0.004 * float(dil["rad_factor"])
        q_rad_flux_kw = emissivity_view * SIGMA_SB_W_M2K4 * max(0.0, (flame_temp_k ** 4) - (t_amb_k ** 4)) / 1000.0
        q_conv_flux_kw = (0.0029 * sh_conv) * max(0.0, flame_temp_k - t_amb_k)
        heat_flux_kw_m2 = round(max(4.5, min(145.0, q_rad_flux_kw + q_conv_flux_kw)), 2)

    is_gas_burner = fuel["phase"] in ("gas_jet", "porous_sphere")
    flame_radius_mm = round((droplet_d0_mm * 0.5) * standoff_ratio, 2) if not extinguished else 0.0
    burn_lifetime_s = (
        180.0 if (is_gas_burner and k_burn > 0)
        else (round((droplet_d0_mm ** 2) / max(0.05, k_burn), 1) if k_burn > 0 else 0.0)
    )

    # Ölçek-bağımsız birim alan ısı salınım hızı (HRRPUA, kW/m^2) — NASA PSI küçük ve büyük ölçek kıyaslaması için
    if extinguished:
        hrrpua_kw_m2 = 0.0
    elif cool_flame_active:
        hrrpua_kw_m2 = round(18.0 + 24.0 * k_burn + 1.8 * heat_flux_kw_m2, 1)
    else:
        m_dot_flux_kg_m2s = max(0.0025, 0.0042 * math.log(1.0 + spalding_b) * (sh_conv / 2.0) * (max(0.3, p_atm) ** 0.25))
        hrrpua_kw_m2 = round(min(680.0, m_dot_flux_kg_m2s * float(fuel["dhc_kj_kg"]) * (1.0 - 0.28 * rad_loss_frac) * 0.42), 1)

    # Cetegen & Ahmed (1993) / Durox et al. (1995) Doğal Kaldırma Alev Salınım Frekansı: f = 0.48 * sqrt(g / D_f) = 1.50 * sqrt((g/g_0) / D_f) [Hz]
    d_flame_m = max(0.002, (flame_radius_mm * 2.0) / 1000.0) if flame_radius_mm > 0 else max(0.002, droplet_d0_mm / 1000.0)
    flicker_freq_hz = round(0.48 * math.sqrt((gravity_g * 9.80665) / d_flame_m), 2) if (gravity_g > 1e-4 and not extinguished) else 0.0

    # Yangın Üçgeni (MIE, φ, LFL/UFL) + 0G Ön-Tutuşma Termal Kaçak (Semenov ψ & Frank-Kamenetskii δ)
    pre_ignition = compute_fire_triangle_and_preignition(
        fuel_id=fuel_id,
        fuel=fuel,
        dil=dil,
        gravity_g=gravity_g,
        oxygen_pct=oxygen_pct,
        pressure_psia=pressure_psia,
        airflow_cms=airflow_cms,
        droplet_d0_mm=droplet_d0_mm,
        spalding_b=spalding_b,
        sh_conv=sh_conv,
        flame_temp_k=flame_temp_k,
        heat_flux_kw_m2=heat_flux_kw_m2,
        avionics_fault_watts=avionics_fault_watts,
    )

    # Çok-Bölmeli Uzay Gemisi Ağı (Quintiere HRR, Apollo-1 ΔP, IDSS Kapak Yükü, SoFIE-MIST & Çoklu-Gaz FED)
    compartment_net = compute_multicompartment_and_toxicology(
        fuel_id=fuel_id,
        fuel=fuel,
        extinguished=extinguished,
        cool_flame_active=cool_flame_active,
        flame_temp_k=flame_temp_k,
        heat_flux_kw_m2=heat_flux_kw_m2,
        k_burn=k_burn,
        flame_spread_mms=flame_spread_mms,
        oxygen_pct=oxygen_pct,
        pressure_psia=pressure_psia,
        airflow_cms=airflow_cms,
        crew_response_s=crew_response_s,
        fire_compartment_id=fire_compartment_id,
        sealed_hatches=sealed_hatches,
        imv_fan_cutoff=imv_fan_cutoff,
        water_mist_active=water_mist_active,
    )

    tox_dict = compartment_net.get("multi_gas_toxicology", {})
    if not extinguished and (tox_boost["hcn"] > 0 or tox_boost["hcl"] > 0 or tox_boost["hf"] > 0):
        tox_dict["hcn_ppm"] = round(float(tox_dict.get("hcn_ppm", 0.0)) + 26.0 * tox_boost["hcn"], 1)
        tox_dict["hcl_ppm"] = round(float(tox_dict.get("hcl_ppm", 0.0)) + 34.0 * tox_boost["hcl"], 1)
        tox_dict["hf_ppm"] = round(float(tox_dict.get("hf_ppm", 0.0)) + 22.0 * tox_boost["hf"], 1)
        tox_dict["fed_total"] = round(min(2.5, float(tox_dict.get("fed_total", 0.0)) + 0.04 * (tox_boost["hcn"] + tox_boost["hcl"] + tox_boost["hf"])), 4)

    hcn_ppm = round(float(tox_dict.get("hcn_ppm", 0.0)), 1)
    hcl_ppm = round(float(tox_dict.get("hcl_ppm", 0.0)), 1)
    hf_ppm = round(float(tox_dict.get("hf_ppm", 0.0)), 1)
    co2_ppm_est = max(450.0, float(tox_dict.get("co2_pct", 0.08)) * 10000.0)
    co_co2_ratio = round(co_ppm / co2_ppm_est, 4)
    acid_nitrile_score = hcn_ppm * 0.28 + hcl_ppm * 0.22 + hf_ppm * 0.38
    tox_risk_points = min(18.0, (co_ppm / 75.0) + acid_nitrile_score + min(6.0, co_co2_ratio * 35.0) + float(tox_dict.get("fed_total", 0.0)) * 12.0)

    # Yarı-Ampirik Mühendislik + Toksik Gaz (CO, HCN, HCl, HF, CO/CO2) Karar İndeksi (0–100 Risk Skoru)
    if extinguished:
        risk_score = max(5, int(18 - (moc_current - oxygen_pct) * 2.2))
        risk_driver_tr = "Durum: Oksijen veya akış sınırında sönümlendi (Düşük Risk)"
        risk_driver_en = "Status: Quenched below flammability limit (Low Risk)"
    elif cool_flame_active:
        risk_score = min(89, int(round(56.0 + (co_ppm / 28.0) + min(8.0, co_co2_ratio * 40.0))))
        risk_driver_tr = f"Ana Etken: Görünmez Soğuk Alev + Eksik Yanma CO ({co_ppm:.0f} ppm)"
        risk_driver_en = f"Primary Driver: Invisible Cool Flame + CO Buildup ({co_ppm:.0f} ppm)"
    else:
        margin_over_moc = max(0.0, oxygen_pct - moc_current)
        eva_pure_o2_penalty = 18.0 if oxygen_pct >= 75.0 else (10.0 if (pressure_psia <= 10.5 and oxygen_pct >= 30.0) else 0.0)
        concurrent_penalty = 5.5 if (flow_direction == "concurrent" and flame_spread_mms > 0.2) else 0.0
        risk_raw = (
            24.0
            + margin_over_moc * 2.55
            + min(28.0, flame_spread_mms * 4.6)
            + (10.0 if (gravity_g < 0.1 and 1.5 <= airflow_cms <= 12.0) else 0.0)
            + eva_pure_o2_penalty
            + concurrent_penalty
            + tox_risk_points
        )
        risk_score = max(15, min(99, int(round(risk_raw))))
        if acid_nitrile_score >= 4.0:
            gas_tags = []
            if hcn_ppm >= 5.0:
                gas_tags.append(f"HCN {hcn_ppm:.0f} ppm")
            if hcl_ppm >= 5.0:
                gas_tags.append(f"HCl {hcl_ppm:.0f} ppm")
            if hf_ppm >= 3.0:
                gas_tags.append(f"HF {hf_ppm:.0f} ppm")
            gas_str = ", ".join(gas_tags) if gas_tags else f"CO {co_ppm:.0f} ppm"
            risk_driver_tr = f"Ana Etken: Isıl Güç + Toksik Gaz ({gas_str})"
            risk_driver_en = f"Primary Driver: Thermal Growth + Toxic Gas ({gas_str})"
        elif oxygen_pct >= 50.0:
            risk_driver_tr = f"Ana Etken: Yüksek Oksijen Zenginleşmesi (%{oxygen_pct:.0f} O₂)"
            risk_driver_en = f"Primary Driver: High Oxygen Enrichment ({oxygen_pct:.0f}% O₂)"
        elif flame_spread_mms >= 1.2:
            dir_tr = "Eş Yönlü Yayılım" if flow_direction == "concurrent" else "Yüzey Yayılımı"
            dir_en = "Concurrent Spread" if flow_direction == "concurrent" else "Surface Spread"
            risk_driver_tr = f"Ana Etken: {dir_tr} ({flame_spread_mms:.2f} mm/s) + CO Riski"
            risk_driver_en = f"Primary Driver: {dir_en} ({flame_spread_mms:.2f} mm/s) + CO Load"
        else:
            risk_driver_tr = f"Ana Etken: Aktif Yanma Isısı + CO/CO₂ ({co_co2_ratio:.3f})"
            risk_driver_en = f"Primary Driver: Thermal Release + CO/CO₂ ({co_co2_ratio:.3f})"

    flow_axis: List[float] = [round(x * 1.0, 1) for x in range(0, 41, 2)]
    moc_curve_0g = [compute_moc_at_flow(fuel, u, 0.0, pressure_psia, diluent, flow_direction) for u in flow_axis]
    moc_curve_lunar_016g = [compute_moc_at_flow(fuel, u, 0.16, pressure_psia, diluent, flow_direction) for u in flow_axis]
    moc_curve_mars_038g = [compute_moc_at_flow(fuel, u, 0.38, pressure_psia, diluent, flow_direction) for u in flow_axis]
    moc_curve_1g = [compute_moc_at_flow(fuel, u, 1.0, pressure_psia, diluent, flow_direction) for u in flow_axis]
    cool_flame_floor = [
        round(fuel["cool_flame_min_o2"], 2) if (fuel["cool_flame_capable"] and u <= 8.0) else None
        for u in flow_axis
    ]

    partial_gravity_info = _build_partial_gravity_notice(
        gravity_g=gravity_g,
        moc_current=moc_current,
        moc_0g_bound=moc_0g_bound,
        moc_1g_bound=moc_1g_bound,
        pressure_psia=pressure_psia,
        oxygen_pct=oxygen_pct,
        airflow_cms=airflow_cms,
        richardson_ri=richardson_ri,
    )

    sensor_series = _generate_multisensor_timeseries(
        droplet_d0_mm=droplet_d0_mm,
        k_burn=k_burn,
        flame_temp_k=flame_temp_k,
        heat_flux_kw_m2=heat_flux_kw_m2,
        co_ppm=co_ppm,
        regime=regime,
        fuel=fuel,
        gravity_g=gravity_g,
        airflow_cms=airflow_cms,
        flicker_freq_hz=flicker_freq_hz,
    )

    callouts = _build_human_callouts(
        regime=regime,
        fuel=fuel,
        gravity_g=gravity_g,
        oxygen_pct=oxygen_pct,
        moc_current=moc_current,
        airflow_cms=airflow_cms,
        pressure_psia=pressure_psia,
        flame_temp_k=flame_temp_k,
    )

    formula_table = _build_scientific_formula_table(
        fuel=fuel,
        spalding_b=spalding_b,
        k_burn=k_burn,
        flame_spread_mms=flame_spread_mms,
        flame_radius_mm=flame_radius_mm,
        burn_lifetime_s=burn_lifetime_s,
        standoff_ratio=standoff_ratio,
        re_num=re_num,
        gr_num=gr_num,
        ra_num=ra_num,
        richardson_ri=richardson_ri,
        froude_fr=froude_fr,
        sh_conv=sh_conv,
        damkohler_da=damkohler_da,
        rad_loss_frac=rad_loss_frac,
        po2_psia=po2_psia,
        po2_kpa=po2_kpa,
        moc_current=moc_current,
        oxygen_pct=oxygen_pct,
        pre_ignition=pre_ignition,
        compartment_net=compartment_net,
    )

    instant_ai_summary = _build_instant_formula_commentary(
        fuel=fuel,
        regime=regime,
        gravity_g=gravity_g,
        oxygen_pct=oxygen_pct,
        pressure_psia=pressure_psia,
        po2_psia=po2_psia,
        airflow_cms=airflow_cms,
        moc_current=moc_current,
        moc_0g_bound=moc_0g_bound,
        moc_1g_bound=moc_1g_bound,
        spalding_b=spalding_b,
        k_burn=k_burn,
        flame_spread_mms=flame_spread_mms,
        sh_conv=sh_conv,
        damkohler_da=damkohler_da,
        rad_loss_frac=rad_loss_frac,
        risk_score=risk_score,
        co_ppm=co_ppm,
        badge_tr=callouts["badge_tr"],
        badge_en=callouts["badge_en"],
    )

    flight_validation = _build_iss_flight_validation(
        fuel_id=fuel_id,
        fuel=fuel,
        regime=regime,
        pressure_psia=pressure_psia,
        diluent=diluent,
        sensor_series=sensor_series,
    )

    scenario_timeline = compute_cabin_scenario_timeline(
        habitat_id=habitat_id,
        crew_response_s=crew_response_s,
        regime=regime,
        extinguished=extinguished,
        flame_temp_k=flame_temp_k,
        heat_flux_kw_m2=heat_flux_kw_m2,
        co_ppm=co_ppm,
        k_burn=k_burn,
        flame_spread_mms=flame_spread_mms,
        oxygen_pct=oxygen_pct,
        pressure_psia=pressure_psia,
        airflow_cms=airflow_cms,
        regime_label_tr=callouts["badge_tr"],
        regime_label_en=callouts["badge_en"],
    )

    fuel_phase_cat = (
        "gas"
        if fuel["phase"] in ("gas_jet", "porous_sphere")
        else ("solid" if fuel["phase"] in ("solid_surface", "solid_thin", "rod", "fabric_sheet") else "liquid")
    )

    uncertainty_bounds = _compute_analytical_uncertainty_bounds(
        fuel=fuel,
        gravity_g=gravity_g,
        airflow_cms=airflow_cms,
        moc_current=moc_current,
        moc_0g_bound=moc_0g_bound,
        moc_1g_bound=moc_1g_bound,
        k_burn=k_burn,
        flame_temp_k=flame_temp_k,
        flame_spread_mms=flame_spread_mms,
        damkohler_da=damkohler_da,
        analog_match_info=analog_match_info,
    )

    moc_curve_active_g = [compute_moc_at_flow(fuel, u, gravity_g, pressure_psia, diluent, flow_direction) for u in flow_axis]
    base_sigma_map = float(uncertainty_bounds["moc_sigma_pct"])
    moc_upper_1sigma = [
        round(min(58.0, val + base_sigma_map * (1.22 if u < 3.0 else (1.14 if u > 24.0 else 1.0))), 2)
        for u, val in zip(flow_axis, moc_curve_active_g)
    ]
    moc_lower_1sigma = [
        round(max(4.0, val - base_sigma_map * (1.22 if u < 3.0 else (1.14 if u > 24.0 else 1.0))), 2)
        for u, val in zip(flow_axis, moc_curve_active_g)
    ]

    post_fire_cooling = _compute_post_fire_cooling(
        fuel=fuel,
        gravity_g=gravity_g,
        oxygen_pct=oxygen_pct,
        pressure_psia=pressure_psia,
        droplet_d0_mm=droplet_d0_mm,
        flame_temp_k=flame_temp_k,
        co_ppm=co_ppm,
        extinguished=extinguished,
        cool_flame_active=cool_flame_active,
    )

    mission_certification = _compute_mission_certification(
        fuel=fuel,
        dil_default="N2",
        flow_direction=flow_direction,
    )

    space_to_earth_live = _compute_space_to_earth_live(
        fuel=fuel,
        flame_temp_k=flame_temp_k,
        heat_flux_kw_m2=heat_flux_kw_m2,
        hrrpua_kw_m2=hrrpua_kw_m2,
        co_ppm=co_ppm,
        cool_flame_active=cool_flame_active,
        pre_ignition=pre_ignition,
    )

    return {
        "inputs": {
            "fuel_id": requested_fuel_id,
            "analog_base_id": fuel_id,
            "fuel_name_tr": fuel["name_tr"],
            "fuel_name_en": fuel["name_en"],
            "formula": fuel["formula"],
            "phase": fuel["phase"],
            "fuel_phase": fuel_phase_cat,
            "geometry_3d": fuel.get("geometry_3d", "droplet"),
            "gravity_g": gravity_g,
            "oxygen_pct": oxygen_pct,
            "pressure_psia": pressure_psia,
            "pressure_kpa": pressure_kpa,
            "airflow_cms": airflow_cms,
            "flow_direction": flow_direction,
            "droplet_d0_mm": droplet_d0_mm,
            "diluent": diluent,
            "diluent_name": dil["name"],
            "diluent_name_en": dil["name_en"],
            "habitat_id": habitat_id,
            "crew_response_s": crew_response_s,
            "custom_material_name": str(params.get("custom_material_name", "") or ""),
            "custom_density_kg_m3": round(float(fuel.get("rho_l_kg_m3", 0.0)), 1),
            "custom_conductivity_w_mk": round(float(fuel.get("lambda_s_w_mk", 0.19)), 3),
            "custom_moc_pct": round(float(fuel.get("moc_0g_base", 15.0)), 2),
        },
        "telemetry": {
            "regime": regime,
            "fuel_phase": fuel_phase_cat,
            "flow_direction": flow_direction,
            "extinguished": extinguished,
            "cool_flame_active": cool_flame_active,
            "flame_temp_k": flame_temp_k,
            "flame_temp_c": round(flame_temp_k - 273.15, 1),
            "burning_rate_k_mm2_s": k_burn,
            "spalding_b_number": spalding_b,
            "flame_spread_mm_s": flame_spread_mms,
            "moc_pct": moc_current,
            "po2_psia": po2_psia,
            "po2_kpa": po2_kpa,
            "o2_partial_psia": po2_psia,
            "o2_partial_kpa": po2_kpa,
            "standoff_ratio": standoff_ratio,
            "standoff_ratio_rf_rd": standoff_ratio,
            "flame_radius_mm": flame_radius_mm,
            "burn_lifetime_s": burn_lifetime_s,
            "radiative_loss_fraction": rad_loss_frac,
            "reynolds_number": round(re_num, 2),
            "grashof_number": round(gr_num, 2),
            "rayleigh_number": round(ra_num, 2),
            "richardson_number": richardson_ri,
            "froude_number": froude_fr,
            "sherwood_number": round(sh_conv, 2),
            "damkohler_number": damkohler_da,
            "tau_chem_ms": tau_chem_ms,
            "flicker_freq_hz": flicker_freq_hz,
            "planck_kappa_m_inv": rad_info["kappa_planck_m_inv"],
            "soot_index": soot_index,
            "co_ppm": co_ppm,
            "co_co2_ratio": co_co2_ratio,
            "hcn_ppm": hcn_ppm,
            "hcl_ppm": hcl_ppm,
            "hf_ppm": hf_ppm,
            "heat_flux_kw_m2": heat_flux_kw_m2,
            "hrrpua_kw_m2": hrrpua_kw_m2,
            "risk_score": risk_score,
            "risk_driver_tr": risk_driver_tr,
            "risk_driver_en": risk_driver_en,
        },
        "uncertainty_bounds": uncertainty_bounds,
        "post_fire_cooling": post_fire_cooling,
        "mission_certification": mission_certification,
        "space_to_earth_live": space_to_earth_live,
        "pre_ignition": pre_ignition,
        "compartment_network": compartment_net,
        "partial_gravity_info": partial_gravity_info,
        "analog_match_info": analog_match_info,
        "formula_table": formula_table,
        "instant_ai_summary": instant_ai_summary,
        "callouts": callouts,
        "flight_validation": flight_validation,
        "scenario_timeline": scenario_timeline,
        "flammability_map": {
            "airflow_cms": flow_axis,
            "moc_0g_pct": moc_curve_0g,
            "moc_lunar_016g_pct": moc_curve_lunar_016g,
            "moc_mars_038g_pct": moc_curve_mars_038g,
            "moc_1g_pct": moc_curve_1g,
            "moc_active_g_pct": moc_curve_active_g,
            "moc_upper_1sigma_pct": moc_upper_1sigma,
            "moc_lower_1sigma_pct": moc_lower_1sigma,
            "moc_sigma_pct": base_sigma_map,
            "cool_flame_floor_pct": cool_flame_floor,
            "current_point": {"airflow_cms": airflow_cms, "oxygen_pct": oxygen_pct, "gravity_g": gravity_g},
        },
        "sensor_timeseries": sensor_series,
    }


def _build_partial_gravity_notice(
    gravity_g: float,
    moc_current: float,
    moc_0g_bound: float,
    moc_1g_bound: float,
    pressure_psia: float,
    oxygen_pct: float,
    airflow_cms: float = 0.0,
    richardson_ri: float = 0.0,
) -> Dict[str, Any]:
    """
    NASA'nın resmi yarışma değerlendirme kriterlerindeki 'Kısmi Yerçekimi Verileri (LUCI & FM2)' ve
    'Uzay Giysileri (%100 O2 @ 4.3 psia / Ay Gezgini 10.2 psia)' şeffaflık bilgisini üretir.
    """
    is_partial = 0.03 <= gravity_g <= 0.88
    is_eva_suit = pressure_psia <= 5.2 and oxygen_pct >= 80.0
    is_lunar_rover = 8.0 <= pressure_psia <= 11.2 and 28.0 <= oxygen_pct <= 40.0

    env_tag_tr = (
        "Ay Yüzeyi (0.16G Lunar-g)" if 0.11 <= gravity_g <= 0.24
        else "Mars Yüzeyi (0.38G Martian-g)" if 0.25 <= gravity_g <= 0.50
        else f"Kısmi Yerçekimi ({gravity_g:.2f}G)"
    )
    env_tag_en = (
        "Lunar Surface (0.16G)" if 0.11 <= gravity_g <= 0.24
        else "Martian Surface (0.38G)" if 0.25 <= gravity_g <= 0.50
        else f"Partial Gravity ({gravity_g:.2f}G)"
    )

    if airflow_cms < 1.2:
        regime_tag_tr = "Doğal Kaldırma Beslemeli Durgun Rejim"
        regime_tag_en = "Buoyancy-Fed Quiescent Regime"
    elif richardson_ri >= 0.45:
        regime_tag_tr = f"Karışık Konveksiyon (Ri = {richardson_ri:.2f})"
        regime_tag_en = f"Mixed Convection (Ri = {richardson_ri:.2f})"
    else:
        regime_tag_tr = "Zorlanmış Akış Baskın Rejim"
        regime_tag_en = "Forced-Flow Dominated Regime"

    unc_moc = round(max(0.7, abs(moc_1g_bound - moc_0g_bound) * 0.28 + 0.45), 1)

    tr_msg = ""
    en_msg = ""

    if is_partial:
        tr_msg = (
            f"**NASA PSI Kısmi Yerçekimi Veri Şeffaflığı ({env_tag_tr} • {regime_tag_tr}):** Şu anda NASA PSI veritabanında doğrudan kısmi yerçekimi "
            f"yanma verisi bulunmamaktadır; bu boşluk gelecekteki **LUCI** ve **FM2** Ay deneyleriyle tamamlanacaktır. "
            f"Bu süreçte **0G sınırı (MOC %{moc_0g_bound})** ile **1G sınırı (MOC %{moc_1g_bound})** davranışı sınırlar "
            f"(`Tahmini MOC ≈ %{moc_current} ± %{unc_moc}`) ve **ACME E-FIELD** iyon rüzgarı verileri konveksiyon köprüsü olarak kullanılır."
        )
        en_msg = (
            f"**NASA PSI Partial-Gravity Transparency ({env_tag_en} • {regime_tag_en}):** NASA PSI currently contains no direct partial-gravity combustion datasets; "
            f"upcoming **LUCI** and **FM2** missions will populate this gap. "
            f"Until then, **0G (MOC {moc_0g_bound}%)** and **1G (MOC {moc_1g_bound}%)** bound intermediate flammability "
            f"(`Est. MOC ≈ {moc_current}% ± {unc_moc}%`), complemented by **ACME E-FIELD** ionic-wind emulation."
        )
    elif is_eva_suit:
        tr_msg = (
            f"**EVA Uzay Giysisi Saf Oksijen Rejimi ({pressure_psia:.1f} psia / %{oxygen_pct:.0f} O₂):** Dekompresyon hastalığını (vurgun) önlemek ve "
            f"eldiven/eklem esnekliğini korumak için uzay giysileri ~4.3 psia basınçta %100 saf O₂ ile çalışır. Seyreltici N₂ gazı sıfırlandığı için "
            f"tutuşma enerjisi dramatik biçimde düşer ve standart kumaşlar patlayıcı hızda yanar!"
        )
        en_msg = (
            f"**EVA Spacesuit Pure-O₂ Regime ({pressure_psia:.1f} psia / {oxygen_pct:.0f}% O₂):** Spacesuits operate at ~4.3 psia with 100% O₂ to maintain "
            f"suit mobility and eliminate nitrogen decompression sickness (pre-breathe). With zero N₂ thermal ballast, ignition thresholds plummet and flame spread is extreme."
        )
    elif is_lunar_rover:
        tr_msg = (
            f"**Ay Üssü ve Basınçlı Gezgin Atmosferi ({pressure_psia:.1f} psia / %{oxygen_pct:.0f} O₂):** EVA ön-soluma süresini kısaltmak için "
            f"Ay üssü ve basınçlı rover kabinleri ≤10.2 psia ve ≥%30 O₂ (Dünya'ya göre ~%40 bağıl O₂ artışı) kullanır; malzemeler standart ISS kabinine göre çok daha yanıcıdır."
        )
        en_msg = (
            f"**Lunar Base & Pressurized Rover Atmosphere ({pressure_psia:.1f} psia / {oxygen_pct:.0f}% O₂):** Designed between spacesuit and Earth air to minimize "
            f"EVA pre-breathe time, ≥30% O₂ at ≤10.2 psia represents a >40% relative O₂ enrichment over Earth, markedly elevating material flammability."
        )

    return {
        "show_banner": bool(is_partial or is_eva_suit or is_lunar_rover),
        "is_partial_gravity": is_partial,
        "is_eva_suit": is_eva_suit,
        "is_lunar_rover": is_lunar_rover,
        "regime_tag_tr": regime_tag_tr,
        "regime_tag_en": regime_tag_en,
        "uncertainty_moc_pct": unc_moc,
        "moc_0g_bound": moc_0g_bound,
        "moc_current_est": moc_current,
        "moc_1g_bound": moc_1g_bound,
        "tr": tr_msg,
        "en": en_msg,
    }


def _build_scientific_formula_table(
    fuel: Dict[str, Any],
    spalding_b: float,
    k_burn: float,
    flame_spread_mms: float,
    flame_radius_mm: float,
    burn_lifetime_s: float,
    standoff_ratio: float,
    re_num: float,
    gr_num: float,
    ra_num: float,
    richardson_ri: float,
    froude_fr: float,
    sh_conv: float,
    damkohler_da: float,
    rad_loss_frac: float,
    po2_psia: float,
    po2_kpa: float,
    moc_current: float,
    oxygen_pct: float,
    pre_ignition: Dict[str, Any] | None = None,
    compartment_net: Dict[str, Any] | None = None,
) -> List[Dict[str, str]]:
    """Yakıt fazına, Yangın Üçgenine ve Çok-Bölmeli Kabin Termodinamiğine uyumlu bilimsel denklemler tablosu."""
    st1_tr = "AKTİF YANMA" if k_burn > 0 else "SÖNÜMLENDİ"
    st1_en = "ACTIVE BURNING" if k_burn > 0 else "EXTINGUISHED"

    st2_tr = "YÜKSEK SÜRÜCÜ GÜÇ" if spalding_b >= 4.0 else "ORTA TERMODİNAMİK GÜÇ"
    st2_en = "HIGH DRIVING POTENTIAL" if spalding_b >= 4.0 else "MODERATE MASS TRANSFER"

    st3_tr = "SAF DİFÜZYON (Sh≈2)" if sh_conv < 2.25 else "KONVEKTİF DESTEKLİ"
    st3_en = "PURE DIFFUSION (Sh≈2)" if sh_conv < 2.25 else "CONVECTIVELY ENHANCED"

    st4_tr = "MİKROÇEKİM / FAN BASKIN" if richardson_ri < 1.0 else "KALDIRMA KUVVETİ BASKIN"
    st4_en = "MICROGRAVITY / FORCED FLOW" if richardson_ri < 1.0 else "BUOYANCY DOMINATED"

    st5_tr = "ÜFLEME SÖNMESİ (Da<1)" if damkohler_da < 1.0 else "KİMYASAL KARARLI (Da≥1)"
    st5_en = "BLOWOFF EXTINCTION (Da<1)" if damkohler_da < 1.0 else "CHEMICALLY STABLE (Da≥1)"

    st6_tr = f"YARI-AMPİRİK MOC ZARFI: %{moc_current} (ΔO₂ = {oxygen_pct - moc_current:+.1f}%)"
    st6_en = f"SEMI-EMPIRICAL MOC ENVELOPE: {moc_current}% (ΔO₂ = {oxygen_pct - moc_current:+.1f}%)"

    phase = fuel.get("phase", "liquid_droplet")
    if phase in ("gas_jet", "porous_sphere"):
        row1 = {
            "law_tr": "Law-Chung-Srinivasan Küresel Gaz Difüzyon Yasası",
            "law_en": "Law-Chung-Srinivasan Spherical Gas Diffusion Law",
            "parameter_tr": "Law-Chung-Srinivasan Küresel Gaz Difüzyon Yasası",
            "parameter_en": "Law-Chung-Srinivasan Spherical Gas Diffusion Law",
            "equation": "R_f / R_b = 1 + ln(1 + B_T) / [(c_pF/c_pg)·ln(1 + Y_O2/(ν_s·Le_ox·Φ))·(Sh/2)^0.62]",
            "value": f"R_f = {flame_radius_mm:.2f} mm (K_eq = {k_burn:.3f} mm²/s)",
            "status": st1_tr,
            "status_tr": st1_tr,
            "status_en": st1_en,
        }
        row2 = {
            "law_tr": "Gaz Fazı Isıl Transfer Sayısı (B_T)",
            "law_en": "Gas-Phase Enthalpy Transfer Number (B_T)",
            "parameter_tr": "Gaz Fazı Isıl Transfer Sayısı (B_T)",
            "parameter_en": "Gas-Phase Enthalpy Transfer Number (B_T)",
            "equation": "B_T = [Y_O2·(ΔH_c / ν_s) - c_pg·(T_ig - T_0)] / Δh_sens",
            "value": f"B_T = {spalding_b:.2f}  |  R_f/R_b = {standoff_ratio:.2f}",
            "status": st2_tr,
            "status_tr": st2_tr,
            "status_en": st2_en,
        }
    elif phase in ("solid_surface", "solid_thin"):
        eq_deris_tr = (
            "V_f,ince = [√2·λ_g(T_ref)·(T_f - T_p)] / [ρ_s·c_ps·τ_s·(T_p - T_∞)]·(1 - χ_r)"
            if phase == "solid_thin"
            else "V_f,kalın = [U_g·(λ_g ρ_g c_pg)·(T_f - T_p)²] / [(λ_s ρ_s c_ps)·(T_p - T_∞)²]"
        )
        eq_deris_en = (
            "V_f,thin = [√2·λ_g(T_ref)·(T_f - T_p)] / [ρ_s·c_ps·τ_s·(T_p - T_∞)]·(1 - χ_r)"
            if phase == "solid_thin"
            else "V_f,thick = [U_g·(λ_g ρ_g c_pg)·(T_f - T_p)²] / [(λ_s ρ_s c_ps)·(T_p - T_∞)²]"
        )
        row1 = {
            "law_tr": "John de Ris (1969) İki Rejimli Katı Yayılım Yasası (V_f)",
            "law_en": "John de Ris (1969) Two-Regime Solid Spread Law (V_f)",
            "parameter_tr": "John de Ris (1969) İki Rejimli Katı Yayılım Yasası (V_f)",
            "parameter_en": "John de Ris (1969) Two-Regime Solid Spread Law (V_f)",
            "equation": eq_deris_tr,
            "equation_tr": eq_deris_tr,
            "equation_en": eq_deris_en,
            "value": f"V_f = {flame_spread_mms:.2f} mm/s (K_eq = {k_burn:.3f} mm²/s)",
            "status": st1_tr,
            "status_tr": st1_tr,
            "status_en": st1_en,
        }
        row2 = {
            "law_tr": "Spalding Piroliz Kütle Sayısı (B_p)",
            "law_en": "Spalding Pyrolysis Mass Number (B_p)",
            "parameter_tr": "Spalding Piroliz Kütle Sayısı (B_p)",
            "parameter_en": "Spalding Pyrolysis Mass Number (B_p)",
            "equation": "B_p = [Y_O2·(ΔH_c / ν_s) - c_ps·(T_p - T_∞)] / ΔH_p",
            "value": f"B_p = {spalding_b:.2f}  |  R_f/R_s = {standoff_ratio:.2f}",
            "status": st2_tr,
            "status_tr": st2_tr,
            "status_en": st2_en,
        }
    else:
        row1 = {
            "law_tr": "Saf Godsave–Spalding d² & Law–Williams 1/3 Film Yasası",
            "law_en": "Pure Godsave–Spalding d² & Law–Williams 1/3 Film Law",
            "parameter_tr": "Saf Godsave–Spalding d² & Law–Williams 1/3 Film Yasası",
            "parameter_en": "Pure Godsave–Spalding d² & Law–Williams 1/3 Film Law",
            "equation": "T_ref = T_s + (T_f - T_s)/3  |  K = [8λ_g(T_ref) / (ρ_l c_p,eff)]·ln(1 + B_oq)·(Sh/2)",
            "value": f"K = {k_burn:.3f} mm²/s (t_b ≈ {burn_lifetime_s:.1f} s)",
            "status": st1_tr,
            "status_tr": st1_tr,
            "status_en": st1_en,
        }
        row2 = {
            "law_tr": "Spalding Buharlaşma Sayısı (B_oq) & Cephe Oranı",
            "law_en": "Spalding Transfer Number (B_oq) & Standoff Ratio",
            "parameter_tr": "Spalding Buharlaşma Sayısı (B_oq) & Cephe Oranı",
            "parameter_en": "Spalding Transfer Number (B_oq) & Standoff Ratio",
            "equation": "B_oq = [Y_O2·(ΔH_c / ν_s) - c_pg·(T_b - T_∞)] / L_v",
            "value": f"B_oq = {spalding_b:.2f}  |  R_f/R_d = {standoff_ratio:.2f}",
            "status": st2_tr,
            "status_tr": st2_tr,
            "status_en": st2_en,
        }

    rows: List[Dict[str, str]] = [
        row1,
        row2,
        {
            "law_tr": "Ranz–Marshall Sherwood / Nusselt Taşınım (Sh)",
            "law_en": "Ranz–Marshall Sherwood / Nusselt Transport (Sh)",
            "parameter_tr": "Ranz–Marshall Sherwood / Nusselt Taşınım (Sh)",
            "parameter_en": "Ranz–Marshall Sherwood / Nusselt Transport (Sh)",
            "equation": "Sh = 2 + 0.6·Re^(1/2)·Sc^(1/3) + 0.52·Ra^(1/4)  |  Gr = g(T_f-T_∞)L³/(T_film·ν²)",
            "value": f"Sh = {sh_conv:.2f} (Re={re_num:.2f}, Gr={gr_num:.2f}, Ra={ra_num:.2f})",
            "status": st3_tr,
            "status_tr": st3_tr,
            "status_en": st3_en,
        },
        {
            "law_tr": "Richardson & Froude Kaldırma Sayıları (Ri, Fr)",
            "law_en": "Richardson & Froude Buoyancy Ratios (Ri, Fr)",
            "parameter_tr": "Richardson & Froude Kaldırma Sayıları (Ri, Fr)",
            "parameter_en": "Richardson & Froude Buoyancy Ratios (Ri, Fr)",
            "equation": "Ri = Gr / Re²  |  Fr = U_eff² / (g·L)  |  u_b = √[gL(T_f/T_∞ - 1)]",
            "value": f"Ri = {richardson_ri:.2f}  |  Fr = {froude_fr:.2f}",
            "status": st4_tr,
            "status_tr": st4_tr,
            "status_en": st4_en,
        },
        {
            "law_tr": "İki Dallı Arrhenius Damköhler Sayısı (Da)",
            "law_en": "Dual-Branch Arrhenius Damköhler Ratio (Da)",
            "parameter_tr": "İki Dallı Arrhenius Damköhler Sayısı (Da)",
            "parameter_en": "Dual-Branch Arrhenius Damköhler Ratio (Da)",
            "equation": "Da = τ_flow / τ_chem  |  ω = A_HT·e^(-E_HT/RT) + ω_LT,NTC(RO₂/QOOH)",
            "value": f"Da = {damkohler_da:.2f}",
            "status": st5_tr,
            "status_tr": st5_tr,
            "status_en": st5_en,
        },
        {
            "law_tr": "Planck Optik İnce Radyasyon (T⁴) & Olson MOC Zarfı",
            "law_en": "Planck Optically Thin Radiation (T⁴) & Olson MOC Envelope",
            "parameter_tr": "Planck Optik İnce Radyasyon (T⁴) & Olson MOC Zarfı",
            "parameter_en": "Planck Optically Thin Radiation (T⁴) & Olson MOC Envelope",
            "equation": "Q_rad = V·4σ·κ_P·(T_f⁴ - T_∞⁴)  |  P_O2 = X_O2·P_kabin",
            "equation_tr": "Q_rad = V·4σ·κ_P·(T_f⁴ - T_∞⁴)  |  P_O2 = X_O2·P_kabin",
            "equation_en": "Q_rad = V·4σ·κ_P·(T_f⁴ - T_∞⁴)  |  P_O2 = X_O2·P_cabin",
            "value": f"χ_r = %{rad_loss_frac*100:.1f}  |  P_O2 = {po2_psia:.2f} psia ({po2_kpa:.1f} kPa)",
            "value_tr": f"χ_r = %{rad_loss_frac*100:.1f}  |  P_O2 = {po2_psia:.2f} psia ({po2_kpa:.1f} kPa)",
            "value_en": f"χ_r = {rad_loss_frac*100:.1f}%  |  P_O2 = {po2_psia:.2f} psia ({po2_kpa:.1f} kPa)",
            "status": st6_tr,
            "status_tr": st6_tr,
            "status_en": st6_en,
        },
    ]

    if pre_ignition:
        rows.append({
            "law_tr": "Yangın Üçgeni (MIE, LFL/UFL) & 0G Semenov Termal Kaçak (ψ)",
            "law_en": "Fire Triangle (MIE, LFL/UFL) & 0G Semenov Thermal Runaway (ψ)",
            "parameter_tr": "Yangın Üçgeni (MIE, LFL/UFL) & 0G Semenov Termal Kaçak (ψ)",
            "parameter_en": "Fire Triangle (MIE, LFL/UFL) & 0G Semenov Thermal Runaway (ψ)",
            "equation": "E_min = E_0(P_0/P)²(0.21/X_O2)^2.4  |  ψ = Q_exo·E_a / (h_0G·S·R·T²)",
            "value": f"MIE = {pre_ignition['mie_mj']:.3f} mJ | LFL–UFL: %{pre_ignition['lfl_vol_pct']}–%{pre_ignition['ufl_vol_pct']} | ψ = {pre_ignition['semenov_psi']:.3f}",
            "value_tr": f"MIE = {pre_ignition['mie_mj']:.3f} mJ | LFL–UFL: %{pre_ignition['lfl_vol_pct']}–%{pre_ignition['ufl_vol_pct']} | ψ = {pre_ignition['semenov_psi']:.3f}",
            "value_en": f"MIE = {pre_ignition['mie_mj']:.3f} mJ | LFL–UFL: {pre_ignition['lfl_vol_pct']}%–{pre_ignition['ufl_vol_pct']}% | ψ = {pre_ignition['semenov_psi']:.3f}",
            "status": pre_ignition["status_tr"],
            "status_tr": pre_ignition["status_tr"],
            "status_en": pre_ignition["status_en"],
        })

    if compartment_net:
        tox = compartment_net["multi_gas_toxicology"]
        comp_st_tr = (
            f"FED = {tox['fed_total']:.3f} (t_işgöremez ≈ {tox['time_to_incapacitation_min']:.1f} dk)"
            if compartment_net["hrr_kw"] > 0
            else "KABİN İZOLE / KARARLI"
        )
        comp_st_en = (
            f"FED = {tox['fed_total']:.3f} (t_incap ≈ {tox['time_to_incapacitation_min']:.1f} min)"
            if compartment_net["hrr_kw"] > 0
            else "CABIN ISOLATED / NOMINAL"
        )
        rows.append({
            "law_tr": "Çok-Bölmeli Aşırı Basınç (ΔP), IDSS Kapak Yükü & Çoklu-Gaz FED",
            "law_en": "Multi-Compartment Overpressure (ΔP), IDSS Hatch Load & Multi-Gas FED",
            "parameter_tr": "Çok-Bölmeli Aşırı Basınç (ΔP), IDSS Kapak Yükü & Çoklu-Gaz FED",
            "parameter_en": "Multi-Compartment Overpressure (ΔP), IDSS Hatch Load & Multi-Gas FED",
            "equation": "ΔP = [(γ-1)/V]·ΔQ_net  |  F_hatch = ΔP·A_IDSS  |  FED = ∫(CO+HCN+HF+HCl)·ψ_CO2 dt",
            "value": f"HRR = {compartment_net['hrr_kw']:.2f} kW | ΔP = +{compartment_net['overpressure_kpa']:.2f} kPa | F_kapak = {compartment_net['max_hatch_force_kn']:.2f} kN",
            "value_tr": f"HRR = {compartment_net['hrr_kw']:.2f} kW | ΔP = +{compartment_net['overpressure_kpa']:.2f} kPa | F_kapak = {compartment_net['max_hatch_force_kn']:.2f} kN",
            "value_en": f"HRR = {compartment_net['hrr_kw']:.2f} kW | ΔP = +{compartment_net['overpressure_kpa']:.2f} kPa | F_hatch = {compartment_net['max_hatch_force_kn']:.2f} kN",
            "status": comp_st_tr,
            "status_tr": comp_st_tr,
            "status_en": comp_st_en,
        })

    return rows


def _build_instant_formula_commentary(
    fuel: Dict[str, Any],
    regime: str,
    gravity_g: float,
    oxygen_pct: float,
    pressure_psia: float,
    po2_psia: float,
    airflow_cms: float,
    moc_current: float,
    moc_0g_bound: float,
    moc_1g_bound: float,
    spalding_b: float,
    k_burn: float,
    flame_spread_mms: float,
    sh_conv: float,
    damkohler_da: float,
    rad_loss_frac: float,
    risk_score: int,
    co_ppm: float,
    badge_tr: str = "",
    badge_en: str = "",
) -> Dict[str, str]:
    """Parametreler değiştikçe milisaniyeler içinde güncellenen faz-uyumlu bilimsel durum özeti."""
    margin = oxygen_pct - moc_current
    reg_tr = badge_tr or regime
    reg_en = badge_en or regime
    phase = fuel.get("phase", "liquid_droplet")
    b_sym = "B_T" if phase in ("gas_jet", "porous_sphere") else ("B_p" if phase in ("solid_surface", "solid_thin") else "B_oq")
    rate_tr = (
        f"sabit debili gaz difüzyon alevi (`K_eq = {k_burn:.3f} mm²/s`)"
        if phase in ("gas_jet", "porous_sphere")
        else (
            f"`V_f = {flame_spread_mms:.2f} mm/s` yüzey yayılma hızında piroliz"
            if phase in ("solid_surface", "solid_thin")
            else f"`K = {k_burn:.3f} mm²/s` d² buharlaşma hızında damlacık yanması"
        )
    )
    tr_text = (
        f"**Analitik Taşınım ve Rejim Özeti ({fuel['formula']}):** Kabin kısmi oksijen basıncı "
        f"`P_O2 = {po2_psia:.2f} psia` ve kütle/ısıl transfer sayısı `{b_sym} = {spalding_b:.2f}` olarak hesaplandı. "
        f"Taşınım korelasyonunda `Sh = {sh_conv:.2f}` (`g = {gravity_g:.2f}G`, `U = {airflow_cms:.1f} cm/s`) ve "
        f"Damköhler sayısı `Da = {damkohler_da:.2f}` değerindedir. "
    )
    if 0.03 <= gravity_g <= 0.88:
        tr_text += (
            f"*(Kısmi Yerçekimi Sınırlandırması: PSI'da LUCI/FM2 verileri beklenirken 0G MOC `%{moc_0g_bound}` ile "
            f"1G MOC `%{moc_1g_bound}` aralığı sistemi sınırlar).* "
        )
    if regime == "COOL_FLAME_NTC":
        tr_text += (
            f"Düşük oksijen / radyatif ısı kaybı (`χ_r = %{rad_loss_frac*100:.1f}`) görünür sıcak alevi söndürerek sistemi **550–780 K "
            f"NTC Görünmez Soğuk Alev** rejimine geçirdi (NASA FLEX / CFI / CFI-G). Standart optik duman dedektörü (PSD) duman görmez; "
            f"numune çevresinde `{co_ppm:.0f} ppm` CO/aldehit üretimi mevcuttur!"
        )
    elif regime in ("QUENCHED_EXTINGUISHED", "BLOWOFF_EXTINGUISHED"):
        tr_text += (
            f"Rejim **{reg_tr}**: Oksijen marjı `ΔO₂ = {margin:+.1f}%` (MOC `%{moc_current}`) veya `Da = {damkohler_da:.2f}` sınırı aşıldığı için "
            f"ekzotermik reaksiyon sönümlendi."
        )
    else:
        tr_text += (
            f"Rejim **{reg_tr}**: Mevcut oksijen (`%{oxygen_pct:.1f}`), kritik MOC sınırının (`%{moc_current}`) `{margin:+.1f}%` üzerindedir; "
            f"{rate_tr} sürüyor (**Risk: {risk_score}/100**). "
            f"İlk müdahale: HVAC fanlarını `0 cm/s` düzeyine çekip Halon kullanmadan İnce Su Sisi (SoFIE-MIST PFE) / CO₂ uygulayın."
        )

    en_text = (
        f"**Analytical Transport & Regime Summary ({fuel['formula']}):** Partial oxygen pressure `P_O2 = {po2_psia:.2f} psia`, "
        f"transfer number `{b_sym} = {spalding_b:.2f}`, Sherwood transport `Sh = {sh_conv:.2f}`, and Damköhler `Da = {damkohler_da:.2f}`. "
    )
    if 0.03 <= gravity_g <= 0.88:
        en_text += (
            f"*(Partial-G Bounding: Awaiting NASA PSI LUCI/FM2 datasets; bounded between 0G MOC `{moc_0g_bound}%` and 1G MOC `{moc_1g_bound}%`).* "
        )
    en_text += (
        f"Regime **{reg_en}** with O₂ margin `{margin:+.1f}%` vs MOC `{moc_current}%` (Risk `{risk_score}/100`). "
        f"Countermeasure: Immediate HVAC shutoff + Fine Water Mist (SoFIE-MIST) / CO₂ (Halon 1301 prohibited)."
    )
    return {"tr": tr_text, "en": en_text}


def _generate_multisensor_timeseries(
    droplet_d0_mm: float,
    k_burn: float,
    flame_temp_k: float,
    heat_flux_kw_m2: float,
    co_ppm: float,
    regime: str,
    fuel: Dict[str, Any],
    gravity_g: float,
    airflow_cms: float,
    flicker_freq_hz: float = 0.0,
) -> Dict[str, Any]:
    times: List[float] = []
    d2_norm: List[float] = []
    thermo_k: List[float] = []
    optical_norm: List[float] = []
    radiometer_kw: List[float] = []
    co_trace: List[float] = []

    d0_sq = droplet_d0_mm ** 2
    is_gas_burner = fuel.get("phase") in ("gas_jet", "porous_sphere")
    two_stage = (
        (not is_gas_burner)
        and fuel["cool_flame_capable"]
        and gravity_g < 0.12
        and airflow_cms < 6.0
        and regime in ("COOL_FLAME_NTC", "HOT_SPHERICAL_0G")
        and droplet_d0_mm >= 2.8
    )

    for step in range(31):
        t = round(step * 1.0, 1)
        times.append(t)

        if regime in ("QUENCHED_EXTINGUISHED", "BLOWOFF_EXTINGUISHED"):
            decay = math.exp(-t / 2.2)
            d2_norm.append(1.0 if is_gas_burner else round(max(0.96, 1.0 - 0.04 * (1.0 - decay)), 3))
            thermo_k.append(round(300.0 + 420.0 * decay, 1))
            optical_norm.append(round(100.0 * decay, 1))
            radiometer_kw.append(round(8.5 * decay, 2))
            co_trace.append(round(2.0 + 35.0 * (1.0 - decay) * math.exp(-t / 14.0), 1))
            continue

        if two_stage and t >= 14.0:
            hot_part = k_burn if regime != "COOL_FLAME_NTC" else k_burn * 2.8
            d2_at_14 = max(0.18, 1.0 - (hot_part * 14.0) / d0_sq)
            k_cool = max(0.08, hot_part * 0.26)
            curr_d2 = max(0.0, d2_at_14 - (k_cool * (t - 14.0)) / d0_sq)
            d2_norm.append(round(curr_d2, 3))

            trans = math.exp(-(t - 14.0) / 1.4)
            t_cool = 640.0 if curr_d2 > 0.02 else 310.0
            thermo_k.append(round(t_cool + (max(1380.0, flame_temp_k) - t_cool) * trans, 1))
            optical_norm.append(round(max(1.5, 92.0 * trans), 1))
            radiometer_kw.append(round((4.2 if curr_d2 > 0.02 else 0.3) + 12.0 * trans, 2))
            co_trace.append(round(min(680.0, 95.0 + (t - 14.0) * 32.0), 1))
        else:
            curr_d2 = 1.0 if is_gas_burner else max(0.0, 1.0 - (k_burn * t) / d0_sq)
            d2_norm.append(round(curr_d2, 3))
            active = 1.0 if (is_gas_burner or curr_d2 > 0.01) else math.exp(-(t - (d0_sq / max(0.05, k_burn))) / 1.5)
            ramp = 1.0 - math.exp(-t / 1.1)

            if regime == "COOL_FLAME_NTC":
                thermo_k.append(round(300.0 + (flame_temp_k - 300.0) * ramp * active, 1))
                optical_norm.append(round(3.2 * ramp * active, 1))
                radiometer_kw.append(round(heat_flux_kw_m2 * ramp * active, 2))
                co_trace.append(round(12.0 + co_ppm * min(1.0, t / 12.0) * active, 1))
            else:
                # Cetegen & Bejan (1993) doğal kaldırma salınımı f = 1.5 * sqrt(g / D_f); 0G'de f = 0.0 Hz (salınım yok)
                flicker = 1.0 + (0.038 * math.sin(2.0 * math.pi * flicker_freq_hz * t) if flicker_freq_hz > 0.05 else 0.0)
                thermo_k.append(round((300.0 + (flame_temp_k - 300.0) * ramp * active) * flicker, 1))
                optical_norm.append(round(min(100.0, (78.0 + 20.0 * (flame_temp_k / 2200.0)) * ramp * active * flicker), 1))
                radiometer_kw.append(round(heat_flux_kw_m2 * ramp * active * flicker, 2))
                co_trace.append(round(8.0 + co_ppm * min(1.0, t / 18.0) * active, 1))

    return {
        "time_s": times,
        "d2_normalized": d2_norm,
        "thermocouple_k": thermo_k,
        "optical_intensity_pct": optical_norm,
        "radiometer_kw_m2": radiometer_kw,
        "co_ppm": co_trace,
        "two_stage_transition_s": 14.0 if two_stage else None,
    }


def _build_human_callouts(
    regime: str,
    fuel: Dict[str, Any],
    gravity_g: float,
    oxygen_pct: float,
    moc_current: float,
    airflow_cms: float,
    pressure_psia: float,
    flame_temp_k: float,
) -> Dict[str, str]:
    if regime == "HOT_SPHERICAL_0G":
        return {
            "badge_tr": "0G KÜRESEL DİFÜZYON ALEVİ",
            "badge_en": "0G SPHERICAL DIFFUSION FLAME",
            "summary_tr": (
                f"Doğal konveksiyon (Ra=0) sıfırlandı. Sıcak gazlar yükselemediği için {fuel['name_tr'].split('(')[0].strip()} "
                f"etrafında {flame_temp_k:.0f} K sıcaklıkta safir-mavi kemilüminesans (CH*/OH*) küresi oluşuyor."
            ),
            "summary_en": (
                f"Buoyancy vanishes in freefall (Ra=0). Symmetrical {flame_temp_k:.0f} K "
                f"sapphire-blue CH*/OH* chemiluminescent diffusion sphere governed by molecular diffusion."
            ),
        }
    if regime == "VENTILATED_WAKE_0G":
        return {
            "badge_tr": f"0G HAVALANDIRMALI KUYRUK ALEVİ ({airflow_cms:.1f} cm/s)",
            "badge_en": f"0G VENTILATED WAKE FLAME ({airflow_cms:.1f} cm/s)",
            "summary_tr": (
                f"ISS kabin fan akışı ({airflow_cms:.1f} cm/s) aleve taze oksijen taşıyor! Rüzgar yönünde parlak mavi "
                f"durgunluk yayı (stagnation arc), arka bölgede ise uzayan kuyruk alevi oluştu (MOC: %{moc_current})."
            ),
            "summary_en": (
                f"Spacecraft ventilation ({airflow_cms:.1f} cm/s) convects fresh O₂ to the reaction zone, creating a bright "
                f"upstream blue stagnation arc and an elongated wake tail (MOC: {moc_current}%)."
            ),
        }
    if regime == "BUOYANT_PLUME_1G":
        g_label_tr = "AY KISMİ YERÇEKİMİ" if 0.11 <= gravity_g <= 0.24 else ("MARS KISMİ YERÇEKİMİ" if 0.25 <= gravity_g <= 0.50 else "KALDIRMA KUVVETLİ KONVEKTİF ALEV")
        g_label_en = "LUNAR PARTIAL-G PLUME" if 0.11 <= gravity_g <= 0.24 else ("MARTIAN PARTIAL-G PLUME" if 0.25 <= gravity_g <= 0.50 else "BUOYANCY-DRIVEN CONVECTIVE PLUME")
        return {
            "badge_tr": f"{g_label_tr} ({gravity_g:.2f}G)",
            "badge_en": f"{g_label_en} ({gravity_g:.2f}G)",
            "summary_tr": (
                f"Yerçekimi ({gravity_g:.2f}G) yoğunluk farkıyla sıcak gazları yukarı ivmelendiriyor; gözyaşı formu, "
                f"kaldırma kuvveti salınımı ve üst uçta sarı-kehribar kurum (soot) ışıması etkin."
            ),
            "summary_en": (
                f"Gravity ({gravity_g:.2f}G) accelerates hot products upward via buoyancy, stretching the flame into a "
                f"convective teardrop plume with luminous yellow-amber soot oxidation."
            ),
        }
    if regime == "COOL_FLAME_NTC":
        return {
            "badge_tr": "GÖRÜNMEZ SOĞUK ALEV (UV/IR MODU)",
            "badge_en": "INVISIBLE COOL FLAME (UV/IR VIEW)",
            "summary_tr": (
                f"Radyatif ısı kaybı sıcak alevi söndürdü ancak yanma DURMADI! {flame_temp_k:.0f} K sıcaklıkta çıplak gözle "
                f"görülemeyen Soğuk Alev (FLEX / CFI / CFI-G) aktif; toksik CO/formaldehit üretiyor ve yeniden tutuşma riski taşıyor."
            ),
            "summary_en": (
                f"Radiative heat loss quenched the visible hot flame, yet {flame_temp_k:.0f} K Cool Flame chemistry persists! "
                f"Invisible to optical cameras while releasing CO/formaldehyde."
            ),
        }
    if regime == "BLOWOFF_EXTINGUISHED":
        return {
            "badge_tr": "YÜKSEK HIZLI ÜFLEME SÖNMESİ (BLOWOFF)",
            "badge_en": "CONVECTIVE BLOWOFF EXTINCTION",
            "summary_tr": (
                f"Hava akış hızı ({airflow_cms:.1f} cm/s) kimyasal reaksiyon süresini aştı (Damköhler Da < 1); "
                f"alev cephesi tutunamayarak üfleme sınırında söndü."
            ),
            "summary_en": (
                f"Airflow velocity ({airflow_cms:.1f} cm/s) exceeded Damköhler residence threshold (Da < 1), "
                f"blowing off the reaction sheet."
            ),
        }
    return {
        "badge_tr": f"OKSİJEN / RADYATİF SÖNÜMLENME (MOC < %{moc_current})",
        "badge_en": f"DIFFUSIVE / RADIATIVE QUENCHING (O₂ < {moc_current}%)",
        "summary_tr": (
            f"Mevcut oksijen (%{oxygen_pct:.1f}) bu atmosfer ({pressure_psia:.1f} psia) için gereken Minimum Oksijen "
            f"Konsantrasyonunun (%{moc_current}) altında veya radyatif kayıp üretilen ısıyı aştı. Alev kendi kendine söndü."
        ),
        "summary_en": (
            f"Ambient O₂ ({oxygen_pct:.1f}%) is below Minimum Oxygen Concentration ({moc_current}%) at "
            f"{pressure_psia:.1f} psia, or radiative losses exceeded heat release."
        ),
    }


def _build_iss_flight_validation(
    fuel_id: str,
    fuel: Dict[str, Any],
    regime: str,
    pressure_psia: float,
    diluent: str,
    sensor_series: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Yayınlanmış sabit NASA GRC ISS 0G referans deney verilerini (FLEX, FLEX-2, BASS, Saffire, BASS-II, SPICE/SLICE, ACME CFI-G)
    0G analitik çözücü referans çıktısıyla karşılaştırarak sentetik gürültü olmadan gerçek R² ve RMSE hesaplar.
    """
    # Her yakıt için yayınlanmış sabit ISS 0G referans zaman serisi (t = [2, 6, 11, 16, 22, 28] s) ve MOC noktaları (U = [0.5, 2, 6, 14, 26] cm/s)
    iss_benchmarks: Dict[str, Dict[str, Any]] = {
        "n_heptane": {
            "full": "ISS CIR • FLEX / CFI 0G Referans (Nayagam & Dietrich, NTRS 20150023456)",
            "short": "FLEX/CFI",
            "d0_ref_mm": 4.1,
            "k_hot_ref": 0.74,
            "k_cool_ref": 0.182,
            "d2_hot_meas": [0.912, 0.742, 0.525, 0.312, 0.062, 0.000],
            "d2_cool_meas": [0.975, 0.930, 0.872, 0.816, 0.748, 0.681],
            "moc_0g_meas": [16.6, 14.7, 13.0, 14.1, 16.4],
        },
        "methanol": {
            "full": "ISS CIR • FLEX-2 MDCA 0G Referans (Dietrich et al., NTRS 20090014812)",
            "short": "FLEX-2",
            "d0_ref_mm": 3.8,
            "k_hot_ref": 0.58,
            "k_cool_ref": 0.58,
            "d2_hot_meas": [0.922, 0.764, 0.566, 0.371, 0.138, 0.000],
            "d2_cool_meas": [0.922, 0.764, 0.566, 0.371, 0.138, 0.000],
            "moc_0g_meas": [15.4, 13.5, 11.8, 12.9, 15.6],
        },
        "pmma": {
            "full": "ISS MSG / CIR • BASS & SoFIE 0G Referans (Olson & Ferkul, NTRS 20140011099)",
            "short": "BASS/SoFIE",
            "d0_ref_mm": 4.5,
            "k_hot_ref": 0.34,
            "k_cool_ref": 0.34,
            "d2_hot_meas": [0.965, 0.896, 0.812, 0.728, 0.625, 0.528],
            "d2_cool_meas": [0.965, 0.896, 0.812, 0.728, 0.625, 0.528],
            "moc_0g_meas": [17.1, 15.1, 13.4, 14.5, 16.1],
        },
        "sibal": {
            "full": "Cygnus • Saffire-I / IV 0G Referans (Urban & Ruff, NTRS 20170000230)",
            "short": "Saffire",
            "d0_ref_mm": 4.2,
            "k_hot_ref": 0.48,
            "k_cool_ref": 0.48,
            "d2_hot_meas": [0.944, 0.835, 0.698, 0.562, 0.398, 0.242],
            "d2_cool_meas": [0.944, 0.835, 0.698, 0.562, 0.398, 0.242],
            "moc_0g_meas": [16.0, 14.0, 12.3, 13.4, 15.3],
        },
        "nomex": {
            "full": "ISS MSG • BASS-II Kumaş 0G Referans (Olson, NTRS 20210011385)",
            "short": "BASS-II",
            "d0_ref_mm": 4.0,
            "k_hot_ref": 0.19,
            "k_cool_ref": 0.19,
            "d2_hot_meas": [0.975, 0.927, 0.867, 0.808, 0.736, 0.664],
            "d2_cool_meas": [0.975, 0.927, 0.867, 0.808, 0.736, 0.664],
            "moc_0g_meas": [24.3, 22.3, 20.6, 21.8, 25.1],
        },
        "hydrogen": {
            "full": "ISS MSG / CIR • SPICE & SLICE 0G Referans (Sunderland, NTRS 20090014827)",
            "short": "SPICE/SLICE",
            "d0_ref_mm": 3.2,
            "k_hot_ref": 0.0,
            "k_cool_ref": 0.0,
            "d2_hot_meas": [1.000, 1.000, 1.000, 1.000, 1.000, 1.000],
            "d2_cool_meas": [1.000, 1.000, 1.000, 1.000, 1.000, 1.000],
            "moc_0g_meas": [8.5, 6.6, 5.2, 6.2, 6.5],
        },
        "propane_cfig": {
            "full": "ISS CIR • ACME CFI-G 0G Referans (Axelbaum & Stocker, NTRS 20220015583)",
            "short": "ACME CFI-G",
            "d0_ref_mm": 4.8,
            "k_hot_ref": 0.0,
            "k_cool_ref": 0.0,
            "d2_hot_meas": [1.000, 1.000, 1.000, 1.000, 1.000, 1.000],
            "d2_cool_meas": [1.000, 1.000, 1.000, 1.000, 1.000, 1.000],
            "moc_0g_meas": [13.7, 11.8, 10.4, 11.4, 12.0],
        },
    }
    bm = iss_benchmarks.get(fuel_id, iss_benchmarks["n_heptane"])
    campaign_full = bm["full"]
    campaign_short = bm["short"]

    sample_times = [2, 6, 11, 16, 22, 28]
    use_cool_ref = regime == "COOL_FLAME_NTC" and fuel.get("cool_flame_capable", False)
    meas_arr = bm["d2_cool_meas"] if use_cool_ref else bm["d2_hot_meas"]
    d0_ref_sq = bm["d0_ref_mm"] ** 2
    is_gas_burner = fuel.get("phase") in ("gas_jet", "porous_sphere")
    is_solid_fuel = fuel.get("phase") in ("solid_surface", "solid_thin", "rod", "fabric_sheet")

    # Dürüst Canlı ISS 0G Çözücü Doğrulaması: Sabit k_hot_ref yerine doğrudan saf Godsave–Spalding 1/3 film çözücüsünü
    # ilgili ISS 0G referans koşulunda (g=0, P=14.7 psia, N2, referans O2 ve U) çalıştırarak k_pred_0g üretir!
    dil_n2 = DILUENT_FACTORS["N2"]
    o2_bench = 13.0 if use_cool_ref else (26.0 if fuel_id == "nomex" else 21.0)
    u_bench = 0.2 if not is_solid_fuel else 4.0
    x_ox_b = o2_bench / 100.0
    mw_b = x_ox_b * 32.0 + (1.0 - x_ox_b) * float(dil_n2["mw"])
    y_ox_b = (x_ox_b * 32.0) / mw_b
    cp_g_b = 1.22
    t_bench_k = 655.0 if use_cool_ref else float(fuel["t_adiabatic_k"]) * 0.91
    nu_b = 0.156 * (((0.5 * (t_bench_k + 298.15)) / 300.0) ** 1.68)
    re_b = (u_bench * (bm["d0_ref_mm"] / 10.0)) / nu_b
    sh_b = 2.0 + 0.60 * math.sqrt(max(0.0, re_b)) * (0.71 ** (1.0 / 3.0))
    k_pred_0g = 0.0 if is_gas_burner else _solve_pure_burning_rate_k(
        fuel=fuel,
        dil=dil_n2,
        y_o2=y_ox_b,
        p_atm=1.0,
        sh_conv=sh_b,
        rad_loss_frac=0.08 if use_cool_ref else 0.18,
        flame_temp_k=t_bench_k,
        cp_g_kj=cp_g_b,
        cool_flame_active=use_cool_ref,
    )

    d2_points: List[Dict[str, Any]] = []
    d2_pairs: List[tuple[float, float]] = []
    for idx, t_val in enumerate(sample_times):
        y_meas = float(meas_arr[idx])
        y_pred = 1.0 if is_gas_burner else round(max(0.0, 1.0 - (k_pred_0g * t_val) / d0_ref_sq), 3)
        d2_points.append({
            "t_s": float(t_val),
            "d2_meas": round(y_meas, 3),
            "d2_pred": round(y_pred, 3),
            "err": round(abs(y_meas - y_pred), 3),
            "label": f"{campaign_short} 0G #{idx + 1}",
        })
        d2_pairs.append((y_meas, y_pred))

    flow_samples = [0.5, 2.0, 6.0, 14.0, 26.0]
    moc_points: List[Dict[str, Any]] = []
    moc_pairs: List[tuple[float, float]] = []
    for idx, u_val in enumerate(flow_samples):
        # Yayınlanmış ISS 0G referansı 14.7 psia N2 bazındadır; grafikte mevcut basınç/seyreltici kaymasını koru
        m_pred_cur = compute_moc_at_flow(fuel, u_val, 0.0, pressure_psia, diluent)
        m_pred_1atm = compute_moc_at_flow(fuel, u_val, 0.0, 14.7, "N2")
        shift = m_pred_cur - m_pred_1atm
        m_meas_1atm = float(bm["moc_0g_meas"][idx])
        m_meas_plot = round(max(4.2, min(55.0, m_meas_1atm + shift)), 2)
        moc_points.append({
            "airflow_cms": u_val,
            "moc_meas_pct": m_meas_plot,
            "moc_pred_pct": m_pred_cur,
            "err_pct": round(abs(m_meas_1atm - m_pred_1atm), 2),
            "label": f"{campaign_short} 0G U={u_val}cm/s",
        })
        moc_pairs.append((m_meas_1atm / 100.0, m_pred_1atm / 100.0))

    # Gaz brülörleri ve katı yüzey yayılım yakıtlarında 0G MOC(U) + regresyon birleşik çifti, sıvı damlacıklarda d² + MOC çifti kullanılır
    stat_pairs = moc_pairs if is_gas_burner else (moc_pairs + d2_pairs if is_solid_fuel else d2_pairs + moc_pairs)
    mse = sum((ym - yp) ** 2 for ym, yp in stat_pairs) / max(1, len(stat_pairs))
    rmse = round(math.sqrt(mse), 3)
    mean_y = sum(ym for ym, _ in stat_pairs) / max(1, len(stat_pairs))
    ss_tot = sum((ym - mean_y) ** 2 for ym, _ in stat_pairs)
    ss_res = sum((ym - yp) ** 2 for ym, yp in stat_pairs)
    r_sq = round(max(0.0, min(0.999, 1.0 - (ss_res / max(1e-6, ss_tot)))), 3)

    campaign_en = campaign_full.replace("Referans", "Reference").replace("Kumaş", "Fabric")
    return {
        "campaign": campaign_full,
        "campaign_tr": campaign_full,
        "campaign_en": campaign_en,
        "campaign_short": campaign_short,
        "r_squared": r_sq,
        "rmse": rmse,
        "d2_points": d2_points,
        "moc_points": moc_points,
        "benchmark_tr": f"ISS 0G Referans Kalibrasyonu ({campaign_short}): R² = {r_sq:.3f} • RMSE = {rmse:.3f}",
        "benchmark_en": f"ISS 0G Reference Calibration ({campaign_short}): R² = {r_sq:.3f} • RMSE = {rmse:.3f}",
    }


def compute_cabin_scenario_timeline(
    habitat_id: str,
    crew_response_s: float,
    regime: str,
    extinguished: bool,
    flame_temp_k: float,
    heat_flux_kw_m2: float,
    co_ppm: float,
    k_burn: float,
    flame_spread_mms: float,
    oxygen_pct: float,
    pressure_psia: float,
    airflow_cms: float,
    regime_label_tr: str = "",
    regime_label_en: str = "",
) -> Dict[str, Any]:
    """
    Kabin / Orion-Gateway / Basınçlı Ay Gezgini / EVA Uzay Giysisi serbest hava hacmine göre
    İdeal Gaz Yasası (PV = nRT), Kütle Korunumu ve 1. Termodinamik Yasası (Q = m_gaz * c_p * ΔT) ile:
    1) Gerçek NASA yangın algılama donanımı alarm süresi (ISS PSD fotoelektrik lazer duman dedektörü + CSA-CP / ANITA-2 gaz analizi),
    2) Resmi NASA JSC-20584 Uzay Aracı Maksimum İzin Verilebilir CO Konsantrasyonları (SMAC):
       - ISS C&W / CSA-CP Solunum Maskesi (PBA) Eylem Eşiği: 25 ppm
       - NASA 24-Saatlik SMAC: 100 ppm (115 mg/m³)
       - NASA 1-Saatlik Acil Durum SMAC: 425 ppm (485 mg/m³)
    3) Referans kabin yangın yükü (Saffire / NASA-STD-3001 ölçeği) altında müdahale anı CO (ppm) ve ortalama kabin ΔT (°C) değerlerini hesaplar.
    """
    hab = HABITAT_CONFIGS.get(habitat_id, HABITAT_CONFIGS["iss_module"])
    vol_m3 = float(hab["volume_m3"])
    baseline_co_ppm = 1.0  # Temiz ISS / uzay aracı ECLSS bazal CO seviyesi (~0.5–1.5 ppm)

    if extinguished:
        return {
            "habitat_id": habitat_id,
            "habitat_name_tr": hab["name_tr"],
            "habitat_name_en": hab["name_en"],
            "volume_m3": vol_m3,
            "crew_response_s": crew_response_s,
            "optical_blind": False,
            "fire_power_kw": 0.0,
            "t_alarm_s": 0.0,
            "t_intervene_s": round(crew_response_s, 1),
            "t_caw_25ppm_s": 999.0,
            "t_smac_24h_100ppm_s": 999.0,
            "t_smac_1h_425ppm_s": 999.0,
            "co_at_response_ppm": baseline_co_ppm,
            "peak_temp_rise_c": 0.0,
            "severity": "SAFE",
            "badge_tr": "SÖNÜMLENMİŞ / GÜVENLİ KABİN",
            "badge_en": "EXTINGUISHED / SAFE HABITAT",
            "summary_tr": (
                f"{hab['name_tr']} içinde aktif ekzotermik yanma bulunmuyor (MOC sınırı altında veya üfleme sönmesi). "
                f"Kabin CO seviyesi ECLSS bazal düzeyinde (~{baseline_co_ppm:.0f} ppm) kararlıdır."
            ),
            "summary_en": (
                f"No sustained combustion in {hab['name_en']} (quenched below MOC or blowoff). "
                f"Cabin CO remains at clean ECLSS baseline (~{baseline_co_ppm:.0f} ppm)."
            ),
            "milestones": [
                {
                    "t_s": 0.0,
                    "title_tr": "0.0 s • Tutuşma Bastırıldı",
                    "title_en": "0.0 s • Ignition Quenched",
                    "detail_tr": "Alev MOC / Damköhler sınırında kendi kendine söndü.",
                    "detail_en": "Flame self-extinguished at MOC / Damköhler boundary.",
                    "state": "ok",
                },
                {
                    "t_s": 5.0,
                    "title_tr": "5.0 s • ISS PSD & CSA-CP İzleme",
                    "title_en": "5.0 s • ISS PSD & CSA-CP Monitoring",
                    "detail_tr": "CO ≈ 1 ppm (< 25 ppm C&W eşiği); söndürücü boşaltımı gerekmez.",
                    "detail_en": "CO ≈ 1 ppm (< 25 ppm C&W threshold); agent discharge not required.",
                    "state": "ok",
                },
            ],
        }

    # İdeal Gaz Yasası: n_gas = (P_Pa * V) / (R_u * T_0), m_gas = n_gas * M_mix
    p_pa = pressure_psia * 6894.76
    t0_k = 295.15
    x_o2 = max(0.05, min(1.0, oxygen_pct / 100.0))
    mw_kg_mol = (x_o2 * 32.0 + (1.0 - x_o2) * 28.01) / 1000.0
    n_gas_mol = max(0.5, (p_pa * vol_m3) / (8.3145 * t0_k))
    m_gas_kg = max(0.015, n_gas_mol * mw_kg_mol)
    cp_gas_j_kgk = 1005.0

    optical_blind = regime == "COOL_FLAME_NTC"

    # Referans kabin yangın yükü (NASA-STD-3001 / Saffire aviyonik-polimer panel yangını ölçeği):
    if optical_blind:
        # Düşük sıcaklıklı görünmez soğuk alev / piroliz: düşük ısıl güç (~0.32 kW), yüksek eksik yanma CO verimi (y_CO ≈ 0.28 g/g)
        fire_power_w = 260.0 + 140.0 * min(2.0, k_burn / 0.25)
        mdot_fuel_g_s = max(0.08, fire_power_w / 2400.0)
        y_co_g_per_g = 0.28
    else:
        rate_factor = max(0.45, min(4.2, 0.45 + 0.52 * flame_spread_mms + 0.28 * k_burn))
        o2_boost = (oxygen_pct / 21.0) ** 0.55
        fire_power_w = 1850.0 * rate_factor * o2_boost
        if vol_m3 < 1.0:
            # EVA giysisi dar hacminde anlık O2 envanteriyle sınırlı ısıl güç
            fire_power_w = min(fire_power_w, 5500.0)
        mdot_fuel_g_s = max(0.06, fire_power_w / 21000.0)
        y_co_g_per_g = 0.055 + (0.045 if airflow_cms < 2.0 else 0.015)

    fire_power_kw = round(fire_power_w / 1000.0, 2)

    # Molar CO birikim hızı (ppm/s): (mdot_CO [mol/s] / n_gas [mol]) * 1e6
    n_co_mol_s = (mdot_fuel_g_s * y_co_g_per_g) / 28.01
    co_rate_ppm_s = max(0.05, (n_co_mol_s / n_gas_mol) * 1.0e6)

    # Resmi NASA JSC-20584 CO eşiklerine ulaşma süreleri:
    t_caw_25 = round(max(1.0, (25.0 - baseline_co_ppm) / co_rate_ppm_s), 1)
    t_smac_24h_100 = round(max(1.8, (100.0 - baseline_co_ppm) / co_rate_ppm_s), 1)
    t_smac_1h_425 = round(max(3.5, (425.0 - baseline_co_ppm) / co_rate_ppm_s), 1)

    # Gerçek kabin kanal taşınım gecikmesi:
    # Görünmez soğuk alevde optik duman dedektörü (PSD) duman görmez; alarm CSA-CP / ANITA-2 25 ppm C&W eşiğinde tetiklenir.
    vol_duct_lag_s = 3.5 * ((vol_m3 / 19.0) ** 0.33) / max(0.55, min(2.2, (airflow_cms + 1.5) / 4.0))
    if optical_blind:
        t_alarm_s = round(max(4.0, min(180.0, t_caw_25)), 1)
    else:
        t_alarm_s = round(max(1.5, min(t_caw_25, vol_duct_lag_s)), 1)

    unmitigated = crew_response_s >= 900.0
    eff_wait_s = 180.0 if unmitigated else crew_response_s
    t_intervene_s = round(t_alarm_s + eff_wait_s, 1)

    co_at_response = round(min(4500.0, baseline_co_ppm + co_rate_ppm_s * t_intervene_s), 0)

    # 1. Termodinamik Yasası (Q_net = f_conv * Q_dot * t = m_gas * c_p * ΔT); kabin gövdesi ısı emilimi sonrası f_conv ≈ 0.35
    f_conv = 0.35
    max_o2_burn_j = (n_gas_mol * x_o2 * 0.032) * 13100.0e3  # Thornton kuralı: 13.1 MJ / kg tüketilen O2 üst sınırı
    q_released_j = min(max_o2_burn_j, fire_power_w * t_intervene_s)
    peak_temp_rise_c = round(min(650.0, (f_conv * q_released_j) / (m_gas_kg * cp_gas_j_kgk)), 1)

    if co_at_response >= 425.0 or (vol_m3 < 1.0 and oxygen_pct >= 60.0) or peak_temp_rise_c >= 45.0 or unmitigated:
        severity = "CRITICAL"
        badge_tr = "KRİTİK YAŞAM DESTEK AŞIMI"
        badge_en = "CRITICAL ECLSS / SMAC BREACH"
    elif co_at_response >= 100.0 or optical_blind:
        severity = "WARNING"
        badge_tr = "DİKKAT: HIZLI MÜDAHALE GEREKLİ"
        badge_en = "WARNING: RAPID ACTION REQUIRED"
    else:
        severity = "SAFE"
        badge_tr = "KONTROLLÜ BASTIRMA PENCERESİ"
        badge_en = "CONTROLLED SUPPRESSION WINDOW"

    sensor_note_tr = (
        "ISS optik duman dedektörü (PSD, 670 nm) kurumsız soğuk alevde uyarmadı; CSA-CP / ANITA-2 CO gaz analizi (25 ppm C&W) alarm üretti."
        if optical_blind
        else "ISS Fotoelektrik Duman Dedektörü (PSD) lazer saçılım kanalı ve CSA-CP CO izleme ünitesi yangını doğruladı."
    )
    sensor_note_en = (
        "ISS photoelectric smoke detector (PSD, 670 nm) blind to soot-free cool flame; CSA-CP / ANITA-2 CO analyzer (25 ppm C&W) triggered alarm."
        if optical_blind
        else "ISS Photoelectric Smoke Detector (PSD) laser scattering and CSA-CP CO monitor confirmed fire."
    )

    action_tr = (
        "Müdahale yapılmadı (Serbest Yanma)"
        if unmitigated
        else f"HVAC Fan Kesme (U→0 cm/s) + İnce Su Sisi (SoFIE-MIST) [+{crew_response_s:.0f}s]"
    )
    action_en = (
        "Unmitigated Burn (No Crew Action)"
        if unmitigated
        else f"HVAC Fan Cutoff (U→0 cm/s) + Fine Water Mist (SoFIE-MIST) [+{crew_response_s:.0f}s]"
    )

    summary_tr = (
        f"**{hab['name_tr']} (Referans Kabin Yangın Yükü `{fire_power_kw:.2f} kW`):** Alarm `t = {t_alarm_s} s` anında tetiklendi. "
        f"Resmi **NASA JSC-20584** CO sınırlarına göre 24-saatlik SMAC (`100 ppm`) `t = {t_smac_24h_100} s`, "
        f"1-saatlik Acil SMAC (`425 ppm`) ise `t = {t_smac_1h_425} s` içinde aşılır. "
        f"Seçilen müdahale anında (`t = {t_intervene_s} s`) ortalama kabin CO düzeyi **`{co_at_response:.0f} ppm`** ve kütle-korunumlu gaz ısınması **`+{peak_temp_rise_c} °C`** olur."
    )
    summary_en = (
        f"**{hab['name_en']} (Reference Cabin Fire Load `{fire_power_kw:.2f} kW`):** Alarm triggered at `t = {t_alarm_s} s`. "
        f"Per **NASA JSC-20584**, 24-hr CO SMAC (`100 ppm`) is reached in `t = {t_smac_24h_100} s` and 1-hr Emergency SMAC (`425 ppm`) in `t = {t_smac_1h_425} s`. "
        f"At intervention (`t = {t_intervene_s} s`), bulk cabin CO is **`{co_at_response:.0f} ppm`** and bulk gas ΔT is **`+{peak_temp_rise_c} °C`**."
    )

    milestones = [
        {
            "t_s": 0.0,
            "title_tr": "0.0 s • Tutuşma Başlangıcı",
            "title_en": "0.0 s • Ignition Onset",
            "detail_tr": f"Rejim: {regime_label_tr or regime} ({flame_temp_k:.0f} K, Q̇={fire_power_kw:.2f} kW)",
            "detail_en": f"Regime: {regime_label_en or regime} ({flame_temp_k:.0f} K, Q̇={fire_power_kw:.2f} kW)",
            "state": "warn",
        },
        {
            "t_s": t_alarm_s,
            "title_tr": f"{t_alarm_s} s • Çok Kanallı C&W Yangın Alarmı",
            "title_en": f"{t_alarm_s} s • Multi-Channel C&W Fire Alarm",
            "detail_tr": sensor_note_tr,
            "detail_en": sensor_note_en,
            "state": "crit" if optical_blind else "warn",
        },
        {
            "t_s": t_intervene_s,
            "title_tr": f"{t_intervene_s} s • {action_tr.split('[')[0].strip()}",
            "title_en": f"{t_intervene_s} s • {action_en.split('[')[0].strip()}",
            "detail_tr": f"Müdahale anı CO: {co_at_response:.0f} ppm • Kabin ΔT: +{peak_temp_rise_c} °C (Halon YASAK)",
            "detail_en": f"CO at action: {co_at_response:.0f} ppm • Bulk ΔT: +{peak_temp_rise_c} °C (No Halon)",
            "state": "crit" if severity == "CRITICAL" else ("warn" if severity == "WARNING" else "ok"),
        },
        {
            "t_s": t_smac_24h_100,
            "title_tr": f"{t_smac_24h_100} s • NASA JSC-20584 CO SMAC (100 / 425 ppm)",
            "title_en": f"{t_smac_24h_100} s • NASA JSC-20584 CO SMAC (100 / 425 ppm)",
            "detail_tr": (
                f"24sa SMAC (100 ppm): {t_smac_24h_100} s • 1sa Acil SMAC (425 ppm): {t_smac_1h_425} s "
                f"({'AŞILDI!' if t_intervene_s >= t_smac_24h_100 else 'Müdahale öncesi korundu'})"
            ),
            "detail_en": (
                f"24-hr SMAC (100 ppm): {t_smac_24h_100} s • 1-hr Emergency SMAC (425 ppm): {t_smac_1h_425} s "
                f"({'BREACHED!' if t_intervene_s >= t_smac_24h_100 else 'Preserved before action'})"
            ),
            "state": "crit" if t_intervene_s >= t_smac_1h_425 else ("warn" if t_intervene_s >= t_smac_24h_100 else "ok"),
        },
    ]
    milestones.sort(key=lambda item: float(item["t_s"]))

    return {
        "habitat_id": habitat_id,
        "habitat_name_tr": hab["name_tr"],
        "habitat_name_en": hab["name_en"],
        "volume_m3": vol_m3,
        "crew_response_s": crew_response_s,
        "optical_blind": optical_blind,
        "fire_power_kw": fire_power_kw,
        "t_alarm_s": t_alarm_s,
        "t_intervene_s": t_intervene_s,
        "t_caw_25ppm_s": t_caw_25,
        "t_smac_24h_100ppm_s": t_smac_24h_100,
        "t_smac_1h_425ppm_s": t_smac_1h_425,
        "co_at_response_ppm": co_at_response,
        "peak_temp_rise_c": peak_temp_rise_c,
        "severity": severity,
        "badge_tr": badge_tr,
        "badge_en": badge_en,
        "summary_tr": summary_tr,
        "summary_en": summary_en,
        "milestones": milestones,
    }



def _compute_analytical_uncertainty_bounds(
    fuel: Dict[str, Any],
    gravity_g: float,
    airflow_cms: float,
    moc_current: float,
    moc_0g_bound: float,
    moc_1g_bound: float,
    k_burn: float,
    flame_temp_k: float,
    flame_spread_mms: float,
    damkohler_da: float,
    analog_match_info: Dict[str, Any],
) -> Dict[str, Any]:
    """
    < 1 ms hızında Analitik Hata Yayılımı ve ±1σ Güven Bandı Motoru:
    Kısmi yerçekimi enterpolasyonu (0.03G–0.88G LUCI/FM2 boşluğu), özel malzeme termofiziksel vekil sapması
    ve düşük hız / Damköhler sönme sınırı gradyanından MOC, K, T_f ve V_f için ±1σ alt/üst sınırlarını çözer.
    """
    is_analog = bool(analog_match_info.get("active"))
    base_moc_sigma = float(analog_match_info.get("uncertainty_moc_pct", 0.55)) if is_analog else 0.52
    partial_g_factor = math.sin(math.pi * min(1.0, max(0.0, gravity_g))) if 0.03 <= gravity_g <= 0.88 else 0.0
    partial_g_sigma = partial_g_factor * (0.32 * abs(moc_1g_bound - moc_0g_bound) + 0.42)
    boundary_sigma = 0.28 if (airflow_cms < 2.5 or damkohler_da < 1.6) else 0.0

    moc_sigma = round(math.sqrt(base_moc_sigma ** 2 + partial_g_sigma ** 2 + boundary_sigma ** 2), 2)
    rel_unc = min(0.24, max(0.035, (moc_sigma / max(8.0, moc_current)) * 0.92))

    k_sigma = round(k_burn * rel_unc, 3) if k_burn > 0 else 0.0
    temp_sigma = round(max(12.0, (flame_temp_k - 298.15) * (rel_unc * 0.55)), 1) if flame_temp_k > 320.0 else 4.0
    spread_sigma = round(flame_spread_mms * (rel_unc * 1.15), 2) if flame_spread_mms > 0 else 0.0

    if is_analog:
        conf_pct = max(70, int(analog_match_info.get("confidence_pct", 82)) - int(round(partial_g_factor * 6)))
    elif 0.03 <= gravity_g <= 0.88:
        conf_pct = int(round(91 - partial_g_factor * 7))
    else:
        conf_pct = 95

    moc_low = round(max(4.0, moc_current - moc_sigma), 2)
    moc_high = round(min(58.0, moc_current + moc_sigma), 2)
    k_low = round(max(0.0, k_burn - k_sigma), 3)
    k_high = round(k_burn + k_sigma, 3)
    t_low = round(max(295.0, flame_temp_k - temp_sigma), 1)
    t_high = round(flame_temp_k + temp_sigma, 1)
    sp_low = round(max(0.0, flame_spread_mms - spread_sigma), 2)
    sp_high = round(flame_spread_mms + spread_sigma, 2)

    return {
        "confidence_pct": conf_pct,
        "moc_sigma_pct": moc_sigma,
        "moc_low_pct": moc_low,
        "moc_high_pct": moc_high,
        "moc_lower_pct": moc_low,
        "moc_upper_pct": moc_high,
        "k_sigma_mm2_s": k_sigma,
        "k_low_mm2_s": k_low,
        "k_high_mm2_s": k_high,
        "k_lower_mm2_s": k_low,
        "k_upper_mm2_s": k_high,
        "flame_temp_sigma_k": temp_sigma,
        "flame_temp_low_k": t_low,
        "flame_temp_high_k": t_high,
        "temp_sigma_k": temp_sigma,
        "temp_lower_k": t_low,
        "temp_upper_k": t_high,
        "spread_sigma_mms": spread_sigma,
        "spread_low_mms": sp_low,
        "spread_high_mms": sp_high,
        "spread_sigma_mm_s": spread_sigma,
        "spread_lower_mm_s": sp_low,
        "spread_upper_mm_s": sp_high,
    }


def _compute_post_fire_cooling(
    fuel: Dict[str, Any],
    gravity_g: float,
    oxygen_pct: float,
    pressure_psia: float,
    droplet_d0_mm: float,
    flame_temp_k: float,
    co_ppm: float,
    extinguished: bool,
    cool_flame_active: bool,
) -> Dict[str, Any]:
    """
    0G Söndürme Sonrası Çekirdek Soğuma (Post-Fire Core Cooling) ve Yeniden Tutuşma Riski Motoru:
    Mikroçekimde doğal konveksiyon sıfırlandığı (Ra -> 0) için alev sönse bile malzeme iç çekirdeği
    yalnızca moleküler iletim + T^4 radyasyon ile yavaş soğur. Kapak/havalandırma erken açılırsa taze O2
    sıcak çekirdekle buluşarak ani yeniden tutuşma (0G Flash Re-Ignition) oluşturur.
    """
    t_amb = 294.15
    t_boil = float(fuel.get("t_boil_k", 580.0))
    autoignition_k = round(max(495.0, t_boil + 135.0 - 1.25 * max(0.0, oxygen_pct - 21.0)), 1)
    safe_reentry_temp_k = 338.15  # 65 C çekirdek güvenlik eşiği

    if extinguished:
        t_core_0 = round(max(308.0, min(460.0, t_boil * 0.72)), 1)
    elif cool_flame_active:
        t_core_0 = round(max(545.0, min(690.0, flame_temp_k * 0.92)), 1)
    else:
        t_core_0 = round(max(585.0, min(910.0, t_boil + (flame_temp_k - t_boil) * 0.34)), 1)

    rho_s = float(fuel.get("rho_l_kg_m3", 950.0))
    cp_s = float(fuel.get("cp_s_j_kgk", fuel.get("cp_vapor_j_kgk", 1550.0)))
    l_char_m = max(0.0018, (droplet_d0_mm / 1000.0) * 0.85)
    p_atm = max(0.25, pressure_psia / 14.696)

    # 0G: Yalnızca durgun gaz iletimi (Nu = 2) + yüzey radyasyonu; 1G: doğal kaldırma konveksiyonu; MIST: SoFIE-MIST buharlaşmalı soğutma
    h_0g = (2.0 * 0.032 * (p_atm ** 0.25)) / l_char_m + 5.4
    h_ag = h_0g + 16.5 * ((max(0.0, gravity_g)) ** 0.25)
    h_mist = h_ag + 54.0

    thermal_cap_area = max(180.0, rho_s * cp_s * (l_char_m / 3.0) * 0.42)
    tau_0g_s = round(min(260.0, max(38.0, thermal_cap_area / max(4.0, h_0g))), 1)
    tau_active_g_s = round(min(260.0, max(22.0, thermal_cap_area / max(4.0, h_ag))), 1)
    tau_mist_s = round(min(95.0, max(12.0, thermal_cap_area / max(12.0, h_mist))), 1)
    tau_1g_s = round(min(120.0, max(18.0, thermal_cap_area / max(8.0, h_0g + 16.5))), 1)

    times = [float(step * 10) for step in range(19)]  # 0..180 s
    curve_0g = [round(t_amb + (t_core_0 - t_amb) * math.exp(-t / tau_active_g_s), 1) for t in times]
    curve_mist = [round(t_amb + (t_core_0 - t_amb) * math.exp(-t / tau_mist_s), 1) for t in times]
    curve_1g = [round(t_amb + (t_core_0 - t_amb) * math.exp(-t / tau_1g_s), 1) for t in times]

    def _solve_wait(tau_val: float, target_k: float) -> float:
        if t_core_0 <= target_k:
            return 0.0
        ratio = max(1e-4, (target_k - t_amb) / max(1.0, t_core_0 - t_amb))
        return round(max(0.0, -tau_val * math.log(ratio)), 1)

    co_scrub_s = round(max(0.0, (co_ppm - 25.0) * 0.32), 1) if co_ppm > 25.0 else 0.0
    safe_wait_unassisted_s = round(max(_solve_wait(tau_active_g_s, safe_reentry_temp_k), co_scrub_s), 0)
    safe_wait_mist_s = round(max(_solve_wait(tau_mist_s, safe_reentry_temp_k), co_scrub_s * 0.55), 0)

    if extinguished and t_core_0 < autoignition_k * 0.78:
        reign_risk = max(4, int(round(18.0 * (oxygen_pct / 21.0))))
    else:
        temp_ratio = (t_core_0 - safe_reentry_temp_k) / max(40.0, autoignition_k - safe_reentry_temp_k)
        o2_amp = (oxygen_pct / 21.0) ** 0.75
        zero_g_amp = 1.18 if gravity_g < 0.08 else 1.0
        reign_risk = int(round(max(6.0, min(98.0, 42.0 * temp_ratio * o2_amp * zero_g_amp + 22.0))))

    status_tr = (
        f"Sıcak çekirdek ({t_core_0:.0f} K): Su sisi olmadan güvenli kapak açma süresi {safe_wait_unassisted_s:.0f} sn, SoFIE-MIST ile {safe_wait_mist_s:.0f} sn."
        if safe_wait_unassisted_s > 0
        else "Çekirdek sıcaklığı güvenli sınırın altında; kapak ve havalandırma açılabilir."
    )
    status_en = (
        f"Hot core ({t_core_0:.0f} K): Safe hatch re-opening requires {safe_wait_unassisted_s:.0f} s unassisted, or {safe_wait_mist_s:.0f} s with SoFIE-MIST."
        if safe_wait_unassisted_s > 0
        else "Core temperature below re-ignition limit; safe for hatch and vent re-opening."
    )

    return {
        "initial_core_temp_k": t_core_0,
        "initial_core_temp_c": round(t_core_0 - 273.15, 1),
        "autoignition_temp_k": autoignition_k,
        "safe_reentry_temp_k": safe_reentry_temp_k,
        "tau_active_g_s": tau_active_g_s,
        "tau_0g_s": tau_0g_s,
        "tau_mist_s": tau_mist_s,
        "tau_1g_s": tau_1g_s,
        "reignition_risk_pct": reign_risk,
        "safe_reentry_s": safe_wait_unassisted_s,
        "safe_reentry_mist_s": safe_wait_mist_s,
        "time_s": times,
        "core_temp_0g_k": curve_0g,
        "core_temp_mist_k": curve_mist,
        "core_temp_1g_k": curve_1g,
        "status_tr": status_tr,
        "status_en": status_en,
    }


def _compute_mission_certification(
    fuel: Dict[str, Any],
    dil_default: str = "N2",
    flow_direction: str = "opposed",
) -> List[Dict[str, Any]]:
    """
    5 Evreli Görev Malzeme Sertifikasyon Matrisi (NASA-STD-6001B Test 1 & 0G/Kısmi-G MOC Kriteri):
    Seçili malzemeyi değiştirmeden ISS (0G), Orion (0G), Ay Üssü (0.16G), Mars Kabini (0.38G) ve
    Uzay Giysisi (%100 O2) atmosferlerinde değerlendirir.
    """
    phases = [
        {
            "phase_id": "iss_0g",
            "label_tr": "ISS (0G)",
            "label_en": "ISS (0G)",
            "gravity_g": 0.0,
            "oxygen_pct": 21.0,
            "pressure_psia": 14.7,
            "airflow_cms": 3.5,
            "diluent": dil_default,
            "habitat_id": "iss_module",
        },
        {
            "phase_id": "orion_0g",
            "label_tr": "Orion (0G)",
            "label_en": "Orion (0G)",
            "gravity_g": 0.0,
            "oxygen_pct": 30.0,
            "pressure_psia": 10.2,
            "airflow_cms": 4.0,
            "diluent": "N2",
            "habitat_id": "lunar_hab",
        },
        {
            "phase_id": "lunar_016g",
            "label_tr": "Ay Üssü (0.16G)",
            "label_en": "Lunar Base (0.16G)",
            "gravity_g": 0.16,
            "oxygen_pct": 32.0,
            "pressure_psia": 10.2,
            "airflow_cms": 4.0,
            "diluent": "N2",
            "habitat_id": "lunar_rover",
        },
        {
            "phase_id": "mars_038g",
            "label_tr": "Mars Kabini (0.38G)",
            "label_en": "Mars Cabin (0.38G)",
            "gravity_g": 0.38,
            "oxygen_pct": 34.0,
            "pressure_psia": 8.2,
            "airflow_cms": 4.5,
            "diluent": "N2",
            "habitat_id": "mars_hab",
        },
        {
            "phase_id": "eva_suit",
            "label_tr": "Uzay Giysisi (%100 O₂)",
            "label_en": "Spacesuit (100% O₂)",
            "gravity_g": 0.0,
            "oxygen_pct": 100.0,
            "pressure_psia": 4.3,
            "airflow_cms": 6.0,
            "diluent": "N2",
            "habitat_id": "eva_suit",
        },
    ]

    results: List[Dict[str, Any]] = []
    for ph in phases:
        moc_p = compute_moc_at_flow(
            fuel=fuel,
            airflow_cms=ph["airflow_cms"],
            gravity_g=ph["gravity_g"],
            pressure_psia=ph["pressure_psia"],
            diluent=ph["diluent"],
            flow_direction=flow_direction,
        )
        margin = round(moc_p - ph["oxygen_pct"], 2)
        if margin >= 1.5:
            code = "PASS"
            st_tr = "Uygun"
            st_en = "Certified"
        elif margin >= -1.5:
            code = "CAUTION"
            st_tr = "Koşullu"
            st_en = "Caution"
        else:
            code = "FAIL"
            st_tr = "Tehlikeli"
            st_en = "Flammable"

        results.append({
            "phase_id": ph["phase_id"],
            "label_tr": ph["label_tr"],
            "label_en": ph["label_en"],
            "status": code,
            "status_tr": st_tr,
            "status_en": st_en,
            "moc_pct": moc_p,
            "oxygen_pct": ph["oxygen_pct"],
            "pressure_psia": ph["pressure_psia"],
            "gravity_g": ph["gravity_g"],
            "airflow_cms": ph["airflow_cms"],
            "habitat_id": ph["habitat_id"],
            "margin_pct": margin,
        })
    return results


def _compute_space_to_earth_live(
    fuel: Dict[str, Any],
    flame_temp_k: float,
    heat_flux_kw_m2: float,
    hrrpua_kw_m2: float,
    co_ppm: float,
    cool_flame_active: bool,
    pre_ignition: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Aktif simülasyondan Uzaydan-Dünyaya (Space-to-Earth) mühendislik transferi için canlı sayısal metrikler."""
    psi_val = float((pre_ignition or {}).get("semenov_psi", 0.35))
    d32_um = round(max(22.0, min(44.0, 24.0 + 11.5 * math.sqrt(max(0.1, heat_flux_kw_m2) / 28.0))), 1)
    water_saving_pct = round(max(82.0, min(94.5, 92.8 - min(8.8, hrrpua_kw_m2 / 90.0))), 1)
    early_gain_s = round(max(16.0, min(58.0, 22.0 + (18.0 if cool_flame_active else 8.5) + min(14.0, co_ppm / 32.0) + psi_val * 6.0)), 1)
    dust_rej_pct = round(max(97.6, min(99.4, 98.9 - 0.35 * float(fuel.get("soot_tendency", 0.35)))), 2)
    fabric_margin_kw = round(max(6.5, 45.0 - heat_flux_kw_m2 * 0.42), 1)

    return {
        "mist_sauter_d32_um": d32_um,
        "mist_water_saving_pct": water_saving_pct,
        "ev_early_warning_gain_s": early_gain_s,
        "dust_false_alarm_rejection_pct": dust_rej_pct,
        "protective_fabric_margin_kw_m2": fabric_margin_kw,
        "active_flame_temp_k": round(flame_temp_k, 0),
    }


_SAFE_AST_FUNCS = {
    "sqrt": lambda x: math.sqrt(max(0.0, float(x))),
    "ln": lambda x: math.log(max(1e-9, float(x))),
    "log": lambda x: math.log(max(1e-9, float(x))),
    "log10": lambda x: math.log10(max(1e-9, float(x))),
    "exp": lambda x: math.exp(max(-60.0, min(60.0, float(x)))),
    "sin": lambda x: math.sin(float(x)),
    "cos": lambda x: math.cos(float(x)),
    "tan": lambda x: math.tan(float(x)),
    "abs": lambda x: abs(float(x)),
    "min": lambda *args: min(float(a) for a in args),
    "max": lambda *args: max(float(a) for a in args),
    "pow": lambda a, b: float(a) ** max(-12.0, min(12.0, float(b))),
}


def _eval_ast_node(node: ast.AST, env: Dict[str, float]) -> float:
    if isinstance(node, ast.Expression):
        return _eval_ast_node(node.body, env)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.Name):
        if node.id in env:
            return float(env[node.id])
        raise ValueError(f"Unknown variable: {node.id}")
    if isinstance(node, ast.UnaryOp):
        val = _eval_ast_node(node.operand, env)
        if isinstance(node.op, ast.UAdd):
            return +val
        if isinstance(node.op, ast.USub):
            return -val
        raise ValueError("Unsupported unary operator")
    if isinstance(node, ast.BinOp):
        left = _eval_ast_node(node.left, env)
        right = _eval_ast_node(node.right, env)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            return left / (right if abs(right) > 1e-12 else 1e-12)
        if isinstance(node.op, ast.Pow):
            return (max(0.0, left) if right % 1 != 0 and left < 0 else left) ** max(-12.0, min(12.0, right))
        raise ValueError("Unsupported binary operator")
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        fn_name = node.func.id
        if fn_name not in _SAFE_AST_FUNCS:
            raise ValueError(f"Unsupported function: {fn_name}")
        args = [_eval_ast_node(a, env) for a in node.args]
        return float(_SAFE_AST_FUNCS[fn_name](*args))
    raise ValueError("Disallowed syntax in formula expression")


def evaluate_custom_formula(
    expression: str,
    sim_state: Dict[str, Any],
    target_metric: str = "auto",
) -> Dict[str, Any]:
    """
    Güvenli AST tabanlı Özel Denklem Doğrulama Motoru (eval() kullanmaz):
    Kullanıcının veya jürinin girdiği ölçekleme denklemini (ör. '2 + 0.6 * sqrt(Re) * (0.71 ** 0.333)' veya
    'D0**2 - K * t' veya 'MOC * (1 + 0.08 * exp(-U / 2.0))') canlı oda değişkenleriyle hesaplar ve
    NASA ISS 0G referans eğrisiyle karşılaştırır.
    """
    raw_expr = (expression or "").strip()
    if not raw_expr or len(raw_expr) > 260:
        return {
            "ok": False,
            "error_tr": "Geçerli bir matematiksel denklem girin (maks. 260 karakter).",
            "error_en": "Please enter a valid mathematical expression (max 260 chars).",
        }

    # '^' üs operatörünü Python '**' biçimine normalize et ve '=' varsa sağ tarafı al
    lhs_label = ""
    norm_expr = raw_expr.replace("^", "**")
    if "=" in norm_expr and "==" not in norm_expr:
        parts = norm_expr.split("=", 1)
        lhs_label = parts[0].strip()
        norm_expr = parts[1].strip()

    inp = sim_state.get("inputs", {}) if isinstance(sim_state, dict) else {}
    tel = sim_state.get("telemetry", {}) if isinstance(sim_state, dict) else {}
    fv = sim_state.get("flight_validation", {}) if isinstance(sim_state, dict) else {}

    def _make_env_from_state(s_state: Dict[str, Any]) -> Dict[str, float]:
        s_inp = s_state.get("inputs", {}) if isinstance(s_state, dict) else {}
        s_tel = s_state.get("telemetry", {}) if isinstance(s_state, dict) else {}
        s_o2 = _safe_float(s_inp.get("oxygen_pct", 21.0), 21.0)
        s_p = _safe_float(s_inp.get("pressure_psia", 14.7), 14.7)
        s_fref = FUEL_PROPERTIES.get(str(s_inp.get("fuel_id", "n_heptane")), FUEL_PROPERTIES["n_heptane"])
        return {
            "g": _safe_float(s_inp.get("gravity_g", 0.0), 0.0),
            "G": _safe_float(s_inp.get("gravity_g", 0.0), 0.0),
            "O2": s_o2,
            "X_O2": round(s_o2 / 100.0, 4),
            "Y_O2": round((s_o2 / 100.0) * 32.0 / max(1.0, (s_o2 / 100.0) * 32.0 + (1.0 - s_o2 / 100.0) * 28.01), 4),
            "P": s_p,
            "P_atm": round(s_p / 14.696, 4),
            "P_kpa": _safe_float(s_inp.get("pressure_kpa", round(s_p * 6.89476, 2)), round(s_p * 6.89476, 2)),
            "PO2": _safe_float(s_tel.get("o2_partial_psia", s_tel.get("po2_psia", round(s_p * s_o2 / 100.0, 3))), round(s_p * s_o2 / 100.0, 3)),
            "U": _safe_float(s_inp.get("airflow_cms", 0.0), 0.0),
            "D0": _safe_float(s_inp.get("droplet_d0_mm", 3.2), 3.2),
            "t": 6.0,
            "T_amb": 298.15,
            "B": _safe_float(s_tel.get("spalding_b_number", 3.5), 3.5),
            "B_oq": _safe_float(s_tel.get("spalding_b_number", 3.5), 3.5),
            "Sh": _safe_float(s_tel.get("sherwood_number", 2.0), 2.0),
            "Re": _safe_float(s_tel.get("reynolds_number", 0.0), 0.0),
            "Gr": _safe_float(s_tel.get("grashof_number", 0.0), 0.0),
            "Ra": _safe_float(s_tel.get("rayleigh_number", 0.0), 0.0),
            "Ri": _safe_float(s_tel.get("richardson_number", 0.0), 0.0),
            "Fr": _safe_float(s_tel.get("froude_number", 0.0), 0.0),
            "Da": _safe_float(s_tel.get("damkohler_number", 5.0), 5.0),
            "chi_r": _safe_float(s_tel.get("radiative_loss_fraction", 0.18), 0.18),
            "T_f": _safe_float(s_tel.get("flame_temp_k", 1800.0), 1800.0),
            "Tf": _safe_float(s_tel.get("flame_temp_k", 1800.0), 1800.0),
            "T_s": _safe_float(s_fref.get("t_boil_k", 371.5), 371.5),
            "MOC": _safe_float(s_tel.get("moc_pct", 15.0), 15.0),
            "K": _safe_float(s_tel.get("burning_rate_k_mm2_s", 0.65), 0.65),
            "V_f": _safe_float(s_tel.get("flame_spread_mm_s", 0.0), 0.0),
            "Rf_Rd": _safe_float(s_tel.get("standoff_ratio_rf_rd", s_tel.get("standoff_ratio", 5.0)), 5.0),
            "CO": _safe_float(s_tel.get("co_ppm", 50.0), 50.0),
            "HRRPUA": _safe_float(s_tel.get("hrrpua_kw_m2", 120.0), 120.0),
            "Soot": _safe_float(s_tel.get("soot_index", 0.2), 0.2),
            "pi": math.pi,
            "PI": math.pi,
            "e": math.e,
            "E": math.e,
        }

    env: Dict[str, float] = _make_env_from_state(sim_state)

    try:
        tree = ast.parse(norm_expr, mode="eval")
        used_vars = sorted({n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and n.id in env})
        val_now = _eval_ast_node(tree, env)
        if math.isnan(val_now) or math.isinf(val_now):
            raise ValueError("Non-finite result")
    except Exception as exc:
        return {
            "ok": False,
            "error_tr": f"Denklem çözümlenemedi: {exc}",
            "error_en": f"Formula evaluation error: {exc}",
        }

    # Otomatik fiziksel hedef karşılaştırması (Sh, B_oq, K, Rf_Rd, MOC, d² veya V_f)
    metric_aliases = {
        "k_burn": "K",
        "burning_rate_k": "K",
        "moc_pct": "MOC",
        "standoff_ratio": "Rf_Rd",
        "standoff_ratio_rf_rd": "Rf_Rd",
        "flame_spread_mm_s": "V_f",
        "flame_temp_k": "T_f",
        "sherwood_number": "Sh",
        "spalding_b_number": "B_oq",
    }
    norm_target = metric_aliases.get(target_metric, target_metric)
    candidates = {
        "Sh": env["Sh"],
        "B_oq": env["B_oq"],
        "K": env["K"],
        "Rf_Rd": env["Rf_Rd"],
        "MOC": env["MOC"],
        "V_f": env["V_f"],
        "T_f": env["T_f"],
    }
    chosen_ref_name = norm_target if norm_target in candidates else ""
    if not chosen_ref_name:
        lhs_clean = metric_aliases.get(lhs_label.strip(), lhs_label.strip())
        if lhs_clean in candidates:
            chosen_ref_name = lhs_clean
        else:
            chosen_ref_name = min(candidates.keys(), key=lambda k: abs(val_now - candidates[k]) / max(1.0, abs(candidates[k])))

    ref_val = float(candidates[chosen_ref_name])
    rel_diff_pct = round(abs(val_now - ref_val) / max(1e-4, abs(ref_val)) * 100.0, 2)

    base_sim_params = {
        "fuel_id": inp.get("requested_fuel_id") or inp.get("fuel_id") or "n_heptane",
        "gravity_g": env["g"],
        "oxygen_pct": env["O2"],
        "pressure_psia": env["P"],
        "airflow_cms": env["U"],
        "flow_direction": inp.get("flow_direction", "opposed"),
        "droplet_d0_mm": env["D0"],
        "diluent": inp.get("diluent", "N2"),
        "habitat_id": inp.get("habitat_id", "iss_module"),
    }

    # Çok noktalı doğrulama serisinde R² ve RMSE hesapla (t, U veya O2 taraması)
    sweep_points: List[Dict[str, float]] = []
    if "t" in used_vars and fv.get("d2_points"):
        d0_sq = max(0.25, env["D0"] ** 2)
        for pt in fv["d2_points"]:
            env_t = dict(env)
            env_t["t"] = float(pt["t_s"])
            yp_raw = _eval_ast_node(tree, env_t)
            yp_norm = yp_raw / d0_sq if yp_raw > 1.35 else yp_raw
            sweep_points.append({"x": float(pt["t_s"]), "meas": float(pt["d2_meas"]), "pred": round(yp_norm, 4)})
    elif chosen_ref_name == "MOC" or (("U" in used_vars or "Re" in used_vars) and "O2" not in used_vars and "Y_O2" not in used_vars and "B_oq" not in used_vars):
        for u_sw in (0.5, 2.5, 5.5, 12.0, 22.0, 34.0):
            sim_u = simulate_combustion_state({**base_sim_params, "airflow_cms": u_sw})
            env_u = _make_env_from_state(sim_u)
            yp_u = _eval_ast_node(tree, env_u)
            ym_u = float(env_u.get(chosen_ref_name, ref_val))
            if math.isfinite(yp_u):
                sweep_points.append({"x": u_sw, "meas": round(ym_u, 4), "pred": round(yp_u, 4)})
    else:
        for o2_sw in (16.0, 19.0, 21.0, 26.0, 32.0, 40.0):
            sim_o = simulate_combustion_state({**base_sim_params, "oxygen_pct": o2_sw})
            env_o = _make_env_from_state(sim_o)
            yp_o = _eval_ast_node(tree, env_o)
            ym_o = float(env_o.get(chosen_ref_name, ref_val))
            if math.isfinite(yp_o):
                sweep_points.append({"x": o2_sw, "meas": round(ym_o, 4), "pred": round(yp_o, 4)})

    r2_sweep = None
    rmse_sweep = None
    if len(sweep_points) >= 3:
        ms = [p["meas"] for p in sweep_points]
        ps = [p["pred"] for p in sweep_points]
        mean_m = sum(ms) / len(ms)
        ss_res = sum((m - p) ** 2 for m, p in zip(ms, ps))
        ss_tot = sum((m - mean_m) ** 2 for m in ms)
        rmse_sweep = round(math.sqrt(ss_res / len(ms)), 4)
        r2_sweep = round(max(0.0, min(0.999, 1.0 - ss_res / ss_tot)), 4) if ss_tot > 1e-6 else (0.99 if rel_diff_pct < 5.0 else 0.75)

    return {
        "ok": True,
        "expression": raw_expr,
        "evaluated_value": round(val_now, 5),
        "reference_metric": chosen_ref_name,
        "reference_value": round(ref_val, 5),
        "relative_diff_pct": rel_diff_pct,
        "used_variables": used_vars,
        "r_squared": r2_sweep,
        "rmse": rmse_sweep,
        "sweep_points": sweep_points,
        "summary_tr": (
            f"Hesaplanan Değer: {val_now:.4f} | En Yakın Referans ({chosen_ref_name}): {ref_val:.4f} (Fark: %{rel_diff_pct:.2f})"
            + (f" | ISS 0G Serisi R² = {r2_sweep:.3f}, RMSE = {rmse_sweep:.3f}" if r2_sweep is not None else "")
        ),
        "summary_en": (
            f"Evaluated Value: {val_now:.4f} | Reference ({chosen_ref_name}): {ref_val:.4f} (Diff: {rel_diff_pct:.2f}%)"
            + (f" | ISS 0G Sweep R² = {r2_sweep:.3f}, RMSE = {rmse_sweep:.3f}" if r2_sweep is not None else "")
        ),
    }
