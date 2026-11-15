# -*- coding: utf-8 -*-
"""
ALTAR-NASA v6.3 — Yangın Üçgeni (Yakıt + Oksijen + Tutuşma Enerjisi),
0G Ön-Tutuşma Termal Kaçak (Semenov / Frank-Kamenetskii) ve İki Dallı Arrhenius Kinetik Motoru.

Kaynak Literatür:
- Lewis, B. & von Elbe, G. (1987). Combustion, Flames and Explosions of Gases (Minimum Ignition Energy MIE).
- Semenov, N. N. (1928) & Frank-Kamenetskii, D. A. (1969). Diffusion and Heat Transfer in Chemical Kinetics.
- Quintiere, J. G. (2006). Fundamentals of Fire Phenomena (Critical Heat Flux & Solid Ignition Delay).
- Ju, Y., Reuter, C. B., Yehia, O. R., Farouk, T. I., & Won, S. H. (2019). Dynamics of Cool Flames (Progress in Energy and Combustion Science, ISS FLEX / CFI-G NTC Kinetics).
- NASA-STD-6001B: Flammability, Offgassing, and Compatibility Requirements and Test Procedures.
"""

from __future__ import annotations

import math
from typing import Any, Dict

R_UNIV_J_MOLK = 8.314462618
SIGMA_SB_W_M2K4 = 5.670374419e-8

# Yakıt bazlı literatür ön-tutuşma, MIE, LFL/UFL ve Arrhenius kinetik sabitleri
IGNITION_KINETIC_DB: Dict[str, Dict[str, Any]] = {
    "n_heptane": {
        "mie_1atm_air_mj": 0.24,
        "lfl_vol_pct": 1.05,
        "ufl_vol_pct": 6.70,
        "t_autoign_k": 488.0,
        "t_surface_ig_k": 371.5,
        "lambda_s_w_mk": 0.14,
        "cp_s_j_kgk": 2240.0,
        "emissivity": 0.92,
        "ea_ht_j_mol": 125500.0,
        "a_ht_pre": 4.8e9,
        "ea_lt_j_mol": 64000.0,
        "a_lt_pre": 2.6e6,
        "ea_ntc_decomp_j_mol": 88000.0,
        "k_ntc_turn": 7.2e5,
    },
    "methanol": {
        "mie_1atm_air_mj": 0.14,
        "lfl_vol_pct": 6.00,
        "ufl_vol_pct": 36.50,
        "t_autoign_k": 737.0,
        "t_surface_ig_k": 338.0,
        "lambda_s_w_mk": 0.20,
        "cp_s_j_kgk": 2530.0,
        "emissivity": 0.90,
        "ea_ht_j_mol": 132000.0,
        "a_ht_pre": 6.2e9,
        "ea_lt_j_mol": 78000.0,
        "a_lt_pre": 0.0,
        "ea_ntc_decomp_j_mol": 90000.0,
        "k_ntc_turn": 1.0e6,
    },
    "pmma": {
        "mie_1atm_air_mj": 18.0,
        "lfl_vol_pct": 1.70,
        "ufl_vol_pct": 12.50,
        "t_autoign_k": 695.0,
        "t_surface_ig_k": 650.0,
        "lambda_s_w_mk": 0.19,
        "cp_s_j_kgk": 1460.0,
        "emissivity": 0.94,
        "ea_ht_j_mol": 136000.0,
        "a_ht_pre": 5.4e9,
        "ea_lt_j_mol": 82000.0,
        "a_lt_pre": 0.0,
        "ea_ntc_decomp_j_mol": 92000.0,
        "k_ntc_turn": 1.0e6,
    },
    "sibal": {
        "mie_1atm_air_mj": 14.0,
        "lfl_vol_pct": 2.40,
        "ufl_vol_pct": 14.00,
        "t_autoign_k": 673.0,
        "t_surface_ig_k": 610.0,
        "lambda_s_w_mk": 0.085,
        "cp_s_j_kgk": 1340.0,
        "emissivity": 0.91,
        "ea_ht_j_mol": 128000.0,
        "a_ht_pre": 4.2e9,
        "ea_lt_j_mol": 76000.0,
        "a_lt_pre": 0.0,
        "ea_ntc_decomp_j_mol": 90000.0,
        "k_ntc_turn": 1.0e6,
    },
    "nomex": {
        "mie_1atm_air_mj": 85.0,
        "lfl_vol_pct": 3.80,
        "ufl_vol_pct": 18.00,
        "t_autoign_k": 773.0,
        "t_surface_ig_k": 715.0,
        "lambda_s_w_mk": 0.13,
        "cp_s_j_kgk": 1260.0,
        "emissivity": 0.89,
        "ea_ht_j_mol": 152000.0,
        "a_ht_pre": 3.5e9,
        "ea_lt_j_mol": 88000.0,
        "a_lt_pre": 0.0,
        "ea_ntc_decomp_j_mol": 95000.0,
        "k_ntc_turn": 1.0e6,
    },
    "hydrogen": {
        "mie_1atm_air_mj": 0.017,
        "lfl_vol_pct": 4.00,
        "ufl_vol_pct": 75.00,
        "t_autoign_k": 845.0,
        "t_surface_ig_k": 845.0,
        "lambda_s_w_mk": 0.18,
        "cp_s_j_kgk": 14300.0,
        "emissivity": 0.25,
        "ea_ht_j_mol": 83700.0,
        "a_ht_pre": 1.8e10,
        "ea_lt_j_mol": 70000.0,
        "a_lt_pre": 0.0,
        "ea_ntc_decomp_j_mol": 90000.0,
        "k_ntc_turn": 1.0e6,
    },
    "propane_cfig": {
        "mie_1atm_air_mj": 0.25,
        "lfl_vol_pct": 2.10,
        "ufl_vol_pct": 9.50,
        "t_autoign_k": 743.0,
        "t_surface_ig_k": 743.0,
        "lambda_s_w_mk": 0.16,
        "cp_s_j_kgk": 1680.0,
        "emissivity": 0.85,
        "ea_ht_j_mol": 129000.0,
        "a_ht_pre": 5.5e9,
        "ea_lt_j_mol": 66500.0,
        "a_lt_pre": 1.9e6,
        "ea_ntc_decomp_j_mol": 89000.0,
        "k_ntc_turn": 6.8e5,
    },
}


def compute_arrhenius_chemical_timescale_ms(
    fuel_id: str,
    temp_eval_k: float,
    x_o2: float,
    p_atm: float,
    cool_flame_capable: bool = False,
) -> Dict[str, float]:
    """
    İki dallı küresel Arrhenius kinetiği üzerinden kimyasal reaksiyon hızını (kg/m³·s)
    ve Damköhler sayısı için gerçek kimyasal zaman ölçeğini (τ_chem, ms) hesaplar:
      1) Yüksek Sıcaklık Dallanma Kolu (H + O2 -> O + OH): E_HT ~ 84–152 kJ/mol
      2) Düşük Sıcaklık Peroksi NTC Soğuk Alev Kolu (R + O2 <-> RO2 <-> QOOH, 520–800 K)
    """
    kin = IGNITION_KINETIC_DB.get(fuel_id, IGNITION_KINETIC_DB["n_heptane"])
    t_k = max(300.0, min(3000.0, float(temp_eval_k)))
    p_pa = max(20000.0, float(p_atm) * 101325.0)
    x_ox = max(0.04, min(1.0, float(x_o2)))

    # İdeal gaz konsantrasyon ölçeği [mol/m³]
    c_tot_mol_m3 = p_pa / (R_UNIV_J_MOLK * t_k)
    c_o2 = c_tot_mol_m3 * x_ox
    c_fuel_st = max(0.15, c_o2 / 3.5)

    # 1. Yüksek sıcaklık zincir dallanma hızı
    exp_ht = math.exp(-float(kin["ea_ht_j_mol"]) / (R_UNIV_J_MOLK * t_k))
    omega_ht = float(kin["a_ht_pre"]) * (c_fuel_st ** 0.25) * (c_o2 ** 1.35) * exp_ht * 1e-3

    # 2. NTC Peroksi soğuk alev hızı (yalnızca alkan/propan gibi C-C peroksi izomerizasyonu olan yakıtlarda)
    omega_lt = 0.0
    if cool_flame_capable and float(kin["a_lt_pre"]) > 0.0:
        exp_lt = math.exp(-float(kin["ea_lt_j_mol"]) / (R_UNIV_J_MOLK * t_k))
        # T > 760 K üzerinde RO2 ters ayrışması nedeniyle NTC düşüşü (Negative Temperature Coefficient)
        ntc_denom = 1.0 + float(kin["k_ntc_turn"]) * math.exp(-float(kin["ea_ntc_decomp_j_mol"]) / (R_UNIV_J_MOLK * t_k))
        if t_k > 720.0:
            ntc_denom *= math.exp((t_k - 720.0) / 55.0)
        omega_lt = (float(kin["a_lt_pre"]) * (c_fuel_st ** 0.5) * (c_o2 ** 1.0) * exp_lt * 1e-3) / max(1.0, ntc_denom)

    omega_tot = max(1e-5, omega_ht + omega_lt)
    # Gaz yoğunluğu ve karakteristik kimyasal tükenme süresi (kalibre referans: 21% O2, 1 atm, 2050 K -> ~1.6 ms)
    rho_g = (p_pa * 0.0288) / (R_UNIV_J_MOLK * t_k)
    y_f_zone = 0.062
    tau_chem_s = (rho_g * y_f_zone) / omega_tot
    tau_chem_ms = max(0.04, min(2500.0, tau_chem_s * 1000.0))

    return {
        "tau_chem_ms": round(tau_chem_ms, 3),
        "omega_ht_kg_m3s": round(omega_ht, 4),
        "omega_lt_ntc_kg_m3s": round(omega_lt, 4),
        "ntc_branch_fraction": round(omega_lt / omega_tot, 3),
    }


def compute_fire_triangle_and_preignition(
    fuel_id: str,
    fuel: Dict[str, Any],
    dil: Dict[str, Any],
    gravity_g: float,
    oxygen_pct: float,
    pressure_psia: float,
    airflow_cms: float,
    droplet_d0_mm: float,
    spalding_b: float,
    sh_conv: float,
    flame_temp_k: float,
    heat_flux_kw_m2: float,
    avionics_fault_watts: float = 0.0,
    ambient_temp_k: float = 295.15,
) -> Dict[str, Any]:
    """
    Yangın Üçgeninin 3 bileşenini (Yakıt + Oksijen + Tutuşma Enerjisi) ve
    0G aviyonik/kablo ön-tutuşma termal kaçak (Semenov ψ & Frank-Kamenetskii δ) analizini çözer.
    """
    kin = IGNITION_KINETIC_DB.get(fuel_id, IGNITION_KINETIC_DB["n_heptane"])
    p_atm = max(0.20, pressure_psia / 14.696)
    x_o2 = max(0.05, min(1.0, oxygen_pct / 100.0))

    # 1. Lewis & von Elbe Minimum Tutuşma Enerjisi (MIE, mJ)
    # E_min(P, X_O2) = E_min,0 * (1 / P_atm)^2 * (0.21 / X_O2)^2.4 * (lambda_g / lambda_N2)^1.5
    lambda_ratio = float(dil.get("lambda_g", 0.076)) / 0.076
    mie_mj = (
        float(kin["mie_1atm_air_mj"])
        * ((1.0 / p_atm) ** 2.0)
        * ((0.21 / x_o2) ** 2.4)
        * (lambda_ratio ** 1.5)
    )
    mie_mj = round(max(0.0005, min(2500.0, mie_mj)), 4)

    # İnsan vücudu elektrostatik deşarj referansı (100 pF @ 3 kV => 0.45 mJ) ve 120 VDC ark enerjisi
    esd_human_mj = 0.45
    esd_spark_vulnerable = mie_mj <= esd_human_mj

    # 2. Zabetakis / Burgess-Wheeler LFL(T,P) ve UFL(T,P,X_O2) Patlama/Yanıcılık Sınırları (% hacim)
    lfl_pct = round(max(0.4, float(kin["lfl_vol_pct"]) * (1.0 - 0.00078 * (ambient_temp_k - 298.15))), 2)
    ufl_pct = round(
        min(
            98.0,
            max(
                lfl_pct + 1.5,
                float(kin["ufl_vol_pct"])
                * (1.0 + 0.00072 * (ambient_temp_k - 298.15) + 0.065 * math.log(max(0.2, p_atm)))
                * ((x_o2 / 0.21) ** 0.85),
            ),
        ),
        2,
    )

    # Sınır tabakası etkin eşdeğerlik oranı φ (Spalding B_oq kütle transferinden yüzey yakıt kesri Y_F,s = B/(1+B))
    mw_mix = x_o2 * 32.0 + (1.0 - x_o2) * float(dil.get("mw", 28.01))
    y_o2 = min(1.0, (x_o2 * 32.0) / max(1.0, mw_mix))
    y_f_surf = spalding_b / (1.0 + spalding_b)
    # Karışım tabakası ortalama yakıt/oksijen oranı
    phi_equiv = round((0.32 * y_f_surf * float(fuel["stoich_o2_fuel"])) / max(0.02, y_o2), 2)

    # 3. Kritik Isı Akısı (CHF, q''_crit kW/m²) ve Pilotlu Tutuşma Gecikme Süresi (t_ig, sn) — Quintiere
    char_len_m = max(0.001, droplet_d0_mm / 1000.0)
    h_conv_w_m2k = max(2.5, (sh_conv * float(dil.get("lambda_g", 0.076))) / char_len_m)
    t_ig_k = float(kin["t_surface_ig_k"])
    eps = max(0.25, float(kin["emissivity"]))
    q_crit_w_m2 = (
        h_conv_w_m2k * max(15.0, t_ig_k - ambient_temp_k)
        + eps * SIGMA_SB_W_M2K4 * ((t_ig_k ** 4) - (ambient_temp_k ** 4))
    ) / eps
    chf_kw_m2 = round(max(0.8, min(65.0, q_crit_w_m2 / 1000.0)), 2)

    ext_flux_kw = max(heat_flux_kw_m2, 18.0 if flame_temp_k > 900.0 else 6.0)
    thermal_inertia = float(kin["lambda_s_w_mk"]) * float(fuel["rho_l_kg_m3"]) * float(kin["cp_s_j_kgk"])
    net_flux_w = max(850.0, (ext_flux_kw - 0.64 * chf_kw_m2) * 1000.0)
    t_ig_delay_s = (math.pi / 4.0) * thermal_inertia * (((max(15.0, t_ig_k - ambient_temp_k)) / net_flux_w) ** 2)
    t_ig_delay_s = round(max(0.1, min(600.0, t_ig_delay_s)), 2)

    # 4. 0G Ön-Tutuşma Termal Kaçak (Semenov ψ & Frank-Kamenetskii δ) — 120 VDC Kablo / Pil Isınması
    # 0G'de doğal konveksiyon soğutması sıfırlandığı için kablo/pil yüzeyi aynı Joule gücünde çok daha fazla ısınır!
    u_buoy_wire_ms = math.sqrt(max(0.0, gravity_g * 9.80665) * 0.015 * 0.35)
    u_wire_ms = math.hypot(airflow_cms / 100.0, u_buoy_wire_ms)
    nu_air_m2s = (1.6e-5) / max(0.22, p_atm)
    re_wire = (u_wire_ms * 0.008) / nu_air_m2s
    nu_wire = 2.0 + 0.60 * math.sqrt(max(0.0, re_wire)) * (0.71 ** (1.0 / 3.0))
    h_wire_w_m2k = (nu_wire * float(dil.get("lambda_g", 0.076))) / 0.008

    # Referans 120 VDC SSPC kaçak yükü (varsayılan 4.5 W kontak direnci veya harici arıza gücü)
    p_joule_w = max(3.6, float(avionics_fault_watts)) if avionics_fault_watts > 0 else 4.2
    wire_area_m2 = math.pi * 0.008 * 0.08  # 8 mm çap, 8 cm kablo demeti segmenti
    wire_vol_m3 = math.pi * (0.004 ** 2) * 0.08
    t_wire_eq_k = min(920.0, ambient_temp_k + p_joule_w / max(0.005, h_wire_w_m2k * wire_area_m2))

    ea_pre = 92000.0  # Polimer/izolasyon ön-oksidasyon aktivasyon enerjisi (J/mol)
    q_exo_w = (
        wire_vol_m3
        * 1.45e11
        * (x_o2 ** 1.2)
        * p_atm
        * math.exp(-ea_pre / (R_UNIV_J_MOLK * t_wire_eq_k))
    )
    semenov_psi = (
        (q_exo_w + 0.18 * p_joule_w)
        * ea_pre
        / max(1e-6, h_wire_w_m2k * wire_area_m2 * R_UNIV_J_MOLK * (t_wire_eq_k ** 2))
    )
    semenov_psi = round(min(4.99, max(0.01, semenov_psi)), 3)
    semenov_crit = round(1.0 / math.e, 3)  # 0.368

    fk_delta = (
        (q_exo_w / max(1e-9, wire_vol_m3))
        * ea_pre
        * (0.004 ** 2)
        / max(1e-6, float(kin["lambda_s_w_mk"]) * R_UNIV_J_MOLK * (t_wire_eq_k ** 2))
    )
    fk_delta = round(min(9.99, max(0.001, fk_delta)), 3)
    thermal_runaway_imminent = semenov_psi >= semenov_crit or fk_delta >= 2.00

    # Kabin 1G soğutma kıyaslaması (0G ısınma çarpanı)
    u_1g_ms = math.hypot(airflow_cms / 100.0, math.sqrt(9.80665 * 0.015 * 0.35))
    nu_1g = 2.0 + 0.60 * math.sqrt((u_1g_ms * 0.008) / nu_air_m2s) * (0.71 ** (1.0 / 3.0))
    zero_g_heating_penalty = round(nu_1g / max(2.0, nu_wire), 2)

    if thermal_runaway_imminent:
        preig_status_tr = f"KRİTİK TERMAL KAÇAK (ψ={semenov_psi:.2f} ≥ 0.368)"
        preig_status_en = f"CRITICAL THERMAL RUNAWAY (ψ={semenov_psi:.2f} ≥ 0.368)"
    elif esd_spark_vulnerable:
        preig_status_tr = f"ESD KIVILCIM RİSKİ (MIE={mie_mj:.3f} mJ ≤ 0.45 mJ)"
        preig_status_en = f"ESD SPARK HAZARD (MIE={mie_mj:.3f} mJ ≤ 0.45 mJ)"
    else:
        preig_status_tr = f"KARARLI ÖN-TUTUŞMA MARJI (ψ={semenov_psi:.2f} < 0.368)"
        preig_status_en = f"STABLE PRE-IGNITION MARGIN (ψ={semenov_psi:.2f} < 0.368)"

    return {
        "mie_mj": mie_mj,
        "esd_human_ref_mj": esd_human_mj,
        "esd_spark_vulnerable": esd_spark_vulnerable,
        "equivalence_ratio_phi": phi_equiv,
        "lfl_vol_pct": lfl_pct,
        "ufl_vol_pct": ufl_pct,
        "critical_heat_flux_kw_m2": chf_kw_m2,
        "ignition_delay_s": t_ig_delay_s,
        "wire_equilibrium_temp_k": round(t_wire_eq_k, 1),
        "semenov_psi": semenov_psi,
        "semenov_crit": semenov_crit,
        "frank_kamenetskii_delta": fk_delta,
        "fk_crit_cylinder": 2.00,
        "zero_g_cooling_penalty": zero_g_heating_penalty,
        "thermal_runaway_imminent": thermal_runaway_imminent,
        "status_tr": preig_status_tr,
        "status_en": preig_status_en,
    }
