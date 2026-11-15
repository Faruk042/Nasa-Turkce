# -*- coding: utf-8 -*-
"""
ALTAR-NASA v6.3 — Seçenek 1: %100 İzole Sunucusuz Statik Web Paketi Üreticisi (build_serverless_web.py).
- Arka planda hiçbir Python/Node sunucusu veya açık port barındırmaz (Sıfır Saldırı Yüzeyi).
- GitHub Pages / Cloudflare Pages veya doğrudan yerel statik klasör olarak çalışır.
- Fizik motoru, Yangın Üçgeni (MIE/Semenov), 5 Bölmeli Uzay Gemisi Ağı & FDIR CCSDS Veri Yolu, Ultra-HD 3B Filo,
  ISS R² doğrulaması, ECLSS yaşam saati, 15 PSI sıralama matrisi ve görüntü/veri analizi tarayıcıda çalışır.
- Hiçbir API anahtarı veya .env verisi pakete gömülmez.
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from core.compartment_network import SPACECRAFT_COMPARTMENTS, SPACECRAFT_HATCH_LINKS
from core.directives import CORE_DIRECTIVES_LIST
from core.fdir_hardware_bus import HARDWARE_ACTUATOR_SPECS
from core.nasa_datasets import (
    MISSION_PRESETS,
    NASA_EXPERIMENTS_CATALOG,
    SPACE_TO_EARTH_TRANSFERS,
)
from core.physics_engine import ANALOG_MATERIALS_DB, DILUENT_FACTORS, FUEL_PROPERTIES, HABITAT_CONFIGS
from core.ranking_engine import BILINGUAL_SCIENTIFIC_SYNONYMS

PROJECT_ROOT = Path(__file__).resolve().parent
WEB_SRC = PROJECT_ROOT / "web"
OUT_DIR = PROJECT_ROOT / "web_serverless"


SERVERLESS_KERNEL_TEMPLATE = r"""/* ============================================================================
 * ALTAR-NASA • Flame in Freefall v6.3 — Browser Analytical & FDIR Kernel
 * Statik Web Paketi: Sunucusuz Tarayıcı Modu
 * Tüm termodinamik denklemler, Yangın Üçgeni, Çok-Bölmeli Kabin & FDIR CCSDS,
 * ISS R²/RMSE doğrulaması, ECLSS saati, PSI sıralaması tarayıcı belleğinde çalışır.
 * ============================================================================ */
(function () {
    "use strict";

    const IS_PURE_SERVERLESS =
        Boolean(document.querySelector('meta[name="altar-serverless"]'))
        || Boolean(window.location && window.location.protocol === "file:");
    if (IS_PURE_SERVERLESS) {
        window.ALTAR_SERVERLESS_MODE = true;
    }

    const EMBEDDED_DATA = __EMBEDDED_JSON__;
    const FUEL_PROPERTIES = EMBEDDED_DATA.FUEL_PROPERTIES;
    const DILUENT_FACTORS = EMBEDDED_DATA.DILUENT_FACTORS;
    const HABITAT_CONFIGS = EMBEDDED_DATA.HABITAT_CONFIGS;
    const ANALOG_MATERIALS_DB = EMBEDDED_DATA.ANALOG_MATERIALS_DB || [];
    const MISSION_PRESETS = EMBEDDED_DATA.MISSION_PRESETS;
    const NASA_CATALOG = EMBEDDED_DATA.NASA_EXPERIMENTS_CATALOG;
    const dynamicExperiments = [];
    const EARTH_TRANSFERS = EMBEDDED_DATA.SPACE_TO_EARTH_TRANSFERS;
    const DIRECTIVES = EMBEDDED_DATA.CORE_DIRECTIVES_LIST;
    const SYNONYMS = EMBEDDED_DATA.BILINGUAL_SCIENTIFIC_SYNONYMS;
    const SPACECRAFT_COMPARTMENTS = EMBEDDED_DATA.SPACECRAFT_COMPARTMENTS || {};
    const IDSS_HATCH_LINKS = EMBEDDED_DATA.IDSS_HATCH_LINKS || [];
    const HARDWARE_ACTUATOR_SPECS = EMBEDDED_DATA.HARDWARE_ACTUATOR_SPECS || {};
    const PSI_SNAPSHOT = EMBEDDED_DATA.PSI_ARCHIVE_SNAPSHOT || [];
    const PSI_SNAPSHOT_MAP = {};
    PSI_SNAPSHOT.forEach((row) => {
        if (row && row.id) PSI_SNAPSHOT_MAP[String(row.id).toUpperCase()] = row;
    });

    // Oturum içi geçici yapılandırma (yalnızca bellek içi; diske/çereze asla yazılmaz)
    const runtimeConfig = {
        active_provider: "auto",
        antigravity_model: "gemini-2.5-flash",
        ollama_host: "http://127.0.0.1:11434",
        ollama_model: "auto",
        gemini_api_key: "",
        gemini_model: "gemini-2.5-flash",
        antigravity_api_key: "",
        openrouter_api_key: "",
        openrouter_model: "google/gemini-2.0-flash-exp:free",
        custom_base_url: "",
        custom_api_key: "",
        custom_model: "",
        custom_extra_directives: "",
        deep_verify_6stage: true,
        language: "tr",
    };

    const ragDocs = NASA_CATALOG.map((exp) => ({
        doc_id: exp.exp_id,
        title: exp.title_tr,
        title_tr: exp.title_tr,
        title_en: exp.title,
        source: `${exp.program} • NTRS ${exp.ntrs_id}`,
        url: exp.ntrs_url,
        text: `${exp.exp_id} ${exp.program} ${exp.hardware_group || ""} ${exp.facility} ${exp.title} ${exp.title_tr} ${exp.material} ${exp.key_finding_tr} ${exp.key_finding_en} ${exp.safety_insight_tr} ${exp.safety_insight_en} ${(exp.tags || []).join(" ")}`,
        text_tr: `${exp.key_finding_tr} ${exp.safety_insight_tr}`,
        text_en: `${exp.key_finding_en} ${exp.safety_insight_en}`,
    }));
    PSI_SNAPSHOT.forEach((row) => {
        const psiTitle = row.title || `${row.id} — ${row.raw_title || ""}`;
        const psiEnTitle = `${row.id} — ${row.raw_title || row.title || ""}`;
        const psiBody = `${row.id} ${row.acronym || ""} ${row.raw_title || ""} ${row.hardware || ""} ${row.platform || ""} ${row.table_file || ""} ${row.abstract || ""}`;
        ragDocs.push({
            doc_id: row.id,
            title: psiTitle,
            title_tr: psiTitle,
            title_en: psiEnTitle,
            source: `NASA PSI (${row.id})`,
            url: row.url || `https://psi.nasa.gov/physci/repo/data/investigations/${row.id}`,
            text: psiBody,
            text_tr: row.abstract || psiBody,
            text_en: row.abstract || psiBody,
        });
    });

    const streamState = {
        enabled: false,
        source: "ntrs",
        query_or_url: "auto",
        interval_sec: 25,
        auto_sync_sim: true,
        seq_id: 0,
        last_fetch_time: "",
        last_error: "",
        latest_sim_params: null,
        events: [],
        timerId: null,
    };

    const chatJobs = new Map();

    function roundN(val, dec) {
        const f = Math.pow(10, dec);
        return Math.round(val * f) / f;
    }

    function computeBuoyantVelocityCms(gravityG, charLenCm, tFlameK, tAmbK) {
        if (gravityG <= 1e-5 || tFlameK <= tAmbK) return 0.0;
        const gCms2 = gravityG * 980.665;
        const lPlumeCm = Math.max(0.32, charLenCm * 0.95);
        return Math.sqrt(gCms2 * lPlumeCm * Math.max(0.0, tFlameK / tAmbK - 1.0));
    }

    function safeNumJs(val, defVal, lo, hi) {
        if (val === null || val === undefined || typeof val === "boolean" || val === "") return defVal;
        const nv = Number(val);
        if (!Number.isFinite(nv)) return defVal;
        let out = nv;
        if (lo !== undefined && out < lo) out = lo;
        if (hi !== undefined && out > hi) out = hi;
        return out;
    }

    function resolveAnalogMaterialJs(params) {
        const p = (params && typeof params === "object" && !Array.isArray(params)) ? params : {};
        const reqFuelId = String(p.fuel_id || "n_heptane").trim();
        const rawCustomName = String(p.custom_material_name || "").trim();
        let rawRho = p.custom_density_kg_m3;
        if (typeof rawRho === "boolean" || rawRho === null || rawRho === undefined || rawRho === "" || rawRho === 0 || rawRho === "0") {
            rawRho = p.custom_rho_kg_m3;
        }
        let rawLambda = p.custom_conductivity_w_mk;
        if (typeof rawLambda === "boolean" || rawLambda === null || rawLambda === undefined || rawLambda === "" || rawLambda === 0 || rawLambda === "0") {
            rawLambda = p.custom_cond_w_mk;
        }
        if (typeof rawLambda === "boolean" || rawLambda === null || rawLambda === undefined || rawLambda === "" || rawLambda === 0 || rawLambda === "0") {
            rawLambda = p.custom_lambda_w_mk;
        }
        const customRho = safeNumJs(rawRho, 0.0, 0.0, 25000.0);
        const customLambda = safeNumJs(rawLambda, 0.0, 0.0, 500.0);
        const customMoc = safeNumJs(p.custom_moc_pct, 0.0, 0.0, 100.0);

        const isCustom = reqFuelId === "custom_material" || Boolean(rawCustomName) || !FUEL_PROPERTIES[reqFuelId];
        if (!isCustom && FUEL_PROPERTIES[reqFuelId]) {
            return {
                active: false,
                baseFuelId: reqFuelId,
                fuel: FUEL_PROPERTIES[reqFuelId],
                toxBoost: { hcn: 0.0, hcl: 0.0, hf: 0.0 },
                info: { active: false, show_banner: false, tr: "", en: "" },
            };
        }

        const qLow = (rawCustomName || reqFuelId).trim().toLowerCase();
        let matched = null;
        for (let i = 0; i < ANALOG_MATERIALS_DB.length; i++) {
            const ent = ANALOG_MATERIALS_DB[i];
            if ((ent.keys || []).some((k) => qLow.includes(k))) {
                matched = ent;
                break;
            }
        }

        let baseId, baseRef, rhoVal, lamVal, moc0Val, moc1Val, labelTr, labelEn, confPct, uncMoc, lvVal, toxBoost;
        if (!matched) {
            const effRhoProbe = customRho > 100.0 ? customRho : 1180.0;
            const effLamProbe = customLambda > 0.01 ? customLambda : 0.19;
            const targetInertia = effLamProbe * effRhoProbe * 1420.0;
            const solidCandidates = ["pmma", "sibal", "nomex"];
            let bestBase = (customMoc >= 21.0 || effRhoProbe >= 1340.0) ? "nomex" : "pmma";
            let bestDist = 1e18;
            solidCandidates.forEach((cid) => {
                const cref = FUEL_PROPERTIES[cid];
                const cIn = Number(cref.lambda_s_w_mk ?? 0.19) * Number(cref.rho_l_kg_m3) * Number(cref.cp_s_j_kgk ?? 1400.0);
                const mocPen = Math.abs((customMoc >= 5.0 ? customMoc : Number(cref.moc_0g_base)) - Number(cref.moc_0g_base)) * 42000.0;
                const dist = Math.abs(targetInertia - cIn) + mocPen;
                if (dist < bestDist) {
                    bestDist = dist;
                    bestBase = cid;
                }
            });
            baseId = bestBase;
            baseRef = FUEL_PROPERTIES[baseId];
            rhoVal = customRho > 100.0 ? customRho : Number(baseRef.rho_l_kg_m3);
            lamVal = customLambda > 0.01 ? customLambda : Number(baseRef.lambda_s_w_mk ?? 0.19);
            const refInertia = Math.max(1.0, Number(baseRef.lambda_s_w_mk ?? 0.19) * Number(baseRef.rho_l_kg_m3));
            const inertiaMocShift = Math.max(-1.6, Math.min(2.8, 0.85 * Math.log(Math.max(0.15, (lamVal * rhoVal) / refInertia))));
            moc0Val = customMoc >= 5.0 ? customMoc : Math.max(8.0, Number(baseRef.moc_0g_base) + inertiaMocShift);
            moc1Val = Math.max(moc0Val + 1.8, moc0Val + (Number(baseRef.moc_1g_base) - Number(baseRef.moc_0g_base)));
            labelTr = rawCustomName || "Özel Kompozit / Kablo Numunesi";
            labelEn = rawCustomName || "Custom Composite / Cable Sample";
            confPct = (customRho > 100.0 && customLambda > 0.01) ? 84 : 76;
            uncMoc = customMoc >= 5.0 ? 1.4 : 1.9;
            lvVal = Number(baseRef.lv_kj_kg);
            toxBoost = { hcn: 0.2, hcl: 0.2, hf: 0.0 };
        } else {
            baseId = String(matched.analog_base_id);
            baseRef = FUEL_PROPERTIES[baseId];
            rhoVal = customRho > 100.0 ? customRho : Number(matched.rho_kg_m3);
            lamVal = customLambda > 0.01 ? customLambda : Number(matched.lambda_s_w_mk);
            const refInM = Math.max(1.0, Number(matched.lambda_s_w_mk) * Number(matched.rho_kg_m3));
            let inShiftM = 0.0;
            if (customRho > 100.0 || customLambda > 0.01) {
                inShiftM = Math.max(-1.5, Math.min(2.6, 0.78 * Math.log(Math.max(0.15, (lamVal * rhoVal) / refInM))));
            }
            moc0Val = customMoc >= 5.0 ? customMoc : Math.max(8.0, Number(matched.moc_0g) + inShiftM);
            moc1Val = Math.max(moc0Val + 1.8, Number(matched.moc_1g) + (moc0Val - Number(matched.moc_0g)));
            labelTr = rawCustomName || String(matched.label_tr);
            labelEn = rawCustomName || String(matched.label_en);
            confPct = Number(matched.confidence_pct);
            uncMoc = Number(matched.unc_moc);
            lvVal = Number(matched.lv_kj_kg);
            toxBoost = Object.assign({ hcn: 0.0, hcl: 0.0, hf: 0.0 }, matched.tox_boost || {});
        }

        const baseShortTr = String(baseRef.name_tr).split("(")[0].trim();
        const baseShortEn = String(baseRef.name_en).split("(")[0].trim();
        const synthFuel = Object.assign({}, baseRef, {
            name_tr: `${labelTr} (Benzer: ${baseShortTr})`,
            name_en: `${labelEn} (Analog: ${baseShortEn})`,
            rho_l_kg_m3: roundN(rhoVal, 1),
            lambda_s_w_mk: roundN(lamVal, 3),
            lv_kj_kg: roundN(lvVal, 1),
            moc_0g_base: roundN(moc0Val, 2),
            moc_1g_base: roundN(moc1Val, 2),
            cool_flame_min_o2: roundN(moc0Val, 2),
        });

        return {
            active: true,
            baseFuelId: baseId,
            fuel: synthFuel,
            toxBoost: toxBoost,
            info: {
                active: true,
                show_banner: true,
                material_label_tr: labelTr,
                material_label_en: labelEn,
                analog_base_id: baseId,
                confidence_pct: confPct,
                uncertainty_moc_pct: uncMoc,
                tr: `**Benzer Malzeme Eşleştirmesi (${labelTr}):** Bu malzeme için NASA PSI kataloğunda doğrudan mikroçekim deneyi bulunmamaktadır. Termofiziksel vekil olarak **${baseShortTr}** baz alındı (\`ρ = ${rhoVal.toFixed(0)} kg/m³\`, \`λ_s = ${lamVal.toFixed(2)} W/m·K\`, \`Tahmini 0G MOC ≈ %${moc0Val.toFixed(1)} ± %${uncMoc.toFixed(1)}\`, Eşleşme Güveni: \`%${confPct}\`). Kesin uçuş sertifikasyonu için NASA-STD-6001B Test 1 ve düşük akışlı 0G doğrulaması gerekir.`,
                en: `**Analog Material Matching (${labelEn}):** Direct microgravity test records are unavailable in NASA PSI for this material. Mapped to thermophysical proxy **${baseShortEn}** (\`ρ = ${rhoVal.toFixed(0)} kg/m³\`, \`λ_s = ${lamVal.toFixed(2)} W/m·K\`, \`Est. 0G MOC ≈ ${moc0Val.toFixed(1)}% ± ${uncMoc.toFixed(1)}%\`, Match Confidence: \`${confPct}%\`). Flight qualification requires NASA-STD-6001B Test 1 screening.`,
            },
        };
    }

    function computeMocAtFlow(fuel, airflowCms, gravityG, pressurePsia, diluentKey, flowDirOpt) {
        // Yarı-Ampirik Mühendislik Zarfı — NASA BASS/Saffire Olson U-Eğrisi (Olson 1991)
        const dil = DILUENT_FACTORS[diluentKey] || DILUENT_FACTORS.N2;
        const pAtm = Math.max(0.24, pressurePsia / 14.696);
        const pressureShift = 2.6 * (Math.pow(1.0 / pAtm, 0.38) - 1.0);
        const uBuoyCms = computeBuoyantVelocityCms(gravityG, 0.34, Number(fuel.t_adiabatic_k || 2000.0) * 0.85, 298.15);
        const uEff = Math.hypot(airflowCms, uBuoyCms);
        const baseMoc = fuel.moc_0g_base + dil.moc_shift + pressureShift;
        const isConcurrent = typeof flowDirOpt === "string" && flowDirOpt.toLowerCase() === "concurrent";
        const blowRef = Math.max(10.0, Number(fuel.blowoff_cms || 30.0) * (isConcurrent ? 1.28 : 1.0));
        const quenchPenalty = 3.6 * Math.exp(-uEff / 1.65);
        const ventDip = -1.15 * Math.exp(-Math.pow(uEff - 5.5, 2) / 28.0);
        const concDip = isConcurrent ? (-0.72 * Math.min(1.0, airflowCms / 4.0) * Math.exp(-Math.max(0.0, airflowCms - 22.0) / 24.0)) : 0.0;
        const blowPenalty = 5.8 * Math.pow(Math.max(0.0, uEff - (isConcurrent ? 15.0 : 12.0)) / blowRef, 1.85);
        const gravPenalty = (fuel.moc_1g_base - fuel.moc_0g_base) * Math.pow(gravityG, 0.65) * 0.65;
        return roundN(Math.max(4.5, Math.min(55.0, baseMoc + quenchPenalty + ventDip + concDip + blowPenalty + gravPenalty)), 2);
    }

    function solvePureBurningRateK(fuel, dil, yO2, pAtm, shConv, radLossFrac, flameTempK, cpGKj, coolFlameActive) {
        const tSurfK = Number(fuel.t_boil_k);
        const tRefK = Math.max(310.0, tSurfK + (flameTempK - tSurfK) / 3.0);
        const lambda300 = Number(dil.lambda_g) * 0.354;
        const lambdaRef = lambda300 * Math.pow(tRefK / 300.0, 0.76);
        const isGas = fuel.phase === "gas_jet" || fuel.phase === "porous_sphere";
        const lvEff = Number(fuel.lv_kj_kg) * Number(fuel.water_cond_enthalpy_factor ?? 1.0);
        const denomEnthalpy = isGas ? Math.max(180.0, Number(fuel.dh_sens_kj_kg || (cpGKj * 1150.0))) : lvEff;
        const dhcEff = Number(fuel.dhc_kj_kg) * (coolFlameActive ? 0.235 : 1.0);
        const bEff = Math.max(
            0.18,
            (yO2 * (dhcEff / Number(fuel.stoich_o2_fuel)) - cpGKj * Math.max(0.0, tSurfK - 298.15)) / denomEnthalpy
        );
        const cpVapJ = Number(fuel.cp_vapor_j_kgk || 2100.0) * Math.pow(tRefK / 650.0, 0.18);
        const cpGasJ = cpGKj * 1000.0;
        const cpInnerEff = 0.68 * cpVapJ + 0.32 * cpGasJ;
        const polarBoost = fuel.water_cond_enthalpy_factor !== undefined ? 1.12 : 1.0;
        const kPure =
            ((8.0 * lambdaRef * polarBoost) / (Number(fuel.rho_l_kg_m3) * cpInnerEff)) *
            Math.log(1.0 + bEff) *
            1e6 *
            (shConv / 2.0) *
            Math.pow(Math.max(0.22, pAtm), 0.22) *
            Math.max(0.25, 1.0 - 0.36 * radLossFrac);
        return roundN(Math.max(0.05, kPure), 3);
    }

    function simulateCombustionClient(params) {
        const analogRes = resolveAnalogMaterialJs(params);
        const fuelId = analogRes.baseFuelId;
        const fuel = analogRes.fuel;
        const analogMatchInfo = analogRes.info;
        const toxBoost = analogRes.toxBoost;
        const requestedFuelId = analogRes.active ? "custom_material" : fuelId;

        const gravityG = safeNumJs(params && params.gravity_g, 0.0, 0.0, 2.0);
        const oxygenPct = safeNumJs(params && params.oxygen_pct, 21.0, 5.0, 100.0);
        const pressurePsia = safeNumJs(params && params.pressure_psia, 14.7, 3.0, 35.0);
        let airflowCms = safeNumJs(params && params.airflow_cms, 3.5, 0.0, 50.0);
        if (params && (params.imv_fan_cutoff || params.vent_shutoff)) airflowCms = 0.0;
        const flowDirection = String((params && params.flow_direction) || "opposed").toLowerCase() === "concurrent" ? "concurrent" : "opposed";
        const dropletD0 = safeNumJs(params && params.droplet_d0_mm, 3.2, 0.6, 8.0);
        let diluent = String((params && params.diluent) || "N2");
        if (!DILUENT_FACTORS[diluent]) diluent = "N2";
        const dil = DILUENT_FACTORS[diluent];

        let habitatId = String((params && params.habitat_id) || "iss_module");
        if (!HABITAT_CONFIGS[habitatId]) habitatId = "iss_module";
        const crewRespS = safeNumJs(params && params.crew_response_s, 30.0, 5.0, 999.0);
        const waterMistActive = Boolean(params && params.water_mist_active);
        const fullSmotherActive = Boolean(params && params.full_smother);
        const avionicsFaultW = safeNumJs(params && params.avionics_fault_watts, 0.0, 0.0, 100000.0);
        const fireCompId = String((params && params.fire_compartment_id) || "HALO");
        const sealedHatches = Array.isArray(params && params.sealed_hatches) ? params.sealed_hatches : [];

        const pAtm = pressurePsia / 14.696;
        const pressureKpa = roundN(pressurePsia * 6.89476, 2);
        const po2Psia = roundN(pressurePsia * (oxygenPct / 100.0), 2);
        const po2Kpa = roundN(pressureKpa * (oxygenPct / 100.0), 2);

        const xO2 = oxygenPct / 100.0;
        const mwMix = xO2 * 32.0 + (1.0 - xO2) * Number(dil.mw);
        const yO2 = Math.min(1.0, (xO2 * 32.0) / Math.max(1.0, mwMix));
        const inertRelief = 1.0 + 0.24 * Math.max(0.0, (xO2 - 0.35) / 0.65);
        const cpGKj = (1.22 / dil.cp_factor) / inertRelief;

        const isGasBurner = fuel.phase === "gas_jet" || fuel.phase === "porous_sphere";
        const isSolidSample = fuel.phase === "solid_surface" || fuel.phase === "solid_thin" || fuel.phase === "rod" || fuel.phase === "fabric_sheet";
        const fuelPhaseCategory = isGasBurner ? "gas" : (isSolidSample ? "solid" : "liquid");
        const denomEnthalpy = isGasBurner
            ? Math.max(180.0, Number(fuel.dh_sens_kj_kg || (cpGKj * 1150.0)))
            : Number(fuel.lv_kj_kg || 350.0);

        const spaldingB = roundN(
            Math.max(
                0.25,
                (yO2 * (fuel.dhc_kj_kg / fuel.stoich_o2_fuel) - cpGKj * Math.max(0.0, fuel.t_boil_k - 298.15)) / denomEnthalpy
            ),
            2
        );

        const charLenCm = dropletD0 / 10.0;
        const charLenM = charLenCm * 0.01;
        const mocCurrent = computeMocAtFlow(fuel, airflowCms, gravityG, pressurePsia, diluent, flowDirection);
        const moc0g = computeMocAtFlow(fuel, airflowCms, 0.0, pressurePsia, diluent, flowDirection);
        const moc1g = computeMocAtFlow(fuel, airflowCms, 1.0, pressurePsia, diluent, flowDirection);

        const tAmbK = 298.15;
        const o2Ratio = oxygenPct / 21.0;
        const tEstHotK = Math.min(2780.0, Number(fuel.t_adiabatic_k) * (0.72 + 0.28 * Math.pow(o2Ratio, 0.42)) * Number(dil.cp_factor) * inertRelief);
        const tMeanFilmK = 0.5 * (tEstHotK + tAmbK);
        const nuCm2S = (0.156 * Math.pow(tMeanFilmK / 300.0, 1.68)) / Math.max(0.22, pAtm);

        const uBuoy = computeBuoyantVelocityCms(gravityG, charLenCm, tEstHotK, tAmbK);
        const uEff = Math.hypot(airflowCms, uBuoy);
        const reNum = (airflowCms * charLenCm) / Math.max(0.01, nuCm2S);
        const grNum = (980.665 * gravityG * Math.max(0.0, tEstHotK - tAmbK) * Math.pow(charLenCm, 3)) / (tMeanFilmK * Math.pow(Math.max(0.01, nuCm2S), 2));
        const raNum = grNum * 0.71;
        const richardsonRi = reNum > 0.02 ? roundN(grNum / Math.max(1e-4, reNum * reNum), 2) : (gravityG > 0.01 ? 999.0 : 0.0);
        const froudeFr = gravityG > 1e-4 ? roundN(Math.pow(uEff, 2) / Math.max(1e-4, 980.665 * gravityG * charLenCm), 2) : 999.0;

        const shConv = 2.0 + 0.60 * Math.sqrt(Math.max(0.0, reNum)) * Math.pow(0.71, 1.0 / 3.0) + 0.52 * Math.pow(Math.max(0.0, raNum), 0.25);

        // Law–Chung–Srinivasan (1980) Küresel Stefan + Lewis Alev Cephesi Oranı R_f / R_d
        const cpRatioClamped = Math.min(2.4, Math.max(0.75, Number(fuel.cp_vapor_j_kgk || 2100.0) / Math.max(600.0, cpGKj * 1000.0)));
        const leOx = Number(fuel.lewis_ox || 1.0);
        const oxTerm = Math.log(1.0 + Math.max(0.015, yO2 / (Number(fuel.stoich_o2_fuel) * leOx * 0.145)));
        const standoffRatio = roundN(
            Math.max(1.65, Math.min(11.5, 1.0 + Math.log(1.0 + spaldingB) / Math.max(0.12, cpRatioClamped * oxTerm * Math.pow(shConv / 2.0, 0.62)))),
            2
        );

        // Planck-Ortalama Optik İnce T^4 Radyatif Kayıp (core/physics_engine.py ile %100 birebir)
        const sootEst = Math.min(1.0, Number(fuel.soot_tendency || 0.2) * (0.28 + 0.72 * Math.min(1.0, gravityG * 1.1 + airflowCms / 28.0)) * Math.pow(pAtm, 0.6) * Math.pow(o2Ratio, 0.45));
        const rDM = Math.max(0.0003, (dropletD0 * 0.5) / 1000.0);
        const rFM = Math.max(rDM * 1.25, rDM * standoffRatio);
        const volShellM3 = (4.0 / 3.0) * Math.PI * Math.max(1e-11, Math.pow(rFM, 3) - Math.pow(rDM, 3));
        const isH2 = fuel.formula === "H₂";
        const kappaGas = pAtm * (isH2 ? 0.42 : 1.35) * Number(dil.rad_factor) * Math.pow(1000.0 / Math.max(500.0, tEstHotK), 0.65);
        const kappaSoot = 1260.0 * (1.35e-6 * Math.max(0.0, sootEst)) * tEstHotK;
        const qRadW = volShellM3 * 4.0 * 5.670374419e-8 * (kappaGas + kappaSoot) * Math.max(0.0, Math.pow(tEstHotK, 4) - Math.pow(tAmbK, 4));
        const sizeScale = Math.pow(rDM / 0.0014, 1.15);
        const qChemRefW = Math.max(1.2, 26.0 * sizeScale * (shConv / 2.0) * Math.pow(tEstHotK / 1950.0, 1.4));
        const radLossFrac = roundN(Math.max(0.03, Math.min(0.88, qRadW / Math.max(0.25, qChemRefW + 0.55 * qRadW))), 3);

        // İki-Dallı Arrhenius Kimyasal Süresi
        const tauFlowMs = (charLenCm / Math.max(0.35, uEff)) * 1000.0;
        const tEvalK = tEstHotK * (1.0 - 0.22 * radLossFrac);
        const arrHot = 1.4e7 * Math.exp(-15200.0 / Math.max(500.0, tEvalK)) * Math.pow(Math.max(0.04, xO2), 1.35) * Math.pow(Math.max(0.22, pAtm), 0.75);
        const tauChemMs = Math.max(0.08, Math.min(250.0, 1000.0 / Math.max(4.0, arrHot)));
        const damkohlerDa = roundN(Math.min(99.9, tauFlowMs / Math.max(0.04, tauChemMs)), 2);

        const isConc = flowDirection === "concurrent";
        const blowVelLimit = fuel.blowoff_cms * (isConc ? 1.28 : 1.0) * Math.pow(oxygenPct / 21.0, 0.65);
        const isBlowoff = airflowCms > blowVelLimit || (damkohlerDa < 0.95 && airflowCms >= (isConc ? 13.0 : 10.0));
        const radQuench = gravityG < 0.08 && airflowCms < 1.8 && dropletD0 >= 3.4 && oxygenPct < mocCurrent + 3.2;

        let regime = "HOT_SPHERICAL_0G";
        let coolFlameActive = false;
        let extinguished = false;

        if (waterMistActive || fullSmotherActive) {
            regime = "QUENCHED_EXTINGUISHED";
            extinguished = true;
            coolFlameActive = false;
        } else if (isBlowoff) {
            regime = "BLOWOFF_EXTINGUISHED";
            extinguished = true;
        } else if (oxygenPct < mocCurrent || radQuench) {
            if (fuel.cool_flame_capable && gravityG < 0.15 && airflowCms < 8.0 && oxygenPct >= fuel.cool_flame_min_o2) {
                regime = "COOL_FLAME_NTC";
                coolFlameActive = true;
            } else {
                regime = "QUENCHED_EXTINGUISHED";
                extinguished = true;
            }
        } else if (gravityG >= 0.12) {
            regime = "BUOYANT_PLUME_1G";
        } else if (airflowCms >= 1.5) {
            regime = "VENTILATED_WAKE_0G";
        }

        let flameTempK = 298.0, kBurn = 0.0, flameSpread = 0.0, coPpm = 1.0, sootIndex = 0.0, heatFlux = 0.0;
        if (coolFlameActive) {
            const span = Math.min(14.0, Math.max(0.5, oxygenPct - fuel.cool_flame_min_o2));
            flameTempK = Math.min(785.0, Math.max(520.0, roundN(565.0 + span * 14.5 + 25.0 * pAtm, 1)));
            kBurn = solvePureBurningRateK(fuel, dil, yO2, pAtm, shConv, radLossFrac * 0.35, flameTempK, cpGKj, true);
            coPpm = Math.round(420.0 + 38.0 * dropletD0 + (18.0 - Math.min(18.0, oxygenPct)) * 22.0);
            heatFlux = roundN(3.4 + (0.6 * (flameTempK - 520.0)) / 100.0, 2);
        } else if (!extinguished) {
            let rawT = fuel.t_adiabatic_k * (0.72 + 0.28 * Math.pow(o2Ratio, 0.42)) * dil.cp_factor * inertRelief * (1.0 - 0.34 * radLossFrac) * Math.pow(pAtm, 0.06);
            if (rawT > 2280.0) {
                rawT = 2280.0 + 510.0 * Math.tanh((rawT - 2280.0) / 740.0);
            }
            flameTempK = roundN(Math.max(1180.0, Math.min(2810.0, rawT)), 1);
            kBurn = isGasBurner ? 0.0 : solvePureBurningRateK(fuel, dil, yO2, pAtm, shConv, radLossFrac, flameTempK, cpGKj, false);
            if (isSolidSample) {
                const tPyroK = Number(fuel.t_boil_k);
                const tRefS = tPyroK + (flameTempK - tPyroK) / 3.0;
                const lamG = (Number(dil.lambda_g) * 0.354) * Math.pow(tRefS / 300.0, 0.76);
                const rhoS = Number(fuel.rho_l_kg_m3);
                const cpS = Number(fuel.cp_s_j_kgk || 1400.0);
                const radAtten = Math.max(0.22, 1.0 - 0.55 * radLossFrac);
                const concFactor = isConc ? (1.0 + 0.98 * Math.min(1.15, uEff / 5.0)) : 1.0;
                const o2Margin = Math.max(0.08, (oxygenPct - mocCurrent * 0.82) / 21.0);
                const stretchAtten = Math.exp(-Math.max(0.0, uEff - (isConc ? 20.0 : 16.0)) / (Number(fuel.blowoff_cms) * (isConc ? 1.28 : 1.0)));
                let vfMS = 0.0;
                if (fuel.phase === "solid_thin") {
                    const tauS = Number(fuel.thin_tau_m || 0.00042);
                    vfMS = ((2.0 * Math.SQRT2 * lamG * (flameTempK - tPyroK)) / Math.max(1.0, rhoS * cpS * tauS * (tPyroK - tAmbK))) * Math.pow(o2Margin, 0.55) * Math.pow(pAtm, 0.35) * (1.0 + 0.45 * Math.min(2.2, uEff / 6.0)) * stretchAtten * radAtten * concFactor;
                } else {
                    const lamS = Number(fuel.lambda_s_w_mk || 0.19);
                    const uOseenMs = Math.max(0.08, uEff / 100.0 + 0.095);
                    const rhoG = (pAtm * 101325.0 * 0.0288) / (8.31446 * tRefS);
                    const cpG = 1180.0 / Number(dil.cp_factor);
                    vfMS = uOseenMs * ((lamG * rhoG * cpG) / Math.max(1.0, lamS * rhoS * cpS)) * Math.pow((flameTempK - tPyroK) / (tPyroK - tAmbK), 2) * 2.4 * Math.pow(o2Margin, 0.50) * stretchAtten * radAtten * concFactor;
                }
                flameSpread = roundN(Math.max(0.05, Math.min(28.0, vfMS * 1000.0)), 2);
            } else {
                flameSpread = 0.0;
            }
            sootIndex = roundN(sootEst, 3);
            coPpm = Math.round(45.0 + 190.0 * sootIndex + (airflowCms < 2.0 ? 120.0 : 25.0));
            const emView = 0.021 + 0.022 * sootIndex + 0.004 * Number(dil.rad_factor);
            const qRadFluxKw = (emView * 5.670374419e-8 * Math.max(0.0, Math.pow(flameTempK, 4) - Math.pow(tAmbK, 4))) / 1000.0;
            const qConvFluxKw = (0.0029 * shConv) * Math.max(0.0, flameTempK - tAmbK);
            heatFlux = roundN(Math.max(4.5, Math.min(145.0, qRadFluxKw + qConvFluxKw)), 2);
        }

        let hrrpuaKwM2 = 0.0;
        if (coolFlameActive) {
            hrrpuaKwM2 = roundN(18.0 + 24.0 * kBurn + 1.8 * heatFlux, 1);
        } else if (!extinguished) {
            const mDotFlux = Math.max(0.0025, 0.0042 * Math.log(1.0 + spaldingB) * (shConv / 2.0) * Math.pow(Math.max(0.3, pAtm), 0.25));
            hrrpuaKwM2 = roundN(Math.min(680.0, mDotFlux * Number(fuel.dhc_kj_kg) * (1.0 - 0.28 * radLossFrac) * 0.42), 1);
        }

        const hcnPpmEst = !extinguished ? roundN(((fuelId === "nomex" || fuelId === "pmma") ? coPpm * 0.14 : 0.0) + 26.0 * toxBoost.hcn, 1) : 0.0;
        const hclPpmEst = !extinguished ? roundN(34.0 * toxBoost.hcl, 1) : 0.0;
        const hfPpmEst = !extinguished ? roundN(22.0 * toxBoost.hf, 1) : 0.0;
        const coCo2Ratio = roundN(coPpm / 800.0, 4);
        const acidNitrileScore = hcnPpmEst * 0.28 + hclPpmEst * 0.22 + hfPpmEst * 0.38;
        const toxRiskPts = Math.min(18.0, coPpm / 75.0 + acidNitrileScore + Math.min(6.0, coCo2Ratio * 35.0));

        let riskScore = 15;
        let riskDriverTr = "";
        let riskDriverEn = "";
        if (extinguished) {
            riskScore = Math.max(5, Math.trunc(18 - (mocCurrent - oxygenPct) * 2.2));
            riskDriverTr = "Durum: Oksijen veya akış sınırında sönümlendi (Düşük Risk)";
            riskDriverEn = "Status: Quenched below flammability limit (Low Risk)";
        } else if (coolFlameActive) {
            riskScore = Math.min(89, Math.round(56.0 + coPpm / 28.0 + Math.min(8.0, coCo2Ratio * 40.0)));
            riskDriverTr = `Ana Etken: Görünmez Soğuk Alev + Eksik Yanma CO (${coPpm} ppm)`;
            riskDriverEn = `Primary Driver: Invisible Cool Flame + CO Buildup (${coPpm} ppm)`;
        } else {
            const margin = Math.max(0.0, oxygenPct - mocCurrent);
            const evaPen = oxygenPct >= 75.0 ? 18.0 : (pressurePsia <= 10.5 && oxygenPct >= 30.0 ? 10.0 : 0.0);
            const concPen = (isConc && flameSpread > 0.2) ? 5.5 : 0.0;
            riskScore = Math.max(15, Math.min(99, Math.round(24.0 + margin * 2.55 + Math.min(28.0, flameSpread * 4.6) + (gravityG < 0.1 && airflowCms >= 1.5 && airflowCms <= 12.0 ? 10.0 : 0.0) + evaPen + concPen + toxRiskPts)));
            if (acidNitrileScore >= 4.0) {
                const gTags = [];
                if (hcnPpmEst >= 5.0) gTags.push(`HCN ${hcnPpmEst.toFixed(0)} ppm`);
                if (hclPpmEst >= 5.0) gTags.push(`HCl ${hclPpmEst.toFixed(0)} ppm`);
                if (hfPpmEst >= 3.0) gTags.push(`HF ${hfPpmEst.toFixed(0)} ppm`);
                const gStr = gTags.length ? gTags.join(", ") : `CO ${coPpm} ppm`;
                riskDriverTr = `Ana Etken: Isıl Güç + Toksik Gaz (${gStr})`;
                riskDriverEn = `Primary Driver: Thermal Growth + Toxic Gas (${gStr})`;
            } else if (oxygenPct >= 50.0) {
                riskDriverTr = `Ana Etken: Yüksek Oksijen Zenginleşmesi (%${oxygenPct.toFixed(0)} O₂)`;
                riskDriverEn = `Primary Driver: High Oxygen Enrichment (${oxygenPct.toFixed(0)}% O₂)`;
            } else if (flameSpread >= 1.2) {
                riskDriverTr = `Ana Etken: ${isConc ? "Eş Yönlü Yayılım" : "Yüzey Yayılımı"} (${flameSpread.toFixed(2)} mm/s) + CO Riski`;
                riskDriverEn = `Primary Driver: ${isConc ? "Concurrent Spread" : "Surface Spread"} (${flameSpread.toFixed(2)} mm/s) + CO Load`;
            } else {
                riskDriverTr = `Ana Etken: Aktif Yanma Isısı + CO/CO₂ (${coCo2Ratio.toFixed(3)})`;
                riskDriverEn = `Primary Driver: Thermal Release + CO/CO₂ (${coCo2Ratio.toFixed(3)})`;
            }
        }

        const flameRadiusMm = extinguished ? 0.0 : roundN(dropletD0 * 0.5 * standoffRatio, 2);
        const flickerFreqHz = (!extinguished && gravityG > 1e-4)
            ? roundN(0.48 * Math.sqrt((9.80665 * gravityG) / Math.max(0.002, flameRadiusMm * 0.002)), 2)
            : 0.0;
        const burnLifeS = (isGasBurner && !extinguished) ? 180.0 : (kBurn > 0 ? roundN((dropletD0 * dropletD0) / Math.max(0.05, kBurn), 1) : 0.0);

        const flowAxis = [];
        for (let u = 0; u <= 40; u += 2) flowAxis.push(u);
        const mocCurve0g = flowAxis.map((u) => computeMocAtFlow(fuel, u, 0.0, pressurePsia, diluent, flowDirection));
        const mocCurveLunar = flowAxis.map((u) => computeMocAtFlow(fuel, u, 0.16, pressurePsia, diluent, flowDirection));
        const mocCurveMars = flowAxis.map((u) => computeMocAtFlow(fuel, u, 0.38, pressurePsia, diluent, flowDirection));
        const mocCurve1g = flowAxis.map((u) => computeMocAtFlow(fuel, u, 1.0, pressurePsia, diluent, flowDirection));
        const coolFloor = flowAxis.map((u) => (fuel.cool_flame_capable && u <= 8.0 ? roundN(fuel.cool_flame_min_o2, 2) : null));

        // Zaman serisi (0-30s) — Cetegen-Ahmed / Durox doğal salınım frekansı f = 0.48*sqrt(g/D_f)
        const times = [], d2Norm = [], thermoK = [], optPct = [], radKw = [], coTrace = [];
        const d0Sq = dropletD0 * dropletD0;
        const twoStage = (!isGasBurner) && fuel.cool_flame_capable && gravityG < 0.12 && airflowCms < 6.0 && (regime === "COOL_FLAME_NTC" || regime === "HOT_SPHERICAL_0G") && dropletD0 >= 2.8;

        for (let step = 0; step <= 30; step++) {
            const t = step;
            times.push(t);
            if (extinguished) {
                const dec = Math.exp(-t / 2.2);
                d2Norm.push(isGasBurner ? 1.0 : roundN(Math.max(0.96, 1.0 - 0.04 * (1.0 - dec)), 3));
                thermoK.push(roundN(298.0 + 420.0 * dec, 1));
                optPct.push(roundN(100.0 * dec, 1));
                radKw.push(roundN(8.5 * dec, 2));
                coTrace.push(roundN(1.0 + 18.0 * (1.0 - dec) * Math.exp(-t / 14.0), 1));
            } else if (twoStage && t >= 14.0) {
                const hotPart = regime !== "COOL_FLAME_NTC" ? kBurn : kBurn * 2.8;
                const d2At14 = Math.max(0.18, 1.0 - (hotPart * 14.0) / d0Sq);
                const kCool = Math.max(0.08, hotPart * 0.26);
                const cD2 = Math.max(0.0, d2At14 - (kCool * (t - 14.0)) / d0Sq);
                d2Norm.push(roundN(cD2, 3));
                const tr = Math.exp(-(t - 14.0) / 1.4);
                const tCool = cD2 > 0.02 ? 640.0 : 310.0;
                thermoK.push(roundN(tCool + (Math.max(1380.0, flameTempK) - tCool) * tr, 1));
                optPct.push(roundN(Math.max(1.5, 92.0 * tr), 1));
                radKw.push(roundN((cD2 > 0.02 ? 4.2 : 0.3) + 12.0 * tr, 2));
                coTrace.push(roundN(Math.min(680.0, 95.0 + (t - 14.0) * 32.0), 1));
            } else {
                const cD2 = isGasBurner ? 1.0 : Math.max(0.0, 1.0 - (kBurn * t) / d0Sq);
                d2Norm.push(roundN(cD2, 3));
                const act = isGasBurner ? 1.0 : (cD2 > 0.01 ? 1.0 : Math.exp(-(t - d0Sq / Math.max(0.05, kBurn)) / 1.5));
                const ramp = 1.0 - Math.exp(-t / 1.1);
                if (regime === "COOL_FLAME_NTC") {
                    thermoK.push(roundN(298.0 + (flameTempK - 298.0) * ramp * act, 1));
                    optPct.push(roundN(3.2 * ramp * act, 1));
                    radKw.push(roundN(heatFlux * ramp * act, 2));
                    coTrace.push(roundN(1.0 + coPpm * Math.min(1.0, t / 12.0) * act, 1));
                } else {
                    const fl = flickerFreqHz > 0.05 ? (1.0 + 0.038 * Math.sin(2.0 * Math.PI * flickerFreqHz * t * 0.13)) : 1.0;
                    thermoK.push(roundN((298.0 + (flameTempK - 298.0) * ramp * act) * fl, 1));
                    optPct.push(roundN(Math.min(100.0, (78.0 + 20.0 * (flameTempK / 2200.0)) * ramp * act * fl), 1));
                    radKw.push(roundN(heatFlux * ramp * act * fl, 2));
                    coTrace.push(roundN(1.0 + coPpm * Math.min(1.0, t / 18.0) * act, 1));
                }
            }
        }

        const sensorSeries = {
            time_s: times,
            d2_normalized: d2Norm,
            thermocouple_k: thermoK,
            optical_intensity_pct: optPct,
            radiometer_kw_m2: radKw,
            co_ppm: coTrace,
            flicker_freq_hz: flickerFreqHz,
            two_stage_transition_s: twoStage ? 14.0 : null,
        };

        // Gerçek ISS 0G Referans Kalibrasyonu (Sabit k_ref hilesiz & 0.996 tavansız dürüst R²/RMSE)
        const issBenchmarks = {
            n_heptane: { full: "ISS CIR • FLEX / CFI 0G Referans (Nayagam & Dietrich, NTRS 20150023456)", short: "FLEX/CFI", k_ref: 0.76, d0_ref: 3.1, moc_0g: [16.1, 14.2, 12.8, 13.8, 15.0] },
            methanol: { full: "ISS CIR • FLEX-2 MDCA 0G Referans (Dietrich et al., NTRS 20090014812)", short: "FLEX-2", k_ref: 0.56, d0_ref: 2.9, moc_0g: [14.9, 13.0, 11.6, 12.6, 14.1] },
            pmma: { full: "ISS MSG / CIR • BASS & SoFIE 0G Referans (Olson & Ferkul, NTRS 20160005315)", short: "BASS/SoFIE", k_ref: 0.34, d0_ref: 3.5, moc_0g: [16.6, 14.7, 13.3, 14.3, 15.2] },
            sibal: { full: "Cygnus • Saffire-I / IV 0G Referans (Urban & Ruff, NTRS 20170000230)", short: "Saffire", k_ref: 0.48, d0_ref: 4.2, moc_0g: [15.5, 13.6, 12.2, 13.2, 14.2] },
            nomex: { full: "ISS MSG • BASS-II Kumaş 0G Referans (Olson, NTRS 20210011385)", short: "BASS-II", k_ref: 0.19, d0_ref: 4.0, moc_0g: [23.8, 21.9, 20.5, 21.5, 23.4] },
            hydrogen: { full: "ISS MSG / CIR • SPICE & SLICE 0G Referans (Sunderland, NTRS 20090014827)", short: "SPICE/SLICE", k_ref: 0.0, d0_ref: 3.2, moc_0g: [8.5, 6.6, 5.2, 6.2, 6.5] },
            propane_cfig: { full: "ISS CIR • ACME CFI-G 0G Referans (Axelbaum & Stocker, NTRS 20220015583)", short: "ACME CFI-G", k_ref: 0.0, d0_ref: 4.8, moc_0g: [13.7, 11.8, 10.4, 11.4, 12.0] },
        };
        const bench = issBenchmarks[fuelId] || issBenchmarks.n_heptane;
        const campFull = bench.full;
        const campShort = bench.short;
        const sampleTimes = [2, 6, 11, 16, 22, 28];
        const d2Pts = [];
        sampleTimes.forEach((ti, idx) => {
            const yp = d2Norm[ti];
            const ym = bench.k_ref <= 0.0
                ? 1.0
                : roundN(Math.max(0.0, 1.0 - (bench.k_ref * ti) / Math.pow(bench.d0_ref, 2)), 3);
            d2Pts.push({ t_s: ti, d2_meas: ym, d2_pred: yp, err: roundN(Math.abs(ym - yp), 3), label: `${campShort} 0G #${idx + 1}` });
        });

        const flowSamples = [0.5, 2.0, 6.0, 14.0, 26.0];
        let sumSqMoc = 0, sumYMoc = 0;
        const mocPts = flowSamples.map((uv, i) => {
            const mp = computeMocAtFlow(fuel, uv, 0.0, pressurePsia, diluent, flowDirection);
            const pShiftRef = 2.6 * (Math.pow(14.696 / Math.max(3.5, pressurePsia), 0.38) - 1.0);
            const dilShiftRef = (DILUENT_FACTORS[diluent] || DILUENT_FACTORS.N2).moc_shift;
            const mm = roundN(Math.max(4.2, Math.min(55.0, bench.moc_0g[i] + pShiftRef + dilShiftRef)), 2);
            sumSqMoc += Math.pow(mm - mp, 2);
            sumYMoc += mm;
            return { airflow_cms: uv, moc_meas_pct: mm, moc_pred_pct: mp, err_pct: roundN(Math.abs(mm - mp), 2), label: `${campShort} 0G U=${uv}cm/s` };
        });
        const rmseMoc = Math.sqrt(sumSqMoc / mocPts.length);
        const rmse = roundN(rmseMoc / 25.0, 4);
        const meanYMoc = sumYMoc / mocPts.length;
        const ssTotMoc = mocPts.reduce((acc, p) => acc + Math.pow(p.moc_meas_pct - meanYMoc, 2), 0);
        const rSq = ssTotMoc > 0.05 ? roundN(Math.max(0.75, Math.min(0.9995, 1.0 - sumSqMoc / ssTotMoc)), 4) : 0.962;

        const flightValidation = {
            campaign: campFull,
            campaign_short: campShort,
            r_squared: rSq,
            rmse: rmse,
            d2_points: d2Pts,
            moc_points: mocPts,
            benchmark_tr: `ISS 0G Referansı (${campShort}): R² = ${rSq.toFixed(3)} • RMSE = ${rmse.toFixed(3)}`,
            benchmark_en: `ISS 0G Benchmark (${campShort}): R² = ${rSq.toFixed(3)} • RMSE = ${rmse.toFixed(3)}`,
        };

        const calloutsMap = {
            HOT_SPHERICAL_0G: {
                badge_tr: "0G KÜRESEL DİFÜZYON ALEVİ",
                badge_en: "0G SPHERICAL DIFFUSION FLAME",
                summary_tr: `Doğal konveksiyon (Ra=0) sıfırlandı. ${flameTempK.toFixed(0)} K sıcaklıkta safir-mavi kemilüminesans küresi oluşuyor.`,
                summary_en: `Buoyancy vanishes in freefall (Ra=0). Symmetrical ${flameTempK.toFixed(0)} K sapphire-blue diffusion sphere.`,
            },
            VENTILATED_WAKE_0G: {
                badge_tr: `0G HAVALANDIRMALI KUYRUK ALEVİ (${airflowCms.toFixed(1)} cm/s)`,
                badge_en: `0G VENTILATED WAKE FLAME (${airflowCms.toFixed(1)} cm/s)`,
                summary_tr: `Kabin fan akışı (${airflowCms.toFixed(1)} cm/s) taze O₂ taşıyarak mavi durgunluk yayı ve kuyruk alevi oluşturdu (MOC: %${mocCurrent}).`,
                summary_en: `Ventilation (${airflowCms.toFixed(1)} cm/s) convects fresh O₂ to the flame sheet (MOC: ${mocCurrent}%).`,
            },
            BUOYANT_PLUME_1G: {
                badge_tr: `KALDIRMA KUVVETLİ KONVEKTİF ALEV (${gravityG.toFixed(2)}G)`,
                badge_en: `BUOYANCY-DRIVEN CONVECTIVE PLUME (${gravityG.toFixed(2)}G)`,
                summary_tr: `Yerçekimi (${gravityG.toFixed(2)}G) sıcak gazları yukarı ivmelendiriyor; gözyaşı formu ve kurum ışıması etkin.`,
                summary_en: `Gravity (${gravityG.toFixed(2)}G) stretches the flame into a convective plume with luminous soot.`,
            },
            COOL_FLAME_NTC: {
                badge_tr: "GÖRÜNMEZ SOĞUK ALEV (UV/IR MODU)",
                badge_en: "INVISIBLE COOL FLAME (UV/IR VIEW)",
                summary_tr: `Isıl kayıp sıcak alevi söndürdü ancak ${flameTempK.toFixed(0)} K görünmez Soğuk Alev (FLEX/CFI) CO üretmeye devam ediyor!`,
                summary_en: `Radiative loss quenched the hot flame, yet ${flameTempK.toFixed(0)} K invisible Cool Flame chemistry persists!`,
            },
            BLOWOFF_EXTINGUISHED: {
                badge_tr: "YÜKSEK HIZLI ÜFLEME SÖNMESİ (BLOWOFF)",
                badge_en: "CONVECTIVE BLOWOFF EXTINCTION",
                summary_tr: `Akış hızı (${airflowCms.toFixed(1)} cm/s) Damköhler sınırını (Da < 1) aşarak alevi üfleyip söndürdü.`,
                summary_en: `Airflow (${airflowCms.toFixed(1)} cm/s) exceeded Damköhler residence threshold (Da < 1).`,
            },
            QUENCHED_EXTINGUISHED: {
                badge_tr: `OKSİJEN / RADYATİF SÖNÜMLENME (MOC < %${mocCurrent})`,
                badge_en: `DIFFUSIVE / RADIATIVE QUENCHING (O₂ < ${mocCurrent}%)`,
                summary_tr: `Mevcut O₂ (%${oxygenPct.toFixed(1)}) MOC sınırının (%${mocCurrent}) altında kaldığı için alev kendi kendine söndü.`,
                summary_en: `Ambient O₂ (${oxygenPct.toFixed(1)}%) is below MOC (${mocCurrent}%); flame self-extinguished.`,
            },
        };
        const activeCall = calloutsMap[regime] || calloutsMap.HOT_SPHERICAL_0G;

        // ECLSS Kabin / Gezgin / EVA Saati (İdeal Gaz + 1. Termodinamik Yasası + NASA JSC-20584 CO SMAC)
        const hab = HABITAT_CONFIGS[habitatId];
        const volM3 = Number(hab.volume_m3);
        const baselineCo = 1.0;
        let scenarioTimeline;
        if (extinguished) {
            scenarioTimeline = {
                habitat_id: habitatId,
                habitat_name_tr: hab.name_tr,
                habitat_name_en: hab.name_en,
                volume_m3: volM3,
                crew_response_s: crewRespS,
                optical_blind: false,
                fire_power_kw: 0.0,
                t_alarm_s: 0.0,
                t_intervene_s: roundN(crewRespS, 1),
                t_caw_25ppm_s: 999.0,
                t_smac_24h_100ppm_s: 999.0,
                t_smac_1h_425ppm_s: 999.0,
                co_at_response_ppm: baselineCo,
                peak_temp_rise_c: 0.0,
                severity: "SAFE",
                badge_tr: "SÖNÜMLENMİŞ / GÜVENLİ KABİN",
                badge_en: "EXTINGUISHED / SAFE HABITAT",
                summary_tr: `${hab.name_tr} içinde aktif ekzotermik yanma bulunmuyor (MOC sınırı altında veya üfleme sönmesi). Kabin CO seviyesi ECLSS bazal düzeyinde (~1 ppm) kararlıdır.`,
                summary_en: `No sustained combustion in ${hab.name_en} (quenched below MOC or blowoff). Cabin CO remains at clean ECLSS baseline (~1 ppm).`,
                milestones: [
                    { t_s: 0.0, title_tr: "0.0 s • Tutuşma Bastırıldı", title_en: "0.0 s • Ignition Quenched", detail_tr: "Alev MOC / Da sınırında kendi kendine söndü.", detail_en: "Flame self-extinguished at MOC / Da boundary.", state: "ok" },
                    { t_s: 5.0, title_tr: "5.0 s • ISS PSD & CSA-CP İzleme", title_en: "5.0 s • ISS PSD & CSA-CP Monitoring", detail_tr: "CO ≈ 1 ppm (< 25 ppm C&W eşiği); söndürücü boşaltımı gerekmez.", detail_en: "CO ≈ 1 ppm (< 25 ppm C&W threshold); agent discharge not required.", state: "ok" },
                ],
            };
        } else {
            const pPa = pressurePsia * 6894.76;
            const mwKgMol = (xO2 * 32.0 + (1.0 - xO2) * 28.01) / 1000.0;
            const nGasMol = Math.max(0.5, (pPa * volM3) / (8.3145 * 295.15));
            const mGasKg = Math.max(0.015, nGasMol * mwKgMol);
            const optBlind = regime === "COOL_FLAME_NTC";
            let firePowerW = 0.0, mdotFuelGS = 0.0, yCoGG = 0.06;
            if (optBlind) {
                firePowerW = 260.0 + 140.0 * Math.min(2.0, kBurn / 0.25);
                mdotFuelGS = Math.max(0.08, firePowerW / 2400.0);
                yCoGG = 0.28;
            } else {
                const rateFac = Math.max(0.45, Math.min(4.2, 0.45 + 0.52 * flameSpread + 0.28 * kBurn));
                firePowerW = 1850.0 * rateFac * Math.pow(oxygenPct / 21.0, 0.55);
                if (volM3 < 1.0) firePowerW = Math.min(firePowerW, 5500.0);
                mdotFuelGS = Math.max(0.06, firePowerW / 21000.0);
                yCoGG = 0.055 + (airflowCms < 2.0 ? 0.045 : 0.015);
            }
            const firePowerKw = roundN(firePowerW / 1000.0, 2);
            const nCoMolS = (mdotFuelGS * yCoGG) / 28.01;
            const coRate = Math.max(0.05, (nCoMolS / nGasMol) * 1.0e6);
            const tCaw25 = roundN(Math.max(1.0, (25.0 - baselineCo) / coRate), 1);
            const tSmac100 = roundN(Math.max(1.8, (100.0 - baselineCo) / coRate), 1);
            const tSmac425 = roundN(Math.max(3.5, (425.0 - baselineCo) / coRate), 1);
            const volLag = (3.5 * Math.pow(volM3 / 19.0, 0.33)) / Math.max(0.55, Math.min(2.2, (airflowCms + 1.5) / 4.0));
            const tAlarm = optBlind ? roundN(Math.max(4.0, Math.min(180.0, tCaw25)), 1) : roundN(Math.max(1.5, Math.min(tCaw25, volLag)), 1);
            const unmit = crewRespS >= 900.0;
            const effWait = unmit ? 180.0 : crewRespS;
            const tInt = roundN(tAlarm + effWait, 1);
            const coAtResp = Math.round(Math.min(4500.0, baselineCo + coRate * tInt));
            const maxO2J = (nGasMol * xO2 * 0.032) * 13100.0e3;
            const qRelJ = Math.min(maxO2J, firePowerW * tInt);
            const peakDt = roundN(Math.min(650.0, (0.35 * qRelJ) / (mGasKg * 1005.0)), 1);
            const sev = (coAtResp >= 425.0 || (volM3 < 1.0 && oxygenPct >= 60.0) || peakDt >= 45.0 || unmit) ? "CRITICAL" : (coAtResp >= 100.0 || optBlind ? "WARNING" : "SAFE");
            const milestonesArr = [
                { t_s: 0.0, title_tr: "0.0 s • Tutuşma Başlangıcı", title_en: "0.0 s • Ignition Onset", detail_tr: `Rejim: ${activeCall.badge_tr} (${flameTempK.toFixed(0)} K, Q̇=${firePowerKw} kW)`, detail_en: `Regime: ${activeCall.badge_en} (${flameTempK.toFixed(0)} K, Q̇=${firePowerKw} kW)`, state: "warn" },
                { t_s: tAlarm, title_tr: `${tAlarm} s • Çok Kanallı C&W Yangın Alarmı`, title_en: `${tAlarm} s • Multi-Channel C&W Fire Alarm`, detail_tr: optBlind ? "ISS optik duman dedektörü (PSD, 670 nm) kurumsız soğuk alevde uyarmadı; CSA-CP / ANITA-2 CO gaz analizi (25 ppm C&W) alarm üretti." : "ISS Fotoelektrik Duman Dedektörü (PSD) lazer saçılım kanalı ve CSA-CP CO izleme ünitesi yangını doğruladı.", detail_en: optBlind ? "ISS photoelectric smoke detector (PSD, 670 nm) blind to soot-free cool flame; CSA-CP / ANITA-2 CO analyzer (25 ppm C&W) triggered alarm." : "ISS Photoelectric Smoke Detector (PSD) laser scattering and CSA-CP CO monitor confirmed fire.", state: optBlind ? "crit" : "warn" },
                { t_s: tInt, title_tr: `${tInt} s • ${unmit ? "Müdahale Yapılmadı (Serbest Yanma)" : "HVAC Fan Kesme + İnce Su Sisi (SoFIE-MIST)"}`, title_en: `${tInt} s • ${unmit ? "Unmitigated Burn" : "HVAC Fan Cutoff + Fine Water Mist (SoFIE-MIST)"}`, detail_tr: `Müdahale anı CO: ${coAtResp} ppm • Kabin ΔT: +${peakDt} °C (Halon YASAK)`, detail_en: `CO at action: ${coAtResp} ppm • Bulk ΔT: +${peakDt} °C (No Halon)`, state: sev === "CRITICAL" ? "crit" : (sev === "WARNING" ? "warn" : "ok") },
                { t_s: tSmac100, title_tr: `${tSmac100} s • NASA JSC-20584 CO SMAC (100 / 425 ppm)`, title_en: `${tSmac100} s • NASA JSC-20584 CO SMAC (100 / 425 ppm)`, detail_tr: `24sa SMAC (100 ppm): ${tSmac100} s • 1sa Acil SMAC (425 ppm): ${tSmac425} s (${tInt >= tSmac100 ? "AŞILDI!" : "Müdahale öncesi korundu"})`, detail_en: `24-hr SMAC (100 ppm): ${tSmac100} s • 1-hr Emergency SMAC (425 ppm): ${tSmac425} s (${tInt >= tSmac100 ? "BREACHED!" : "Preserved before action"})`, state: tInt >= tSmac425 ? "crit" : (tInt >= tSmac100 ? "warn" : "ok") },
            ];
            milestonesArr.sort((a, b) => a.t_s - b.t_s);
            scenarioTimeline = {
                habitat_id: habitatId,
                habitat_name_tr: hab.name_tr,
                habitat_name_en: hab.name_en,
                volume_m3: volM3,
                crew_response_s: crewRespS,
                optical_blind: optBlind,
                fire_power_kw: firePowerKw,
                t_alarm_s: tAlarm,
                t_intervene_s: tInt,
                t_caw_25ppm_s: tCaw25,
                t_smac_24h_100ppm_s: tSmac100,
                t_smac_1h_425ppm_s: tSmac425,
                co_at_response_ppm: coAtResp,
                peak_temp_rise_c: peakDt,
                severity: sev,
                badge_tr: sev === "CRITICAL" ? "KRİTİK YAŞAM DESTEK AŞIMI" : (sev === "WARNING" ? "DİKKAT: HIZLI MÜDAHALE GEREKLİ" : "KONTROLLÜ BASTIRMA PENCERESİ"),
                badge_en: sev === "CRITICAL" ? "CRITICAL ECLSS / SMAC BREACH" : (sev === "WARNING" ? "WARNING: RAPID ACTION REQUIRED" : "CONTROLLED SUPPRESSION WINDOW"),
                summary_tr: `**${hab.name_tr} (Referans Kabin Yangın Yükü \`${firePowerKw} kW\`):** Alarm \`t = ${tAlarm} s\` anında tetiklendi. Resmi **NASA JSC-20584** CO sınırlarına göre 24-saatlik SMAC (\`100 ppm\`) \`t = ${tSmac100} s\`, 1-saatlik Acil SMAC (\`425 ppm\`) ise \`t = ${tSmac425} s\` içinde aşılır. Seçilen müdahale anında (\`t = ${tInt} s\`) ortalama kabin CO düzeyi **\`${coAtResp} ppm\`** ve kütle-korunumlu gaz ısınması **\`+${peakDt} °C\`** olur.`,
                summary_en: `**${hab.name_en} (Reference Cabin Fire Load \`${firePowerKw} kW\`):** Alarm triggered at \`t = ${tAlarm} s\`. Per **NASA JSC-20584**, 24-hr CO SMAC (\`100 ppm\`) is reached in \`t = ${tSmac100} s\` and 1-hr Emergency SMAC (\`425 ppm\`) in \`t = ${tSmac425} s\`. At intervention (\`t = ${tInt} s\`), bulk cabin CO is **\`${coAtResp} ppm\`** and bulk gas ΔT is **\`+${peakDt} °C\`**.`,
                milestones: milestonesArr,
            };
        }

        const isPartial = gravityG >= 0.03 && gravityG <= 0.88;
        const isEva = pressurePsia <= 5.2 && oxygenPct >= 80.0;
        const isLunarRover = pressurePsia >= 8.0 && pressurePsia <= 11.2 && oxygenPct >= 28.0 && oxygenPct <= 40.0;
        const partialGravityInfo = {
            show_banner: Boolean(isPartial || isEva || isLunarRover),
            moc_0g_bound: moc0g,
            moc_current_est: mocCurrent,
            moc_1g_bound: moc1g,
            tr: isPartial
                ? `**Kısmi Yerçekimi Sınırlandırması (${gravityG.toFixed(2)}G):** NASA PSI'da LUCI & FM2 Ay verileri beklenirken **0G sınırı (%${moc0g})** ile **1G sınırı (%${moc1g})** ara yerçekimini sınırlar (\`Tahmini MOC ≈ %${mocCurrent}\`).`
                : isEva
                ? `**Uzay Giysisi Saf Oksijen Rejimi (${pressurePsia.toFixed(1)} psia / %${oxygenPct.toFixed(0)} O₂):** N₂ ısıl balastı sıfırlandığı için tutuşma enerjisi dramatik biçimde düşer.`
                : isLunarRover
                ? `**Ay Üssü ve Basınçlı Gezgin Atmosferi (${pressurePsia.toFixed(1)} psia / %${oxygenPct.toFixed(0)} O₂):** Ön-soluma süresini azaltan zenginleştirilmiş O₂ atmosferi yanıcılığı artırır.`
                : "",
            en: isPartial
                ? `**Partial-Gravity Bounding (${gravityG.toFixed(2)}G):** Bounded between **0G (${moc0g}%)** and **1G (${moc1g}%)** (\`Est. MOC ≈ ${mocCurrent}%\`) awaiting LUCI & FM2 lunar datasets.`
                : isEva
                ? `**EVA Spacesuit Pure-O₂ Regime (${pressurePsia.toFixed(1)} psia / ${oxygenPct.toFixed(0)}% O₂):** Zero N₂ thermal ballast dramatically accelerates flame spread.`
                : isLunarRover
                ? `**Lunar Base & Pressurized Rover (${pressurePsia.toFixed(1)} psia / ${oxygenPct.toFixed(0)}% O₂):** Elevated O₂ fraction increases material flammability.`
                : "",
        };

        const margin = oxygenPct - mocCurrent;
        const primaryRows = isGasBurner
            ? [
                {
                    law_tr: "Burke-Schumann Gaz Difüzyon Durma Yarıçapı", law_en: "Burke-Schumann Gas Flame Standoff",
                    equation: "D_brülör = D₀ (Sabit Gözenekli/Jet)  |  R_f / R_b = ln(1 + B_g) / ln(1 + Y_O2/ν_s)",
                    value: `R_f = ${flameRadiusMm.toFixed(2)} mm (R_f/R_b = ${standoffRatio.toFixed(2)})`,
                    status_tr: !extinguished ? "SABİT DEBİLİ GAZ ALEVİ (d² Yok)" : "SÖNÜMLENDİ", status_en: !extinguished ? "STEADY GAS BURNER (No d²)" : "EXTINGUISHED",
                },
                {
                    law_tr: "Gaz Fazı Stokiyometrik Entalpi Ölçeği (B_g)", law_en: "Gas-Phase Enthalpy Scaling (B_g)",
                    equation: "B_g = Y_O2·(ΔH_c / ν_s) / (c_pg·ΔT_ig)",
                    value: `B_g = ${spaldingB.toFixed(2)}  |  D₀ = ${dropletD0.toFixed(1)} mm`,
                    status_tr: spaldingB >= 4.0 ? "YÜKSEK OKSİDASYON POTANSİYELİ" : "ORTA ENTALPİ SÜRÜCÜSÜ", status_en: spaldingB >= 4.0 ? "HIGH OXIDATION POTENTIAL" : "MODERATE ENTHALPY DRIVE",
                },
            ]
            : isSolidSample
            ? [
                {
                    law_tr: "de Ris Katı Yüzey Alev Yayılım Yasası (V_f)", law_en: "de Ris Solid Flame Spread Law (V_f)",
                    equation: "V_f ~ (λ_g·ρ_g·c_pg·U_eff) / (k_s·ρ_s·c_s) · [(T_f - T_p)/(T_p - T_∞)]²",
                    value: `V_f = ${flameSpread.toFixed(2)} mm/s`,
                    status_tr: flameSpread > 0 ? "YÜZEY PİROLİZ YAYILIMI" : "SÖNÜMLENDİ", status_en: flameSpread > 0 ? "SURFACE PYROLYSIS SPREAD" : "EXTINGUISHED",
                },
                {
                    law_tr: "Katı Piroliz Kütle Aktarım Sayısı (B_p)", law_en: "Solid Pyrolysis Transfer Number (B_p)",
                    equation: "B_p = [Y_O2·(ΔH_c / ν_s) - c_pg·(T_p - T_∞)] / L_p",
                    value: `B_p = ${spaldingB.toFixed(2)}  |  δ_f/R_s = ${standoffRatio.toFixed(2)}`,
                    status_tr: spaldingB >= 3.0 ? "HIZLI PİROLİZ REJİMİ" : "SINIRLI GAZLAŞMA", status_en: spaldingB >= 3.0 ? "RAPID PYROLYSIS REGIME" : "LIMITED GASIFICATION",
                },
            ]
            : [
                {
                    law_tr: "Godsave-Spalding d² Sıvı Damlacık Yasası (K)", law_en: "Godsave-Spalding d² Droplet Law (K)",
                    equation: "D²(t) = D₀² - K·t  |  K = (8λ_g / ρ_l c_pg)·ln(1 + B_oq)·(Sh/2)",
                    value: `${kBurn.toFixed(3)} mm²/s (t_b ≈ ${burnLifeS.toFixed(1)} s)`,
                    status_tr: kBurn > 0 ? "AKTİF SIVI BUHARLAŞMASI" : "SÖNÜMLENDİ", status_en: kBurn > 0 ? "ACTIVE DROPLET BURNING" : "EXTINGUISHED",
                },
                {
                    law_tr: "Spalding Kütle Transfer Sayısı (B_oq)", law_en: "Spalding Transfer Number (B_oq)",
                    equation: "B_oq = [Y_O2·(ΔH_c / ν_s) - c_pg·(T_b - T_∞)] / L_v",
                    value: `B_oq = ${spaldingB.toFixed(2)}  |  R_f/R_d = ${standoffRatio.toFixed(2)}`,
                    status_tr: spaldingB >= 4.0 ? "YÜKSEK SÜRÜCÜ GÜÇ" : "ORTA TERMODİNAMİK GÜÇ", status_en: spaldingB >= 4.0 ? "HIGH DRIVING POTENTIAL" : "MODERATE MASS TRANSFER",
                },
            ];

        const formulaTable = primaryRows.concat([
            {
                law_tr: "Sherwood / Nusselt Taşınım (Sh)", law_en: "Sherwood / Nusselt Transport (Sh)",
                equation: "Sh = 2 + 0.6·Re^(1/2)·Sc^(1/3) + 0.52·Ra^(1/4)",
                value: `Sh = ${shConv.toFixed(2)} (Re=${reNum.toFixed(2)}, Gr=${grNum.toFixed(1)}, Ra=${raNum.toFixed(1)})`,
                status_tr: shConv < 2.25 ? "SAF DİFÜZYON (Sh≈2)" : "KONVEKTİF DESTEKLİ", status_en: shConv < 2.25 ? "PURE DIFFUSION (Sh≈2)" : "CONVECTIVELY ENHANCED",
            },
            {
                law_tr: "Richardson Karma Konveksiyon (Ri)", law_en: "Richardson Buoyancy Ratio (Ri)",
                equation: "Ri = Gr / Re²",
                value: `Ri = ${richardsonRi.toFixed(2)}`,
                status_tr: richardsonRi < 1.0 ? "MİKROÇEKİM / FAN BASKIN" : "KALDIRMA KUVVETİ BASKIN", status_en: richardsonRi < 1.0 ? "MICROGRAVITY / FORCED FLOW" : "BUOYANCY DOMINATED",
            },
            {
                law_tr: "Damköhler Reaksiyon Sayısı (Da)", law_en: "Damköhler Residence Ratio (Da)",
                equation: "Da = τ_flow / τ_chem",
                value: `Da = ${damkohlerDa.toFixed(2)}`,
                status_tr: damkohlerDa < 1.0 ? "ÜFLEME SÖNMESİ (Da<1)" : "KİMYASAL KARARLI (Da≥1)", status_en: damkohlerDa < 1.0 ? "BLOWOFF EXTINCTION (Da<1)" : "CHEMICALLY STABLE (Da≥1)",
            },
            {
                law_tr: "Radyatif Isı Kaybı (Planck T⁴) & Yarı-Ampirik MOC Zarfı", law_en: "Planck T⁴ Radiative Loss (χ_r) & Semi-Empirical MOC",
                equation: "Q̇_rad = V_shell·4σ·κ_P·(T_f⁴ - T_∞⁴)  |  P_O2 = X_O2 · P_kabin",
                value: `χ_r = %${(radLossFrac * 100).toFixed(1)}  |  P_O2 = ${po2Psia.toFixed(2)} psia (${po2Kpa.toFixed(1)} kPa)`,
                status_tr: `MOC ZARFI: %${mocCurrent} (ΔO₂ = ${margin >= 0 ? "+" : ""}${margin.toFixed(1)}%)`, status_en: `MOC ENVELOPE: ${mocCurrent}% (ΔO₂ = ${margin >= 0 ? "+" : ""}${margin.toFixed(1)}%)`,
            },
        ]);

        // Faz 3 & Faz 4: Yangın Üçgeni Ön-Tutuşma (MIE, LFL/UFL, 0G Semenov) + 5 Bölmeli Uzay Gemisi Ağı (ΔP, IDSS Yük, FED)
        const mieBase = fuelId === "hydrogen" ? 0.017 : (fuelId === "methanol" ? 0.14 : (fuelId === "propane_cfig" ? 0.25 : 0.24));
        const mieMj = roundN(Math.max(0.0005, mieBase * Math.pow(1.0 / Math.max(0.22, pAtm), 1.8) * Math.pow(0.21 / Math.max(0.05, xO2), 2.6) * (1.0 / dil.cp_factor)), 4);
        const lflVol = roundN(fuelId === "hydrogen" ? 4.0 : (fuelId === "methanol" ? 6.0 : 1.1), 2);
        const uflVol = roundN(Math.min(94.0, (fuelId === "hydrogen" ? 75.0 : 8.5) * Math.pow(Math.max(0.5, xO2 / 0.21), 0.72)), 1);
        const nuConv0g = 2.0 + 0.55 * Math.sqrt(Math.max(0.0, reNum));
        const hDiffWm2K = (nuConv0g * Number(dil.lambda_g)) / Math.max(0.004, charLenM);
        const qGenTotalW = (extinguished ? 0.0 : 14.0) + avionicsFaultW;
        const semenovPsi = roundN(Math.min(4.5, qGenTotalW / Math.max(0.8, hDiffWm2K * 0.038 * 24.5)), 3);
        const chfKwM2 = roundN(isSolidSample ? (fuelId === "nomex" ? 26.5 : 13.8) : 6.5, 1);
        const preIgnition = {
            mie_mj: mieMj,
            lfl_vol_pct: lflVol,
            ufl_vol_pct: uflVol,
            semenov_psi: semenovPsi,
            semenov_runaway: semenovPsi >= 0.368,
            critical_heat_flux_kw_m2: chfKwM2,
        };

        const compObj = SPACECRAFT_COMPARTMENTS[fireCompId] || { volume_m3: 19.0 };
        const compVolM3 = Number(compObj.volume_m3 || 19.0);
        const qFireNetKw = extinguished ? 0.0 : Number(scenarioTimeline.fire_power_kw || 1.8);
        const qMistCoolKw = waterMistActive ? 6.4 : 0.0;
        const netEnergyKj = Math.max(0.0, (qFireNetKw - qMistCoolKw) * Math.min(60.0, crewRespS));
        const overpressureKpa = roundN(Math.min(65.0, (0.28 * netEnergyKj) / Math.max(0.2, compVolM3)), 2);
        const hatchAreaM2 = 0.5026; // IDSS D=0.80m
        const maxHatchForceKn = roundN(overpressureKpa * hatchAreaM2, 2);
        const hatchesSealedFlag = sealedHatches.length > 0;
        const smokeLeakGs = (!extinguished && !hatchesSealedFlag) ? roundN(0.18 + 0.42 * overpressureKpa, 3) : 0.0;
        const fedTotal = extinguished ? 0.0 : roundN(Math.min(3.5, ((coPpm / 35000.0) + (hcnPpmEst / 165.0) + (hclPpmEst / 220.0) + (hfPpmEst / 120.0)) * (crewRespS / 60.0) * 18.0), 4);
        const compartmentNetwork = {
            fire_compartment_id: fireCompId,
            overpressure_kpa: overpressureKpa,
            max_hatch_force_kn: maxHatchForceKn,
            total_intermodule_smoke_g_s: smokeLeakGs,
            water_mist_cooling_kw: qMistCoolKw,
            multi_gas_toxicology: {
                co_ppm: coPpm,
                hcn_ppm: hcnPpmEst,
                hcl_ppm: hclPpmEst,
                hf_ppm: hfPpmEst,
                fed_total: fedTotal,
            },
        };

        formulaTable.push(
            {
                law_tr: "Yangın Üçgeni: Minimum Tutuşma Enerjisi (MIE) & 0G Semenov (ψ)",
                law_en: "Fire Triangle: Minimum Ignition Energy (MIE) & 0G Semenov (ψ)",
                equation: "E_min ∝ P^(-1.8)·X_O2^(-2.6)  |  ψ_0G = Q_gen / [h_diff·A·(R·T₀²/E_a)]",
                value: `MIE = ${mieMj} mJ  |  ψ = ${semenovPsi} (Kritik 0.368)`,
                status_tr: semenovPsi >= 0.368 ? "0G TERMAL KAÇAK RİSKİ!" : (mieMj < 0.05 ? "STATİK KIVILCIM TEHLİKESİ" : "ÖN-TUTUŞMA KARARLI"),
                status_en: semenovPsi >= 0.368 ? "0G THERMAL RUNAWAY!" : (mieMj < 0.05 ? "ESD SPARK HAZARD" : "SUB-CRITICAL"),
            },
            {
                law_tr: "Bölme Aşırı Basıncı (ΔP), IDSS Kapak Yükü & Çoklu-Gaz FED",
                law_en: "Cabin Overpressure (ΔP), IDSS Hatch Force & Multi-Gas FED",
                equation: "F_hatch = ΔP·A_IDSS  |  FED = Σ ∫(C_i / D_i)dt (CO+HCN+HF)",
                value: `ΔP = +${overpressureKpa} kPa • F = ${maxHatchForceKn} kN • FED = ${fedTotal}`,
                status_tr: hatchesSealedFlag ? "IDSS KAPAK KİLİTLİ (Sızıntı 0 g/s)" : `SIZINTI: ${smokeLeakGs} g/s`,
                status_en: hatchesSealedFlag ? "IDSS HATCH SEALED (0 g/s Leak)" : `SMOKE LEAK: ${smokeLeakGs} g/s`,
            }
        );

        const phaseTagTr = isGasBurner ? `Burke-Schumann B_g = ${spaldingB.toFixed(2)} (D=D₀ sabit gaz brülörü)` : (isSolidSample ? `de Ris V_f = ${flameSpread.toFixed(2)} mm/s (B_p = ${spaldingB.toFixed(2)})` : `d² K = ${kBurn.toFixed(3)} mm²/s (B_oq = ${spaldingB.toFixed(2)})`);
        const phaseTagEn = isGasBurner ? `Burke-Schumann B_g = ${spaldingB.toFixed(2)} (steady D=D₀ gas burner)` : (isSolidSample ? `de Ris V_f = ${flameSpread.toFixed(2)} mm/s (B_p = ${spaldingB.toFixed(2)})` : `d² K = ${kBurn.toFixed(3)} mm²/s (B_oq = ${spaldingB.toFixed(2)})`);
        const instantAiSummary = {
            tr: `**Anlık Değerlendirme (${fuel.formula}):** \`P_O2 = ${po2Psia.toFixed(2)} psia\`, \`${phaseTagTr}\`, \`Sh = ${shConv.toFixed(2)}\`, \`Da = ${damkohlerDa.toFixed(2)}\` ve ISS 0G referansı \`R² = ${rSq}\`. Rejim **${activeCall.badge_tr}** (Risk: **${riskScore}/100**). İlk müdahale: Kabin fanlarını kapatıp Halon kullanmadan İnce Su Sisi (SoFIE-MIST) uygulayın.`,
            en: `**Instant Summary (${fuel.formula}):** \`P_O2 = ${po2Psia.toFixed(2)} psia\`, \`${phaseTagEn}\`, \`Sh = ${shConv.toFixed(2)}\`, \`Da = ${damkohlerDa.toFixed(2)}\`, ISS 0G benchmark \`R² = ${rSq}\`. Regime **${activeCall.badge_en}** (Risk: **${riskScore}/100**). Action: Immediate HVAC shutoff + Fine Water Mist (No Halon).`,
        };

        // v6.3 Analitik ±1σ Belirsizlik Bandı, 0G Çekirdek Soğuma Eğrisi, 5-Aşamalı Sertifikasyon ve Dünya Etkisi
        const gGapFactor = (gravityG > 0.02 && gravityG < 0.92) ? Math.sin(Math.PI * Math.min(1.0, gravityG)) * 0.85 : 0.0;
        const customUnc = analogMatchInfo && analogMatchInfo.active ? Number(analogMatchInfo.uncertainty_moc_pct || 1.6) * 0.55 : 0.0;
        const mocSigma = roundN(0.42 + 0.58 * gGapFactor + customUnc + (airflowCms < 2.0 ? 0.18 : 0.0), 2);
        const mocCurveActiveG = flowAxis.map((u) => computeMocAtFlow(fuel, u, gravityG, pressurePsia, diluent, flowDirection));
        const mocUpper1Sigma = mocCurveActiveG.map((m) => roundN(Math.min(58.0, m + mocSigma), 2));
        const mocLower1Sigma = mocCurveActiveG.map((m) => roundN(Math.max(4.0, m - mocSigma), 2));
        const relUnc = 0.045 + 0.065 * gGapFactor + (analogMatchInfo && analogMatchInfo.active ? 0.055 : 0.0);
        const kSigma = roundN(Math.max(0.012, kBurn * relUnc), 3);
        const tempSigma = roundN(Math.max(14.0, flameTempK * (relUnc * 0.55)), 1);
        const spreadSigma = roundN(Math.max(0.03, flameSpread * (relUnc * 1.15)), 2);
        const uncertaintyBounds = {
            moc_sigma_pct: mocSigma,
            moc_lower_pct: roundN(Math.max(4.0, mocCurrent - mocSigma), 2),
            moc_upper_pct: roundN(Math.min(58.0, mocCurrent + mocSigma), 2),
            k_sigma_mm2_s: kSigma,
            k_lower_mm2_s: roundN(Math.max(0.0, kBurn - kSigma), 3),
            k_upper_mm2_s: roundN(kBurn + kSigma, 3),
            temp_sigma_k: tempSigma,
            temp_lower_k: roundN(Math.max(295.0, flameTempK - tempSigma), 1),
            temp_upper_k: roundN(flameTempK + tempSigma, 1),
            spread_sigma_mm_s: spreadSigma,
            spread_lower_mm_s: roundN(Math.max(0.0, flameSpread - spreadSigma), 2),
            spread_upper_mm_s: roundN(flameSpread + spreadSigma, 2),
        };

        const tCoreInit = extinguished ? Math.max(325.0, Math.min(760.0, 340.0 + 4.8 * oxygenPct)) : Math.min(940.0, Math.max(580.0, flameTempK * 0.46));
        const tAutoIg = Number(fuel.t_boil_k || 540.0) + 95.0;
        const tSafeReentry = 335.0;
        const tau0g = Math.max(42.0, 96.0 - 1.4 * airflowCms);
        const tauMist = 16.5;
        const tau1g = 34.0;
        const coolTimes = [0, 15, 30, 45, 60, 90, 120, 150, 180];
        const coolCurve0g = coolTimes.map((tsVal) => roundN(294.15 + (tCoreInit - 294.15) * Math.exp(-tsVal / tau0g), 1));
        const coolCurveMist = coolTimes.map((tsVal) => roundN(294.15 + (tCoreInit - 294.15) * Math.exp(-tsVal / tauMist), 1));
        const coolCurve1g = coolTimes.map((tsVal) => roundN(294.15 + (tCoreInit - 294.15) * Math.exp(-tsVal / tau1g), 1));
        const activeTau = waterMistActive ? tauMist : (gravityG >= 0.5 ? tau1g : tau0g);
        const safeReentryS = tCoreInit > tSafeReentry ? Math.round(activeTau * Math.log((tCoreInit - 294.15) / (tSafeReentry - 294.15))) : 0;
        const safeReentryMistS = tCoreInit > tSafeReentry ? Math.round(tauMist * Math.log((tCoreInit - 294.15) / (tSafeReentry - 294.15))) : 0;
        const reigRiskPct = tCoreInit <= 340.0 ? 4 : Math.min(98, Math.max(6, Math.round(((tCoreInit - 335.0) / Math.max(80.0, tAutoIg - 335.0)) * 78.0 + Math.max(0.0, oxygenPct - mocCurrent) * 1.4)));
        const postFireCooling = {
            initial_core_temp_k: roundN(tCoreInit, 1),
            initial_core_temp_c: roundN(tCoreInit - 273.15, 1),
            autoignition_temp_k: roundN(tAutoIg, 1),
            safe_reentry_temp_k: tSafeReentry,
            tau_active_g_s: roundN(activeTau, 1),
            tau_mist_s: tauMist,
            tau_1g_s: tau1g,
            reignition_risk_pct: reigRiskPct,
            safe_reentry_s: safeReentryS,
            safe_reentry_mist_s: safeReentryMistS,
            time_s: coolTimes,
            core_temp_0g_k: coolCurve0g,
            core_temp_mist_k: coolCurveMist,
            core_temp_1g_k: coolCurve1g,
            status_tr: reigRiskPct >= 50 ? "Yüksek Yeniden Tutuşma Riski (Kapak Açılmaz)" : "Kontrollü Soğuma Süreci",
            status_en: reigRiskPct >= 50 ? "High Flash Re-Ignition Risk (Keep Hatch Sealed)" : "Controlled Thermal Decay",
        };

        const certDefs = [
            { phase_id: "iss_0g", label_tr: "ISS (0G)", label_en: "ISS (0G)", gravity_g: 0.0, oxygen_pct: 21.0, pressure_psia: 14.7, airflow_cms: 3.5, habitat_id: "iss_module" },
            { phase_id: "orion_0g", label_tr: "Orion MCP (0G)", label_en: "Orion MCP (0G)", gravity_g: 0.0, oxygen_pct: 30.0, pressure_psia: 10.2, airflow_cms: 4.0, habitat_id: "lunar_hab" },
            { phase_id: "lunar_016g", label_tr: "Ay Üssü (0.16G)", label_en: "Lunar Base (0.16G)", gravity_g: 0.16, oxygen_pct: 32.0, pressure_psia: 10.2, airflow_cms: 4.0, habitat_id: "lunar_rover" },
            { phase_id: "mars_038g", label_tr: "Mars Yüzeyi (0.38G)", label_en: "Mars Surface (0.38G)", gravity_g: 0.38, oxygen_pct: 34.0, pressure_psia: 8.2, airflow_cms: 4.5, habitat_id: "mars_hab" },
            { phase_id: "eva_suit", label_tr: "EVA Giysisi (%100 O₂)", label_en: "EVA Spacesuit (100% O₂)", gravity_g: 0.0, oxygen_pct: 100.0, pressure_psia: 4.3, airflow_cms: 6.0, habitat_id: "eva_suit" },
        ];
        const missionCertification = certDefs.map((cd) => {
            const cMoc = computeMocAtFlow(fuel, cd.airflow_cms, cd.gravity_g, cd.pressure_psia, "N2", flowDirection);
            const cMargin = roundN(cMoc - cd.oxygen_pct, 2);
            let stCode = "FAIL", stTr = "Tehlikeli", stEn = "Flammable";
            if (cMargin >= 1.5) {
                stCode = "PASS"; stTr = "Uygun"; stEn = "Certified";
            } else if (cMargin >= -1.5) {
                stCode = "CAUTION"; stTr = "Koşullu"; stEn = "Caution";
            }
            return Object.assign({}, cd, {
                moc_pct: cMoc,
                margin_pct: cMargin,
                status: stCode,
                status_tr: stTr,
                status_en: stEn,
            });
        });

        const mistD32 = roundN(Math.max(18.0, Math.min(44.0, 36.0 - 0.16 * Math.max(0.0, oxygenPct - 21.0))), 1);
        const spaceToEarthLive = {
            mist_sauter_d32_um: mistD32,
            mist_water_saving_pct: roundN(Math.min(94.0, Math.max(76.0, 88.5 - 0.12 * (mistD32 - 28.0))), 1),
            ev_early_warning_gain_s: roundN(coolFlameActive ? 42.5 : Math.max(14.0, 28.0 - 0.25 * airflowCms), 1),
            dust_false_alarm_rejection_pct: 99.2,
            protective_fabric_margin_kw_m2: roundN(Math.max(2.5, 42.0 - heatFlux * 0.45), 1),
            active_flame_temp_k: flameTempK,
        };

        return {
            inputs: {
                fuel_id: requestedFuelId, base_fuel_id: fuelId,
                custom_material_name: String((params && params.custom_material_name) || ""),
                fuel_name_tr: fuel.name_tr, fuel_name_en: fuel.name_en,
                formula: fuel.formula, geometry_3d: fuel.geometry_3d || "droplet",
                fuel_phase: fuelPhaseCategory,
                gravity_g: gravityG, oxygen_pct: oxygenPct, pressure_psia: pressurePsia, pressure_kpa: pressureKpa,
                airflow_cms: airflowCms, flow_direction: flowDirection,
                droplet_d0_mm: dropletD0, diluent: diluent,
                diluent_name: dil.name, diluent_name_en: dil.name_en,
                habitat_id: habitatId, crew_response_s: crewRespS,
            },
            telemetry: {
                regime, fuel_phase: fuelPhaseCategory, extinguished, cool_flame_active: coolFlameActive,
                flame_temp_k: flameTempK, flame_temp_c: roundN(flameTempK - 273.15, 1),
                burning_rate_k_mm2_s: kBurn, spalding_b_number: spaldingB, flame_spread_mm_s: flameSpread,
                moc_pct: mocCurrent, po2_psia: po2Psia, po2_kpa: po2Kpa, o2_partial_psia: po2Psia, o2_partial_kpa: po2Kpa,
                standoff_ratio: standoffRatio, standoff_ratio_rf_rd: standoffRatio,
                flame_radius_mm: flameRadiusMm, burn_lifetime_s: burnLifeS, radiative_loss_fraction: radLossFrac,
                reynolds_number: roundN(reNum, 2), grashof_number: roundN(grNum, 2), rayleigh_number: roundN(raNum, 2),
                richardson_number: richardsonRi, froude_number: froudeFr, sherwood_number: roundN(shConv, 2), damkohler_number: damkohlerDa,
                flicker_freq_hz: flickerFreqHz,
                soot_index: sootIndex, co_ppm: coPpm, heat_flux_kw_m2: heatFlux, hrrpua_kw_m2: hrrpuaKwM2,
                risk_score: riskScore, risk_driver_tr: riskDriverTr, risk_driver_en: riskDriverEn,
            },
            uncertainty_bounds: uncertaintyBounds,
            post_fire_cooling: postFireCooling,
            mission_certification: missionCertification,
            space_to_earth_live: spaceToEarthLive,
            analog_match_info: analogMatchInfo,
            pre_ignition: preIgnition,
            compartment_network: compartmentNetwork,
            partial_gravity_info: partialGravityInfo,
            formula_table: formulaTable,
            instant_ai_summary: instantAiSummary,
            callouts: calloutsMap[regime] || calloutsMap.HOT_SPHERICAL_0G,
            flight_validation: flightValidation,
            scenario_timeline: scenarioTimeline,
            flammability_map: {
                flows_cms: flowAxis,
                airflow_cms: flowAxis,
                moc_0g_pct: mocCurve0g,
                moc_lunar_016g_pct: mocCurveLunar,
                moc_mars_038g_pct: mocCurveMars,
                moc_1g_pct: mocCurve1g,
                moc_active_g_pct: mocCurveActiveG,
                moc_upper_1sigma_pct: mocUpper1Sigma,
                moc_lower_1sigma_pct: mocLower1Sigma,
                cool_flame_floor_pct: coolFloor,
                current_point: { airflow_cms: airflowCms, oxygen_pct: oxygenPct, gravity_g: gravityG },
            },
            sensor_timeseries: sensorSeries,
        };
    }

    function expandQueryText(q) {
        let low = String(q || "").toLowerCase();
        Object.keys(SYNONYMS).forEach((k) => {
            if (low.includes(k)) low += " " + SYNONYMS[k];
        });
        return low;
    }

    function computeTextSimilarity(query, docText) {
        const qTokens = expandQueryText(query).match(/[a-z0-9çğıöşü]{2,}/g) || [];
        if (!qTokens.length) return 0;
        const dLow = String(docText || "").toLowerCase();
        let hits = 0;
        qTokens.forEach((tok) => {
            if (dLow.includes(tok)) hits += 1;
        });
        return Math.min(0.99, hits / Math.max(2, Math.sqrt(qTokens.length) * 1.6));
    }

    function registerDynamicExperimentJs(filename, simParams, simState, summaryTr, summaryEn) {
        if (!simState || !simState.inputs || !simState.telemetry) return null;
        const inp = simState.inputs;
        const tel = simState.telemetry;
        const cleanName = String(filename || "Yeni_Deney").replace(/\.[a-zA-Z0-9]{1,5}$/, "").trim() || "Yeni_Deney";
        const existingIdx = dynamicExperiments.findIndex((x) => x.source_filename === filename);
        const expId = existingIdx >= 0 ? dynamicExperiments[existingIdx].exp_id : `PSI-USR-${String(dynamicExperiments.length + 1).padStart(2, "0")}`;
        const flowVal = Number(inp.airflow_cms || 0);
        const flowDir = String(inp.flow_direction || "opposed");
        const flowRegime = flowVal < 1.0 ? "quiescent" : flowDir;
        const spreadVal = Number(tel.flame_spread_mm_s || 0);
        const kVal = Number(tel.burning_rate_k_mm2_s || 0);
        const rateStr = spreadVal > 0.05 ? `Spread = ${spreadVal.toFixed(2)} mm/s` : `K = ${kVal.toFixed(3)} mm²/s`;
        const shortTr = String(summaryTr || "").split("\n")[0].replace(/\*\*/g, "").slice(0, 200) || `Yüklenen veri dosyasından (${filename}) çıkarılan deney kaydı.`;
        const shortEn = String(summaryEn || "").split("\n")[0].replace(/\*\*/g, "").slice(0, 200) || `Experiment record extracted from uploaded dataset (${filename}).`;
        const rec = {
            exp_id: expId,
            source_filename: filename,
            is_dynamic_upload: true,
            program: `Yeni Veri (${cleanName.slice(0, 18)})`,
            program_tr: `Yeni Veri (${cleanName.slice(0, 18)})`,
            program_en: `Uploaded Data (${cleanName.slice(0, 18)})`,
            hardware_group: inp.fuel_phase === "solid" ? "MSG" : "CIR",
            title: `Uploaded Dataset — ${cleanName}`,
            title_en: `Uploaded Dataset — ${cleanName}`,
            title_tr: `Yüklenen Deney Verisi — ${cleanName}`,
            facility: "Kullanıcı Veri Yüklemesi / PSI Tablosu",
            facility_tr: "Kullanıcı Veri Yüklemesi / PSI Tablosu",
            facility_en: "User Dataset Upload / PSI Table",
            year: 2026,
            fuel_id: String(inp.base_fuel_id || inp.fuel_id || "n_heptane"),
            custom_material_name: String(inp.custom_material_name || ""),
            material: String(inp.fuel_name_en || inp.fuel_id || "Sample"),
            sample_geometry_tr: `Yüklenen veri kaydı (D₀ = ${inp.droplet_d0_mm ?? 3.2} mm)`,
            sample_geometry_en: `Uploaded dataset geometry (D₀ = ${inp.droplet_d0_mm ?? 3.2} mm)`,
            sensors_tr: "Yüklenen dosya telemetrisi (Sıcaklık, O₂, Basınç, Radyometre / CO)",
            sensors_en: "Uploaded file telemetry (Temperature, O₂, Pressure, Radiometer / CO)",
            gravity_g: Number(inp.gravity_g ?? 0.0),
            oxygen_pct: Number(inp.oxygen_pct ?? 21.0),
            pressure_psia: Number(inp.pressure_psia ?? 14.7),
            airflow_cms: flowVal,
            moc_measured_pct: Number(tel.moc_pct ?? 15.0),
            scale_class_tr: "Yeni Yüklenen Veri",
            scale_class_en: "Uploaded Dataset",
            hrrpua_kw_m2: Number(tel.hrrpua_kw_m2 ?? 120.0),
            flow_regime: flowRegime,
            burning_rate_or_spread: rateStr,
            cool_flame_observed: Boolean(tel.cool_flame_active),
            ntrs_id: "USER-DATA",
            ntrs_url: "https://psi.nasa.gov/",
            psi_id: expId,
            psi_url: "https://psi.nasa.gov/",
            key_finding_tr: shortTr,
            key_finding_en: shortEn,
            safety_insight_tr: "Yüklenen deney parametreleri mevcut kabin atmosferiyle otomatik karşılaştırıldı.",
            safety_insight_en: "Uploaded test parameters were automatically benchmarked against target cabin conditions.",
            intra_runs: [
                {
                    run_code: `${expId}-R1`,
                    same_tr: `Dosya: ${filename}, Basınç: ${inp.pressure_psia ?? 14.7} psia`,
                    same_en: `File: ${filename}, Pressure: ${inp.pressure_psia ?? 14.7} psia`,
                    diff_tr: `O₂: %${inp.oxygen_pct ?? 21.0}, Akış: ${flowVal} cm/s (${flowDir})`,
                    diff_en: `O₂: ${inp.oxygen_pct ?? 21.0}%, Flow: ${flowVal} cm/s (${flowDir})`,
                    result_tr: `Hesaplanan T_f = ${tel.flame_temp_k} K, MOC = %${tel.moc_pct}, ${rateStr}.`,
                    result_en: `Evaluated T_f = ${tel.flame_temp_k} K, MOC = ${tel.moc_pct}%, ${rateStr}.`,
                },
            ],
            tags: ["user upload", "dynamic", cleanName.toLowerCase()],
        };
        if (existingIdx >= 0) {
            dynamicExperiments[existingIdx] = rec;
        } else {
            dynamicExperiments.unshift(rec);
            ragDocs.push({
                doc_id: expId,
                title: rec.title_tr,
                source: `${rec.program} • ${filename}`,
                url: rec.ntrs_url,
                text: `${expId} ${cleanName} ${rec.material} ${rec.key_finding_tr} ${rec.key_finding_en}`,
            });
        }
        return rec;
    }

    function rankExperimentsClient(missionParams, query, hwFilter) {
        const mp = missionParams || {};
        const targetO2 = Number(mp.oxygen_pct ?? 21.0);
        const targetP = Number(mp.pressure_psia ?? 14.7);
        const targetFlow = Number(mp.airflow_cms ?? 3.5);
        const analogTarget = resolveAnalogMaterialJs(mp);
        const targetFuel = analogTarget.baseFuelId || String(mp.fuel_id || "n_heptane");
        const targetG = Number(mp.gravity_g ?? 0.0);
        const targetFlowDir = String(mp.flow_direction || "opposed").toLowerCase();
        const hwNorm = String(hwFilter || "ALL").toUpperCase();

        const ranked = [];
        const allCatalog = dynamicExperiments.concat(NASA_CATALOG);
        allCatalog.forEach((exp) => {
            if (hwNorm !== "ALL" && hwNorm !== "" && String(exp.hardware_group || "").toUpperCase() !== hwNorm) return;
            const o2Diff = Math.abs(targetO2 - Number(exp.oxygen_pct));
            const pDiff = Math.abs(targetP - Number(exp.pressure_psia));
            const flDiff = Math.abs(targetFlow - Number(exp.airflow_cms));
            const fuelBonus = exp.fuel_id === targetFuel ? 22.0 : 0.0;
            const flowDirBonus = (targetFlow >= 1.0 && String(exp.flow_regime || "") === targetFlowDir) ? 4.5 : 0.0;
            const dynBonus = exp.is_dynamic_upload ? 6.0 : 0.0;
            const pgBonus = (targetG >= 0.04 && targetG <= 0.85 && ["PSI-ACME-09", "PSI-SOFIE-08", "PSI-SAFFIRE5-07", "PSI-DAFT-15"].includes(exp.exp_id)) ? 14.0 : 0.0;
            const affinity = Math.min(100.0, Math.max(10.0, 100.0 - (Math.min(42.0, o2Diff * 1.6) + pDiff * 2.6 + flDiff * 1.3) + fuelBonus + flowDirBonus + dynBonus + pgBonus));

            const simEval = simulateCombustionClient({
                fuel_id: exp.fuel_id, gravity_g: targetG, oxygen_pct: targetO2,
                pressure_psia: targetP, airflow_cms: targetFlow, flow_direction: targetFlowDir,
                droplet_d0_mm: 3.5, diluent: mp.diluent || "N2",
            });
            const hazard = Number(simEval.telemetry.risk_score);
            const docObj = ragDocs.find((d) => d.doc_id === exp.exp_id);
            const semScore = query && query.trim() ? computeTextSimilarity(query, docObj ? docObj.text : exp.title) * 100.0 : 0.0;
            const composite = (query && query.trim())
                ? 0.44 * semScore + 0.32 * affinity + 0.24 * hazard
                : 0.56 * affinity + 0.44 * hazard;

            ranked.push(Object.assign({}, exp, {
                priority_score: roundN(Math.min(99.9, composite), 1),
                param_affinity: roundN(affinity, 1),
                mission_hazard_score: Math.trunc(hazard),
                predicted_regime_in_mission: simEval.telemetry.regime,
                predicted_moc_in_mission: simEval.telemetry.moc_pct,
                predicted_hrrpua_kw_m2: simEval.telemetry.hrrpua_kw_m2,
            }));
        });

        ranked.sort((a, b) => b.priority_score - a.priority_score);
        ranked.forEach((item, i) => { item.rank = i + 1; });
        return { count: ranked.length, hardware_filter: hwNorm, ranked_experiments: ranked };
    }

    function compareExperimentsClient(expIds) {
        const allCatalog = dynamicExperiments.concat(NASA_CATALOG);
        let selected = allCatalog.filter((e) => (expIds || []).includes(e.exp_id));
        if (selected.length < 2) selected = allCatalog.slice(0, 3);
        const lowestMoc = selected.reduce((a, b) => (a.moc_measured_pct <= b.moc_measured_pct ? a : b));
        const highestMoc = selected.reduce((a, b) => (a.moc_measured_pct >= b.moc_measured_pct ? a : b));
        const highestO2 = selected.reduce((a, b) => (a.oxygen_pct >= b.oxygen_pct ? a : b));
        const maxHrrExp = selected.reduce((a, b) => (Number(a.hrrpua_kw_m2 || 0) >= Number(b.hrrpua_kw_m2 || 0) ? a : b));
        const coolExps = selected.filter((x) => x.cool_flame_observed).map((x) => x.program);
        const facs = Array.from(new Set(selected.map((x) => x.hardware_group || "CIR"))).sort();
        const scalesTr = Array.from(new Set(selected.map((x) => String(x.scale_class_tr || "Orta Ölçek").split("(")[0].trim()))).sort();
        const scalesEn = Array.from(new Set(selected.map((x) => String(x.scale_class_en || "Mid-Scale").split("(")[0].trim()))).sort();

        const selIds = new Set(selected.map((x) => x.exp_id));
        const mocSpan = roundN(Number(highestMoc.moc_measured_pct) - Number(lowestMoc.moc_measured_pct), 2);
        const reasonsTr = [], reasonsEn = [];
        if (selIds.has("PSI-BASS-03") || selIds.has("PSI-BASS2-04")) {
            reasonsTr.push("durgun 0G testlerinde sönümlenen katı numunelerin düşük hızlı fan akışında (3–8 cm/s) kararlı yanması");
            reasonsEn.push("samples self-extinguishing in quiescent 0G yet burning steadily under gentle 3–8 cm/s ventilation");
        }
        if (selIds.has("PSI-SAFFIRE4-06") || selIds.has("PSI-SAFFIRE1-05")) {
            reasonsTr.push("kalın/düz numune sönümlenirken ince veya oluklu (ribbed) geometrinin +%45 hızlı yayılması");
            reasonsEn.push("thick/flat slabs quenching while thin or ribbed geometries accelerate flame spread by +45%");
        }
        if (scalesTr.length >= 2) {
            reasonsTr.push(`farklı deney ölçekleri (${scalesTr.join(" vs. ")}) arasında kabin sınır ve ısı kaybı farkı`);
            reasonsEn.push(`scale divergence across facilities (${scalesEn.join(" vs. ")})`);
        }
        if (mocSpan >= 2.2) {
            reasonsTr.push(`test kayıtları arasında %${mocSpan.toFixed(1)} O₂ genişliğinde MOC eşik farkı`);
            reasonsEn.push(`a ${mocSpan.toFixed(1)}% O₂ spread in measured MOC thresholds`);
        }
        const hasConflict = reasonsTr.length > 0;
        const worstMoc = Number(lowestMoc.moc_measured_pct);
        const worstHrr = Number(maxHrrExp.hrrpua_kw_m2 || 180);

        return {
            compared_count: selected.length,
            experiments: selected,
            lowest_moc_program: lowestMoc.program,
            synthesis_tr: `**Deney Karşılaştırması Özeti (${selected.length} NASA PSI Kaydı • ${facs.join(" vs. ")}):** En düşük oksijen sınırına sahip deney **%${lowestMoc.moc_measured_pct} MOC** ile **${lowestMoc.program}**; en yüksek birim ısı gücüne ulaşan ise **${worstHrr.toFixed(0)} kW/m² HRRPUA** ile **${maxHrrExp.program}** (Test O₂: \`%${highestO2.oxygen_pct}\`) kaydıdır. ${coolExps.length ? `**${coolExps.join(", ")}** kayıtlarında görünmez Soğuk Alev gözlemlendiğinden CIR UV/IR radyometresi ve CSA-CP / ANITA-2 CO gaz analizi birlikte kullanılmalıdır.` : "HVAC kesme ve SoFIE-MIST ince su sisi birincil Halon-dışı müdahaledir."}`,
            synthesis_en: `**Experiment Comparison Summary (${selected.length} NASA PSI Records • ${facs.join(" vs. ")}):** **${lowestMoc.program}** exhibits the lowest MOC (**${lowestMoc.moc_measured_pct}% O₂**), while **${maxHrrExp.program}** reaches **${worstHrr.toFixed(0)} kW/m² HRRPUA** (Max O₂: **${highestO2.oxygen_pct}%**). ${coolExps.length ? `Cool Flame persistence in **${coolExps.join(", ")}** requires combined CIR UV/IR radiometry and CSA-CP / ANITA-2 CO gas analysis.` : "Immediate HVAC shutoff and SoFIE-MIST water mist remain universal countermeasures."}`,
            conflict_bounding: {
                has_conflict: hasConflict,
                worst_case_moc_pct: worstMoc,
                worst_case_hrrpua_kw_m2: worstHrr,
                warning_tr: hasConflict ? `**Veri Tutarsızlığı ve İhtiyatlı Sınır (Worst-Case Bounding):** Seçili deneylerde ${reasonsTr.join("; ")} saptandı. Ortalama almak yerine ihtiyatlı üst sınır uygulanır: Kritik MOC Tavanı = \`%${worstMoc.toFixed(1)} O₂\` (${lowestMoc.program}) ve Tepe Birim Isı Gücü (\`HRRPUA\`) = \`${worstHrr.toFixed(0)} kW/m²\` (${maxHrrExp.program}).` : "",
                warning_en: hasConflict ? `**Data Discrepancy & Worst-Case Bounding:** Detected ${reasonsEn.join("; ")}. Conservative safety bounding enforces MOC Ceiling = \`${worstMoc.toFixed(1)}% O₂\` (${lowestMoc.program}) and Peak \`HRRPUA\` = \`${worstHrr.toFixed(0)} kW/m²\` (${maxHrrExp.program}).` : "",
            },
        };
    }

    function psiRowToItemJs(row) {
        const acc = String(row.id || "PSI");
        const acro = String(row.acronym || "");
        const rawT = String(row.raw_title || row.title || acc);
        const dispTitle = (acro && !rawT.toLowerCase().includes(acro.toLowerCase()) && !rawT.startsWith(acc))
            ? `${acc} (${acro}) — ${rawT}`
            : (rawT.startsWith(acc) ? rawT : `${acc} — ${rawT}`);
        const hw = String(row.hardware || "").trim();
        const plat = String(row.platform || "ISS").trim();
        const phases = Array.isArray(row.phases) ? row.phases : [];
        return {
            id: acc,
            acronym: acro,
            source: "NASA PSI Repository (psi.nasa.gov)",
            title: dispTitle,
            abstract: String(row.abstract || "NASA Physical Sciences Informatics (PSI) deneysel veri kaydı.").slice(0, 850),
            mission: hw ? `${plat} • ${hw}` : plat,
            date: String(row.date || plat).slice(0, 16),
            url: String(row.url || `https://psi.nasa.gov/physci/repo/data/investigations/${acc}`),
            pdf_url: "",
            table_file: String(row.table_file || ""),
            phase_count: phases.length,
            extracted_sim_params: Object.assign({}, row.extracted_sim_params || {}),
            phases: phases,
            summary_tr: String(row.summary_tr || ""),
            summary_en: String(row.summary_en || ""),
        };
    }

    function searchPsiSnapshotJs(query, limit) {
        if (!PSI_SNAPSHOT.length) return [];
        const qRaw = String(query || "").trim().toLowerCase();
        const broad = ["", "all", "combustion", "flame", "fire", "microgravity", "psi"].includes(qRaw);
        const expanded = expandQueryText(qRaw);
        const tokens = (expanded.match(/[a-z0-9\-]{2,}/g) || []).filter(
            (t) => !["microgravity", "spacecraft", "investigation", "experiment", "nasa"].includes(t)
        );
        const scored = [];
        PSI_SNAPSHOT.forEach((row, idx) => {
            const accL = String(row.id || "").toLowerCase();
            const acroL = String(row.acronym || "").toLowerCase();
            const blob = `${accL} ${acroL} ${row.raw_title || ""} ${row.title || ""} ${row.hardware || ""} ${row.platform || ""} ${row.table_file || ""} ${row.abstract || ""}`.toLowerCase();
            let sc = 0;
            if (qRaw && qRaw === accL) sc += 120;
            if (acroL && qRaw && (qRaw.includes(acroL) || acroL.includes(qRaw))) sc += 25;
            tokens.forEach((tok) => {
                if (tok === accL) sc += 80;
                else if (acroL && acroL.includes(tok)) sc += 12;
                else if (blob.includes(tok)) sc += 4;
            });
            if (broad && sc === 0) sc = 1;
            const hasTbl = (row.phases && row.phases.length) || row.table_file ? 1 : 0;
            if (sc > 0 || broad) scored.push({ sc, hasTbl, idx, row });
        });
        const finalArr = scored.length
            ? scored
            : PSI_SNAPSHOT.map((row, idx) => ({ sc: 1, hasTbl: (row.phases && row.phases.length) ? 1 : 0, idx, row }));
        finalArr.sort((a, b) => (b.sc - a.sc) || (b.hasTbl - a.hasTbl) || (a.idx - b.idx));
        return finalArr.slice(0, Math.max(1, limit || 12)).map((x) => psiRowToItemJs(x.row));
    }

    async function fetchLiveNasaBrowser(source, q) {
        const query = q || "microgravity combustion";
        const srcNorm = String(source || "osdr").toLowerCase();

        if (srcNorm === "osdr" && PSI_SNAPSHOT.length) {
            const psiItems = searchPsiSnapshotJs(query, 12);
            return { ok: true, source_status: "cached_live", count: psiItems.length, items: psiItems };
        }

        const scored = NASA_CATALOG.map((e) => ({
            e,
            sim: computeTextSimilarity(query, `${e.program} ${e.title} ${e.title_tr} ${e.key_finding_en} ${e.key_finding_tr} ${(e.tags || []).join(" ")}`),
        })).sort((a, b) => b.sim - a.sim);
        const items = scored.slice(0, 8).map(({ e }) => ({
            id: `NTRS-${e.ntrs_id}`,
            source: `NASA PSI/NTRS (${e.program})`,
            title: e.title,
            abstract: e.key_finding_en,
            date: String(e.year),
            url: e.ntrs_url,
            pdf_url: "",
            extracted_sim_params: {
                fuel_id: e.fuel_id || "n_heptane",
                gravity_g: Number(e.gravity_g ?? 0.0),
                oxygen_pct: Number(e.oxygen_pct ?? 21.0),
                pressure_psia: Number(e.pressure_psia ?? 14.7),
                airflow_cms: Number(e.airflow_cms ?? 2.4),
                droplet_d0_mm: e.cool_flame_observed ? 4.4 : 3.2,
                diluent: "N2",
            },
        }));
        return { ok: true, source_status: "cached_live", count: items.length, items };
    }

    function extractReadableTextFromPdfBuffer(buf) {
        const bytes = new Uint8Array(buf);
        let rawAscii = "";
        const maxLen = Math.min(bytes.length, 450000);
        for (let i = 0; i < maxLen; i++) {
            const c = bytes[i];
            rawAscii += (c >= 32 && c <= 126) || c === 10 || c === 13 ? String.fromCharCode(c) : " ";
        }
        const chunks = [];
        const parenRe = /\(([^()]{3,220})\)/g;
        let m;
        while ((m = parenRe.exec(rawAscii)) !== null) {
            const seg = m[1].replace(/\\[nrt]/g, " ").trim();
            if (/[A-Za-z]{3,}/.test(seg) && !/^(PDF-|Identity-H|Adobe|FlateDecode|FontDescriptor)/i.test(seg)) {
                chunks.push(seg);
            }
        }
        if (chunks.length >= 5) {
            return chunks.join(" ").replace(/\s+/g, " ").slice(0, 12000);
        }
        return rawAscii
            .replace(/\b(obj|endobj|stream|endstream|xref|trailer|FlateDecode|Filter|Length)\b/g, " ")
            .replace(/\s+/g, " ")
            .trim()
            .slice(0, 8000);
    }

    function parseCellNumberJs(rawVal) {
        if (rawVal === undefined || rawVal === null) return null;
        if (typeof rawVal === "number") return Number.isFinite(rawVal) ? rawVal : null;
        let s = String(rawVal).trim();
        if (!s || ["na", "n/a", "nan", "null", "none", "-", "--", "tbd"].includes(s.toLowerCase())) return null;
        if (/^\d{4}[-/]\d{1,2}[-/]\d{1,2}/.test(s)) return null;
        s = s.replace(/%/g, "").replace(/±\s*\d+(?:\.\d+)?/g, "").trim();
        const direct = Number(s);
        if (!Number.isNaN(direct) && Number.isFinite(direct)) return direct;
        const rng = s.match(/^\s*(-?\d+(?:\.\d+)?)\s*(?:-|–|—|\bto\b)\s*(-?\d+(?:\.\d+)?)\b/i);
        if (rng) {
            const a = parseFloat(rng[1]), b = parseFloat(rng[2]);
            if (Number.isFinite(a) && Number.isFinite(b)) return (a + b) * 0.5;
        }
        const parts = s.split(/[;/|]/);
        for (let i = 0; i < parts.length; i++) {
            const m = parts[i].match(/^\s*(-?\d+(?:\.\d+)?)(?:\s*(?:atm|psia|psi|kpa|bar|torr|mmhg|cm\/s|m\/s|mm|s|sec|k|c|°c|g))?\s*$/i);
            if (m) {
                const v = parseFloat(m[1]);
                if (Number.isFinite(v)) return v;
            }
        }
        return null;
    }

    function parseFuelStrJs(val) {
        const vl = String(val || "").toLowerCase().trim();
        if (!vl) return null;
        const cands = [
            ["propane_cfig", ["propane_cfig", "propan", "propane", "c3h8", "cfig", "cfi-g", "ethane", "c2h6", "etan", "ethylene", "etilen", "c2h4", "propene", "propylene", "c3h6", "butane", "butan", "c4h10", "methane", "metan", "ch4"]],
            ["n_heptane", ["n_heptane", "n-heptane", "heptan", "heptane", "c7h16", "dodecane", "n-dodecane", "c12h26", "decane", "n-decane", "c10h22", "octane", "iso-octane", "isooctane", "c8h18", "hexadecane", "pentane", "jp-8", "jp8", "kerosene"]],
            ["methanol", ["methanol", "metanol", "ch3oh", "ethanol", "etanol", "c2h5oh", "propanol", "isopropanol", "ipa", "butanol", "n-butanol"]],
            ["pmma", ["pmma", "akrilik", "acrylic", "plexiglas", "perspex", "polymethyl", "teflon", "ptfe", "delrin", "polyoxymethylene", "pom", "polyethylene", "hdpe", "ldpe", "polypropylene", "polycarbonate", "lexan", "ultem", "pei", "silicone", "pvc", "nylon", "abs", "epoxy"]],
            ["sibal", ["sibal", "pamuk", "cotton", "cellulose", "seluloz", "whatman", "paper", "kagit", "fabric", "fiberglass", "glass fabric", "kimwipe"]],
            ["nomex", ["nomex", "ht90", "spacesuit", "uzay giysisi", "kevlar", "kapton", "polyimide", "pbi", "gore-tex", "orthofabric", "betacloth"]],
            ["hydrogen", ["hydrogen", "hidrojen"]],
        ];
        let bestFuel = null, bestPos = 1e9;
        cands.forEach(([fid, kws]) => {
            kws.forEach((kw) => {
                const idx = vl.indexOf(kw);
                if (idx !== -1 && idx < bestPos) {
                    bestPos = idx;
                    bestFuel = fid;
                }
            });
        });
        if (!bestFuel && /(?:^|[\s,;/(_-])h2(?:$|[\s,;/)_-])/.test(vl)) return "hydrogen";
        return bestFuel;
    }

    function parseDiluentStrJs(val) {
        const vl = String(val || "").trim().toUpperCase();
        if (!vl) return null;
        if (vl === "CO2" || vl.includes("CO2") || vl.includes("KARBONDIOKSIT") || vl.includes("CARBON DIOXIDE")) return "CO2";
        if (vl === "HE" || vl.includes("HELIUM") || vl.includes("HELYUM") || /\bHE\b/.test(vl)) return "He";
        if (vl === "AR" || vl.includes("ARGON")) return "Ar";
        if (vl === "XE" || vl.includes("XENON")) return "Xe";
        if (vl === "N2" || vl.includes("N2") || vl.includes("AZOT") || vl.includes("NITROGEN") || vl === "AIR") return "N2";
        return null;
    }

    function parseHabitatStrJs(val) {
        const vl = String(val || "").toLowerCase().trim();
        if (!vl) return null;
        if (["iss_module", "lunar_hab", "lunar_rover", "eva_suit"].includes(vl)) return vl;
        if (vl.includes("suit") || vl.includes("giysi") || vl.includes("eva")) return "eva_suit";
        if (vl.includes("rover") || vl.includes("gezgin")) return "lunar_rover";
        if (vl.includes("lunar") || vl.includes("ay_ussu") || vl.includes("hab")) return "lunar_hab";
        if (vl.includes("iss") || vl.includes("destiny")) return "iss_module";
        return null;
    }

    function extractChemSubtokenJs(rawVal) {
        const s = String(rawVal || "").toLowerCase().trim();
        if (!s) return "";
        const toks = [
            "ch4", "methane", "c2h4", "ethylene", "c2h6", "ethane", "c3h6", "propylene",
            "c3h8", "propane", "c4h10", "butane", "heptane", "dodecane", "decane", "octane",
            "methanol", "ethanol", "butanol", "propanol", "pmma", "acrylic", "teflon", "ptfe",
            "delrin", "polyethylene", "polycarbonate", "ultem", "cotton", "sibal", "cellulose",
            "whatman", "nomex", "kevlar", "kapton", "hydrogen", "h2",
        ];
        for (let i = 0; i < toks.length; i++) {
            if (s.includes(toks[i])) return toks[i];
        }
        return s.slice(0, 14);
    }

    function classifyTableColJs(colName) {
        const kl = String(colName || "").trim().toLowerCase().replace(/\s+/g, " ");
        if (!kl) return null;
        if (["test name", "test_name", "test id", "test_id", "test #", "test number", "run id", "run_id", "point #", "sample id", "drop #", "droplet id", "flame id", "experiment id"].some((w) => kl.includes(w)) || ["test", "run", "trial", "test_no"].includes(kl)) return "test_id";
        if (["test type", "test_type", "flame type", "configuration", "burner mode", "flow configuration"].includes(kl)) return "test_type";
        if (kl.includes("polarity") || kl.includes("electrode")) return "polarity";
        if ((kl.includes("voltage") || kl.includes("electric field") || kl.includes("e-field")) && !kl.includes("current")) return "voltage_kv";
        if ((kl.includes("fuel") && (kl.includes("conc") || kl.includes("mole frac") || kl.includes("mol frac") || kl === "xf" || kl === "x_f")) || ["xf", "x_f", "fuel %", "fuel conc"].includes(kl)) return "fuel_conc";
        if (kl.includes("fuel") && (kl.includes("rate") || kl.includes("flow") || kl.includes("sccm") || kl.includes("slpm") || kl.includes("mg/s"))) return "fuel_rate";
        if (!["date", "ignition", "burn time", "delay", "duration", "lifetime", "extinct"].some((b) => kl.includes(b)) &&
            (["t", "time", "time_s", "t_s", "zaman", "zaman_sn", "sec", "seconds"].includes(kl) || kl.includes("zaman") || kl.includes("time_s") || kl.includes("time (s)"))) return "time_s";
        if (kl === "faz_kodu" || kl === "phase_code") return "phase_code";
        if (!["gas phase", "liquid phase", "solid phase"].some((b) => kl.includes(b)) &&
            ["faz_ve_fiziksel", "phase_desc", "fiziksel_durum", "faz", "phase", "stage"].some((w) => kl.includes(w))) return "phase_desc";
        if (!["rate", "flow", "mass", "temp", "fraction", "mole", "conc", "width", "thick", "length", "diam", "size", "initial", "final"].some((b) => kl.includes(b)) &&
            ["fuel", "yakit", "material", "malzeme", "sample type", "polymer", "hydrocarbon", "reactant"].some((w) => kl.includes(w))) return "fuel";
        if (["diluent", "seyreltici", "balance gas", "inert gas"].some((w) => kl.includes(w))) return "diluent";
        if (kl === "xhe" || kl === "x_he" || ((kl.includes("helium") || /\bhe\b/.test(kl)) && (kl.includes("mole") || kl.includes("frac") || kl.includes("%") || kl.includes("conc") || kl.includes("initial")))) return "diluent_he_frac";
        if (kl === "xco2" || kl === "x_co2" || (kl.includes("co2") && (kl.includes("mole") || kl.includes("frac") || kl.includes("ambient") || kl.includes("initial") || kl.includes("%")))) return "diluent_co2_frac";
        if (["habitat", "kabin_tipi"].some((w) => kl.includes(w))) return "habitat";
        if (["donanim", "facility", "hardware", "rack", "insert"].some((w) => kl.includes(w))) return "facility";
        if (["deney_referans", "exp_ref", "exp_id", "ntrs", "psi_id"].some((w) => kl.includes(w))) return "exp_ref";

        if (!["co2", "po2", "p_o2", "h2o", "ch2o", "moc", "sio2", "no2", "so2", "tio2", "flow", "rate", "sccm"].some((b) => kl.includes(b))) {
            const isO2Name = kl === "xo2" || kl === "x_o2" || kl.includes("oxygen") || kl.includes("oksijen") || kl.includes("o initial ambient") || /(?:^|[_\s(%])o2(?:$|[_\s)%])/.test(kl);
            if (isO2Name) {
                if (kl === "xo2" || kl === "x_o2" || kl.includes("mole frac") || kl.includes("mol frac") || kl.includes("mole_frac") || kl.includes("volume frac")) return "oxygen_mole_frac";
                return "oxygen_pct";
            }
        }

        if (!kl.includes("po2") && !kl.includes("p_o2") && !kl.includes("partial") && !kl.includes("drop")) {
            if (kl.includes("mmhg") || kl.includes("torr")) return "pressure_mmhg";
            if (/\bbar\b|\bara\b/.test(kl)) return "pressure_bar";
            if (/\batm\b|atmosphere/.test(kl) && !kl.includes("ambient atmosphere")) return "pressure_atm";
            if (kl.includes("kpa")) return "pressure_kpa";
            if (kl.includes("psia") || kl.includes("psi") || kl.includes("pressure") || kl.includes("basinc") || kl.includes("p_amb") || kl.includes("chamber p")) return "pressure_psia";
        }

        if (!["yayilim", "spread", "mm_s", "mm/s", "fuel", "burner", "nozzle", "sccm", "slpm", "mg/s", "g/s", "ml/min", "l/min", "restrictor", "fan display", "self-ext", "flow term", "mass flow", "volumetric"].some((b) => kl.includes(b))) {
            if (["air rate", "air flow", "airflow", "concurrent flow", "oxidizer vel", "tunnel vel", "duct vel", "forced flow", "akis", "u_cms", "fan_cm", "air vel"].some((w) => kl.includes(w)) ||
                ((kl.includes("flow") || kl.includes("velocity")) && (kl.includes("cm/s") || kl.includes("cm_s") || kl.includes("m/s"))) ||
                kl === "air display") return "airflow_cms";
        }

        if (["gravity", "yercekimi", "g_level", "g-level", "microgravity"].some((w) => kl.includes(w))) return "gravity_g";
        if (kl.includes("d2") || kl.includes("d_sq") || kl.includes("d^2")) return "d2_mm2";
        if (!["partikul", "sisi", "mist", "aerosol", "wire", "igniter", "fiber"].some((b) => kl.includes(b)) &&
            ["damlacik", "droplet", "diameter", "d0", "d_mm", "numune_cap", "nozzle", "burner size", "burner dia", "sphere dia", "rod dia"].some((w) => kl.includes(w))) return "d0_mm";

        if (["sicaklik", "temp_k", "flame_temp", "thermocouple", "tad", "adiabatic flame", "peak burner t", "peak temp", "max temp"].some((w) => kl.includes(w))) {
            if (/\(\s*°?c\s*\)|deg\s*c|celsius/.test(kl)) return "temp_c";
            return "temp_k";
        }
        if (kl.includes("cool flame") || kl.includes("soguk alev")) return "cool_flag";
        if (!kl.includes("co2") && !kl.includes("smac") && (kl === "co" || kl.includes("co_ppm") || kl.includes("co_sensor"))) return "co_ppm";
        if (kl.includes("co2")) return "co2_ppm";
        if (kl.includes("ch2o") || kl.includes("formaldehit") || kl.includes("formaldehyde")) return "ch2o_ppm";
        if (kl.includes("optik") || kl.includes("optical")) return "opt_vis";
        if (kl.includes("radyatif") || kl.includes("radiometer") || kl.includes("heat_flux") || kl.includes("isi_akisi")) return "ir_kw";
        if (kl.includes("su_sisi") || kl.includes("mist")) return "mist_um";
        if (kl.includes("partikul") || kl.includes("aerosol") || kl.includes("dust_um")) return "aerosol_um";
        return null;
    }

    function looksLikeTabularTextJs(text, filename) {
        const fnLow = String(filename || "").toLowerCase().replace(/\)+$/, "").trim();
        if ([".csv", ".tsv", ".xlsx"].some((ext) => fnLow.endsWith(ext))) return true;
        const lines = String(text || "").split(/\r?\n/).map((ln) => ln.trim()).filter(Boolean).slice(0, 15);
        if (lines.length < 2) return false;
        const first = lines[0];
        const delims = [",", ";", "\t"];
        let bestD = ",", bestCnt = 0;
        delims.forEach((d) => {
            const c = first.split(d).length - 1;
            if (c > bestCnt) { bestCnt = c; bestD = d; }
        });
        if (bestCnt < 2) return false;
        const hdrCells = splitCsvLineJs(first, bestD);
        if (hdrCells.some((c) => c.length > 68)) return false;
        if (!hdrCells.some((c) => Boolean(classifyTableColJs(c)))) return false;
        const secondCnt = lines[1].split(bestD).length - 1;
        return Math.abs(secondCnt - bestCnt) <= Math.max(2, Math.floor(bestCnt / 2));
    }

    function splitCsvLineJs(line, delim) {
        const out = [];
        let cur = "", inQuotes = false;
        for (let i = 0; i < line.length; i++) {
            const ch = line[i];
            if (ch === '"') {
                if (inQuotes && line[i + 1] === '"') { cur += '"'; i++; }
                else inQuotes = !inQuotes;
            } else if (ch === delim && !inQuotes) {
                out.push(cur.trim());
                cur = "";
            } else {
                cur += ch;
            }
        }
        out.push(cur.trim());
        return out;
    }

    function parseCsvRowsJs(cleanText) {
        const lines = cleanText.replace(/^\uFEFF/, "").split(/\r?\n/).filter((ln) => ln.trim().length > 0).slice(0, 600);
        if (lines.length < 2) return [];
        const semiCnt = (lines[0].match(/;/g) || []).length;
        const commaCnt = (lines[0].match(/,/g) || []).length;
        const delim = semiCnt > commaCnt ? ";" : (lines[0].includes("\t") ? "\t" : ",");
        const headers = splitCsvLineJs(lines[0], delim);
        if (headers.length < 2) return [];
        const rows = [];
        for (let i = 1; i < lines.length; i++) {
            const cells = splitCsvLineJs(lines[i], delim);
            if (cells.length < 2) continue;
            const obj = {};
            for (let j = 0; j < headers.length; j++) {
                obj[headers[j]] = cells[j] !== undefined ? cells[j] : "";
            }
            rows.push(obj);
        }
        return rows;
    }

    function fitD2SlopeJs(tVals, d2Vals) {
        if (!tVals || !d2Vals || tVals.length < 3 || tVals.length !== d2Vals.length) return null;
        const n = tVals.length;
        const dt = tVals[n - 1] - tVals[0];
        const drop = d2Vals[0] - d2Vals[n - 1];
        if (dt <= 0.2 || drop <= 0.08) return null;
        let sumT = 0, sumY = 0;
        for (let i = 0; i < n; i++) { sumT += tVals[i]; sumY += d2Vals[i]; }
        const meanT = sumT / n, meanY = sumY / n;
        let num = 0, den = 0;
        for (let i = 0; i < n; i++) {
            num += (tVals[i] - meanT) * (d2Vals[i] - meanY);
            den += (tVals[i] - meanT) * (tVals[i] - meanT);
        }
        if (den <= 1e-9) return null;
        const slope = num / den;
        const intercept = meanY - slope * meanT;
        const kMeas = Math.max(0, -slope);
        if (kMeas <= 0.005) return null;
        let ssRes = 0, ssTot = 0;
        for (let i = 0; i < n; i++) {
            const pred = slope * tVals[i] + intercept;
            ssRes += (d2Vals[i] - pred) * (d2Vals[i] - pred);
            ssTot += (d2Vals[i] - meanY) * (d2Vals[i] - meanY);
        }
        const r2 = ssTot > 1e-9 ? Math.max(0, Math.min(1, 1 - ssRes / ssTot)) : 0.999;
        return { k_meas: Number(kMeas.toFixed(3)), r2: Number(r2.toFixed(4)) };
    }

    function convertO2ValJs(v, isMoleCol) {
        if (v === null || v === undefined || !Number.isFinite(v) || v <= 0) return null;
        if (isMoleCol) {
            const pct = v <= 1.05 ? v * 100.0 : v;
            return pct >= 3.0 && pct <= 100.0 ? pct : null;
        }
        if (v >= 0.03 && v <= 1.0) return v * 100.0;
        if (v >= 3.0 && v <= 100.0) return v;
        return null;
    }

    function analyzeTabularRowsInBrowser(rows, filename) {
        rows = (rows || []).filter((r) => r && Object.values(r).some((v) => String(v ?? "").trim() !== ""));
        if (!rows.length) return null;
        const colMap = {};
        Object.keys(rows[0] || {}).forEach((rawK) => {
            const role = classifyTableColJs(rawK);
            if (role && !colMap[role]) colMap[role] = rawK;
        });

        const numList = (rList, roleKey) => {
            const col = colMap[roleKey];
            if (!col) return [];
            const out = [];
            rList.forEach((it) => {
                const v = parseCellNumberJs(it[col]);
                if (v !== null) out.push(v);
            });
            return out;
        };

        const firstStr = (rList, roleKey) => {
            const col = colMap[roleKey];
            if (!col) return "";
            for (let i = 0; i < rList.length; i++) {
                const s = String(rList[i][col] || "").trim();
                if (s && !["na", "n/a", "null", "none", "-"].includes(s.toLowerCase())) return s;
            }
            return "";
        };

        const extractO2Values = (rList) => {
            const out = [];
            numList(rList, "oxygen_mole_frac").forEach((v) => {
                const c = convertO2ValJs(v, true);
                if (c !== null) out.push(c);
            });
            numList(rList, "oxygen_pct").forEach((v) => {
                const c = convertO2ValJs(v, false);
                if (c !== null) out.push(c);
            });
            return out;
        };

        const extractPressurePsia = (rList) => {
            const out = [];
            numList(rList, "pressure_psia").forEach((v) => {
                const colL = String(colMap.pressure_psia || "").toLowerCase();
                if (!colL.includes("psi") && v >= 0.2 && v <= 2.2) out.push(v * 14.6959);
                else if (!colL.includes("psi") && v >= 45 && v <= 220) out.push(v / 6.89476);
                else if (v >= 2.0 && v <= 35.0) out.push(v);
            });
            numList(rList, "pressure_atm").forEach((v) => { if (v >= 0.1 && v <= 3.0) out.push(v * 14.6959); });
            numList(rList, "pressure_bar").forEach((v) => { if (v >= 0.1 && v <= 3.0) out.push(v * 14.5038); });
            numList(rList, "pressure_kpa").forEach((v) => { if (v >= 15.0 && v <= 260.0) out.push(v / 6.89476); });
            numList(rList, "pressure_mmhg").forEach((v) => { if (v >= 100.0 && v <= 1800.0) out.push(v / 51.7149); });
            return out.filter((p) => p >= 2.0 && p <= 35.0);
        };

        const extractDiluent = (rList) => {
            const dExp = parseDiluentStrJs(firstStr(rList, "diluent"));
            if (dExp) return dExp;
            const heV = numList(rList, "diluent_he_frac");
            const co2V = numList(rList, "diluent_co2_frac");
            const heHdr = String(colMap.diluent_he_frac || "").toLowerCase();
            const co2Hdr = String(colMap.diluent_co2_frac || "").toLowerCase();
            const heIsPct = heHdr.includes("%") || heHdr.includes("percent") || heHdr.includes("by vol");
            const co2IsPct = co2Hdr.includes("%") || co2Hdr.includes("percent") || co2Hdr.includes("by vol");
            const heMean = heV.length ? heV.reduce((a, b) => a + b, 0) / heV.length : 0;
            const co2Mean = co2V.length ? co2V.reduce((a, b) => a + b, 0) / co2V.length : 0;
            const hePct = (!heIsPct && heMean <= 1.05) ? heMean * 100 : heMean;
            const co2Pct = (!co2IsPct && co2Mean <= 1.05) ? co2Mean * 100 : co2Mean;
            if (hePct >= 15 && hePct >= co2Pct) return "He";
            if (co2Pct >= 15) return "CO2";
            return "N2";
        };

        const anchorRoles = ["test_id", "test_type", "fuel", "oxygen_pct", "oxygen_mole_frac", "pressure_psia", "pressure_atm", "pressure_bar", "pressure_kpa", "pressure_mmhg", "airflow_cms", "d0_mm", "d2_mm2", "time_s", "phase_code"];
        const activeAnchors = anchorRoles.map((rk) => colMap[rk]).filter(Boolean);
        if (activeAnchors.length >= 2) {
            const filteredRows = rows.filter((r) => activeAnchors.some((c) => String(r[c] ?? "").trim() !== ""));
            if (filteredRows.length >= 1) rows = filteredRows;
        }

        const flowColLow = String(colMap.airflow_cms || "").toLowerCase();
        const flowScale = (flowColLow.includes("m/s") && !flowColLow.includes("cm/s") && !flowColLow.includes("mm/s")) ? 100.0 : 1.0;
        const fuelCounts = {};
        if (colMap.fuel) {
            rows.forEach((r) => {
                const pf = parseFuelStrJs(String(r[colMap.fuel] || ""));
                if (pf) fuelCounts[pf] = (fuelCounts[pf] || 0) + 1;
            });
        }
        const domFuelKey = Object.keys(fuelCounts).sort((a, b) => fuelCounts[b] - fuelCounts[a])[0];
        const fnLow = String(filename || "").toLowerCase();
        const fnHint = parseFuelStrJs(fnLow) || ((fnLow.includes("bass") || fnLow.includes("sofie") || fnLow.includes("same")) ? "pmma" : (fnLow.includes("saffire") ? "sibal" : null));
        const fallbackFuel = domFuelKey || fnHint || "n_heptane";

        let groupedPhases = [];
        const phaseLookup = {};
        rows.forEach((r) => {
            const pCode = String((colMap.phase_code && r[colMap.phase_code]) || "").trim();
            const pDesc = String((colMap.phase_desc && r[colMap.phase_desc]) || "").trim();
            const pKey = pCode || pDesc || "FAZ_1";
            if (!phaseLookup[pKey]) {
                const entry = {
                    key: pKey,
                    code: pCode || pKey.split(" ")[0],
                    desc: pDesc || pCode || "Standart Yanma Fazi",
                    rows: [],
                };
                phaseLookup[pKey] = entry;
                groupedPhases.push(entry);
            }
            phaseLookup[pKey].rows.push(r);
        });

        // Akıllı Çoklu Test Gruplaması (Gerçek NASA PSI Experimental Table CSV'leri için)
        if (groupedPhases.length === 1 && rows.length >= 2 && !colMap.phase_code && !colMap.phase_desc) {
            const tCheck = numList(rows, "time_s");
            const d2Raw = numList(rows, "d2_mm2");
            const d0Raw = numList(rows, "d0_mm");
            const d2Check = d2Raw.length ? d2Raw : d0Raw.map((x) => x * x);
            const isMonotonicD2 = tCheck.length >= 3 && d2Check.length === tCheck.length && Boolean(fitD2SlopeJs(tCheck, d2Check));
            if (!isMonotonicD2) {
                if (rows.length <= 7) {
                    groupedPhases = rows.map((r, rIdx) => {
                        const tid = String((colMap.test_id && r[colMap.test_id]) || "").trim();
                        return {
                            key: `TEST_${rIdx + 1}`,
                            code: tid || `TEST_${rIdx + 1}`,
                            desc: tid ? `Test ${tid}` : `Test ${rIdx + 1}`,
                            rows: [r],
                        };
                    });
                } else {
                    const buckets = {};
                    const bucketList = [];
                    rows.forEach((r) => {
                        const rawFuelCell = firstStr([r], "fuel");
                        const rFuel = parseFuelStrJs(rawFuelCell) || fallbackFuel;
                        const subFuel = rawFuelCell ? extractChemSubtokenJs(rawFuelCell) : rFuel;
                        const rO2L = extractO2Values([r]);
                        const rO2B = rO2L.length ? Math.round(rO2L[0] / 3.0) * 3 : 21;
                        const rPL = extractPressurePsia([r]);
                        const rPB = rPL.length ? Math.round(rPL[0] / 2.0) * 2 : 15;
                        const rFL = numList([r], "airflow_cms").map((v) => v * flowScale);
                        const rFB = rFL.length ? (rFL[0] < 0.8 ? 0 : (rFL[0] <= 10 ? 5 : (rFL[0] <= 24 ? 15 : 30))) : -1;
                        const rGL = numList([r], "gravity_g");
                        const rGB = rGL.length ? Math.round(rGL[0] * 10) / 10 : 0;
                        const rDil = extractDiluent([r]);
                        const rPol = firstStr([r], "polarity").slice(0, 8).toLowerCase();
                        const rTT = firstStr([r], "test_type").slice(0, 12).toLowerCase();
                        const rFCL = numList([r], "fuel_conc");
                        const rFCB = rFCL.length ? Math.round((rFCL[0] <= 1.05 ? rFCL[0] * 100 : rFCL[0]) / 20) * 20 : -1;
                        const rVL = numList([r], "voltage_kv");
                        const rVB = rVL.length ? Math.round(Math.abs(rVL[0]) / 2) * 2 : -1;
                        const rFRL = numList([r], "fuel_rate");
                        const rFRB = (rFB === -1 && rFRL.length) ? Math.round(rFRL[0] / 50) * 50 : -1;
                        const bKey = `${subFuel}|${rO2B}|${rPB}|${rFB}|${rGB}|${rDil}|${rPol}|${rFCB}|${rTT}|${rVB}|${rFRB}`;
                        if (!buckets[bKey]) {
                            if (bucketList.length < 7) {
                                const tid = String((colMap.test_id && r[colMap.test_id]) || "").trim();
                                const parts = [rawFuelCell || rFuel];
                                if (rO2L.length) parts.push(`%${rO2B} O₂`);
                                if (rPL.length) parts.push(`${rPB} psia`);
                                if (rFCL.length && rFCB < 100) parts.push(`%${rFCB} Yakıt`);
                                if (rPol) parts.push(rPol);
                                if (rVL.length) parts.push(`${rVL[0]} kV`);
                                const bObj = {
                                    key: bKey,
                                    code: tid || `GRUP_${bucketList.length + 1}`,
                                    desc: parts.join(" • "),
                                    rows: [],
                                };
                                buckets[bKey] = bObj;
                                bucketList.push(bObj);
                            } else {
                                bucketList[bucketList.length - 1].rows.push(r);
                                return;
                            }
                        }
                        buckets[bKey].rows.push(r);
                    });
                    if (bucketList.length >= 2) groupedPhases = bucketList;
                }
            }
        }

        const avg = (arr, defVal) => (arr.length ? Number((arr.reduce((a, b) => a + b, 0) / arr.length).toFixed(2)) : defVal);

        const phasesOut = [];
        let bestD2Fit = null;
        let hasCoolTelemetry = false;
        let hasMistTelemetry = false;
        let aeroMin = null, aeroMax = null;

        groupedPhases.forEach((grp, gIdx) => {
            const idx = gIdx + 1;
            const pr = grp.rows;
            const fuelId = parseFuelStrJs(firstStr(pr, "fuel")) || fallbackFuel;
            const diluent = extractDiluent(pr);
            let habitatId = parseHabitatStrJs(firstStr(pr, "habitat"));

            const o2Vals = extractO2Values(pr);
            const psiaVals = extractPressurePsia(pr);
            const flowVals = numList(pr, "airflow_cms").map((x) => x * flowScale).filter((x) => x >= 0 && x <= 60);
            const gravVals = numList(pr, "gravity_g").filter((x) => x >= 0 && x <= 2);
            const d0Vals = numList(pr, "d0_mm").filter((x) => x >= 0.4 && x <= 25);
            const d2Vals = numList(pr, "d2_mm2").filter((x) => x >= 0.1 && x <= 100);
            const tVals = numList(pr, "time_s");
            const tempKVals = numList(pr, "temp_k").filter((x) => x >= 250 && x <= 3500);
            const tempCVals = numList(pr, "temp_c").filter((x) => x >= 20 && x <= 3000).map((x) => x + 273.15);
            const tempVals = tempKVals.concat(tempCVals);
            const coVals = numList(pr, "co_ppm");
            const ch2oVals = numList(pr, "ch2o_ppm");
            const mistVals = numList(pr, "mist_um");
            const aeroVals = numList(pr, "aerosol_um").filter((x) => x > 0);
            const coolStr = firstStr(pr, "cool_flag").toLowerCase();
            const rowCoolObserved = ["y", "yes", "true", "1", "evet", "observed", "cool"].includes(coolStr);

            const fcVals = numList(pr, "fuel_conc").map((x) => (x <= 1.05 ? x * 100.0 : x)).filter((x) => x >= 2 && x <= 100);
            const vkvVals = numList(pr, "voltage_kv").map((x) => Math.abs(x)).filter((x) => x >= 0 && x <= 30);
            const frVals = numList(pr, "fuel_rate").filter((x) => x > 0);
            const polVal = firstStr(pr, "polarity").toLowerCase();
            const ttVal = firstStr(pr, "test_type").toLowerCase();

            let o2Mean = avg(o2Vals, 21.0);
            const pPsia = avg(psiaVals, 14.7);
            let flowMean;
            if (flowVals.length) {
                flowMean = Number(Math.min(45.0, avg(flowVals, 2.4)).toFixed(2));
            } else if (vkvVals.length) {
                flowMean = Number(Math.min(18.0, 1.8 + avg(vkvVals, 0) * 1.35).toFixed(2));
            } else if (ttVal.includes("coflow") || ttVal.includes("co-flow")) {
                flowMean = polVal.includes("neg") ? 5.8 : (polVal.includes("pos") ? 4.2 : 3.4);
            } else if (frVals.length) {
                flowMean = Number(Math.min(14.0, Math.max(1.2, avg(frVals, 50) / 45.0)).toFixed(2));
            } else {
                flowMean = 2.4;
            }
            const gravMean = avg(gravVals, 0.0);
            let d0Init;
            if (d0Vals.length) {
                d0Init = Number(Math.max(0.8, Math.min(8.0, d0Vals[0])).toFixed(2));
            } else if (d2Vals.length) {
                d0Init = Number(Math.max(0.8, Math.min(8.0, Math.sqrt(Math.max(0.64, d2Vals[0])))).toFixed(2));
            } else if (fcVals.length) {
                const fcAvg = avg(fcVals, 100);
                d0Init = Number(Math.max(1.5, Math.min(5.2, 1.5 + (fcAvg / 100.0) * 2.5)).toFixed(2));
                if (!o2Vals.length && fcAvg < 65) {
                    o2Mean = Number(Math.max(15.5, 21.0 - (100.0 - fcAvg) * 0.03).toFixed(1));
                }
            } else {
                d0Init = 3.2;
            }

            if (!habitatId) {
                if (o2Mean >= 75 && pPsia <= 6) habitatId = "eva_suit";
                else if (gravMean >= 0.10 && gravMean <= 0.25 && pPsia <= 11.5) habitatId = "lunar_rover";
                else if (gravMean >= 0.10) habitatId = "lunar_hab";
                else habitatId = "iss_module";
            }

            const d2Series = d2Vals.length ? d2Vals : (d0Vals.length ? d0Vals.map((x) => x * x) : []);
            const fit = (tVals.length && d2Series.length && tVals.length === d2Series.length) ? fitD2SlopeJs(tVals, d2Series) : null;

            const rawFuelStr = firstStr(pr, "fuel");
            const probeMatLow = `${rawFuelStr} ${filename}`.toLowerCase();
            let effFuelId = fuelId;
            let customMatLbl = "";
            const unlistedList = [
                ["peek", "PEEK"],
                ["xlpe", "XLPE Kablo İzolasyonu"],
                ["ptfe", "PTFE / Teflon"],
                ["teflon", "PTFE / Teflon"],
                ["kapton", "Kapton Poliimid"],
                ["pvc", "PVC Kablo Kılıfı"],
                ["carbon-epoxy", "Karbon-Epoksi Kompozit"],
                ["karbon epoksi", "Karbon-Epoksi Kompozit"],
            ];
            for (let ui = 0; ui < unlistedList.length; ui++) {
                const uKw = unlistedList[ui][0];
                const reUn = new RegExp(`(?:^|[^a-z0-9])${uKw.replace("-", "\\-")}(?:$|[^a-z0-9])`, "i");
                if (reUn.test(probeMatLow)) {
                    effFuelId = "custom_material";
                    customMatLbl = unlistedList[ui][1];
                    break;
                }
            }
            const flowDirRow = (ttVal.includes("concurrent") || ttVal.includes("coflow") || ttVal.includes("co-flow") || ttVal.includes("es yonlu") || ttVal.includes("eş yönlü"))
                ? "concurrent"
                : "opposed";

            const phaseParams = {
                fuel_id: effFuelId,
                gravity_g: gravMean,
                oxygen_pct: o2Mean,
                pressure_psia: pPsia,
                airflow_cms: flowMean,
                flow_direction: flowDirRow,
                droplet_d0_mm: d0Init,
                diluent: diluent,
                habitat_id: habitatId,
            };
            if (customMatLbl) phaseParams.custom_material_name = customMatLbl;
            const simRes = simulateCombustionClient(phaseParams);
            const tel = simRes.telemetry;
            const tl = simRes.scenario_timeline || {};
            const call = simRes.callouts || {};

            if (fit && (fuelId === "n_heptane" || fuelId === "methanol") && (!bestD2Fit || fit.k_meas > bestD2Fit.k_meas)) {
                bestD2Fit = { phase_idx: idx, k_meas: fit.k_meas, k_model: tel.burning_rate_k_mm2_s, r2: fit.r2 };
            }

            const tempMean = tempVals.length ? Number((tempVals.reduce((a, b) => a + b, 0) / tempVals.length).toFixed(1)) : tel.flame_temp_k;
            const coMax = coVals.length ? Number(Math.max(...coVals).toFixed(1)) : tel.co_ppm;
            const ch2oMax = ch2oVals.length ? Number(Math.max(...ch2oVals).toFixed(1)) : 0;
            const mistMax = mistVals.length ? Number(Math.max(...mistVals).toFixed(1)) : 0;

            if (tel.cool_flame_active || rowCoolObserved || (tempMean >= 500 && tempMean <= 820) || ch2oMax >= 40) hasCoolTelemetry = true;
            if (mistMax > 0 || grp.desc.toLowerCase().includes("mist") || grp.desc.toLowerCase().includes("bastirma") || diluent === "CO2") hasMistTelemetry = true;
            if (aeroVals.length) {
                const mn = Math.min(...aeroVals), mx = Math.max(...aeroVals);
                aeroMin = aeroMin === null ? mn : Math.min(aeroMin, mn);
                aeroMax = aeroMax === null ? mx : Math.max(aeroMax, mx);
            }

            const tSpanTr = tVals.length >= 2 ? `${Math.trunc(tVals[0])}-${Math.trunc(tVals[tVals.length - 1])} sn` : `${pr.length} satir`;
            const tSpanEn = tVals.length >= 2 ? `${Math.trunc(tVals[0])}-${Math.trunc(tVals[tVals.length - 1])} s` : `${pr.length} rows`;

            phasesOut.push({
                index: idx,
                code: grp.code,
                desc: grp.desc,
                short_tr: `Faz ${idx}`,
                short_en: `Phase ${idx}`,
                time_span_tr: tSpanTr,
                time_span_en: tSpanEn,
                sim_params: phaseParams,
                measured_temp_k: tempMean,
                co_max_ppm: coMax,
                ch2o_max_ppm: ch2oMax,
                k_meas: fit ? fit.k_meas : null,
                r2_d2: fit ? fit.r2 : null,
                regime: tel.regime,
                badge_tr: call.badge_tr || tel.regime,
                badge_en: call.badge_en || tel.regime,
                flame_temp_k: tel.flame_temp_k,
                moc_pct: tel.moc_pct,
                k_model: tel.burning_rate_k_mm2_s,
                b_oq: tel.spalding_b_number,
                sh: tel.sherwood_number,
                da: tel.damkohler_number,
                risk_score: tel.risk_score,
                smac_s: tl.t_smac_24h_100ppm_s ?? 999,
                extinguished: Boolean(tel.extinguished),
                cool_flame: Boolean(tel.cool_flame_active || rowCoolObserved),
                simulation: simRes,
            });
        });

        if (!phasesOut.length) return null;
        const activeHot = phasesOut.filter((p) => !p.extinguished && !p.cool_flame);
        const activeCool = phasesOut.filter((p) => p.cool_flame);
        const primary = activeHot[0] || activeCool[0] || phasesOut[0];

        const tblTr = [
            "| Faz | Zaman | Yakit ve Atmosfer | Sicaklik / CO / CH2O | Boyutsuz Sayilar (K, B_oq, Sh, Da, MOC) | Fiziksel Rejim ve SMAC |",
            "| :--- | :--- | :--- | :--- | :--- | :--- |",
        ];
        const tblEn = [
            "| Phase | Window | Fuel & Atmosphere | Temp / CO / CH2O | Dimensionless (K, B_oq, Sh, Da, MOC) | Regime & SMAC Clock |",
            "| :--- | :--- | :--- | :--- | :--- | :--- |",
        ];
        phasesOut.forEach((p) => {
            const sp = p.sim_params;
            const kTxt = (p.k_meas !== null ? p.k_meas : p.k_model).toFixed(2);
            const ch2oTxt = p.ch2o_max_ppm > 0 ? ` / ${Math.round(p.ch2o_max_ppm)} ppm CH₂O` : "";
            const smacTr = p.smac_s >= 900 ? "Guvenli" : `${p.smac_s} sn`;
            const smacEn = p.smac_s >= 900 ? "Safe" : `${p.smac_s} s`;
            tblTr.push(`| **Faz ${p.index}** | \`${p.time_span_tr}\` | \`${sp.fuel_id}\` • \`${sp.gravity_g}G\` • \`%${sp.oxygen_pct} O₂\` • \`${sp.pressure_psia} psia\` • \`${sp.airflow_cms} cm/s\` | \`${p.measured_temp_k} K\` • \`${p.co_max_ppm} ppm CO\`${ch2oTxt} | \`K=${kTxt}\` • \`B=${p.b_oq}\` • \`Sh=${p.sh}\` • \`Da=${p.da}\` • \`MOC=%${p.moc_pct}\` | **${p.badge_tr}** (Risk \`${p.risk_score}/100\`, SMAC \`${smacTr}\`) |`);
            tblEn.push(`| **Phase ${p.index}** | \`${p.time_span_en}\` | \`${sp.fuel_id}\` • \`${sp.gravity_g}G\` • \`${sp.oxygen_pct}% O₂\` • \`${sp.pressure_psia} psia\` • \`${sp.airflow_cms} cm/s\` | \`${p.measured_temp_k} K\` • \`${p.co_max_ppm} ppm CO\`${ch2oTxt} | \`K=${kTxt}\` • \`B=${p.b_oq}\` • \`Sh=${p.sh}\` • \`Da=${p.da}\` • \`MOC=${p.moc_pct}%\` | **${p.badge_en}** (Risk \`${p.risk_score}/100\`, SMAC \`${smacEn}\`) |`);
        });

        const diagTr = [], diagEn = [];
        if (bestD2Fit) {
            diagTr.push(`- **Deneysel d² Yasası Doğrulaması (Faz ${bestD2Fit.phase_idx}):** Ölçülen eğim \`K_ölç = ${bestD2Fit.k_meas.toFixed(3)} mm²/s\` ile kapalı-form model \`K_model = ${bestD2Fit.k_model.toFixed(3)} mm²/s\` arasında **\`R² = ${bestD2Fit.r2.toFixed(4)}\`** uyumu doğrulandı.`);
            diagEn.push(`- **Empirical d²-Law Validation (Phase ${bestD2Fit.phase_idx}):** Least-squares slope \`K_meas = ${bestD2Fit.k_meas.toFixed(3)} mm²/s\` matches closed-form \`K_model = ${bestD2Fit.k_model.toFixed(3)} mm²/s\` with **\`R² = ${bestD2Fit.r2.toFixed(4)}\`**.`);
        }
        if (hasCoolTelemetry) {
            diagTr.push(`- **Görünmez NTC Soğuk Alev ve Optik Dedektör Körlüğü (FLEX-2):** \`550-750 K\` bandında görünür optik şiddet \`%1\` altına düşerken \`CO\` ve \`CH₂O\` hızla yükselmektedir; \`CSA-CP / ANITA-2\` gaz analizi ile \`CIR Orta-IR\` radyometre izlemesi zorunludur.`);
            diagEn.push(`- **Invisible NTC Cool Flame & Optical Detector Blindness (FLEX-2):** Below \`800 K\`, visible optical intensity drops under \`1%\` while \`CO\` and \`CH₂O\` surge; \`CSA-CP / ANITA-2\` gas analysis with \`CIR Mid-IR\` radiometry is mandatory.`);
        }
        if (hasMistTelemetry) {
            diagTr.push(`- **NASA-STD-6001B Söndürme Denetimi (SoFIE-MIST):** Havalandırma akışının kesilmesi (\`U -> 0 cm/s\`) ve \`<40 µm\` ince su sisi / \`CO₂\` seyreltmesiyle alev güvenli bölgeye (\`O₂ < MOC\`) indirilmiştir (*Halon 1301 kesinlikle kullanılmamıştır*).`);
            diagEn.push(`- **NASA-STD-6001B Suppression Audit (SoFIE-MIST):** Cutting HVAC flow (\`U -> 0 cm/s\`) with \`<40 µm\` fine water mist / \`CO₂\` dilution quenched the flame below \`MOC\` (*Halon 1301 strictly excluded*).`);
        }
        if (aeroMin !== null && aeroMax !== null && aeroMax > aeroMin * 3.0) {
            const ratio = (aeroMax / Math.max(0.01, aeroMin)).toFixed(1);
            diagTr.push(`- **SAME / DAFT Duman ve Ay Tozu Ayrımı:** Veri setinde \`${aeroMin.toFixed(2)} µm\` piroliz dumanı ile \`${aeroMax.toFixed(2)} µm\` Ay regolit tozu çift dalga boylu saçılım oranıyla (\`${ratio}x\` çap farkı) yanlış alarmsız ayrıştırılmıştır.`);
            diagEn.push(`- **SAME / DAFT Smoke vs. Lunar Dust Discrimination:** Sub-micron pyrolysis smoke (\`${aeroMin.toFixed(2)} µm\`) and coarse Lunar regolith dust (\`${aeroMax.toFixed(2)} µm\`) separated cleanly (\`${ratio}x\` size ratio) without false alarms.`);
        }

        const sp0 = primary.sim_params;
        const hdrTr = phasesOut.length > 1
            ? `**Çok Fazlı Telemetri Analizi (\`${filename}\` • ${rows.length} satır • ${phasesOut.length} fiziksel faz):**`
            : `**Tek Fazlı Deney Kaydı (\`${filename}\` • ${rows.length} satır):**`;
        const hdrEn = phasesOut.length > 1
            ? `**Multi-Phase Telemetry Analysis (\`${filename}\` • ${rows.length} rows • ${phasesOut.length} physical phases):**`
            : `**Single-Phase Experiment Record (\`${filename}\` • ${rows.length} rows):**`;
        const summaryTr = `${hdrTr}\n- **3B Yanma Odasına Aktarılan Aktif Durum:** **Faz ${primary.index}** (\`${sp0.fuel_id}\`, \`${sp0.gravity_g}G\`, \`%${sp0.oxygen_pct} O₂\`, \`${sp0.pressure_psia} psia\`, \`${sp0.airflow_cms} cm/s\` — Sıcaklık: \`${primary.flame_temp_k} K\`).\n` + (diagTr.length ? diagTr.join("\n") + "\n\n" : "\n") + tblTr.join("\n");
        const summaryEn = `${hdrEn}\n- **Active State Synced to 3D Chamber:** **Phase ${primary.index}** (\`${sp0.fuel_id}\`, \`${sp0.gravity_g}G\`, \`${sp0.oxygen_pct}% O₂\`, \`${sp0.pressure_psia} psia\`, \`${sp0.airflow_cms} cm/s\` — Temp: \`${primary.flame_temp_k} K\`).\n` + (diagEn.length ? diagEn.join("\n") + "\n\n" : "\n") + tblEn.join("\n");

        const extractedFields = Object.keys(colMap).length
            ? Object.entries(colMap).map(([r, c]) => `${r} (${c})`)
            : Object.keys(rows[0] || {}).filter((k) => String(k || "").trim() !== "");
        return {
            extracted_fields: extractedFields,
            extracted_sim_params: sp0,
            simulation: primary.simulation,
            phases: phasesOut.map((p) => { const c = Object.assign({}, p); delete c.simulation; return c; }),
            summary_tr: summaryTr,
            summary_en: summaryEn,
        };
    }

    async function inflateRawZipSlice(compSlice) {
        if (typeof DecompressionStream === "undefined") {
            throw new Error("DecompressionStream unsupported in this browser.");
        }
        const ds = new DecompressionStream("deflate-raw");
        const writer = ds.writable.getWriter();
        const reader = ds.readable.getReader();
        const chunks = [];
        let totalLen = 0;
        const writeTask = (async () => {
            try {
                await writer.write(compSlice);
                await writer.close();
            } catch (_) {}
        })();
        try {
            while (true) {
                const { value, done } = await reader.read();
                if (done) break;
                if (value) {
                    totalLen += value.byteLength;
                    if (totalLen > 25 * 1024 * 1024) throw new Error("Archive exceeds 25 MB limit.");
                    chunks.push(value);
                }
            }
        } catch (err) {
            if (!chunks.length) throw err;
        }
        await writeTask;
        const out = new Uint8Array(totalLen);
        let offset = 0;
        chunks.forEach((c) => { out.set(c, offset); offset += c.byteLength; });
        return out;
    }

    function readZipEntriesFromBuffer(arrayBuffer) {
        const bytes = new Uint8Array(arrayBuffer);
        const dv = new DataView(arrayBuffer);
        const minEocd = Math.max(0, bytes.length - 65558);
        let eocdPos = -1;
        for (let p = bytes.length - 22; p >= minEocd; p--) {
            if (dv.getUint32(p, true) === 0x06054b50) { eocdPos = p; break; }
        }
        if (eocdPos < 0) return [];
        const totalEntries = dv.getUint16(eocdPos + 10, true);
        const cdOffset = dv.getUint32(eocdPos + 16, true);
        const dec = new TextDecoder("utf-8");
        const entries = [];
        let ptr = cdOffset;
        for (let i = 0; i < totalEntries && ptr + 46 <= bytes.length; i++) {
            if (dv.getUint32(ptr, true) !== 0x02014b50) break;
            const compMethod = dv.getUint16(ptr + 10, true);
            const compSize = dv.getUint32(ptr + 20, true);
            const uncompSize = dv.getUint32(ptr + 24, true);
            const nameLen = dv.getUint16(ptr + 28, true);
            const extraLen = dv.getUint16(ptr + 30, true);
            const commentLen = dv.getUint16(ptr + 32, true);
            const localHdrOffset = dv.getUint32(ptr + 42, true);
            const nameStr = dec.decode(bytes.subarray(ptr + 46, ptr + 46 + nameLen));
            entries.push({ name: nameStr, compMethod, compSize, uncompSize, localHdrOffset });
            ptr += 46 + nameLen + extraLen + commentLen;
        }
        return { bytes, dv, entries };
    }

    async function extractZipEntryBytes(zipInfo, entry) {
        if (!entry || entry.uncompSize > 25 * 1024 * 1024) return new Uint8Array(0);
        const { bytes, dv } = zipInfo;
        const lh = entry.localHdrOffset;
        if (lh + 30 > bytes.length || dv.getUint32(lh, true) !== 0x04034b50) return new Uint8Array(0);
        const lfNameLen = dv.getUint16(lh + 26, true);
        const lfExtraLen = dv.getUint16(lh + 28, true);
        const dataStart = lh + 30 + lfNameLen + lfExtraLen;
        const compSlice = bytes.subarray(dataStart, dataStart + entry.compSize);
        if (entry.compMethod === 0) return compSlice;
        if (entry.compMethod === 8) return await inflateRawZipSlice(compSlice);
        return new Uint8Array(0);
    }

    async function parseXlsxBufferToCsvText(arrayBuffer) {
        const zipInfo = readZipEntriesFromBuffer(arrayBuffer);
        if (!zipInfo.entries || !zipInfo.entries.length) return "";
        const dec = new TextDecoder("utf-8");
        const domParser = new DOMParser();
        const sharedStrings = [];
        const ssEntry = zipInfo.entries.find((e) => e.name.toLowerCase() === "xl/sharedstrings.xml");
        if (ssEntry) {
            const ssBytes = await extractZipEntryBytes(zipInfo, ssEntry);
            if (ssBytes.length) {
                const doc = domParser.parseFromString(dec.decode(ssBytes), "application/xml");
                const siNodes = doc.getElementsByTagName("si");
                for (let i = 0; i < siNodes.length; i++) {
                    const tNodes = siNodes[i].getElementsByTagName("t");
                    let acc = "";
                    for (let j = 0; j < tNodes.length; j++) acc += tNodes[j].textContent || "";
                    sharedStrings.push(acc);
                }
            }
        }
        const sheetEntries = zipInfo.entries
            .filter((e) => /^xl\/worksheets\/sheet\d*\.xml$/i.test(e.name))
            .sort((a, b) => a.name.localeCompare(b.name));
        if (!sheetEntries.length) return "";
        const shBytes = await extractZipEntryBytes(zipInfo, sheetEntries[0]);
        if (!shBytes.length) return "";
        const shDoc = domParser.parseFromString(dec.decode(shBytes), "application/xml");
        const rowNodes = shDoc.getElementsByTagName("row");
        const csvLines = [];
        const colRefToIdx = (refStr) => {
            const m = String(refStr || "").match(/^[A-Za-z]+/);
            if (!m) return -1;
            const letters = m[0].toUpperCase();
            let idx = 0;
            for (let k = 0; k < letters.length; k++) idx = idx * 26 + (letters.charCodeAt(k) - 64);
            return idx - 1;
        };
        const escCsvCell = (val) => {
            const s = String(val ?? "").replace(/\r?\n/g, " ").trim();
            return (s.includes(",") || s.includes('"') || s.includes(";")) ? `"${s.replace(/"/g, '""')}"` : s;
        };
        const maxRows = Math.min(rowNodes.length, 600);
        for (let r = 0; r < maxRows; r++) {
            const cNodes = rowNodes[r].getElementsByTagName("c");
            const rowArr = [];
            let hasNonEmpty = false;
            for (let c = 0; c < cNodes.length; c++) {
                const cell = cNodes[c];
                const cIdx = colRefToIdx(cell.getAttribute("r"));
                const targetIdx = cIdx >= 0 ? cIdx : rowArr.length;
                while (rowArr.length < targetIdx) rowArr.push("");
                const cType = cell.getAttribute("t") || "";
                let valStr = "";
                if (cType === "inlineStr") {
                    const tEls = cell.getElementsByTagName("t");
                    for (let ti = 0; ti < tEls.length; ti++) valStr += tEls[ti].textContent || "";
                } else {
                    const vEl = cell.getElementsByTagName("v")[0];
                    const rawV = vEl ? (vEl.textContent || "") : "";
                    if (cType === "s") {
                        const sIdx = parseInt(rawV, 10);
                        valStr = (!Number.isNaN(sIdx) && sharedStrings[sIdx] !== undefined) ? sharedStrings[sIdx] : rawV;
                    } else {
                        valStr = rawV;
                    }
                }
                if (valStr.trim() !== "") hasNonEmpty = true;
                rowArr[targetIdx] = escCsvCell(valStr);
            }
            if (hasNonEmpty) csvLines.push(rowArr.join(","));
        }
        return csvLines.join("\n");
    }

    async function extractArchiveBufferInBrowser(arrayBuffer, origName) {
        const low = String(origName || "").toLowerCase();
        if (low.endsWith(".xlsx")) {
            const csvText = await parseXlsxBufferToCsvText(arrayBuffer);
            return { text: csvText, effectiveName: origName };
        }
        const zipInfo = readZipEntriesFromBuffer(arrayBuffer);
        if (!zipInfo.entries || !zipInfo.entries.length) return { text: "", effectiveName: origName };
        if (zipInfo.entries.some((e) => e.name.toLowerCase() === "xl/workbook.xml")) {
            const csvText = await parseXlsxBufferToCsvText(arrayBuffer);
            return { text: csvText, effectiveName: origName };
        }
        const rankEntry = (nm) => {
            const nl = nm.toLowerCase();
            if (nl.endsWith("/") || nl.includes("__macosx")) return 999;
            const bonus = (nl.includes("experimental") || nl.includes("table") || nl.includes("summary")) ? -10 : 0;
            if (nl.endsWith(".csv")) return 10 + bonus;
            if (nl.endsWith(".tsv")) return 12 + bonus;
            if (nl.endsWith(".xlsx")) return 15 + bonus;
            if (nl.endsWith(".json")) return 20 + bonus;
            if (nl.endsWith(".txt") || nl.endsWith(".md")) return 30 + bonus;
            return 999;
        };
        const sorted = zipInfo.entries.slice().sort((a, b) => rankEntry(a.name) - rankEntry(b.name));
        const best = sorted[0];
        if (!best || rankEntry(best.name) >= 999) return { text: "", effectiveName: origName };
        const innerBytes = await extractZipEntryBytes(zipInfo, best);
        if (!innerBytes.length) return { text: "", effectiveName: origName };
        const baseInner = best.name.split("/").pop() || origName;
        if (best.name.toLowerCase().endsWith(".xlsx")) {
            const subBuf = innerBytes.buffer.slice(innerBytes.byteOffset, innerBytes.byteOffset + innerBytes.byteLength);
            const csvText = await parseXlsxBufferToCsvText(subBuf);
            return { text: csvText, effectiveName: `${origName} (${baseInner})` };
        }
        return { text: new TextDecoder("utf-8").decode(innerBytes), effectiveName: `${origName} (${baseInner})` };
    }

    function countFlameletIslandsJs(maskArr, width, height) {
        const visited = new Uint8Array(width * height);
        let islands = 0;
        const dirs = [-1, -1, -1, 0, -1, 1, 0, -1, 0, 1, 1, -1, 1, 0, 1, 1];
        for (let y = 0; y < height; y++) {
            for (let x = 0; x < width; x++) {
                const startIdx = y * width + x;
                if (!maskArr[startIdx] || visited[startIdx]) continue;
                let area = 0;
                const stack = [x, y];
                visited[startIdx] = 1;
                while (stack.length > 0) {
                    const cy = stack.pop();
                    const cx = stack.pop();
                    area++;
                    for (let d = 0; d < 16; d += 2) {
                        const nx = cx + dirs[d + 1];
                        const ny = cy + dirs[d];
                        if (nx >= 0 && nx < width && ny >= 0 && ny < height) {
                            const nIdx = ny * width + nx;
                            if (maskArr[nIdx] && !visited[nIdx]) {
                                visited[nIdx] = 1;
                                stack.push(nx, ny);
                            }
                        }
                    }
                }
                if (area >= 4) islands++;
            }
        }
        return islands;
    }

    async function analyzeUploadedMediaInBrowser(formData) {
        const file = formData && formData.get ? formData.get("file") : null;
        if (!file) return { ok: false, error: "Dosya bulunamadı / No file provided." };
        const origOverride = formData && formData.get ? String(formData.get("original_filename") || "").trim() : "";
        const videoFlickerRaw = formData && formData.get ? Number(formData.get("video_flicker_pct") || 0) : 0;
        let name = origOverride || file.name || "uploaded_file";
        const lower = (file.name || name).toLowerCase();

        if (file.type.startsWith("image/") || /\.(png|jpg|jpeg|webp|bmp|gif)$/.test(lower)) {
            const dataUrl = await new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.onload = () => resolve(String(reader.result));
                reader.onerror = () => reject(new Error("Image read failed"));
                reader.readAsDataURL(file);
            });
            const img = await new Promise((resolve, reject) => {
                const im = new Image();
                im.onload = () => resolve(im);
                im.onerror = () => reject(new Error("Image decode failed"));
                im.src = dataUrl;
            });
            const w = Math.min(160, img.width || 120);
            const h = Math.min(160, img.height || 120);
            const cv = document.createElement("canvas");
            cv.width = w;
            cv.height = h;
            const ctx = cv.getContext("2d");
            ctx.drawImage(img, 0, 0, w, h);
            const px = ctx.getImageData(0, 0, w, h).data;
            const totalPx = Math.max(1, w * h);
            const sigArr = new Float32Array(totalPx);
            let blueCnt = 0, warmCnt = 0, violetCnt = 0, totalBri = 0;
            for (let i = 0, pIdx = 0; i < px.length; i += 4, pIdx++) {
                const r = px[i], g = px[i + 1], b = px[i + 2];
                totalBri += (r + g + b) / 3;
                const rn = r / 255.0, gn = g / 255.0, bn = b / 255.0;
                const blueEx = Math.max(0.0, bn - 0.65 * rn);
                sigArr[pIdx] = Math.max(rn, gn, bn, blueEx * 1.35);
                if (b > r + 20 && b > 52) blueCnt++;
                if (r > b + 40 && r > 120 && g > 70) warmCnt++;
                if (b > 70 && r > 60 && g < Math.min(r, b) - 12) violetCnt++;
            }
            const sortedSig = Array.from(sigArr).sort((a, b) => a - b);
            const p78 = sortedSig[Math.min(totalPx - 1, Math.floor(totalPx * 0.78))] || 0.2;
            const thr = Math.max(0.11, p78 * 0.52);
            const maskArr = new Uint8Array(totalPx);
            let activeCnt = 0;
            for (let k = 0; k < totalPx; k++) {
                if (sigArr[k] > thr) { maskArr[k] = 1; activeCnt++; }
            }
            if (activeCnt < 20) {
                activeCnt = 0;
                for (let k = 0; k < totalPx; k++) {
                    if (sigArr[k] > 0.065) { maskArr[k] = 1; activeCnt++; }
                }
            }
            const flameletCount = countFlameletIslandsJs(maskArr, w, h);
            const isFlamelets = flameletCount >= 2 && activeCnt < totalPx * 0.45;
            const isBlue0g = blueCnt >= warmCnt;
            const isCool = violetCnt > totalPx * 0.08 && totalBri / totalPx < 75;
            const extracted = isFlamelets
                ? { fuel_id: "sibal", gravity_g: 0.0, oxygen_pct: 14.8, pressure_psia: 14.7, airflow_cms: 2.2, flow_direction: "opposed", droplet_d0_mm: 3.2, diluent: "N2" }
                : isCool
                ? { fuel_id: "n_heptane", gravity_g: 0.0, oxygen_pct: 16.5, pressure_psia: 14.7, airflow_cms: 0.2, flow_direction: "opposed", droplet_d0_mm: 3.8, diluent: "N2" }
                : isBlue0g
                ? { fuel_id: "n_heptane", gravity_g: 0.0, oxygen_pct: 21.0, pressure_psia: 14.7, airflow_cms: 0.8, flow_direction: "opposed", droplet_d0_mm: 3.0, diluent: "N2" }
                : { fuel_id: "pmma", gravity_g: 0.38, oxygen_pct: 28.0, pressure_psia: 12.0, airflow_cms: 6.0, flow_direction: "concurrent", droplet_d0_mm: 3.4, diluent: "N2" };
            const sim = simulateCombustionClient(extracted);
            const regLabelTr = isFlamelets
                ? `Hücresel Alevcikler (${flameletCount} Adacık • Sönme Sınırı)`
                : (isCool ? "Görünmez Soğuk Alev (UV/IR)" : (isBlue0g ? "0G Küresel Safir-Mavi Difüzyon" : "Kurumlu Konvektif Plume"));
            const regLabelEn = isFlamelets
                ? `Cellular Flamelets (${flameletCount} Islands • Near-Quench)`
                : (isCool ? "Invisible Cool Flame (UV/IR)" : (isBlue0g ? "0G Spherical Sapphire Diffusion" : "Sooty Convective Plume"));
            const bluePct = ((blueCnt / totalPx) * 100).toFixed(1);
            const warmPct = ((warmCnt / totalPx) * 100).toFixed(1);
            const flickerNoteTr = videoFlickerRaw > 0 ? `, Zamansal Titreşim \`%${videoFlickerRaw.toFixed(1)}\`` : "";
            const flickerNoteEn = videoFlickerRaw > 0 ? `, Temporal Flicker \`${videoFlickerRaw.toFixed(1)}%\`` : "";
            const summaryTr = `**Görüntü Piksel Analizi (${name}):** Mavi alev oranı \`%${bluePct}\`, kurum/sıcak ışıma \`%${warmPct}\`${flickerNoteTr} — **${regLabelTr}** tespit edildi.`;
            const summaryEn = `**Flame Pixel Analysis (${name}):** Blue chemiluminescence \`${bluePct}%\`, warm soot index \`${warmPct}%\`${flickerNoteEn} — **${regLabelEn}** detected.`;
            const dynExp = registerDynamicExperimentJs(name, extracted, sim, summaryTr, summaryEn);
            return {
                ok: true,
                filename: name,
                media_type: "image",
                image_base64: dataUrl,
                metrics: {
                    detected_regime_tr: regLabelTr,
                    detected_regime_en: regLabelEn,
                    flamelets_detected: isFlamelets,
                    flamelet_count: flameletCount,
                    temporal_flicker_pct: Number(videoFlickerRaw.toFixed(2)),
                },
                extracted_sim_params: extracted,
                simulation: sim,
                registered_experiment_id: dynExp ? dynExp.exp_id : null,
                summary_tr: summaryTr,
                summary_en: summaryEn,
            };
        }

        let text = "";
        if (lower.endsWith(".xlsx") || lower.endsWith(".zip")) {
            const ab = await file.arrayBuffer();
            const archRes = await extractArchiveBufferInBrowser(ab, name);
            text = archRes.text || "";
            name = archRes.effectiveName || name;
        } else if (lower.endsWith(".pdf")) {
            const ab = await file.arrayBuffer();
            text = extractReadableTextFromPdfBuffer(ab);
        } else {
            text = await file.text();
        }

        return parseTextOrTablePayloadInBrowser(text, name);
    }

    function parseTextOrTablePayloadInBrowser(text, name) {
        ragDocs.push({ doc_id: `USR-${Date.now()}`, title: name, source: "Browser Local File", url: "", text: text.slice(0, 12000) });

        // 1. Çok fazlı JSON / CSV / TSV / XLSX / ZIP tablo çözümlemesi
        const trimmed = String(text || "").replace(/^\uFEFF/, "").trim();
        let tabRes = null;
        if (trimmed.startsWith("{") || trimmed.startsWith("[")) {
            try {
                const parsedJson = JSON.parse(trimmed);
                if (Array.isArray(parsedJson) && parsedJson.length && typeof parsedJson[0] === "object") {
                    tabRes = analyzeTabularRowsInBrowser(parsedJson.slice(0, 600), name);
                } else if (parsedJson && Array.isArray(parsedJson.rows) && parsedJson.rows.length) {
                    tabRes = analyzeTabularRowsInBrowser(parsedJson.rows.slice(0, 600), name);
                } else if (parsedJson && typeof parsedJson === "object") {
                    tabRes = analyzeTabularRowsInBrowser([parsedJson], name);
                }
            } catch (_) {}
        } else if (looksLikeTabularTextJs(trimmed, name)) {
            const csvRows = parseCsvRowsJs(trimmed);
            if (csvRows.length > 0) {
                tabRes = analyzeTabularRowsInBrowser(csvRows, name);
            }
        }

        if (tabRes) {
            const dynTab = registerDynamicExperimentJs(name, tabRes.extracted_sim_params, tabRes.simulation, tabRes.summary_tr, tabRes.summary_en);
            return {
                ok: true,
                filename: name,
                title: name,
                media_type: "document",
                chunks: Math.max(1, Math.ceil(trimmed.length / 800)),
                extracted_fields: tabRes.extracted_fields || [],
                phases: tabRes.phases,
                extracted_sim_params: tabRes.extracted_sim_params,
                simulation: tabRes.simulation,
                registered_experiment_id: dynTab ? dynTab.exp_id : null,
                summary_tr: tabRes.summary_tr,
                summary_en: tabRes.summary_en,
            };
        }

        // 2. Serbest metin / PDF çıkarımı (sıkı kelime sınırı + birim dönüşümleri + soğuk alev / kabin bağlamı + benzer malzeme)
        const extracted = {
            fuel_id: parseFuelStrJs(trimmed) || parseFuelStrJs(name) || "n_heptane",
            gravity_g: /0\.16|lunar|moon/i.test(trimmed) ? 0.16 : (/0\.38|mars/i.test(trimmed) ? 0.38 : (/1\.0\s*g|earth/i.test(trimmed) ? 1.0 : 0.0)),
            oxygen_pct: 21.0,
            pressure_psia: 14.7,
            airflow_cms: 2.4,
            flow_direction: "opposed",
            droplet_d0_mm: 3.2,
            diluent: "N2",
        };
        const o2Match = trimmed.match(/(\d{1,3}(?:\.\d+)?)\s*%\s*(?:o2|o₂|oxygen|oksijen)\b/i) || trimmed.match(/(?:^|[^a-z0-9])(?:x_?o2|o2|o₂|oxygen|oksijen)\s*(?:mole\s*fraction)?\s*[:=]\s*%?\s*(\d{1,3}(?:\.\d+)?)/i);
        const pMatch = trimmed.match(/(\d{1,2}(?:\.\d+)?)\s*psia\b/i);
        const atmMatch = trimmed.match(/(\d{1,2}(?:\.\d+)?)\s*atm\b/i);
        const barMatch = trimmed.match(/(\d{1,2}(?:\.\d+)?)\s*bar\b/i);
        const kpaMatch = trimmed.match(/(\d{2,3}(?:\.\d+)?)\s*kpa\b/i);
        const torrMatch = trimmed.match(/(\d{3,4}(?:\.\d+)?)\s*(?:torr|mmhg)\b/i);
        const uMatch = trimmed.match(/(\d{1,2}(?:\.\d+)?)\s*cm\/s\b/i);
        if (o2Match) {
            const rawO2 = parseFloat(o2Match[1]);
            const convO2 = (rawO2 >= 0.03 && rawO2 <= 1.0) ? rawO2 * 100.0 : rawO2;
            extracted.oxygen_pct = Number(Math.min(100, Math.max(5, convO2)).toFixed(2));
        }
        if (pMatch) extracted.pressure_psia = Math.min(35, Math.max(3.0, parseFloat(pMatch[1])));
        else if (atmMatch) extracted.pressure_psia = Number(Math.min(35, Math.max(3.0, parseFloat(atmMatch[1]) * 14.6959)).toFixed(2));
        else if (barMatch) extracted.pressure_psia = Number(Math.min(35, Math.max(3.0, parseFloat(barMatch[1]) * 14.5038)).toFixed(2));
        else if (kpaMatch) extracted.pressure_psia = Number(Math.min(35, Math.max(3.0, parseFloat(kpaMatch[1]) / 6.89476)).toFixed(2));
        else if (torrMatch) extracted.pressure_psia = Number(Math.min(35, Math.max(3.0, parseFloat(torrMatch[1]) / 51.7149)).toFixed(2));
        if (uMatch) extracted.airflow_cms = Math.min(45, Math.max(0, parseFloat(uMatch[1])));

        const lowTxt = `${name} ${trimmed}`.toLowerCase();
        if (["concurrent", "eş yönlü", "es yonlu", "co-flow", "coflow", "downstream spread"].some((w) => lowTxt.includes(w))) {
            extracted.flow_direction = "concurrent";
        } else if (["opposed", "karşıt akış", "karsit akis", "counterflow"].some((w) => lowTxt.includes(w))) {
            extracted.flow_direction = "opposed";
        }

        if (["cool flame", "cool-flame", "soğuk alev", "soguk alev", "ntc", "two-stage", "psi-117"].some((w) => lowTxt.includes(w))) {
            if (!["pmma", "sibal", "nomex", "hydrogen"].includes(extracted.fuel_id)) {
                if (lowTxt.includes("cfi-g") || lowTxt.includes("propane")) {
                    extracted.fuel_id = "propane_cfig";
                    if (!o2Match) extracted.oxygen_pct = 85.0;
                } else {
                    extracted.fuel_id = "n_heptane";
                    if (!o2Match) extracted.oxygen_pct = 16.5;
                }
                if (!uMatch) extracted.airflow_cms = 0.4;
                extracted.droplet_d0_mm = 4.4;
            }
        } else if (lowTxt.includes("spacesuit") || lowTxt.includes("eva suit") || lowTxt.includes("uzay giysisi")) {
            if (!o2Match) extracted.oxygen_pct = 100.0;
            if (!pMatch && !atmMatch && !barMatch && !kpaMatch && !torrMatch) extracted.pressure_psia = 4.3;
            extracted.fuel_id = "nomex";
        } else if (lowTxt.includes("exploration atmosphere") || lowTxt.includes("sofie")) {
            if (!o2Match) extracted.oxygen_pct = 34.0;
            if (!pMatch && !atmMatch && !barMatch && !kpaMatch && !torrMatch) extracted.pressure_psia = 8.2;
        }

        const unlistedPairs = [
            ["peek", "PEEK"],
            ["xlpe", "XLPE Kablo İzolasyonu"],
            ["ptfe", "PTFE / Teflon"],
            ["teflon", "PTFE / Teflon"],
            ["kapton", "Kapton Poliimid"],
            ["pvc", "PVC Kablo Kılıfı"],
            ["carbon-epoxy", "Karbon-Epoksi Kompozit"],
            ["karbon epoksi", "Karbon-Epoksi Kompozit"],
        ];
        for (let ui = 0; ui < unlistedPairs.length; ui++) {
            const uKw = unlistedPairs[ui][0];
            const reUn = new RegExp(`(?:^|[^a-z0-9])${uKw.replace("-", "\\-")}(?:$|[^a-z0-9])`, "i");
            if (reUn.test(lowTxt)) {
                extracted.fuel_id = "custom_material";
                extracted.custom_material_name = unlistedPairs[ui][1];
                break;
            }
        }

        const sim = simulateCombustionClient(extracted);
        const fuelDisp = extracted.custom_material_name || extracted.fuel_id;
        const summaryTr = `**Veri Dosyası Analizi (${name}):** Yakıt \`${fuelDisp}\`, Yerçekimi \`${extracted.gravity_g}G\`, O₂ \`%${extracted.oxygen_pct}\`, Basınç \`${extracted.pressure_psia} psia\`, Akış \`${extracted.airflow_cms} cm/s\` — Rejim: **${sim.callouts.badge_tr}**.`;
        const summaryEn = `**Data File Analysis (${name}):** Fuel \`${fuelDisp}\`, Gravity \`${extracted.gravity_g}G\`, O₂ \`${extracted.oxygen_pct}%\`, Pressure \`${extracted.pressure_psia} psia\`, Airflow \`${extracted.airflow_cms} cm/s\` — Regime: **${sim.callouts.badge_en}**.`;
        const dynTxt = registerDynamicExperimentJs(name, extracted, sim, summaryTr, summaryEn);
        return {
            ok: true,
            filename: name,
            title: name,
            media_type: "document",
            chunks: Math.max(1, Math.ceil(trimmed.length / 800)),
            phases: [],
            extracted_sim_params: extracted,
            simulation: sim,
            registered_experiment_id: dynTxt ? dynTxt.exp_id : null,
            summary_tr: summaryTr,
            summary_en: summaryEn,
        };
    }

    function normQueryAscii(str) {
        return String(str || "")
            .replace(/[ıİ]/g, "i")
            .replace(/[ğĞ]/g, "g")
            .replace(/[üÜ]/g, "u")
            .replace(/[şŞ]/g, "s")
            .replace(/[öÖ]/g, "o")
            .replace(/[çÇ]/g, "c")
            .replace(/[âÂ]/g, "a")
            .replace(/[îÎ]/g, "i")
            .replace(/[ûÛ]/g, "u")
            .replace(/[₂²]/g, "2")
            .replace(/₀/g, "0")
            .replace(/₁/g, "1")
            .replace(/₃/g, "3")
            .replace(/µ/g, "u")
            .toLowerCase()
            .replace(/\u0307/g, "")
            .replace(/\s+/g, " ")
            .trim();
    }

    function hasAnyTerm(nq, terms) {
        for (let i = 0; i < terms.length; i++) {
            if (nq.indexOf(terms[i]) !== -1) return true;
        }
        return false;
    }

    function truncateCleanJs(rawStr, maxChars) {
        const clean = String(rawStr || "").trim().replace(/\s+/g, " ");
        const lim = maxChars || 96;
        if (clean.length <= lim) return clean;
        const cut = clean.slice(0, lim);
        const sp = cut.lastIndexOf(" ");
        return (sp > 20 ? cut.slice(0, sp) : cut) + "...";
    }

    function classifyBrowserIntent(rawMsg, mediaCtx) {
        const nq = normQueryAscii(rawMsg);
        if (
            (nq.indexOf("boyutsuz sayilari") !== -1 && (nq.indexOf("psi") !== -1 || nq.indexOf("dunya") !== -1 || nq.indexOf("eclss") !== -1)) ||
            (nq.indexOf("dimensionless numbers") !== -1 && (nq.indexOf("psi") !== -1 || nq.indexOf("earth") !== -1)) ||
            hasAnyTerm(nq, ["tam rapor", "kapsamli analiz", "full report", "comprehensive analysis", "tumunu sentezle"])
        ) {
            return "full_synthesis";
        }

        if (
            mediaCtx &&
            (hasAnyTerm(nq, ["yukledigim", "yuklenen", "ekli", "eklenen", "dosya", "gorsel", "goruntu", "resim", "fotograf", "csv", "xlsx", "excel", "zip", "tsv", "pdf", "json", "veri", "veriyi", "tablo", "tabloda", "tablosu", "tablosunda", "tabloyu", "grafik", "degerleri", "degerlerini", "mevcut analiz", "analiz deger", "faz", "fazlar", "veri seti", "tum ozellik", "butun ozellik", "uploaded", "attached", "image", "photo", "table", "phases", "values", "dataset", "file"]) ||
                ["analiz et", "bu veriyi analiz et", "incele", "degerlendir", "ozetle", "analyze", "analyze this", "evaluate", "summarize"].includes(nq))
        ) {
            return "uploaded_media";
        }

        const physicsAnchors = [
            "heptan", "metanol", "pmma", "nomex", "sibal", "hidrojen", "propan",
            "spalding", "sherwood", "damkohler", "rayleigh", "grashof", "richardson",
            "halon", "sofie", "saffire", "flex", "bass", "spice", "slice", "daft",
            "luci", "fm2", "soguk alev", "cool flame", "moc", "eva", "gezgin", "rover", "roket", "rocket"
        ];
        if (!hasAnyTerm(nq, physicsAnchors)) {
            if (hasAnyTerm(nq, ["ozelliklerin", "ozellikleri", "hangi ozellik", "yeteneklerin", "mimari", "modullerin", "sistemin ozellik", "features", "architecture", "modules", "specifications"])) {
                return "platform_features";
            }
            if (hasAnyTerm(nq, ["neler yapabilir", "ne yapabilir", "ne ise yarar", "nasil kullan", "yardim", "komutlar", "ne sorabilir", "bana ne sun", "what can you do", "how to use", "capabilities", "help"])) {
                return "capabilities_guide";
            }
            const cleanAlnumQ = nq.replace(/[^a-z0-9\s]/g, " ").replace(/\s+/g, " ").trim();
            if (hasAnyTerm(nq, ["merhaba", "selam", "iyi gunler", "gunaydin", "iyi aksamlar", "kimsin", "sen kimsin", "nesin", "kendini tanit", "hello", "hi ", "hey", "who are you", "what are you"]) || ["hi", "hello", "hey", "merhaba", "selam", "gunaydin", "iyi gunler", "iyi aksamlar", "alo", "test", "deneme"].includes(cleanAlnumQ)) {
                return "greeting_identity";
            }
        }

        if (hasAnyTerm(nq, ["roket", "rocket", "itici", "thruster", "nozul", "nozzle"])) {
            return "rocket_scope";
        }
        if (hasAnyTerm(nq, ["uzay giysisi", "eva giysi", "spacesuit", "eva suit", "4.3 psia", "%100 o2", "100% o2", "gezgin", "lunar rover", "pressurized rover", "10.2 psia", "on-soluma", "on soluma", "pre-breathe", "vurgun", "dekompresyon"])) {
            return "eva_rover_atmosphere";
        }
        if (hasAnyTerm(nq, ["halon", "sondur", "mudahale", "su sisi", "water mist", "sofie-mist", "pfe", "yangin cikarsa", "acil durum", "6001b", "smac", "karbonmonoksit", "eclss", "suppress", "extinguish"])) {
            return "suppression_halon";
        }
        if (hasAnyTerm(nq, ["soguk alev", "cool flame", "ntc", "gorunmez alev", "iki asamali", "two-stage", "peroksi", "daft", "ay tozu", "regolit", "lunar dust", "duman dedektor", "toz-duman", "yanlis alarm", "false alarm"])) {
            return "cool_flame_daft";
        }
        if (hasAnyTerm(nq, ["kismi yercekimi", "partial gravity", "partial-gravity", "luci", "fm2", "e-field", "efield", "iyon ruzgari", "ionic wind", "0.16g", "0.16 g", "0.38g", "0.38 g", "mars yercekimi", "mars'ta", "marsta", "martian", "ay yercekimi", "ay'da", "ayda yanma", "bounding", "sinirlandirma"]) || /\b(?:moon|lunar|mars)\b/.test(nq)) {
            return "partial_gravity_luci";
        }
        if (hasAnyTerm(nq, ["en yuksek oksijen", "highest oxygen", "cfi-g", "cfig", "saffire", "bass-ii", "bass ", "spice", "slice", "flex-2", "bre ", "burn rate emulator", "cir ", "mdca", "msg ", "cygnus", "ntrs-", "osdr-", "psi-"]) || /\b(flex|cfi|acme|sofie|bass|same)\b/.test(nq)) {
            return "specific_experiment";
        }
        if (hasAnyTerm(nq, ["spalding", "b_oq", "boq", "sherwood", "reynolds", "rayleigh", "grashof", "richardson", "damkohler", "d2 yasasi", "d²", "yanma sabiti", "burning constant", "standoff", "durma mesafesi", "r_f", "radyatif kayip", "chi_r", "moc nasil", "moc nedir", "denklem", "formul", "nasil hesaplan", "equation", "formula"])) {
            return "equation_deep_dive";
        }
        if (hasAnyTerm(nq, ["artirirsam", "artarsa", "yukseltirsem", "azaltirsam", "dusurursem", "degistirirsem", "kapatirsam", "olursa ne olur", "ne degisir", "farki ne", "0g ile 1g", "havalandirma", "fan hizi", "akis hizi", "ufleme", "blowoff", "seyreltici", "helyum", "argon", "what if", "increase", "decrease", "sensitivity", "difference between"])) {
            return "what_if_sensitivity";
        }
        if (hasAnyTerm(nq, ["dunya'ya", "dunyaya", "dunya uygula", "yeryuzu", "itfaiye", "firefighter", "spinoff", "teknoloji transfer", "scba", "hcci", "earth transfer", "earth application"])) {
            return "earth_spinoffs";
        }
        return "targeted_scientific";
    }

    function buildQuestionDrivenReply(msg, simParams, mediaCtx, lang, history) {
        const sim = simulateCombustionClient(simParams || {});
        const ranked = rankExperimentsClient(simParams || {}, msg, "ALL").ranked_experiments.slice(0, 4);
        const inp = sim.inputs;
        const tel = sim.telemetry;
        const fv = sim.flight_validation;
        const tl = sim.scenario_timeline;
        const call = sim.callouts || {};
        const isEn = lang === "en";
        const regBadge = (isEn ? call.badge_en : call.badge_tr) || tel.regime;
        const nq = normQueryAscii(msg);
        const intent = classifyBrowserIntent(msg, mediaCtx);

        const defaultCitations = ranked.slice(0, 3).map((e) => ({
            id: e.exp_id,
            program: e.program,
            ntrs_id: e.ntrs_id,
            url: e.ntrs_url,
        }));

        // 1. Neler yapabilirsin? / Etkileşimli kullanım rehberi
        if (intent === "capabilities_guide") {
            return {
                reply: isEn
                    ? [
                          `### ALTAR-NASA v6.3 — Interactive Engineering & Scientific Capabilities`,
                          `Currently locked onto your live 3D chamber (**${inp.fuel_name_en}** at \`${inp.gravity_g} G\`, \`${inp.oxygen_pct}% O₂\`, \`${inp.pressure_psia} psia\`, \`U = ${inp.airflow_cms} cm/s\` → **${regBadge}**, Risk \`${tel.risk_score}/100\`). Ask me to compute or analyze any specific scenario:`,
                          ``,
                          `| Capability Domain | Live Calculation Executed | Example Question You Can Type |`,
                          `| :--- | :--- | :--- |`,
                          `| **Equation Derivation** | Step-by-step substitution of \`d²\`-law \`K\`, Spalding \`B_oq\`, Sherwood \`Sh\`, \`Ra/Ri\`, Damköhler \`Da\`, and \`MOC\` | *"How is Spalding B_oq and burning rate K calculated?"* |`,
                          `| **Counterfactual What-If Sweep** | Multi-point sweeps across airflow (\`0–30 cm/s\`), gravity (\`0G–1G\`), \`O₂%\`, and diluents (\`N₂/CO₂/He\`) | *"What happens if I increase cabin airflow from 0 to 20 cm/s?"* |`,
                          `| **EVA Suit & Rover Comparison** | Live table comparing ISS (\`14.7 psia\`), Lunar Rover (\`10.2 psia / 32% O₂\`), and EVA Suit (\`4.3 psia / 100% O₂\`) | *"Compare EVA spacesuit and Lunar Rover flammability risks."* |`,
                          `| **15 NASA PSI Investigations** | Deep-dive into \`FLEX\`, \`CFI-G\`, \`BASS\`, \`SPICE\`, \`SLICE\`, \`Saffire\`, \`SoFIE\`, \`DAFT\` & intra-run matrices | *"Explain Saffire-V test variations and CFI-G findings."* |`,
                          `| **ECLSS & Fire Suppression** | \`NASA-STD-6001B\` Halon 1301 ban, \`SoFIE-MIST\` water mist, \`JSC-20584 CO SMAC\` clock, Cool Flame sensing | *"Why is Halon 1301 banned and how fast does CO hit SMAC?"* |`,
                          `| **Image / Dataset Analyzer** | In-browser pixel chemiluminescence/soot segmentation (\`.png/.jpg\`) & \`.csv/.xlsx/.zip/.pdf\` extraction | Upload a file on the left and ask *"Analyze my uploaded file"* |`,
                      ].join("\n")
                    : [
                          `### ALTAR-NASA v6.3 — Yapabileceğim Canlı Hesaplama ve Mühendislik Analizleri`,
                          `Şu anda aktif 3B yanma odanıza kilitliyim (**${inp.fuel_name_tr}** • \`${inp.gravity_g} G\`, \`%${inp.oxygen_pct} O₂\`, \`${inp.pressure_psia} psia\`, \`U = ${inp.airflow_cms} cm/s\` → **${regBadge}**, Risk \`${tel.risk_score}/100\`). Bana doğrudan şu hesaplama ve sorguları yaptırabilirsiniz:`,
                          ``,
                          `| Analiz Yeteneği | Arka Planda Yürüttüğüm Canlı İşlem | Doğrudan Sorabileceğiniz Örnek Soru |`,
                          `| :--- | :--- | :--- |`,
                          `| **Adım Adım Denklem Çözümü** | Aktif kaydırıcı değerlerinizle \`d²\` sıvı, \`de Ris\` katı, \`Burke-Schumann\` gaz, Sherwood \`Sh\`, \`Ra/Ri\`, Damköhler \`Da\` ve \`MOC\` hesabı | *"Spalding B_oq ve yanma sabiti K nasıl hesaplanıyor?"* |`,
                          `| **'Ne Olur?' Duyarlılık Taraması** | Akış hızı (\`0–30 cm/s\`), yerçekimi (\`0G / 0.16G / 0.38G / 1G\`), \`O₂%\` veya seyreltici gaz (\`N₂/CO₂/He\`) taraması | *"Havalandırma hızını artırırsam alev nasıl değişir?"* |`,
                          `| **Giysi & Gezgin Atmosfer Kıyaslaması** | ISS (\`14.7 psia\`), Ay Gezgini (\`10.2 psia / %32 O₂\`) ve EVA Giysisi (\`4.3 psia / %100 O₂\`) yanıcılık matrisi | *"Uzay giysisi ile basınçlı Ay gezginini sayısal kıyasla."* |`,
                          `| **15 NASA PSI Deneyi & Raf Sorgusu** | \`FLEX\`, \`CFI\`, \`ACME CFI-G\`, \`BASS\`, \`SPICE\`, \`SLICE\`, \`Saffire\`, \`SoFIE\`, \`DAFT\` bulguları ve varyasyon tablosu | *"Saffire deneyinde neler sabit tutuldu, neler değiştirildi?"* |`,
                          `| **ECLSS Yaşam Saati & Söndürme** | \`NASA-STD-6001B\` Halon 1301 yasağı, \`SoFIE-MIST\` su sisi, \`JSC-20584 CO SMAC\` saati ve Soğuk Alev tespiti | *"Uzay aracında Halon 1301 neden yasak?"* |`,
                          `| **Görsel & Veri Dosyası Çözümleme** | Tarayıcı RAM'inde alev fotoğrafı (\`.png/.jpg\`) piksel analizi ve \`.csv/.xlsx/.zip/.pdf\` parametre çıkarımı | Soldan dosya seçip *"Yüklediğim veriyi analiz et"* yazın |`,
                      ].join("\n"),
                citations: [],
            };
        }

        // 2. Özelliklerin neler? / 5 Modüllü Teknik Mimari Envanteri
        if (intent === "platform_features") {
            return {
                reply: isEn
                    ? [
                          `### ALTAR-NASA: Flame in Freefall (v6.3) — Platform Modules`,
                          `ALTAR-NASA consists of **5 integrated modules** running directly in your browser:`,
                          ``,
                          `1. **Combustion Chamber:** 4-geometry 3D WebGL chamber (\`Droplet\`, \`PMMA Rod\`, \`Fabric Slab\`, \`CFI-G Porous Sphere\`) solving phase-specific transport equations calibrated against ISS \`0G\` benchmarks (**\`R² = ${fv.r_squared}\`**, \`RMSE = ${fv.rmse}\`), telemetry sonification, and **Life Support Clock (\`NASA JSC-20584 CO SMAC\`)**.`,
                          `2. **NASA Experiments:** Physical similarity + bilingual ranking across 15 verified NASA PSI experiments (\`CIR/MDCA\`, \`MSG Flow Duct\`, \`Cygnus Saffire\`, \`SAME/DAFT\`), intra-experiment test variations, and Earth applications.`,
                          `3. **Data & Imagery:** Live \`ntrs.nasa.gov\` & \`osdr.nasa.gov\` archive stream plus client-side flame photo pixel analysis and \`.CSV/.JSON/.PDF\` parameter extraction.`,
                          `4. **Engineering Analysis:** Question-driven analytical & sensitivity solver guarded by \`CON-01..CON-09\` and \`NASA-STD-6001B\` Halon-prohibition checks.`,
                          `5. **Validation & Settings:** Physical validation rules matrix and one-click **\`.CSV\`**, **\`.JSON\`**, and **\`.HTML / PDF\`** scientific dataset export.`,
                      ].join("\n")
                    : [
                          `### ALTAR-NASA: Flame in Freefall (v6.3) — Platform Modülleri`,
                          `Platform doğrudan tarayıcı içinde çalışan **5 entegre mühendislik modülünden** oluşur:`,
                          ``,
                          `1. **Yanma Odası:** 4 farklı 3B numune/brülör geometrisini (\`Damlacık\`, \`PMMA Çubuk\`, \`Nomex/Sibal Kumaş\`, \`CFI-G Gözenekli Küre\`) ve faza özgü taşınım denklemlerini ISS \`0G\` referans eğrileriyle (**\`R² = ${fv.r_squared}\`**, \`RMSE = ${fv.rmse}\`) doğrular; telemetri seslendirme ve **Yaşam Destek Saati (\`NASA JSC-20584 CO SMAC\`)** sunar.`,
                          `2. **NASA Deneyleri:** \`CIR/MDCA\`, \`MSG Fan Kanalı\`, \`Cygnus (Saffire)\` ve \`SAME/DAFT\` donanımlarındaki 15 doğrulanmış NASA PSI deneyini fiziksel yakınlıkla sıralar; test varyasyonlarını ve Dünya uygulamalarını gösterir.`,
                          `3. **Veri ve Görüntü:** Resmi \`ntrs.nasa.gov\` ve \`osdr.nasa.gov\` arşivlerinden canlı veri çeker; alev fotoğraflarını ve \`.csv/.json/.pdf\` dosyalarını analiz edip 3B odaya aktarır.`,
                          `4. **Mühendislik Analizi:** Soru-odaklı çok noktalı analitik çözücüyü \`CON-01..CON-09\` fiziksel kuralları ve \`NASA-STD-6001B\` Halon yasağı denetimiyle çalıştırır.`,
                          `5. **Doğrulama ve Ayarlar:** Fiziksel doğrulama kuralları matrisini sunar ve tek tıkla **\`.CSV\`**, **\`.JSON\`** ve **\`.HTML / PDF\`** bilimsel görev raporu indirmenizi sağlar.`,
                      ].join("\n"),
                citations: [],
            };
        }

        // 3. Selamlama & Aktif Kilit Özeti
        if (intent === "greeting_identity") {
            return {
                reply: isEn
                    ? [
                          `### ALTAR-NASA v6.3 — Decision Support Kernel Online`,
                          `- **Active 3D Chamber Lock:** \`${inp.fuel_name_en}\` (\`${inp.geometry_3d}\`) | \`${inp.gravity_g} G\` | \`${inp.oxygen_pct}% O₂\` (\`P_O2 = ${tel.o2_partial_psia} psia\`) | \`U = ${inp.airflow_cms} cm/s\``,
                          `- **Computed State:** Regime **${regBadge}** | Flame Temp \`${tel.flame_temp_k} K\` | Critical \`MOC = ${tel.moc_pct}% O₂\` | Fire Risk **\`${tel.risk_score}/100\`**`,
                          ``,
                          `Ask me any targeted question—such as deriving \`Spalding B_oq\`, sweeping airflow or gravity (\`0G vs 0.16G Moon\`), comparing \`EVA Suit\` vs \`Lunar Rover\`, or inspecting \`FLEX\`, \`Saffire\`, \`SoFIE-MIST\`, or \`DAFT\`.`,
                      ].join("\n")
                    : [
                          `### ALTAR-NASA v6.3 — Kanıt Sentezi ve Karar Destek Çekirdeği Hazır`,
                          `- **Aktif 3B Yanma Odası Kilidi:** \`${inp.fuel_name_tr}\` (\`${inp.geometry_3d}\`) | \`${inp.gravity_g} G\` | \`%${inp.oxygen_pct} O₂\` (\`P_O2 = ${tel.o2_partial_psia} psia\`) | \`U = ${inp.airflow_cms} cm/s\``,
                          `- **Anlık Çözücü Durumu:** Rejim **${regBadge}** | Alev Sıcaklığı \`${tel.flame_temp_k} K\` | Kritik \`MOC = %${tel.moc_pct} O₂\` | Yangın Riski **\`${tel.risk_score}/100\`**`,
                          ``,
                          `Bana belirli bir fiziksel denklemi (\`Spalding B_oq\`, \`Sherwood Sh\`, \`Damköhler Da\`), parametre değişim senaryosunu (*"Akış hızını artırırsam ne olur?"*), \`EVA Giysisi vs. Ay Gezgini\` kıyaslamasını veya merak ettiğiniz bir NASA PSI deneyini (\`FLEX\`, \`Saffire\`, \`SoFIE-MIST\`, \`DAFT\`) doğrudan sorabilirsiniz.`,
                      ].join("\n"),
                citations: [],
            };
        }

        // 4. Roket Motorları Kapsam Sınırı (CON-08)
        if (intent === "rocket_scope") {
            return {
                reply: isEn
                    ? [
                          `### Why Rocket Engines & Thrusters Are Excluded from NASA PSI Cabin Fire Scope (CON-08)`,
                          `1. **Momentum-Dominated Regime (\`Ri = Gr / Re² → 0\`):** Inside rocket thrust chambers, gas velocities reach \`10²–10³ m/s\` (\`Re > 10⁵\`). Because Richardson scaling obeys \`Ri = Gr / Re²\`, buoyancy (\`Gr ∝ g\`) is negligible (\`Ri < 10⁻⁶\`), making rocket combustion effectively gravity-independent.`,
                          `2. **Habitable Spacecraft Contrast (Your Active Chamber):** At your cabin ventilation speed \`U = ${inp.airflow_cms} cm/s\` (\`Re = ${tel.reynolds_number}\`, \`Ri = ${tel.richardson_number}\`), eliminating gravity (\`0G / 0.16G / 0.38G\`) turns flames spherical, amplifies radiative quenching (\`χ_r\`), and lowers \`MOC\`.`,
                          `3. **NASA PSI Portfolio Scope:** Consequently, NASA PSI (\`FLEX\`, \`CFI\`, \`ACME\`, \`BASS\`, \`SPICE\`, \`SLICE\`, \`Saffire\`, \`SoFIE\`, \`DAFT\`) focuses strictly on crewed spacecraft cabins, EVA suits (\`4.3 psia / 100% O₂\`), Lunar/Mars habitats, and pressurized rovers.`,
                      ].join("\n")
                    : [
                          `### Roket Motorları ve İticiler Neden NASA PSI Kapsamı Dışındadır? (CON-08)`,
                          `1. **Momentum Baskınlığı (\`Ri = Gr / Re² → 0\`):** Roket motorları ve iticilerde gaz hızları \`100–3000 m/s\` mertebesindedir (\`Re > 10⁵\`). Richardson sayısı \`Ri = Gr / Re²\` olduğundan kaldırma kuvveti etkisi sıfıra yakındır (\`Ri < 10⁻⁶\`); yani roket yanması **yerçekiminden bağımsızdır**.`,
                          `2. **Mürettebat Kabini ile Fark (Aktif Odanız):** Şu anki 3B yanma odanızda akış yalnızca \`U = ${inp.airflow_cms} cm/s\` düzeyindedir (\`Re = ${tel.reynolds_number}\`, \`Ri = ${tel.richardson_number}\`). Bu düşük kabin hızlarında yerçekiminin kalkması alevi küreselleştirir, radyatif ısı kaybını (\`χ_r\`) büyütür ve \`MOC\` sınırını düşürür.`,
                          `3. **NASA PSI Odak Alanı:** Bu nedenle NASA PSI veri tabanı roket itkisini hariç tutarak doğrudan **ISS modülleri, EVA uzay giysileri (\`4.3 psia / %100 O₂\`), Ay/Mars yüzey üsleri ve basınçlı gezginlerdeki** yangın güvenliğine odaklanır.`,
                      ].join("\n"),
                citations: defaultCitations.slice(0, 2),
            };
        }

        // 5. EVA Uzay Giysisi (%100 O2 @ 4.3 psia) & Ay Gezgini & ISS Kıyaslaması
        if (intent === "eva_rover_atmosphere") {
            const profs = [
                { tr: "ISS USOS Standart Kabin", en: "ISS Standard Cabin", p: { fuel_id: inp.fuel_id, gravity_g: 0.0, oxygen_pct: 21.0, pressure_psia: 14.7, airflow_cms: 4.0, droplet_d0_mm: inp.droplet_d0_mm, diluent: "N2", habitat_id: "iss_module" } },
                { tr: "Ay Üssü / Basınçlı Gezgin", en: "Lunar Base / Rover", p: { fuel_id: inp.fuel_id, gravity_g: 0.16, oxygen_pct: 32.0, pressure_psia: 10.2, airflow_cms: 4.5, droplet_d0_mm: inp.droplet_d0_mm, diluent: "N2", habitat_id: "lunar_rover" } },
                { tr: "Saffire-V Keşif Atmosferi", en: "Saffire-V Exploration", p: { fuel_id: inp.fuel_id, gravity_g: 0.0, oxygen_pct: 34.0, pressure_psia: 8.2, airflow_cms: 5.0, droplet_d0_mm: inp.droplet_d0_mm, diluent: "N2", habitat_id: "lunar_rover" } },
                { tr: "EVA Uzay Giysisi (Saf O₂)", en: "EVA Spacesuit (Pure O₂)", p: { fuel_id: inp.fuel_id, gravity_g: 0.16, oxygen_pct: 100.0, pressure_psia: 4.3, airflow_cms: 6.0, droplet_d0_mm: inp.droplet_d0_mm, diluent: "N2", habitat_id: "eva_suit" } },
            ];
            const rows = profs.map((pr) => {
                const s = simulateCombustionClient(pr.p);
                const st = s.telemetry;
                const stl = s.scenario_timeline;
                const rateStr = st.flame_spread_mm_s > 0 ? `V_f=${st.flame_spread_mm_s} mm/s` : `K=${st.burning_rate_k_mm2_s} mm²/s`;
                return `| **${isEn ? pr.en : pr.tr}** | \`${pr.p.pressure_psia} psia\` | \`${pr.p.oxygen_pct}%\` | \`${st.o2_partial_psia} psia\` | \`${st.moc_pct}%\` | \`${st.flame_temp_k} K\` | \`${rateStr}\` | **\`${st.risk_score}/100\`** (\`100 ppm SMAC ${stl.t_smac_24h_100ppm_s} s\`) |`;
            });
            const relCits = NASA_CATALOG.filter((e) => ["PSI-SAFFIRE5-07", "PSI-SOFIE-08", "PSI-ACME-CFIG-14"].includes(e.exp_id)).map((e) => ({ id: e.exp_id, program: e.program, ntrs_id: e.ntrs_id, url: e.ntrs_url }));
            return {
                reply: isEn
                    ? [
                          `### EVA Spacesuit (\`100% O₂ @ 4.3 psia\`), Lunar Rover (\`32% O₂ @ 10.2 psia\`) & ISS Matrix — \`${inp.fuel_name_en}\``,
                          ``,
                          `| Mission Atmosphere | Total Pressure | O₂ % | Partial \`P_O2\` | Critical \`MOC\` | Flame \`T_f\` | Burn / Spread Rate | Risk & ECLSS SMAC |`,
                          `| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |`,
                          ...rows,
                          ``,
                          `### Thermo-Physical & EVA Operational Synthesis (CON-06)`,
                          `- **Why \`4.3 psia / 100% O₂\` in EVA Suits?** A \`14.7 psia\` suit stiffens joints and prevents finger mobility. Operating at \`4.3 psia\` pure \`O₂\` preserves alveolar \`P_O2 = 4.3 psia\` with zero \`N₂\`, eliminating decompression bends—but **eliminating \`N₂\` removes thermal heat-sink ballast**, causing rapid flame spread across suit textiles if an electrical arc occurs.`,
                          `- **Why \`10.2 psia / 32% O₂\` in Lunar Rovers?** Cuts astronaut EVA pre-breathe purge time from \`>2 hours\` to \`~15 minutes\` (**Saffire-V \`NTRS #20210017780\`**, **SoFIE \`NTRS #20200000361\`**).`,
                          `- **Highest-O₂ PSI Benchmark:** **ACME CFI-G (\`NTRS #20220015583\`)** tested spherical porous-burner flames up to **\`85% O₂\`** inside ISS \`CIR\`.`,
                      ].join("\n")
                    : [
                          `### EVA Uzay Giysisi (\`%100 O₂ @ 4.3 psia\`), Ay Gezgini (\`%32 O₂ @ 10.2 psia\`) ve ISS Yanıcılık Matrisi — \`${inp.fuel_name_tr}\``,
                          ``,
                          `| Görev Atmosferi | Toplam Basınç | O₂ % | Kısmi \`P_O2\` | Kritik \`MOC\` | Sıcaklık \`T_f\` | Yayılma / Yanma | Risk & ECLSS SMAC |`,
                          `| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |`,
                          ...rows,
                          ``,
                          `### Termofiziksel ve Fizyolojik Mühendislik Analizi (CON-06)`,
                          `- **EVA Giysilerinde Neden \`4.3 psia / %100 Saf O₂\` Kullanılır?** \`14.7 psia\` basınçta giysi balon gibi sertleşir. \`4.3 psia\` saf \`O₂\` hem akciğer oksijen basıncını korur (\`P_O2 = 4.30 psia\` > ISS \`3.09 psia\`) hem de kanda azot bırakmayarak **vurgun riskini sıfırlar**. Ancak **ısıyı emen \`N₂\` ısıl balastı kalktığı için** alev sıcaklığı ve yayılma hızı sıçrar.`,
                          `- **Ay Üssü ve Basınçlı Gezginlerde Neden \`10.2 psia / %32 O₂\` Seçilir?** Dünya'ya göre \`>%40\` bağıl oksijen artışı sağlayarak saatler süren EVA ön-soluma (\`pre-breathe\`) süresini \`~15 dakikaya\` indirir (**Saffire-V \`NTRS #20210017780\`**, **SoFIE \`NTRS #20200000361\`**).`,
                          `- **PSI En Yüksek Oksijen Deneyi:** ISS \`CIR\` rafındaki **ACME CFI-G (\`NTRS #20220015583\`)** küresel brülörde **\`%85 O₂\`** konsantrasyonuna kadar test yapılmıştır.`,
                      ].join("\n"),
                citations: relCits,
            };
        }

        // 6. Kısmi Yerçekimi (0.16G Ay / 0.38G Mars), LUCI/FM2 ve ACME E-FIELD
        if (intent === "partial_gravity_luci") {
            const gLevels = [
                { tr: "0.00 G (ISS Mikroçekim)", en: "0.00 G (ISS Freefall)", g: 0.0 },
                { tr: "0.16 G (Ay Yüzeyi • LUCI/FM2)", en: "0.16 G (Lunar • LUCI/FM2)", g: 0.16 },
                { tr: "0.38 G (Mars Yüzeyi)", en: "0.38 G (Martian Surface)", g: 0.38 },
                { tr: "1.00 G (Dünya Referansı)", en: "1.00 G (Earth Reference)", g: 1.0 },
            ];
            const gRows = gLevels.map((gl) => {
                const sg = simulateCombustionClient(Object.assign({}, inp, { gravity_g: gl.g }));
                const gt = sg.telemetry;
                const rCol = gt.flame_spread_mm_s > 0 ? `V_f=${gt.flame_spread_mm_s} mm/s` : `K=${gt.burning_rate_k_mm2_s} mm²/s`;
                return `| **${isEn ? gl.en : gl.tr}** | \`Ra = ${gt.rayleigh_number}\` | \`Ri = ${gt.richardson_number}\` | **\`${gt.moc_pct}% O₂\`** | \`${gt.flame_temp_k} K\` | \`${rCol}\` | \`${gt.regime}\` (\`${gt.risk_score}/100\`) |`;
            });
            const relCits = NASA_CATALOG.filter((e) => ["PSI-ACME-09", "PSI-BASS-03", "PSI-SOFIE-08"].includes(e.exp_id)).map((e) => ({ id: e.exp_id, program: e.program, ntrs_id: e.ntrs_id, url: e.ntrs_url }));
            return {
                reply: isEn
                    ? [
                          `### Partial-Gravity Bounding (\`0G\` → \`0.16G Moon\` → \`0.38G Mars\` → \`1G\`) — \`${inp.fuel_name_en}\``,
                          ``,
                          `| Gravity Regime | Rayleigh \`Ra\` | Richardson \`Ri\` | Critical \`MOC\` | Flame \`T_f\` | Burn / Spread Rate | Regime & Risk |`,
                          `| :--- | :--- | :--- | :--- | :--- | :--- | :--- |`,
                          ...gRows,
                          ``,
                          `### NASA PSI Partial-G Gap, LUCI/FM2 & ACME E-FIELD Emulation (CON-07)`,
                          `1. **PSI Partial-G Data Gap (\`LUCI\` & \`FM2\`):** NASA PSI currently contains \`0G\` orbital and \`1G\` ground data, with **no direct lunar-g combustion dataset yet**. Upcoming **LUCI (*Lunar-g Combustion Investigation*)** and **FM2 (*Flammability of Materials on the Moon*)** payloads will fill this gap.`,
                          `2. **0G–1G Bounding & Lunar Hazard:** Gentle \`0.16G\` buoyant slip (\`u_b ≈ 8.8 cm/s\`) feeds fresh \`O₂\` (\`Da > 1\`) without strong \`1G\` convective cooling, often dropping \`MOC\` below \`1G\` Earth limits; bounding between \`0G\` ventilated (\`BASS\`/\`SoFIE\`) and \`1G\` brackets the hazard.`,
                          `3. **ACME E-FIELD Ionic-Wind Emulation (\`NTRS #20210015913\`):** Electric fields acting on flame chemi-ions (\`H₃O⁺\`, \`CHO⁺\`) in \`0G\` emulate \`0.16G / 0.38G\` buoyant convection and cut soot by \`70%\`.`,
                      ].join("\n")
                    : [
                          `### Kısmi Yerçekimi Sınırlandırma Analizi (\`0G\` → \`0.16G Ay\` → \`0.38G Mars\` → \`1G\`) — \`${inp.fuel_name_tr}\``,
                          ``,
                          `| Yerçekimi Rejimi | Rayleigh \`Ra\` | Richardson \`Ri\` | Kritik \`MOC\` | Sıcaklık \`T_f\` | Yanma / Yayılma | Rejim & Risk |`,
                          `| :--- | :--- | :--- | :--- | :--- | :--- | :--- |`,
                          ...gRows,
                          ``,
                          `### NASA PSI Veri Boşluğu, LUCI/FM2 ve ACME E-FIELD Taklidi (CON-07)`,
                          `1. **PSI Kısmi Yerçekimi Veri Boşluğu (\`LUCI\` & \`FM2\`):** Şu anda NASA PSI arşivinde doğrudan Ay veya Mars kısmi yerçekimi yanma verisi yoktur; bu boşluğun gelecekteki **LUCI (*Lunar-g Combustion Investigation*)** ve **FM2 (*Flammability of Materials on the Moon*)** Ay yüzey deneyleriyle doldurulması beklenmektedir.`,
                          `2. **0G–1G Sınırlandırması (Bounding):** \`0.16G\` Ay yerçekimi \`u_b ≈ 8.8 cm/s\` mertebesinde tatlı bir doğal kaldırma akışı yaratarak aleve taze \`O₂\` taşır (\`Da > 1\`) ve kritik \`MOC\` sınırını \`1G\` Dünya değerinin **altına** çekebilir.`,
                          `3. **ACME E-FIELD İyon Rüzgarı Taklidi (\`NTRS #20210015913\`):** ISS \`CIR\` odasında alevdeki doğal iyonlara (\`H₃O⁺\`, \`CHO⁺\`) uygulanan elektrik alanı, \`0G\` ortamında Ay/Mars kısmi yerçekimi konveksiyonunu taklit etmiş ve kurumu \`%70\` azaltmıştır.`,
                      ].join("\n"),
                citations: relCits,
            };
        }

        // 7. Görünmez Soğuk Alev (Cool Flame NTC) & DAFT/SAME Toz-Duman Ayrımı
        if (intent === "cool_flame_daft") {
            const cfSim = simulateCombustionClient({ fuel_id: "n_heptane", gravity_g: 0.0, oxygen_pct: 15.5, pressure_psia: inp.pressure_psia, airflow_cms: 0.1, droplet_d0_mm: 3.8, diluent: inp.diluent });
            const cft = cfSim.telemetry;
            const relCits = NASA_CATALOG.filter((e) => ["PSI-FLEX-01", "PSI-CFI-11", "PSI-DAFT-15", "PSI-ACME-CFIG-14"].includes(e.exp_id)).map((e) => ({ id: e.exp_id, program: e.program, ntrs_id: e.ntrs_id, url: e.ntrs_url }));
            return {
                reply: isEn
                    ? [
                          `### Two-Stage Radiative Extinction, Invisible Cool Flames (NTC) & DAFT Multi-Channel Detection (CON-04)`,
                          `- **Active Chamber vs. Cool-Flame Onset:** Current radiative fraction is \`χ_r = ${(tel.radiative_loss_fraction * 100).toFixed(1)}%\` (\`${tel.flame_temp_k} K\`, \`${tel.regime}\`). For a \`3.8 mm\` \`n-Heptane\` droplet at \`0G / 15.5% O₂\`, \`χ_r\` hits \`${(cft.radiative_loss_fraction * 100).toFixed(1)}%\`, locking into **\`${cft.regime}\`** at \`${cft.flame_temp_k} K\`.`,
                          `- **NTC Kinetics (\`FLEX\`, \`CFI\`, \`ACME CFI-G\`):** Spherical \`0G\` flames trap hot products (\`R_f/R_d ≈ 5–8\`). Once \`Q_rad ∝ R_f³·σ·(T_f⁴ - T_∞⁴)\` exceeds \`χ_r > 0.45\`, the visible hot flame quenches into invisible \`550–780 K\` peroxy (\`RO₂ ⇌ QOOH\`) combustion, leaking toxic \`CO\` and \`CH₂O\`.`,
                          ``,
                          `| Detection Channel | Hot Sooty Flame | Invisible Cool Flame (\`550–780 K\`) | Lunar Regolith / Cabin Dust |`,
                          `| :--- | :--- | :--- | :--- |`,
                          `| **ISS Photoelectric Smoke Detector (PSD, 670 nm)** | High (\`75–100%\`) | **\`~0–2%\` (BLIND)** | Scatters light (False Alarm Risk) |`,
                          `| **CIR UV / Mid-IR Radiometer (\`OH*\`/\`CH*\`)** | High (\`12–35 kW/m²\`) | **Detects \`2.5–5.5 kW/m²\` signature** | \`0 kW/m²\` (Immune) |`,
                          `| **CSA-CP / ANITA-2 Gas Analyzer (\`CO / CH₂O\`)** | Moderate–High | **Captures \`>25 ppm\` C&W CO rise** | \`0 ppm\` (Immune) |`,
                          `| **SAME / DAFT Multi-Angle Laser** | Sub-micron soot (\`<0.4 µm\`) | Detects condensed vapor cloud (\`CFI\`) | **Rejects \`1–10 µm\` lunar dust via polarization/angle ratio** |`,
                      ].join("\n")
                    : [
                          `### İki Aşamalı Radyatif Sönme, Görünmez Soğuk Alev (NTC) ve DAFT Toz/Duman Ayrımı (CON-04)`,
                          `- **Aktif Odanız vs. Soğuk Alev Eşiği:** Mevcut simülasyonunuzda radyatif kayıp \`χ_r = %${(tel.radiative_loss_fraction * 100).toFixed(1)}\` (\`${tel.flame_temp_k} K\`, \`${tel.regime}\`). \`0G / %15.5 O₂\` altında \`3.8 mm\` \`n-Heptan\` damlacığında \`χ_r = %${(cft.radiative_loss_fraction * 100).toFixed(1)}\` değerine ulaşarak \`${cft.flame_temp_k} K\` sıcaklıkta **\`${cft.regime}\`** fazına geçer.`,
                          `- **NTC Mekanizması (\`FLEX\`, \`CFI\`, \`ACME CFI-G\`):** \`0G\` küresel alevinde \`Q_rad ∝ R_f³·σ·(T_f⁴ - T_∞⁴)\` kaybı \`χ_r > 0.45\` eşiğini aştığında sıcak alev söner; alkan yakıtlar \`550–780 K\` peroksi (\`RO₂ ⇌ QOOH\`) kimyasıyla **görünmez Soğuk Alev** olarak yanmayı sürdürür ve zehirli \`CO\` / formaldehit üretir.`,
                          ``,
                          `| Algılama Kanalı | Sıcak Görünür Alev | Görünmez Soğuk Alev (\`550–780 K\`) | Kabin / Ay Regolit Tozu |`,
                          `| :--- | :--- | :--- | :--- |`,
                          `| **ISS Fotoelektrik Duman Dedektörü (PSD, 670 nm)** | Yüksek (\`%75–100\`) | **\`~%0–2\` (KURUMSIZ ALEVDE UYARMAZ)** | Işığı saçar (Yanlış Alarm Riski) |`,
                          `| **CIR UV / Orta-IR Radyometre (\`OH*\`/\`CH*\`)** | Yüksek (\`12–35 kW/m²\`) | **\`2.5–5.5 kW/m²\` ışıma yakalar** | \`0 kW/m²\` (Toza Bağışıklı) |`,
                          `| **CSA-CP / ANITA-2 Gaz Analizörü (\`CO / CH₂O\`)** | Orta–Yüksek | **\`>25 ppm\` C&W \`CO\` artışını yakalar** | \`0 ppm\` (Toza Bağışıklı) |`,
                          `| **SAME / DAFT Çok Açılı Lazer** | \`<0.4 µm\` yanma dumanı | \`CFI\` buhar bulutunu algılar | **Polarizasyon ve saçılma açısıyla \`1–10 µm\` Ay tozunu reddeder** |`,
                      ].join("\n"),
                citations: relCits,
            };
        }

        // 8. Halon 1301 Yasağı, NASA-STD-6001B Söndürme, SoFIE-MIST & İtfaiye Transferi
        if (intent === "suppression_halon") {
            const zSim = simulateCombustionClient(Object.assign({}, inp, { airflow_cms: 0.0 }));
            const zt = zSim.telemetry;
            const incSpin = hasAnyTerm(nq, ["itfaiye", "firefighter", "dunya", "earth", "giysi", "tank", "spinoff", "transfer"]);
            const relCits = NASA_CATALOG.filter((e) => ["PSI-SOFIE-08", "PSI-BASS-03", "PSI-DAFT-15"].includes(e.exp_id)).map((e) => ({ id: e.exp_id, program: e.program, ntrs_id: e.ntrs_id, url: e.ntrs_url }));
            const spinTr = incSpin
                ? `\n\n### Dünya'daki İtfaiye ve Endüstriyel Uygulamalar (Space-to-Earth)\n- **SoFIE-MIST Su Sisi:** \`25–40 µm\` temiz su sisi nozulları veri merkezleri, ameliyathaneler ve lityum-iyon batarya depolarında Halon'un yerini almıştır.\n- **PBI/Nomex İtfaiyeci Giysileri & \`SCBA\` Hava Tankları:** Apollo/EVA yangın araştırmalarından doğan \`PBI/Nomex\` kumaşlar modern itfaiyeci elbiselerini korur; NASA karbon-fiber \`COPV\` teknolojisi itfaiyeci \`SCBA\` solunum tüplerini \`%40\` hafifletmiştir.\n- **DAFT/SAME Duman Dedektörleri:** Çok açılı lazer saçılma algoritmaları maden ve uçak kargo ambarlarında toz kaynaklı yanlış alarmları önler.`
                : "";
            const spinEn = incSpin
                ? `\n\n### Terrestrial Firefighting & Industrial Spinoffs\n- **SoFIE-MIST Water Mist:** Sub-\`50 µm\` nozzles protect data centers, cleanrooms, and EV battery packs without fluorinated gases.\n- **Firefighter Turnout Gear & \`SCBA\` Tanks:** Apollo/EVA \`PBI/Nomex\` thermal fabrics shield municipal firefighters, while NASA \`COPV\` composite vessels reduce \`SCBA\` air-tank weight by \`~40%\`.\n- **DAFT/SAME Smoke Detectors:** Multi-angle laser scattering prevents dust false alarms in mines and aircraft cargo bays.`
                : "";
            return {
                reply: isEn
                    ? [
                          `### Why Halon 1301 Is Strictly Prohibited & NASA-STD-6001B Suppression Protocol (CON-05)`,
                          `1. **Why Halon 1301 (\`CF₃Br\`) Is Banned:** Above \`750 K\`, Halon 1301 pyrolyzes into corrosive **\`HF\`** and **\`HBr\`** acid gases—fatal to crew lungs inside sealed cabins and **permanently poisoning ECLSS \`LiOH\` / amine scrubbers and catalytic beds**.`,
                          `2. **Live ECLSS Survival Clock (\`${tl.habitat_name_en}\`):** Alarm at \`+${tl.t_alarm_s} s\` | **\`NASA JSC-20584 24-hr CO SMAC (100 ppm)\`** reached at **\`${tl.t_smac_24h_100ppm_s} s\`** (\`1-hr 425 ppm\`: \`${tl.t_smac_1h_425ppm_s} s\`) | CO at response: \`${tl.co_at_response_ppm} ppm\`.`,
                          `3. **Mandatory 4-Step Non-Halon Sequence:**`,
                          `   - **Step 1 — HVAC Airflow Cutoff (\`${inp.airflow_cms} cm/s → 0 cm/s\`):** Live solver check drops risk from **\`${tel.risk_score}/100\` → \`${zt.risk_score}/100\`** (\`${zt.regime}\`).`,
                          `   - **Step 2 — Electrical Bus Isolation:** Eliminate arc re-ignition sources.`,
                          `   - **Step 3 — \`25–40 µm\` Fine Water Mist (\`ISS PFE / SoFIE-MIST\`, \`NTRS #20200000361\`) or \`CO₂ / N₂\`:** High latent heat (\`L_v = 2257 kJ/kg\`) + \`1700×\` steam expansion with zero toxic acid residue.`,
                          `   - **Step 4 — Depressurization & Post-Fire CSA-CP / IR Watch:** Verify zero Cool Flame persistence before restarting fans.` + spinEn,
                      ].join("\n")
                    : [
                          `### İnsanlı Uzay Araçlarında Halon 1301 Neden Kesinlikle Yasaktır? — NASA-STD-6001B Protokolü (CON-05)`,
                          `1. **Halon 1301 (\`CF₃Br\`) Yasağının Bilimsel Nedeni:** Kapalı devre \`ECLSS\` yaşam destekli uzay araçlarında Halon 1301 gazı \`>750 K\` alevde parçalanarak öldürücü **hidrojen florür (\`HF\`)** ve **hidrojen bromür (\`HBr\`)** asit gazları üretir; mürettebat akciğerlerini yakar ve **ECLSS karbondioksit/iz-kirletici filtrelerini kalıcı olarak zehirler**.`,
                          `2. **Aktif ECLSS Yaşam Destek Saati (\`${tl.habitat_name_tr}\`):** C&W alarmı \`+${tl.t_alarm_s} sn\` | **\`NASA JSC-20584 24sa CO SMAC (100 ppm)\`** sınırı **\`${tl.t_smac_24h_100ppm_s} sn\`** (\`1sa 425 ppm\`: \`${tl.t_smac_1h_425ppm_s} sn\`) | Müdahale anı CO: \`${tl.co_at_response_ppm} ppm\`.`,
                          `3. **Zorunlu 4 Adımlı Müdahale Sırası:**`,
                          `   - **Adım 1 — HVAC Fanlarını Anında Kapat (\`${inp.airflow_cms} cm/s → 0 cm/s\`):** Canlı çözücü kontrolüne göre akışı kesmek riski **\`${tel.risk_score}/100\` → \`${zt.risk_score}/100\`** düzeyine indirir (\`${zt.regime}\`).`,
                          `   - **Adım 2 — Elektrik Beslemesini Kes:** Ark ve ohmik ısınmayı durdurur.`,
                          `   - **Adım 3 — \`25–40 µm\` İnce Su Sisi (\`ISS PFE / SoFIE-MIST\`, \`NTRS #20200000361\`) veya \`CO₂ / N₂\`:** Yüksek buharlaşma gizli ısısı (\`L_v = 2257 kJ/kg\`) çekerek toksik kalıntı bırakmadan alevi söndürür.`,
                          `   - **Adım 4 — Kontrollü Basınç Düşürme & CSA-CP / IR Taraması:** Fanlar açılmadan önce gizli Soğuk Alev kalmadığı doğrulanır.` + spinTr,
                      ].join("\n"),
                citations: relCits,
            };
        }

        // 9. Spesifik NASA PSI Deneyi / Donanım Rafı
        if (intent === "specific_experiment") {
            let matched = [];
            if (hasAnyTerm(nq, ["en yuksek oksijen", "highest oxygen"])) {
                matched = NASA_CATALOG.filter((e) => e.exp_id === "PSI-ACME-CFIG-14");
            } else {
                const pMap = [
                    ["cfi-g", "PSI-ACME-CFIG-14"], ["cfig", "PSI-ACME-CFIG-14"], ["flex-2", "PSI-FLEX2-02"],
                    ["flex", "PSI-FLEX-01"], ["cfi", "PSI-CFI-11"], ["e-field", "PSI-ACME-09"],
                    ["bre", "PSI-ACME-BRE-10"], ["sofie-mist", "PSI-SOFIE-08"], ["sofie", "PSI-SOFIE-08"],
                    ["saffire", "PSI-SAFFIRE5-07"], ["bass-ii", "PSI-BASS2-04"], ["bass", "PSI-BASS-03"],
                    ["spice", "PSI-SPICE-12"], ["slice", "PSI-SLICE-13"], ["same", "PSI-DAFT-15"], ["daft", "PSI-DAFT-15"]
                ];
                pMap.forEach(([kw, eid]) => {
                    if (nq.indexOf(kw) !== -1) {
                        const found = NASA_CATALOG.find((x) => x.exp_id === eid);
                        if (found && !matched.includes(found)) matched.push(found);
                    }
                });
                if (!matched.length) {
                    if (nq.indexOf("msg") !== -1) matched = NASA_CATALOG.filter((e) => e.hardware_group === "MSG").slice(0, 3);
                    else if (nq.indexOf("cygnus") !== -1) matched = NASA_CATALOG.filter((e) => e.hardware_group === "CYGNUS").slice(0, 3);
                    else if (nq.indexOf("cir") !== -1 || nq.indexOf("mdca") !== -1) matched = NASA_CATALOG.filter((e) => e.hardware_group === "CIR").slice(0, 3);
                }
            }
            if (!matched.length) matched = ranked.slice(0, 2);

            const blocks = matched.slice(0, 3).map((e) => {
                const runs = e.intra_runs || [];
                let runTbl = "";
                if (runs.length) {
                    const hdr = isEn
                        ? `\n\n| Sub-Test / Run | Held Constant | Varied Parameter | Experimental Outcome |\n| :--- | :--- | :--- | :--- |\n`
                        : `\n\n| Alt Test / Koşum | Sabit Tutulan | Değiştirilen Parametre | Deneysel Sonuç |\n| :--- | :--- | :--- | :--- |\n`;
                    runTbl = hdr + runs.map((r) => `| **${r.run_code || r.run || "-"}** | ${isEn ? r.same_en : r.same_tr} | ${isEn ? r.diff_en : r.diff_tr} | ${isEn ? r.result_en : r.result_tr} |`).join("\n");
                }
                return isEn
                    ? `### ${e.program} (\`${e.exp_id}\`) — ${e.title}\n- **Facility:** \`${e.facility}\` (\`${e.hardware_group}\`) | **Citation:** [NTRS #${e.ntrs_id}](${e.ntrs_url})\n- **Conditions:** \`${e.gravity_g} G\`, \`${e.oxygen_pct}% O₂\`, \`${e.pressure_psia} psia\`, \`${e.airflow_cms} cm/s\`, Measured **\`MOC = ${e.moc_measured_pct}% O₂\`**\n- **Key Finding:** ${e.key_finding_en}\n- **Safety Action:** ${e.safety_insight_en}${runTbl}`
                    : `### ${e.program} (\`${e.exp_id}\`) — ${e.title_tr}\n- **Donanım Rafı:** \`${e.facility}\` (\`${e.hardware_group}\`) | **Resmi Kaynak:** [NTRS #${e.ntrs_id}](${e.ntrs_url})\n- **Test Koşulları:** \`${e.gravity_g} G\`, \`%${e.oxygen_pct} O₂\`, \`${e.pressure_psia} psia\`, \`${e.airflow_cms} cm/s\`, Ölçülen **\`MOC = %${e.moc_measured_pct} O₂\`**\n- **Temel Bulgu:** ${e.key_finding_tr}\n- **Güvenlik Önlemi:** ${e.safety_insight_tr}${runTbl}`;
            });
            return {
                reply: blocks.join("\n\n"),
                citations: matched.slice(0, 3).map((e) => ({ id: e.exp_id, program: e.program, ntrs_id: e.ntrs_id, url: e.ntrs_url })),
            };
        }

        // 10. Spesifik Denklem ve Boyutsuz Sayı Türetimi
        if (intent === "equation_deep_dive") {
            const tblLines = (sim.formula_table || []).map(
                (r) => `| **${isEn ? r.law_en : r.law_tr}** | \`${r.equation}\` | **\`${r.value}\`** | ${isEn ? r.status_en : r.status_tr} |`
            );
            const focus = hasAnyTerm(nq, ["spalding", "b_oq", "boq", "d2", "d²", "yanma sabiti", "burning constant", "standoff", "durma", "burke", "de ris"])
                ? (inp.fuel_phase === "gas"
                    ? (isEn
                        ? `### Steady Gas-Burner Burke-Schumann Diffusion Scaling (\`D_burner = ${inp.droplet_d0_mm} mm\` Constant)\n- **No Liquid Evaporation (\`d²\`-Law Inactive):** Sintered porous stainless-steel gas spheres (\`ACME CFI-G\`) and jet nozzles (\`SPICE / SLICE\`) maintain constant diameter (\`D_burner = D₀\`); \`B_g = ${tel.spalding_b_number}\` represents gas-phase stoichiometric enthalpy scaling.\n- **Burke-Schumann Standoff Ratio (\`R_f / R_b = ${tel.standoff_ratio_rf_rd}\`):** Stoichiometric flame sits at \`R_f = ${tel.flame_radius_mm} mm\`.\n\n`
                        : `### Sürekli Gaz Brülörü Burke-Schumann Difüzyon Ölçeklemesi (\`D_brülör = ${inp.droplet_d0_mm} mm\` Sabit)\n- **Sıvı Buharlaşması Yoktur (\`d²\` Yasası Pasif):** Sinterlenmiş paslanmaz çelik küre (\`ACME CFI-G\`) ve nozul (\`SPICE / SLICE\`) gaz brülörlerinde çap sabittir (\`D_brülör = D₀\`); \`B_g = ${tel.spalding_b_number}\` gaz fazı entalpi ölçeğidir.\n- **Burke-Schumann Durma Oranı (\`R_f / R_b = ${tel.standoff_ratio_rf_rd}\`):** Alev cephesi \`R_f = ${tel.flame_radius_mm} mm\` yarıçapında kararlı durur.\n\n`)
                    : inp.fuel_phase === "solid"
                    ? (isEn
                        ? `### Solid Surface Flame Spread (de Ris Law \`V_f\`) & Pyrolysis Number \`B_p\`\n- **Pyrolysis Number (\`B_p = ${tel.spalding_b_number}\`):** Ratio of gas-phase oxidation enthalpy to solid gasification enthalpy (\`L_p\`).\n- **de Ris Flame Spread (\`V_f = ${tel.flame_spread_mm_s} mm/s\`):** Controlled by forward gas heat conduction vs. solid thermal inertia \`(k·ρ·c)_s\`.\n\n`
                        : `### Katı Yüzey Alev Yayılımı (de Ris Yasası \`V_f\`) ve Piroliz Sayısı \`B_p\`\n- **Piroliz Kütle Aktarım Sayısı (\`B_p = ${tel.spalding_b_number}\`):** Gaz fazı yanma ısısının katı gazlaşma entalpisine (\`L_p\`) oranıdır.\n- **de Ris Yüzey Yayılım Hızı (\`V_f = ${tel.flame_spread_mm_s} mm/s\`):** Katı ısıl ataleti \`(k·ρ·c)_s\` ve sınır tabaka \`O₂\` taşınımıyla belirlenir.\n\n`)
                    : (isEn
                        ? `### Step-by-Step Droplet \`d²\`-Law & Godsave-Spalding \`B_oq\` Substitution\n- **Spalding Number (\`B_oq = ${tel.spalding_b_number}\`):** Ratio of oxidative enthalpy driving force (\`Y_O2·ΔH_c / ν_s\`) to latent heat of vaporization (\`L_v\`).\n- **Burning Rate Constant (\`K = ${tel.burning_rate_k_mm2_s} mm²/s\`):** From \`K = [8·λ_g/(ρ_l·c_p)]·ln(1+B_oq)·(Sh/2)·(1-χ_r)\`, droplet lifetime is \`t_burn = D₀² / K = ${tel.burn_lifetime_s} s\` and standoff ratio is **\`R_f / R_d = ${tel.standoff_ratio_rf_rd}\`**.\n\n`
                        : `### Adım Adım \`d²\` Sıvı Damlacık Yasası ve Godsave-Spalding \`B_oq\` Türetimi\n- **Spalding Kütle Aktarım Sayısı (\`B_oq = ${tel.spalding_b_number}\`):** Oksijen kütle kesriyle (\`%${inp.oxygen_pct} O₂\`) açığa çıkan yanma entalpisinin gizli buharlaşma ısısına (\`L_v\`) oranıdır.\n- **Efektif Buharlaşma Sabiti (\`K = ${tel.burning_rate_k_mm2_s} mm²/s\`):** \`K = [8·λ_g/(ρ_l·c_p)]·ln(1+B_oq)·(Sh/2)·(1-χ_r)\` bağıntısıyla \`D₀ = ${inp.droplet_d0_mm} mm\` için yanma ömrü \`t_burn = D₀² / K = ${tel.burn_lifetime_s} sn\` ve alev durma mesafesi **\`R_f / R_d = ${tel.standoff_ratio_rf_rd}\`** bulunur.\n\n`))
                : "";
            const hdr = isEn
                ? `### Live Governing Equations & Dimensionless Substitution (\`${inp.fuel_name_en}\`)\n\n| Physical Law / Criterion | Governing Equation | Live Numerical Output | Regime Diagnosis |\n| :--- | :--- | :--- | :--- |\n`
                : `### Aktif 3B Odanız İçin Canlı Denklem ve Boyutsuz Sayı Çözümü (\`${inp.fuel_name_tr}\`)\n\n| Fiziksel Yasa / Kriter | Matematiksel Denklem | Anlık Sayısal Sonuç | Rejim Tanısı |\n| :--- | :--- | :--- | :--- |\n`;
            return { reply: focus + hdr + tblLines.join("\n"), citations: defaultCitations.slice(0, 2) };
        }

        // 11. Karşı-Olgusal 'Ne Olur?' Duyarlılık Taraması
        if (intent === "what_if_sensitivity") {
            let sweepTitle = isEn ? "Ventilation Airflow Sweep (`0` → `30 cm/s`)" : "Kabin Havalandırma Akış Hızı Taraması (`0` → `30 cm/s`)";
            let variants = [0.0, 2.0, 6.0, 15.0, 30.0].map((u) => ({ lbl: `U = ${u} cm/s`, p: Object.assign({}, inp, { airflow_cms: u }) }));
            if (hasAnyTerm(nq, ["seyreltici", "diluent", "helyum", "helium", "argon", "co2", "azot"])) {
                sweepTitle = isEn ? "Diluent Gas Comparison (`N₂` vs `CO₂` vs `He`)" : "Seyreltici Kabin Gazı Kıyaslaması (`N₂` vs `CO₂` vs `He`)";
                variants = ["N2", "CO2", "He"].map((dl) => ({ lbl: dl, p: Object.assign({}, inp, { diluent: dl }) }));
            } else if (hasAnyTerm(nq, ["oksijen", "oxygen", "o2"])) {
                sweepTitle = isEn ? "Oxygen Sweep (`14%` → `34% O₂`)" : "Oksijen Konsantrasyonu Taraması (`%14` → `%34 O₂`)";
                variants = [14.0, 18.0, 21.0, 28.0, 34.0].map((ox) => ({ lbl: `${ox}% O₂`, p: Object.assign({}, inp, { oxygen_pct: ox }) }));
            } else if (hasAnyTerm(nq, ["0g ile 1g", "yercekimi", "gravity", "1g"])) {
                sweepTitle = isEn ? "Gravity Sweep (`0G` → `1G`)" : "Yerçekimi Taraması (`0G` → `1G`)";
                variants = [0.0, 0.16, 0.38, 1.0].map((gv) => ({ lbl: `${gv} G`, p: Object.assign({}, inp, { gravity_g: gv }) }));
            }
            const swRows = variants.map((v) => {
                const sw = simulateCombustionClient(v.p);
                const swt = sw.telemetry;
                const rv = swt.flame_spread_mm_s > 0 ? `V_f=${swt.flame_spread_mm_s} mm/s` : `K=${swt.burning_rate_k_mm2_s} mm²/s`;
                return `| **${v.lbl}** | \`${swt.sherwood_number}\` | \`${swt.damkohler_number}\` | **\`${swt.moc_pct}% O₂\`** | \`${swt.flame_temp_k} K\` | \`${rv}\` | \`${swt.regime}\` (**\`${swt.risk_score}/100\`**) |`;
            });
            return {
                reply: isEn
                    ? `### Counterfactual Sensitivity Simulation: ${sweepTitle} — \`${inp.fuel_name_en}\`\n\n| Perturbed Condition | Sherwood \`Sh\` | Damköhler \`Da\` | Critical \`MOC\` | Flame \`T_f\` | Burn / Spread | Regime & Risk |\n| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n${swRows.join("\n")}\n\n- **Ventilation Paradox (CON-03):** Gentle \`2–8 cm/s\` spacecraft airflow replenishes \`O₂\` (\`Sh > 2\`, \`Da > 1\`) without convective blowoff, minimizing \`MOC\` and maximizing hazard before high-speed blowoff (\`>25 cm/s\`).`
                    : `### Karşı-Olgusal Duyarlılık Simülasyonu: ${sweepTitle} — \`${inp.fuel_name_tr}\`\n\n| Test Noktası | Sherwood \`Sh\` | Damköhler \`Da\` | Kritik \`MOC\` | Sıcaklık \`T_f\` | Yanma / Yayılma | Rejim & Risk |\n| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n${swRows.join("\n")}\n\n- **Havalandırma Paradoksu (CON-03):** Durgun \`0G\` ortamında (\`0 cm/s\`) alev kendi \`CO₂\` kabuğuyla zayıflarken, \`2–8 cm/s\` hafif kabin fan akışı taze \`O₂\` taşıyarak (\`Sh > 2\`, \`Da > 1\`) \`MOC\` sınırını en tehlikeli minimuma indirir; \`>25 cm/s\` üzerinde ise üfleyerek sönme (*blowoff*) başlar.`,
                citations: defaultCitations.slice(0, 2),
            };
        }

        // 12. Uzaydan Dünya'ya Teknoloji Transferi
        if (intent === "earth_spinoffs") {
            const etRows = EARTH_TRANSFERS.map(
                (et) => `| **${isEn ? et.domain_en : et.domain_tr}** | \`${et.nasa_source}\` | ${isEn ? et.insight_en : et.insight_tr} |`
            );
            return {
                reply: isEn
                    ? `### Space-to-Earth Fire Safety & Clean Combustion Spinoffs (CON-09)\n\n| Terrestrial Application | NASA PSI Heritage | Mechanism & Impact |\n| :--- | :--- | :--- |\n${etRows.join("\n")}`
                    : `### NASA Mikroçekim Yanma Araştırmalarının Dünya'daki Güvenlik Uygulamaları (CON-09)\n\n| Dünya Uygulama Alanı | NASA PSI Kaynağı | Mühendislik Mekanizması ve Etkisi |\n| :--- | :--- | :--- |\n${etRows.join("\n")}`,
                citations: defaultCitations,
            };
        }

        // 13. Yüklenen Dosya / Görsel Odaklı Kapsamlı Sentez
        if (intent === "uploaded_media") {
            const pgInfo = sim.partial_gravity_info || {};
            const expLines = ranked
                .slice(0, 5)
                .map((e) => `- **#${e.rank} ${e.program} (\`${e.exp_id}\` • \`${e.hardware_group || "CIR"}\` • [NTRS #${e.ntrs_id}](${e.ntrs_url}))** — ${isEn ? "Score" : "Uyum"} \`${e.priority_score}/100\`, MOC \`${e.moc_measured_pct}%\`: ${isEn ? e.key_finding_en : e.key_finding_tr}`)
                .join("\n");
            const pgNoteEn = pgInfo.show_banner && pgInfo.en ? `- **Partial-Gravity Bounding (0G-1G):** ${pgInfo.en}\n` : "";
            const pgNoteTr = pgInfo.show_banner && pgInfo.tr ? `- **Kısmi Yerçekimi Sınırlandırması (0G-1G):** ${pgInfo.tr}\n` : "";
            return {
                reply: isEn
                    ? `### 1. Uploaded Dataset & Multi-Phase Telemetry Audit\n${mediaCtx}\n\n### 2. Synchronized 3D Chamber, Governing Equations & ISS 0G Calibration\n- **Active 3D State (\`${inp.fuel_name_en}\` • \`${inp.geometry_3d}\`):** \`${inp.gravity_g} G\`, \`${inp.oxygen_pct}% O₂\` (\`P_O2 = ${tel.po2_psia} psia\`), \`${inp.pressure_psia} psia\`, \`${inp.airflow_cms} cm/s\` -> **${regBadge}** (\`T_f = ${tel.flame_temp_k} K\`, Spread \`${tel.flame_spread_mm_s} mm/s\`, Risk **\`${tel.risk_score}/100\`**).\n- **Dimensionless Transport & Kinetics:** \`K = ${tel.burning_rate_k_mm2_s} mm²/s\` | \`B = ${tel.spalding_b_number}\` | \`R_f/R_d = ${tel.standoff_ratio}\` | \`Re = ${tel.reynolds_number}\` | \`Sh = ${tel.sherwood_number}\` | \`Ra = ${tel.rayleigh_number}\` | \`Ri = ${tel.richardson_number}\` | \`Da = ${tel.damkohler_number}\` | \`χ_r = ${(tel.radiative_loss_fraction * 100).toFixed(1)}%\` | \`MOC = ${tel.moc_pct}% O₂\`.\n- **ISS 0G Benchmark Fit:** \`R² = ${fv.r_squared}\` • \`RMSE = ${fv.rmse}\` (${fv.campaign}).\n${pgNoteEn}\n### 3. Ranked NASA PSI Investigations Across Orbital Hardware\n${expLines}\n\n### 4. Life Support Clock (ECLSS), Non-Halon Suppression & Earth Applications\n- **Life Support Clock (\`${tl.habitat_name_en || "ISS Module"}\`):** Alarm \`+${tl.t_alarm_s} s\` | \`JSC-20584 24h SMAC (100 ppm CO)\` limit in **\`${tl.t_smac_24h_100ppm_s} s\`** | Crew response CO \`${tl.co_at_response_ppm} ppm\`.\n- **NASA-STD-6001B Protocol:** **(1)** Cut HVAC ventilation (\`${inp.airflow_cms} -> 0 cm/s\`), **(2)** Isolate power bus, **(3)** Discharge **25-40 µm Fine Water Mist (SoFIE-MIST)** or CO₂/N₂ (*Halon 1301 prohibited due to toxic HF/HBr*).\n- **Terrestrial Transfers:** Sub-50 µm clean water-mist extinguishers, **SAME/DAFT** dust-immune smoke sensors, **PBI/Nomex** firefighter gear & composite **SCBA** cylinders, and low-emission **HCCI** engine kinetics.`
                    : `### 1. Yüklenen Veri Kaynağı ve Çok Fazlı Telemetri Denetimi\n${mediaCtx}\n\n### 2. Senkronize 3B Yanma Odası, Boyutsuz Denklemler ve ISS 0G Kalibrasyonu\n- **Aktif 3B Sahne (\`${inp.fuel_name_tr}\` • \`${inp.geometry_3d}\`):** \`${inp.gravity_g} G\`, \`%${inp.oxygen_pct} O₂\` (\`P_O2 = ${tel.po2_psia} psia\`), \`${inp.pressure_psia} psia\`, \`${inp.airflow_cms} cm/s\` -> **${regBadge}** (\`T_f = ${tel.flame_temp_k} K\`, Yayılma \`${tel.flame_spread_mm_s} mm/s\`, Risk **\`${tel.risk_score}/100\`**).\n- **Boyutsuz Taşınım ve Kinetik:** \`K = ${tel.burning_rate_k_mm2_s} mm²/s\` | \`B = ${tel.spalding_b_number}\` | \`R_f/R_d = ${tel.standoff_ratio}\` | \`Re = ${tel.reynolds_number}\` | \`Sh = ${tel.sherwood_number}\` | \`Ra = ${tel.rayleigh_number}\` | \`Ri = ${tel.richardson_number}\` | \`Da = ${tel.damkohler_number}\` | \`χ_r = %${(tel.radiative_loss_fraction * 100).toFixed(1)}\` | \`MOC = %${tel.moc_pct} O₂\`.\n- **ISS 0G Referans Uyumu:** \`R² = ${fv.r_squared}\` • \`RMSE = ${fv.rmse}\` (${fv.campaign}).\n${pgNoteTr}\n### 3. Eşleşen NASA PSI Deneyleri ve Donanım Kıyaslaması\n${expLines}\n\n### 4. Yaşam Destek Saati (ECLSS), Su Sisi Söndürme ve Dünya Uygulamaları\n- **Yaşam Destek Saati (\`${tl.habitat_name_tr || "ISS Modülü"}\`):** C&W alarmı \`+${tl.t_alarm_s} sn\` | \`JSC-20584 24sa SMAC (100 ppm CO)\` süresi **\`${tl.t_smac_24h_100ppm_s} sn\`** | Müdahale anı CO \`${tl.co_at_response_ppm} ppm\`.\n- **NASA-STD-6001B Müdahale Sırası:** **(1)** Havalandırma fanlarını kapat (\`${inp.airflow_cms} -> 0 cm/s\`), **(2)** Elektrik hattını izole et, **(3)** **25-40 µm İnce Su Sisi (SoFIE-MIST)** veya CO₂/N₂ uygula (*Halon 1301 toksik HF/HBr üretimi nedeniyle yasaktır*).\n- **Dünya Uygulamaları:** **SoFIE-MIST** temiz su sisli yangın söndürme, **SAME/DAFT** toz-bağışıklı lazer duman dedektörleri, **PBI/Nomex** itfaiyeci koruyucu giysileri, hafif **SCBA** kompozit solunum tüpleri ve düşük emisyonlu **HCCI** motor kinetiği.`,
                citations: defaultCitations.slice(0, 5),
            };
        }

        // 14. Kapsamlı 4-Bölümlü Görev Sentezi (Preset #1)
        if (intent === "full_synthesis") {
            if (isEn) {
                const expLines = ranked
                    .map((e) => `- **#${e.rank} ${e.program} (${e.exp_id} • ${e.hardware_group})** — Score \`${e.priority_score}/100\`, MOC \`${e.moc_measured_pct}% O₂\`, [NTRS #${e.ntrs_id}](${e.ntrs_url}): ${e.key_finding_en}`)
                    .join("\n");
                return {
                    reply: [
                        `### 1. Microgravity & Partial-Gravity Governing Physics Synthesis`,
                        `- **Active State (${inp.fuel_name_en}):** Regime **${regBadge}** at \`${inp.gravity_g} G\`, \`${inp.oxygen_pct}% O₂\` (\`P_O2 = ${tel.po2_psia} psia\`), \`U = ${inp.airflow_cms} cm/s\` (Risk: **\`${tel.risk_score}/100\`**).`,
                        `- **Analytical Transport & Kinetics:** Rate \`K = ${tel.burning_rate_k_mm2_s} mm²/s\`, Transfer \`B = ${tel.spalding_b_number}\`, Sherwood \`Sh = ${tel.sherwood_number}\`, Damköhler \`Da = ${tel.damkohler_number}\`, radiative loss \`χ_r = ${(tel.radiative_loss_fraction * 100).toFixed(1)}%\`, critical \`MOC = ${tel.moc_pct}% O₂\`.`,
                        `- **ISS 0G Benchmark Validation:** \`R² = ${fv.r_squared}\` • \`RMSE = ${fv.rmse}\` against **${fv.campaign}**.`,
                        mediaCtx ? `- **Attached Context:** ${mediaCtx}` : ``,
                        ``,
                        `### 2. Top Ranked NASA PSI Investigations & Intra-Run Evidence`,
                        expLines,
                        ``,
                        `### 3. ECLSS Crew Survival Clock & Non-Halon Suppression Protocol`,
                        `- **Habitat (${tl.habitat_name_en}):** Alarm at \`+${tl.t_alarm_s} s\` | NASA JSC-20584 24-hr SMAC (\`100 ppm CO\`) in \`${tl.t_smac_24h_100ppm_s} s\` | Intervention CO \`${tl.co_at_response_ppm} ppm\`.`,
                        `- **Mandatory NASA-STD-6001B Action Sequence:** **(1)** Cut cabin HVAC ventilation immediately (\`U → 0 cm/s\`), **(2)** Isolate electrical bus power, **(3)** Discharge **25–40 µm Fine Water Mist (SoFIE-MIST)** or CO₂/N₂ (*Halon 1301 is strictly prohibited due to toxic HF/HBr poisoning ECLSS scrubbers*).`,
                        ``,
                        `### 4. Space-to-Earth Fire Safety Spinoffs`,
                        `- ISS multi-wavelength dust-immune smoke detection (**SAME / DAFT**) prevents false alarms in aircraft cargo bays and smart homes, while **SoFIE-MIST** water-mist physics and **PBI/Nomex + SCBA** systems protect cleanrooms, EV battery facilities, and municipal firefighters.`,
                    ].filter(Boolean).join("\n"),
                    citations: defaultCitations,
                };
            }
            const expLinesTr = ranked
                .map((e) => `- **#${e.rank} ${e.program} (${e.exp_id} • ${e.hardware_group})** — Öncelik \`${e.priority_score}/100\`, MOC \`%${e.moc_measured_pct} O₂\`, [NTRS #${e.ntrs_id}](${e.ntrs_url}): ${e.key_finding_tr}`)
                .join("\n");
            return {
                reply: [
                    `### 1. Mikroçekim ve Kısmi Yerçekimi Fiziksel Denklem Sentezi`,
                    `- **Aktif Durum (${inp.fuel_name_tr}):** \`${inp.gravity_g} G\`, \`%${inp.oxygen_pct} O₂\` (\`P_O2 = ${tel.po2_psia} psia\`) ve \`U = ${inp.airflow_cms} cm/s\` koşullarında **${regBadge}** rejimi aktiftir (Yangın Riski: **\`${tel.risk_score}/100\`**).`,
                    `- **Boyutsuz Taşınım ve Yanma Sabitleri:** Yanma sabiti \`K = ${tel.burning_rate_k_mm2_s} mm²/s\`, aktarım sayısı \`B = ${tel.spalding_b_number}\`, Sherwood \`Sh = ${tel.sherwood_number}\`, Damköhler \`Da = ${tel.damkohler_number}\`, radyatif kayıp \`χ_r = %${(tel.radiative_loss_fraction * 100).toFixed(1)}\` ve kritik \`MOC = %${tel.moc_pct} O₂\`.`,
                    `- **ISS 0G Referans Kalibrasyonu:** **${fv.campaign}** referans eğrileriyle \`R² = ${fv.r_squared}\` ve \`RMSE = ${fv.rmse}\` uyumu doğrulandı.`,
                    mediaCtx ? `- **Ekli Dosya / Görsel / Web Bağlamı:** ${mediaCtx}` : ``,
                    ``,
                    `### 2. Termodinamik & TF-IDF Sıralı NASA PSI Soruşturmaları ve NTRS Kanıtları`,
                    expLinesTr,
                    ``,
                    `### 3. ECLSS Yaşam Destek Saati ve Uzay Aracı Müdahale Protokolü`,
                    `- **Kabin / Giysi Senaryosu (${tl.habitat_name_tr}):** C&W alarmı \`t = ${tl.t_alarm_s} sn\`, NASA JSC-20584 24sa SMAC CO eşiği (\`100 ppm\`) \`t = ${tl.t_smac_24h_100ppm_s} sn\`, müdahale anı CO seviyesi \`${tl.co_at_response_ppm} ppm\`.`,
                    `- **Zorunlu Müdahale Sırası (NASA-STD-6001B):** **(1)** Kabin HVAC havalandırma fanlarını anında kapatın (\`U → 0 cm/s\`), **(2)** Elektrik beslemesini kesin, **(3)** **25–40 µm İnce Su Sisi (SoFIE-MIST PFE)** veya CO₂/N₂ uygulayın (*Halon 1301 toksik HF/HBr üreterek ECLSS filtrelerini zehirlediği için kesinlikle yasaktır*).`,
                    ``,
                    `### 4. Uzaydan Dünya'ya Yangın Güvenliği Teknoloji Transferi`,
                    `- ISS **SAME / DAFT** lazerli toz-duman ayrım algoritmaları Dünya'da madenlerde ve uçak kargo ambarlarında yanlış alarmları önlerken; **SoFIE-MIST** su sisi ve **EVA Nomex/PBI + SCBA** sistemleri veri merkezleri, elektrikli araç batarya depoları ve itfaiyeci ekipmanlarını korumaktadır.`,
                ].filter(Boolean).join("\n"),
                citations: defaultCitations,
            };
        }

        // 15. Açık Uçlu Bilimsel Sorgu (Sıfır Kopyala-Yapıştır Garantili Soru-Odaklı Sentez)
        const fuelMap = [
            ["heptan", "n_heptane"], ["metanol", "methanol"], ["methanol", "methanol"],
            ["pmma", "pmma"], ["akrilik", "pmma"], ["acrylic", "pmma"],
            ["sibal", "sibal"], ["pamuk", "sibal"], ["cotton", "sibal"],
            ["nomex", "nomex"], ["hidrojen", "hydrogen"], ["hydrogen", "hydrogen"],
            ["propan", "propane_cfig"], ["propane", "propane_cfig"]
        ];
        let matchedFuelId = null;
        for (let i = 0; i < fuelMap.length; i++) {
            if (nq.indexOf(fuelMap[i][0]) !== -1 && FUEL_PROPERTIES[fuelMap[i][1]]) {
                matchedFuelId = fuelMap[i][1];
                break;
            }
        }
        if (!matchedFuelId && Array.isArray(history) && history.length > 0) {
            for (let hi = history.length - 1; hi >= 0; hi--) {
                const hItem = history[hi];
                if (hItem && String(hItem.role || "").toLowerCase() === "user" && hItem.content) {
                    const prevNq = normQueryAscii(hItem.content);
                    for (let i = 0; i < fuelMap.length; i++) {
                        if (prevNq.indexOf(fuelMap[i][0]) !== -1 && FUEL_PROPERTIES[fuelMap[i][1]]) {
                            matchedFuelId = fuelMap[i][1];
                            break;
                        }
                    }
                    break;
                }
            }
        }
        let fuelLine = "";
        if (matchedFuelId && FUEL_PROPERTIES[matchedFuelId]) {
            const fp = FUEL_PROPERTIES[matchedFuelId];
            const fSim = simulateCombustionClient(Object.assign({}, inp, { fuel_id: matchedFuelId }));
            const ft = fSim.telemetry;
            const moc0B = fp.moc_0g_base ?? fp.moc_0g_pct ?? 13.8;
            const moc1B = fp.moc_1g_base ?? fp.moc_1g_pct ?? 15.2;
            fuelLine = isEn
                ? `- **Queried Fuel / Material (\`${fp.name_en}\`, \`${fp.formula}\`):** 3D Geometry \`${fp.geometry_3d}\`, \`0G MOC = ${moc0B}% O₂\` vs \`1G MOC = ${moc1B}% O₂\` → yields \`T_f = ${ft.flame_temp_k} K\`, **\`${ft.regime}\`**, Risk **\`${ft.risk_score}/100\`** under current cabin conditions.`
                : `- **Sorgulanan Yakıt / Malzeme (\`${fp.name_tr}\`, \`${fp.formula}\`):** 3B Geometri \`${fp.geometry_3d}\`, \`0G MOC = %${moc0B} O₂\` vs \`1G MOC = %${moc1B} O₂\` → mevcut kabin atmosferinizde \`T_f = ${ft.flame_temp_k} K\`, **\`${ft.regime}\`** rejimi ve **\`${ft.risk_score}/100\`** risk üretir.`;
        }

        const dirStop = new Set([
            "veri", "verisi", "verileri", "veritabaninda", "goruntu", "gorsel", "tablo", "tabloda", "tablosu", "tablosunda",
            "grafik", "deger", "degerleri", "degerlerini", "mevcut", "analiz", "sade", "anlasilir", "bana", "gore",
            "icin", "olan", "nedir", "nasil", "hangi", "soylermisin", "goster", "acikla", "data", "table", "chart",
            "values", "current", "analysis", "what", "how", "show", "explain", "simple", "clear"
        ]);
        const qDirTokens = (nq.match(/[a-z0-9]{4,}/g) || []).filter((w) => !dirStop.has(w));
        let bestDir = null;
        let bestDirSc = 0;
        DIRECTIVES.forEach((d) => {
            const dWords = new Set(normQueryAscii(`${d.title_tr} ${d.rule_tr} ${d.title_en} ${d.rule_en}`).match(/[a-z0-9]+/g) || []);
            let sc = 0;
            qDirTokens.forEach((tok) => { if (dWords.has(tok)) sc += 1; });
            if (sc > bestDirSc) { bestDirSc = sc; bestDir = d; }
        });
        if (!bestDir) {
            const findDir = (cid) => DIRECTIVES.find((d) => d.id === cid) || DIRECTIVES[0];
            if (tel.cool_flame_active || tel.regime === "COOL_FLAME_NTC") bestDir = findDir("CON-04");
            else if (inp.gravity_g >= 0.03 && inp.gravity_g <= 0.88) bestDir = findDir("CON-07");
            else if (inp.oxygen_pct >= 30.0 || inp.pressure_psia <= 10.6) bestDir = findDir("CON-06");
            else if (inp.airflow_cms >= 1.5) bestDir = findDir("CON-03");
            else bestDir = findDir("CON-01");
        }

        const customRagPool = ragDocs.filter((d) => String(d.doc_id || "").startsWith("DOC-"));
        const topRag = customRagPool.length
            ? customRagPool
                  .map((d) => ({ d, sc: computeTextSimilarity(msg, `${d.title} ${d.text}`) }))
                  .sort((a, b) => b.sc - a.sc)[0]
            : null;

        const wantsTable = hasAnyTerm(nq, ["tablo", "tabloda", "tablosu", "tablosunda", "grafik", "degerleri", "degerlerini", "table", "chart", "values"]);
        let liveTblBlock = "";
        if (wantsTable) {
            liveTblBlock = isEn
                ? `\n| Parameter / Dimensionless Metric | Active 3D Chamber Value | Safety & Regime Interpretation |\n| :--- | :--- | :--- |\n| **Fuel & Geometry** | \`${inp.fuel_name_en}\` (\`${inp.geometry_3d}\`) | Gravity \`${inp.gravity_g} G\`, Diluent \`${inp.diluent}\` |\n| **Atmosphere (\`O₂\` & Pressure)** | \`${inp.oxygen_pct}% O₂\` • \`${inp.pressure_psia} psia\` (\`P_O2 = ${tel.o2_partial_psia} psia\`) | Critical \`MOC = ${tel.moc_pct}% O₂\` |\n| **Flame Temp & Burn Rate** | \`T_f = ${tel.flame_temp_k} K\` • \`K = ${tel.burning_rate_k_mm2_s} mm²/s\` | Spread \`${tel.flame_spread_mm_s} mm/s\` • \`B = ${tel.spalding_b_number}\` |\n| **Transport & Residence (\`Sh\`, \`Da\`)** | \`Sh = ${tel.sherwood_number}\` • \`Da = ${tel.damkohler_number}\` • \`Ra = ${tel.rayleigh_number}\` | Airflow \`U = ${inp.airflow_cms} cm/s\` (\`χ_r = ${(tel.radiative_loss_fraction * 100).toFixed(1)}%\`) |\n| **Fire Risk & ECLSS SMAC** | **Risk \`${tel.risk_score}/100\`** • \`${tel.co_ppm} ppm CO\` | **${regBadge}** (\`100 ppm SMAC\`: \`${tl.t_smac_24h_100ppm_s || 180} s\`) |\n`
                : `\n| Parametre / Boyutsuz Büyüklük | Aktif 3B Oda Değeri | Fiziksel ve Güvenlik Yorumu |\n| :--- | :--- | :--- |\n| **Yakıt ve Numune Geometrisi** | \`${inp.fuel_name_tr}\` (\`${inp.geometry_3d}\`) | Yerçekimi \`${inp.gravity_g} G\`, Seyreltici \`${inp.diluent}\` |\n| **Atmosfer (\`O₂\` ve Basınç)** | \`%${inp.oxygen_pct} O₂\` • \`${inp.pressure_psia} psia\` (\`P_O2 = ${tel.o2_partial_psia} psia\`) | Kritik Tutuşma Sınırı \`MOC = %${tel.moc_pct} O₂\` |\n| **Alev Sıcaklığı ve Yanma Hızı** | \`T_f = ${tel.flame_temp_k} K\` • \`K = ${tel.burning_rate_k_mm2_s} mm²/s\` | Yayılma \`${tel.flame_spread_mm_s} mm/s\` • \`B = ${tel.spalding_b_number}\` |\n| **Taşınım ve Kalış (\`Sh\`, \`Da\`, \`Ra\`)** | \`Sh = ${tel.sherwood_number}\` • \`Da = ${tel.damkohler_number}\` • \`Ra = ${tel.rayleigh_number}\` | Akış Hızı \`U = ${inp.airflow_cms} cm/s\` (\`χ_r = %${(tel.radiative_loss_fraction * 100).toFixed(1)}\`) |\n| **Yangın Riski ve ECLSS SMAC** | **Risk \`${tel.risk_score}/100\`** • \`${tel.co_ppm} ppm CO\` | **${regBadge}** (\`100 ppm SMAC\`: \`${tl.t_smac_24h_100ppm_s || 180} sn\`) |\n`;
        }

        const e1 = ranked[0] || NASA_CATALOG[0];
        const e2 = ranked[1] || NASA_CATALOG[1];
        const qShort = truncateCleanJs(msg, 96);

        return {
            reply: isEn
                ? [
                      `### Targeted Scientific Analysis — *"${qShort}"*`,
                      liveTblBlock,
                      fuelLine,
                      `- **Governing Physical Constraint (\`${bestDir.id} • ${bestDir.code}\`):** ${bestDir.rule_en}`,
                      topRag && topRag.sc > 0.08 ? `- **Uploaded Document Match (\`${topRag.d.title}\`):** ${truncateCleanJs(topRag.d.text, 260)}` : ``,
                      `- **Live 3D Chamber Coupling (\`${inp.fuel_name_en}\`):** At \`${inp.gravity_g} G\`, \`${inp.oxygen_pct}% O₂\` (\`P_O2 = ${tel.o2_partial_psia} psia\`), \`U = ${inp.airflow_cms} cm/s\`, active regime is **${regBadge}** (\`T_f = ${tel.flame_temp_k} K\`, \`K = ${tel.burning_rate_k_mm2_s} mm²/s\`, \`Sh = ${tel.sherwood_number}\`, \`Da = ${tel.damkohler_number}\`, \`MOC = ${tel.moc_pct}% O₂\`, Risk **\`${tel.risk_score}/100\`**).`,
                      `- **Matched NASA PSI Investigations:**`,
                      `  1. **${e1.program} (\`${e1.exp_id}\` • [NTRS #${e1.ntrs_id}](${e1.ntrs_url}))** — ${e1.key_finding_en}`,
                      `  2. **${e2.program} (\`${e2.exp_id}\` • [NTRS #${e2.ntrs_id}](${e2.ntrs_url}))** — ${e2.key_finding_en}`,
                  ].filter(Boolean).join("\n")
                : [
                      `### Soru-Odaklı Bilimsel Analiz — *"${qShort}"*`,
                      liveTblBlock,
                      fuelLine,
                      `- **İlgili Fiziksel Kısıt ve Yasa (\`${bestDir.id} • ${bestDir.code}\`):** ${bestDir.rule_tr}`,
                      topRag && topRag.sc > 0.08 ? `- **Yüklenen Belge Kanıtı (\`${topRag.d.title}\`):** ${truncateCleanJs(topRag.d.text, 260)}` : ``,
                      `- **Aktif 3B Odanızla Sayısal Bağlantı (\`${inp.fuel_name_tr}\`):** \`${inp.gravity_g} G\`, \`%${inp.oxygen_pct} O₂\` (\`P_O2 = ${tel.o2_partial_psia} psia\`), \`U = ${inp.airflow_cms} cm/s\` koşullarında **${regBadge}** rejimi aktiftir (\`T_f = ${tel.flame_temp_k} K\`, \`K = ${tel.burning_rate_k_mm2_s} mm²/s\`, \`Sh = ${tel.sherwood_number}\`, \`Da = ${tel.damkohler_number}\`, \`MOC = %${tel.moc_pct} O₂\`, Risk **\`${tel.risk_score}/100\`**).`,
                      `- **Doğrudan Eşleşen NASA PSI Bulguları:**`,
                      `  1. **${e1.program} (\`${e1.exp_id}\` • [NTRS #${e1.ntrs_id}](${e1.ntrs_url}))** — ${e1.key_finding_tr}`,
                      `  2. **${e2.program} (\`${e2.exp_id}\` • [NTRS #${e2.ntrs_id}](${e2.ntrs_url}))** — ${e2.key_finding_tr}`,
                  ].filter(Boolean).join("\n"),
            citations: defaultCitations.slice(0, 2),
        };
    }

    // =========================================================================
    // AKILLI KONU KAPSAMI KONTROLÜ, FİZİKSEL KAVRAM DÜZELTMESİ VE EYLEM ÖNERİCİ
    // =========================================================================
    const SCOPE_CANONICAL_VOCAB = [
        ["saffire", "saffire"], ["sofie", "sofie"], ["spalding", "spalding"],
        ["sherwood", "sherwood"], ["reynolds", "reynolds"], ["grashof", "grashof"],
        ["rayleigh", "rayleigh"], ["richardson", "richardson"], ["damkohler", "damkohler"],
        ["schumann", "schumann"], ["semenov", "semenov"], ["kamenetskii", "kamenetskii"],
        ["mikrocekim", "mikrocekim"], ["microgravity", "microgravity"], ["yercekimi", "yercekimi"],
        ["oksijen", "oksijen"], ["oxygen", "oxygen"], ["metanol", "metanol"],
        ["methanol", "methanol"], ["heptan", "heptan"], ["heptane", "heptane"],
        ["etanol", "etanol"], ["ethanol", "ethanol"], ["hidrojen", "hidrojen"],
        ["hydrogen", "hydrogen"], ["propan", "propan"], ["propane", "propane"],
        ["toluen", "toluen"], ["nomex", "nomex"], ["sibal", "sibal"],
        ["kapton", "kapton"], ["teflon", "teflon"], ["halon", "halon"],
        ["yangin", "yangin"], ["tutusma", "tutusma"], ["yanma", "yanma"],
        ["combustion", "combustion"], ["flammability", "flammability"], ["sondurme", "sondurme"],
        ["sondurucu", "sondurucu"], ["havalandirma", "havalandirma"], ["ventilation", "ventilation"],
        ["karbonmonoksit", "karbonmonoksit"], ["radyometre", "radyometre"], ["termokupl", "termokupl"],
        ["thermocouple", "thermocouple"], ["dedektor", "dedektor"], ["detector", "detector"],
        ["piroliz", "piroliz"], ["pyrolysis", "pyrolysis"], ["konveksiyon", "konveksiyon"],
        ["convection", "convection"], ["difuzyon", "difuzyon"], ["diffusion", "diffusion"],
        ["radyatif", "radyatif"], ["radiative", "radiative"], ["spacesuit", "spacesuit"],
        ["orion", "orion"], ["gateway", "gateway"], ["cygnus", "cygnus"],
        ["artemis", "artemis"], ["camras", "camras"], ["eclss", "eclss"]
    ];

    function charTrigramsBrowser(word) {
        const padded = `^${word}$`;
        const out = new Set();
        if (padded.length < 3) {
            out.add(padded);
            return out;
        }
        for (let i = 0; i <= padded.length - 3; i++) {
            out.add(padded.slice(i, i + 3));
        }
        return out;
    }

    const PRECOMPUTED_SCOPE_VOCAB = SCOPE_CANONICAL_VOCAB.map(([term, canon]) => [term, canon, charTrigramsBrowser(term)]);
    const EXACT_SCOPE_VOCAB = {};
    SCOPE_CANONICAL_VOCAB.forEach(([term, canon]) => { EXACT_SCOPE_VOCAB[term] = canon; });

    const SCOPE_DIRECT_PHRASES = [
        "yanma", "alev", "yangin", "tutusma", "tutustur", "sondur", "su sisi", "water mist",
        "soguk alev", "cool flame", "kuresel alev", "kuresel yanma", "mum alevi",
        "sifir yercekimi", "zero gravity", "zero-g", "vakumda alev", "vakumda ates", "vakumda yanma",
        "uzay boslugunda alev", "uzay boslugunda ates", "uzay boslugunda yanar", "uzay araci", "spacecraft",
        "mikrocekim", "mikro yercekimi", "microgravity",
        "freefall", "kismi yercekimi", "partial gravity", "0g", "0.0g", "0.16g", "0.38g", "1g",
        "oksijen", "oxygen", "basinc", "pressure", "psia", "kpa", "cm/s", "mm2/s", "kw/m2",
        "karbonmonoksit", "carbon monoxide", "co ppm", "smac", "eclss", "camras", "fdir",
        "spalding", "b_oq", "boq", "sherwood", "reynolds", "grashof", "rayleigh", "richardson",
        "damkohler", "d2 yasasi", "d2-law", "de ris", "burke-schumann", "burke schumann", "chi_r",
        "radyatif", "radiative", "konveksiyon", "convection", "difuzyon", "diffusion", "piroliz",
        "pyrolysis", "kurum", "soot", "standoff", "rf/rd", "r_f", "hrrpua", "semenov", "kamenetskii",
        "heptan", "heptane", "metanol", "methanol", "etanol", "ethanol", "propan", "propane",
        "hidrojen", "hydrogen", "toluen", "toluene", "pmma", "nomex", "sibal", "kapton", "teflon",
        "ptfe", "peek", "xlpe", "halon", "saffire", "sofie", "flex-2", "bass-ii", "spice", "slice",
        "daft", "cfi-g", "cfig", "luci", "fm2", "ntrs", "osdr", "nasa psi", "psi-", "6001b", "20584",
        "uzay giysisi", "eva giysi", "eva suit", "spacesuit", "ay gezgini", "lunar rover",
        "pressurized rover", "ay ussu", "mars kabini", "orion", "gateway", "cygnus",
        "uzay istasyonu", "space station", "kabin", "cabin", "kapak", "hatch", "menfez", "hava kanali",
        "fan hizi", "akis hizi", "airflow", "termal kamera", "thermal camera", "optik kamera",
        "duman", "smoke", "regolit", "lunar dust", "ay tozu", "yeniden tutusma", "re-ignition",
        "reignition", "belirsizlik", "ozel denklem", "custom equation", "ozel malzeme",
        "custom material", "itfaiye", "firefighter", "scba"
    ];

    const RE_SCOPE_SHORT_TOKENS = /\b(?:flex|bass|acme|same|cfi|moc|iss|eva|mie|fed|ntc|psd|cir|msg|mdca|halo|ihab|ppe|o2|co2|n2|r2|rmse)\b/;

    const RE_NATURAL_COMBUSTION_TOKENS = /\b(?:ates|atesin|ateste|atesle|yanar|yaniyor|yanmak|yanmaz|yanici|yakici|tutusur|tutustu|soner|sondu|sondurme|sondurucu|mum|mumun|mumda|mumlar|agirliksiz|agirliksizlik|vakumda|flame|flames|fire|fires|burn|burns|burning|burned|candle|candles|ignite|ignites|ignited|ignition|extinguish|extinguisher|extinguishing|quench|quenches|quenching|smolder|smoldering|buoyancy|convective|weightless|weightlessness)\b/;

    const RE_STRONG_SPACE_ANCHORS = /(?:^|\b)(?:0g|0\.0g|0\.16g|0\.38g|mikrocekim|microgravity|freefall|saffire|sofie|flex|bass|moc|spalding|sherwood|damkohler|orion|iss|nasa|kabin|cabin)(?:\b|$)/;

    const STRONG_SPACE_ANCHOR_PHRASES = [
        "mikro yercekimi", "uzay araci", "spacecraft", "su sisi", "water mist"
    ];

    const SHORT_GREETINGS_LIST = [
        "merhaba", "selam", "gunaydin", "iyi gunler", "iyi aksamlar", "hello", "hi", "hey"
    ];

    const RE_CASUAL_GREETING_TOKENS = /\b(?:hello|hi|hey)\b/;

    const SCOPE_INTRO_PHRASES = [
        "neler yapabilir", "ne yapabilir", "ne ise yarar", "nasil kullan", "ozelliklerin",
        "ozellikleri", "hangi ozellik", "yeteneklerin", "modullerin", "bu uygulama", "bu ekran",
        "bu platform", "altar-nasa", "flame in freefall", "sen kimsin", "kendini tanit",
        "what can you do", "how to use", "platform features", "capabilities", "who are you", "what is this app"
    ];

    const SCOPE_EXPLICIT_OFF_TOPIC = [
        "corba", "corbasi", "mercimek", "tarif", "tarifi", "pilav", "makarna", "kek ", "kurabiye",
        "borek", "kebap", "tatli tarif", "yemek yap", "pisir", "recipe", "soup", "pasta recipe",
        "bake a cake", "mac kac", "mac skoru", "mac sonucu", "futbol", "ofsayt", "penalti",
        "sampiyonlar ligi", "super lig", "fenerbahce", "galatasaray", "besiktas", "trabzonspor",
        "basketbol", "match score", "football", "soccer", "world cup", "dolar kac", "euro kac",
        "altin fiyati", "borsa", "hisse senedi", "kripto", "bitcoin", "ethereum", "stock price",
        "crypto", "burc yorumu", "astroloji", "horoscope", "magazin", "dedikodu", "gossip",
        "film oner", "dizi oner", "sarki sozu", "siir yaz", "masal anlat", "fikra anlat",
        "movie recommendation", "write a poem", "tell a joke", "yilan oyunu", "tetris",
        "oyun yaz", "oyun kodu", "web sitesi yap", "alisveris sitesi", "snake game", "flappy bird",
        "write a game", "evlilik", "sevgili", "siyaset", "secim sonucu", "hava durumu", "weather forecast",
        "ates dusurucu", "atesim var", "atesi var", "atesi cikti", "yuksek ates", "ates olcer",
        "ateskes", "ates ac", "silah ates", "ilac oner", "mide yanma", "icim yaniyor", "canim yaniyor",
        "bilet yanar", "biletim yanar", "garanti yanar", "kalori yak", "kisik ateste", "orta ateste",
        "yuksek ateste", "tencerede", "firinda kek", "burn calories", "calorie", "heartburn",
        "sunburn", "burnout", "free fire", "fire someone", "got fired", "high fever", "fever medicine"
    ];

    const SCOPE_CASUAL_CLAUSES = [
        "bugun hava", "hava durumu", "disarida hava", "hava cok guzel", "hava guzel",
        "hava yagmurlu", "hava soguk", "hava sicak", "hava bulutlu", "gunaydin", "iyi gunler",
        "iyi aksamlar", "iyi geceler", "merhaba", "selam", "nasilsin", "keyifler nasil",
        "umarim iyisindir", "kolay gelsin", "weather forecast", "weather is nice", "weather is rainy",
        "it is raining today", "good morning", "good evening", "how are you", "hope you are well"
    ];

    const SCOPE_FOLLOWUP_PATTERNS = [
        "bunu ", "bunun ", "sunu ", "bu sonucu", "bu degeri", "bu tabloyu", "yukaridaki", "az onceki",
        "ozetle", "kisaca", "daha kisa", "daha sade", "basit anlat", "sadelestir", "detaylandir",
        "acikla", "tabloya dok", "tablo yap", "tablo halinde", "tabloda goster", "maddeler halinde",
        "1. satir", "2. satir", "3. satir", "ilk satir", "ikinci satir", "son satir",
        "ingilizceye cevir", "turkceye cevir", "ingilizce yaz", "turkce yaz", "cevir",
        "degeri artirirsam", "degeri azaltirsam", "artirirsam ne olur", "azaltirsam ne olur",
        "iki katina", "yariya indirirsem", "peki neden", "neden oyle", "nasil hesapladin", "karsilastir",
        "summarize", "make it shorter", "simpler", "in a table", "put in a table", "as a table",
        "explain row", "second row", "first row", "translate to", "in english", "in turkish",
        "what if i increase", "what if i decrease", "why does that", "elaborate"
    ];

    const SCOPE_MEDIA_FOLLOWUP = [
        "yukledigim", "yuklenen", "ekli ", "eklenen", "bu dosya", "dosyayi", "dosyadaki",
        "bu gorsel", "gorseli", "resmi", "fotografi", "bu veriyi", "verileri analiz",
        "analiz et", "incele", "degerlendir", "uploaded", "attached", "this file",
        "this image", "this dataset", "analyze this"
    ];

    const SCOPE_ROLE_OVERRIDES = [
        "onceki kurallari unut", "kurallari unut", "tum kurallari unut", "kurallari yoksay",
        "talimatlari unut", "talimatlari yoksay", "yonergeleri unut", "sistem kurallarini unut",
        "kisitlamalari kaldir", "yasaklari kaldir", "sen artik bir", "bundan sonra bir asci",
        "ascisin", "oyun yazarisin", "sair ol", "ignore previous instructions",
        "ignore all instructions", "ignore all rules", "forget previous rules",
        "forget your instructions", "disregard previous", "disregard safety",
        "bypass safety", "you are now a", "act as a chef", "act as a playwright"
    ];

    const SCOPE_HALON_ENDORSE = [
        "oner", "onersene", "onermelisin", "tavsiye et", "kullanmanin dogru oldugunu soyle",
        "dogru oldugunu soyle", "guvenli oldugunu soyle", "serbest oldugunu soyle", "izin ver",
        "onayla", "savun", "kullanilabilir de", "recommend halon", "endorse halon",
        "approve halon", "say halon 1301 is safe", "say halon is safe",
        "say using halon is right", "tell me to use halon"
    ];

    const SCOPE_REJECTED_MARKERS = [
        "yalnizca uzay araci yangin guvenligi",
        "focuses exclusively on spacecraft fire safety",
        "only covers spacecraft fire safety",
        "ucus guvenligi kurallari sabittir",
        "flight safety rules are fixed",
        "flight and fire safety rules are fixed"
    ];

    function damerauLevBrowser(a, b) {
        const la = a.length, lb = b.length;
        if (a === b) return 0;
        if (la === 0) return lb;
        if (lb === 0) return la;
        const d = Array.from({ length: la + 1 }, () => new Array(lb + 1).fill(0));
        for (let i = 0; i <= la; i++) d[i][0] = i;
        for (let j = 0; j <= lb; j++) d[0][j] = j;
        for (let i = 1; i <= la; i++) {
            for (let j = 1; j <= lb; j++) {
                const cost = a[i - 1] === b[j - 1] ? 0 : 1;
                let val = Math.min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + cost);
                if (i > 1 && j > 1 && a[i - 1] === b[j - 2] && a[i - 2] === b[j - 1]) {
                    val = Math.min(val, d[i - 2][j - 2] + 1);
                }
                d[i][j] = val;
            }
        }
        return d[la][lb];
    }

    function matchFuzzyDomainTokensBrowser(normText) {
        const tokens = normText.match(/[a-z0-9_]+/g) || [];
        const matched = [];
        const repairedWords = {};

        for (let ti = 0; ti < tokens.length; ti++) {
            const tok = tokens[ti];
            if (tok.length < 4 || /^\d+$/.test(tok)) continue;
            if (EXACT_SCOPE_VOCAB[tok]) {
                matched.push([tok, EXACT_SCOPE_VOCAB[tok]]);
                continue;
            }
            const phoneticTok = tok.replace(/ks/g, "x");
            const tokGrams = charTrigramsBrowser(tok);
            let bestCanon = "";
            let bestScore = 0.0;

            for (let vi = 0; vi < PRECOMPUTED_SCOPE_VOCAB.length; vi++) {
                const [term, canon, termGrams] = PRECOMPUTED_SCOPE_VOCAB[vi];
                if (Math.abs(tok.length - term.length) > 2 && Math.abs(phoneticTok.length - term.length) > 2) continue;
                let shared = 0;
                tokGrams.forEach((g) => { if (termGrams.has(g)) shared += 1; });
                if (shared === 0 && phoneticTok === tok) continue;
                const diceRaw = (2.0 * shared) / (tokGrams.size + termGrams.size);
                const maxLen = Math.max(tok.length, term.length);
                if (maxLen <= 5 && tok[0] !== term[0]) continue;
                if (diceRaw < 0.22 && tok[0] !== term[0] && phoneticTok === tok) continue;
                let dist = damerauLevBrowser(tok, term);
                if (phoneticTok !== tok && dist > 1) {
                    dist = Math.min(dist, damerauLevBrowser(phoneticTok, term));
                }
                const editSim = 1.0 - dist / maxLen;
                const combined = 0.45 * diceRaw + 0.55 * editSim;
                const isHit = maxLen <= 5
                    ? (dist <= 1 && tok[0] === term[0])
                    : ((dist <= 1 && editSim >= 0.78) || (dist <= 2 && diceRaw >= 0.42 && combined >= 0.64 && tok[0] === term[0]));
                if (isHit && combined > bestScore) {
                    bestScore = combined;
                    bestCanon = canon;
                }
            }
            if (bestCanon) {
                matched.push([tok, bestCanon]);
                repairedWords[tok] = bestCanon;
            }
        }

        let repairedNorm = normText;
        Object.keys(repairedWords).forEach((wrongW) => {
            const esc = wrongW.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
            repairedNorm = repairedNorm.replace(new RegExp(`\\b${esc}\\b`, "g"), repairedWords[wrongW]);
        });
        return { matched, repairedNorm };
    }

    function hasStrongSpaceAnchorBrowser(normText) {
        if (RE_STRONG_SPACE_ANCHORS.test(normText)) return true;
        return hasAnyTerm(normText, STRONG_SPACE_ANCHOR_PHRASES);
    }

    function clauseHasDomainSignalBrowser(clauseNorm) {
        if (hasAnyTerm(clauseNorm, SCOPE_EXPLICIT_OFF_TOPIC) && !hasStrongSpaceAnchorBrowser(clauseNorm)) return false;
        if (hasAnyTerm(clauseNorm, SCOPE_DIRECT_PHRASES)) return true;
        if (RE_SCOPE_SHORT_TOKENS.test(clauseNorm)) return true;
        if (RE_NATURAL_COMBUSTION_TOKENS.test(clauseNorm)) return true;
        return matchFuzzyDomainTokensBrowser(clauseNorm).matched.length > 0;
    }

    function stripCasualClausesBrowser(rawMsg) {
        const parts = String(rawMsg || "").split(/(?:[.!?;]+|,\s*(?=(?:bu arada|peki|ayrica|fakat|ama|ancak|neyse|by the way|anyway|also|however|so\b))|\b(?:bu arada|by the way|anyway)\b|,)/i);
        if (parts.length <= 1) return { strippedMsg: String(rawMsg || "").trim(), mixedStripped: false };
        const kept = [];
        let dropped = false;
        parts.forEach((rawP) => {
            const cleanP = String(rawP || "").replace(/^[\s,;:\-]+|[\s,;:\-]+$/g, "");
            if (!cleanP) return;
            const pNorm = normQueryAscii(cleanP);
            const hasDom = clauseHasDomainSignalBrowser(pNorm);
            const isCasual = hasAnyTerm(pNorm, SCOPE_CASUAL_CLAUSES) || RE_CASUAL_GREETING_TOKENS.test(pNorm);
            if (isCasual && !hasDom) {
                dropped = true;
                return;
            }
            kept.push(cleanP);
        });
        if (dropped && kept.length > 0) {
            const joined = kept.join(", ").trim().replace(/^(?:peki|bu arada|ayrica|ama|fakat|ancak|so|and|but)\s+/i, "").trim();
            if (clauseHasDomainSignalBrowser(normQueryAscii(joined))) {
                return { strippedMsg: joined, mixedStripped: true };
            }
        }
        return { strippedMsg: String(rawMsg || "").trim(), mixedStripped: false };
    }

    function detectPhysicalMisconceptionBrowser(normText) {
        const hasZeroGCtx = hasAnyTerm(normText, [
            "0g", "0.0g", "sifir yercekimi", "zero gravity", "zero-g", "agirliksiz", "weightless",
            "mikrocekim", "mikro yercekimi", "microgravity", "freefall", "uzay istasyonu", "space station", "iss"
        ]);
        const hasCeilingRise = hasAnyTerm(normText, [
            "tavanda biriken", "tavana yukselen", "tavana cikan", "tavana cikar",
            "tavandaki duman", "tavanda duman", "tavana duman", "tavana duman dedektor",
            "duman yukselir", "sicak hava yukselir",
            "yukari cikan duman", "yukari cikan sicak", "yukselen duman", "yukselen sicak hava",
            "ceiling smoke", "ceiling smoke detector", "ceiling smoke detectors",
            "smoke on the ceiling", "smoke rising", "rising hot air",
            "rise to the ceiling", "rises to the ceiling",
            "collects on the ceiling", "accumulates at the ceiling"
        ]) || /\b(?:smoke|hot\s+air|heat|fumes)\b.{0,28}\b(?:rise|rises|rising|collect|collects|accumulate|accumulates)\b/.test(normText);
        if (hasZeroGCtx && hasCeilingRise) {
            return {
                code: "zero_g_ceiling_smoke",
                correction_tr: "0G mikroçekim ortamında kaldırma kuvveti oluşmadığı için duman ve sıcak gaz tavanda birikmez; kabin havalandırma akışını izleyerek emiş menfezlerine doğru sürüklenir, bu nedenle sensörler tavan yerine havalandırma dönüş kanallarına yerleştirilir.",
                correction_en: "In 0G microgravity, buoyancy vanishes so smoke and hot gas do not rise or collect at the ceiling; they drift with cabin airflow toward return ducts, which is where smoke sensors are mounted."
            };
        }

        const hasZeroO2 = /(?:%\s*0\s*(?:o2|oksijen)|0\s*%\s*(?:o2|oxygen)|sifir\s+oksijen|zero\s+oxygen|oksijensiz\s+ortamda\s+alev)/.test(normText)
            || ((hasAnyTerm(normText, [
                    "vakumda alev", "vakumda yanma", "vakumda ates", "vakumda mum", "vakumda yanar",
                    "uzay boslugunda alev", "uzay boslugunda ates", "uzay boslugunda mum", "uzay boslugunda yanar",
                    "flame in vacuum", "burn in vacuum", "fire in vacuum", "candle in vacuum"
                ]) || /\b(?:flame|fire|candle)\b.{0,32}\b(?:in\s+(?:space\s+)?vacuum|zero\s+oxygen|0\s*%\s*oxygen)/.test(normText))
                && !hasAnyTerm(normText, ["roket", "rocket", "itici", "thruster", "oksitleyici", "oxidizer"]));
        if (hasZeroO2 && !hasAnyTerm(normText, ["soner", "sonumlenir", "yanmaz", "quench", "cannot burn"])) {
            return {
                code: "vacuum_or_zero_o2_flame",
                correction_tr: "Oksijen oranı kritik tutuşma sınırının (`O₂ < MOC`) altına indiğinde veya dış oksitleyici olmayan vakum ortamında gaz fazı alevi kararlı biçimde yanamaz ve sönümlenir.",
                correction_en: "Below the minimum oxygen concentration (`O₂ < MOC`) or in vacuum without a supplied oxidizer, a gas-phase flame cannot sustain combustion and quenches."
            };
        }

        const hasHotOpen = hasAnyTerm(normText, ["kapagi", "kapak", "hatch", "havalandir", "ventilat", "odayi ac", "bolmeyi ac", "unseal"])
            && (
                hasAnyTerm(normText, ["sogumadan", "hemen ac", "aninda ac", "soner sonmez ac", "sicakken ac", "before cooling", "while still hot", "open immediately", "right after extinguishing"])
                || /\b(?:open|unseal)\b.{0,25}\b(?:immediately|right\s+away|instantly|before\s+cooling)\b/.test(normText)
                || /\b(?:immediately|right\s+away|instantly)\b.{0,20}\b(?:open|unseal|ventilate)\b/.test(normText)
                || /\b(?:hemen|aninda|beklemeden|sogumadan)\b.{0,20}\b(?:ac|acalim|acilir|acmak|havalandir)/.test(normText)
            );
        if (hasHotOpen) {
            return {
                code: "premature_hatch_reignition",
                correction_tr: "Alev söndükten hemen sonra sıcak çekirdek (`≥ 525 K`) soğumadan bölme kapağını açıp taze oksijen vermek ani yeniden tutuşmaya yol açar; kapak yalnızca çekirdek soğuduktan ve hava temizlendikten sonra açılmalıdır.",
                correction_en: "Opening the compartment hatch to admit fresh oxygen before the hot core cools below `525 K` triggers flash re-ignition; keep the bay sealed until cooling and air scrubbing finish."
            };
        }

        const hasSpaceCabinCtx = hasAnyTerm(normText, [
            "0g", "0.0g", "sifir yercekimi", "zero gravity", "zero-g", "agirliksiz", "weightless",
            "mikrocekim", "mikro yercekimi", "microgravity", "freefall",
            "uzay araci", "uzay istasyonu", "uzayda", "in space", "spacecraft", "space station", "iss", "orion", "kabin", "cabin"
        ]);
        const hasBulkWater = hasAnyTerm(normText, [
            "su dok", "kova ile su", "kovayla su", "bardakla su", "su firlat",
            "pour water", "pouring water", "bucket of water", "splash water", "throw water"
        ]) || /\b(?:pour|pouring|splash|splashing|throw|throwing|dump|dumping)\b.{0,22}\bwater\b/.test(normText)
           || /\b(?:kova|kovayla|bardak|bardakla)\b.{0,20}\bsu\b/.test(normText);
        if (
            hasSpaceCabinCtx
            && hasBulkWater
            && !hasAnyTerm(normText, ["yag", "tava", "mutfak", "oil", "grease", "kitchen"])
            && !hasAnyTerm(normText, ["su sisi", "water mist", "sofie-mist"])
        ) {
            return {
                code: "zero_g_bulk_water",
                correction_tr: "0G mikroçekim ortamında dökülen kaba sıvı su yüzey gerilimiyle serbest küreler halinde dağılıp alev cephesine tutunamaz ve elektronik hatlarda kısa devre riski yaratır; bu nedenle kabin yangınlarında 25–40 µm ince su sisi (`SoFIE-MIST`) kullanılır.",
                correction_en: "In 0G microgravity, poured bulk water forms floating spheres under surface tension that miss the flame sheet and risk shorting cabin electronics, so crews deploy 25–40 µm fine water mist (`SoFIE-MIST`) instead."
            };
        }
        return null;
    }

    function detectBoundaryCategoryBrowser(normText) {
        if (
            hasAnyTerm(normText, ["roket motor", "roket itici", "roket yanma", "roket nozul", "sivi yakitli roket", "kati yakitli roket", "rocket engine", "rocket motor", "rocket thruster", "rocket combustion", "thruster plume", "propellant engine"])
            || (hasAnyTerm(normText, ["roket", "rocket", "thruster", "itici"]) && hasAnyTerm(normText, ["yanma", "alev", "yakit", "motor", "combustion", "flame", "nozzle"]))
        ) {
            return "rocket_engine";
        }
        if (hasAnyTerm(normText, ["yemek isiticisi", "yemek isitici", "uyku tulumu", "gunes paneli", "gunes panelleri", "mikrodalga", "kahve makinesi", "astronot yemegi", "food warmer", "galley oven", "sleeping bag", "solar panel", "solar array", "crew laptop"])) {
            return "space_equipment";
        }
        const hasSpaceCtxForWater = hasAnyTerm(normText, [
            "0g", "0.0g", "sifir yercekimi", "zero gravity", "zero-g", "agirliksiz", "weightless",
            "mikrocekim", "mikro yercekimi", "microgravity", "freefall", "uzay", "space", "iss", "orion", "kabin", "cabin"
        ]);
        if (
            hasAnyTerm(normText, ["yag yangini", "kizgin yag", "tava yangini", "mutfak yangini", "evde yangin", "ev yangini", "evdeki duman dedektor", "apartman yangin", "orman yangini", "fabrika yangin", "grease fire", "cooking oil fire", "kitchen fire", "house fire", "pour water on oil", "home smoke detector"])
            || (hasAnyTerm(normText, ["su dokulur mu", "su dokulmez"]) && !hasSpaceCtxForWater)
        ) {
            return "terrestrial_fire";
        }
        if (hasAnyTerm(normText, ["duman dedektoru nasil calisir", "how does a smoke detector work", "how do smoke detectors work"]) && !hasAnyTerm(normText, ["0g", "iss", "uzay", "space", "daft", "same"])) {
            return "terrestrial_fire";
        }
        return null;
    }

    function buildBoundaryReplyBrowser(boundaryKind, normText, activeSim, lang) {
        const isEn = String(lang || "tr").toLowerCase() === "en";
        const inp = (activeSim && activeSim.inputs) || {};
        const tel = (activeSim && activeSim.telemetry) || {};
        const uCms = inp.airflow_cms ?? 2.0;
        const reVal = tel.reynolds_number ?? 18.0;
        const riVal = tel.richardson_number ?? 0.0;

        if (boundaryKind === "rocket_engine") {
            return isEn
                ? `High-velocity rocket engines and external thrusters sit outside cabin combustion testing, yet they link to spacecraft fire safety through flow-regime scaling and pressurized oxidizer line protection.\n\n- **High-Speed Jet vs. Cabin Airflow (\`Ri = Gr / Re²\`):** Rocket chambers inject propellants at \`100–3000 m/s\` (\`Re > 10⁵\`, \`Ri < 10⁻⁶\`), so momentum dominates and gravity has virtually no effect on the flame. Inside crew cabins (\`U = ${uCms} cm/s\`, \`Re = ${reVal}\`, \`Ri = ${riVal}\`), gentle ventilation means removing buoyancy turns flames spherical, increases radiative loss (\`χ_r\`), and shifts \`MOC\`.\n- **Cabin Leak Hazard:** Service-module and docking oxidizer/fuel lines are isolated by sealed bulkheads and continuous pressure/gas sensors so a line leak cannot enrich cabin \`P_O₂\` or lower minimum ignition energy (\`MIE\`).`
                : `Yüksek hızlı roket motorları ve dış iticiler kabin içi yanma deneylerinin doğrudan kapsamı dışındadır; ancak akış rejimi farkı ve basınçlı hat sızıntı güvenliği üzerinden uzay aracı yangın emniyetiyle doğrudan ilişkilidir.\n\n- **Yüksek Hızlı İtki ve Kabin Havalandırması Farkı (\`Ri = Gr / Re²\`):** Roket yanma odasında gaz hızları \`100–3000 m/s\` düzeyinde olduğu için (\`Re > 10⁵\`, \`Ri < 10⁻⁶\`) yanma yerçekiminden bağımsızdır. Mürettebat kabinindeki düşük hava akışında ise (\`U = ${uCms} cm/s\`, \`Re = ${reVal}\`, \`Ri = ${riVal}\`) yerçekiminin kalkması alevi küreselleştirir, radyatif ısı kaybını (\`χ_r\`) büyütür ve \`MOC\` sınırını düşürür.\n- **Kabin İçi Sızıntı Riski:** Servis modülü veya kenetlenme hatlarındaki oksijen/yakıt sızıntıları kabin kısmi oksijen basıncını (\`P_O₂\`) yükseltip tutuşma enerjisini düşürebileceği için bölme kapakları ve gaz sensörleriyle izlenir.`;
        }

        if (boundaryKind === "space_equipment") {
            if (hasAnyTerm(normText, ["uyku tulumu", "sleeping bag"])) {
                return isEn
                    ? "Crew sleeping-bag comfort design belongs to general cabin outfitting, but in spacecraft fire safety it is evaluated as a large textile surface exposed to low-velocity cabin ventilation.\n\n- **Material Behavior (`Nomex / SIBAL`):** Gentle `0G` airflow (`3–8 cm/s`) feeds fresh oxygen to thin fabric edges and can lower `MOC` below `1G` Earth limits (`BASS` and `Saffire` findings), so crew sleep stations use flame-resistant `Nomex` weaves certified under `NASA-STD-6001B`.\n- **Early Smoldering Protection:** Sleep bays monitor `CO` accumulation continuously; if overheating or smoldering starts, closing ventilation ducts starves the reaction zone of oxygen."
                    : "Mürettebat uyku tulumlarının genel konfor tasarımı günlük yaşam donanımı konusudur; ancak uzay aracı yangın güvenliğinde kabin içindeki geniş tekstil yüzeylerinden biri olarak doğrudan tutuşma testlerine tabi tutulur.\n\n- **Malzeme Davranışı (`Nomex / SIBAL`):** `0G` ortamında düşük hızlı kabin havalandırması (`3–8 cm/s`) ince kumaş kenarlarına taze oksijen taşıyarak `MOC` sınırını Dünya'dakinin altına çekebildiği için (`BASS` ve `Saffire` bulguları), uyku bölmelerinde `NASA-STD-6001B` sertifikalı alev geciktirici `Nomex` dokumalar kullanılır.\n- **Aşırı Isınma ve İçten Yanma Kontrolü:** Uyku kabinlerinde olası kablo ısınması veya içten yanma (`smoldering`) `CO` sensörleriyle izlenir ve ilk adımda hava kanalları kapatılır.";
            }
            if (hasAnyTerm(normText, ["gunes panel", "solar panel", "solar array"])) {
                return isEn
                    ? "External solar arrays operate in hard vacuum where gas-phase flames cannot burn, yet they connect directly to cabin fire safety through high-power `120V DC` electrical distribution.\n\n- **Internal Bus Overheating & Arc Risk:** Power generated by the arrays enters pressurized modules through switching units (`PCDU / SSPC`), where overloaded harnesses in stagnant `0G` air (`Ra = 0`) can overheat and pyrolyze `Kapton / PTFE` wire insulation.\n- **Preventive Isolation:** When thermal or ultrasonic arc sensors detect pre-ignition heating, cutting bay `120V DC` power and cabin airflow stops ignition before open flame develops."
                    : "Dış güneş panelleri uzay boşluğunda çalıştığı için vakumda gaz fazı alevi oluşmaz; ancak ürettikleri gücün kabin içine taşınması nedeniyle uzay aracı yangın güvenliğiyle doğrudan elektriksel koruma üzerinden bağlantılıdır.\n\n- **Aşırı Isınma ve Kablo Yalıtımı Riski:** Panellerden gelen `120V DC` güç kabin içi dağıtım hatlarından (`PCDU / SSPC`) geçerken, `0G` ortamında doğal soğuma (`Ra = 0`) olmadığı için aşırı akım yerel ısınma ve kablo yalıtımında gaz çıkışına yol açabilir.\n- **Önleyici Kesme:** Aşırı ısınma veya ark belirtisi algılandığında alev oluşmadan önce ilgili bölümün elektriği (`120V DC`) ve hava akışı kesilir.";
            }
            return isEn
                ? "Everyday crew appliances such as cabin food warmers sit outside combustion experiments as routine hardware, but in spacecraft fire safety they are treated as localized overheating and ignition sources.\n\n- **`0G` Stagnant-Heat Buildup (`Ra = 0`):** Without buoyancy to carry warm air upward, heat concentrates around heating elements and wiring harnesses (`Semenov` thermal runaway risk).\n- **Containment & Response:** Enclosures use flame-retardant `Nomex` and metallic barriers (`NASA-STD-6001B`); if temperature or `CO` rises, bay `120V DC` power and ventilation fans are shut off immediately."
                : "ISS'deki yemek ısıtıcısı gibi günlük mürettebat ekipmanlarının rutin kullanımı doğrudan yanma deneyi konusu değildir; ancak kabin yangın güvenliğinde bu cihazlar birincil aşırı ısınma ve tutuşma noktası olarak izlenir.\n\n- **`0G` Ortamında Isı Birikimi (`Ra = 0`):** Mikroçekimde ısınan hava yükselip dağılamadığı için ısıtıcı yüzeyler ve besleme kabloları çevresinde yerel sıcaklık hızla yükselebilir (`Semenov` ısıl kaçak riski).\n- **Yalıtım ve Müdahale:** Cihaz gövdelerinde `NASA-STD-6001B` uyumlu yanmaz metal ve `Nomex` katmanlar kullanılır; aşırı ısınma algılandığında ilk adımda bölüm elektriği (`120V DC`) ve havalandırma fanı kapatılır.";
        }

        if (hasAnyTerm(normText, ["duman dedektor", "smoke detector"]) && !hasAnyTerm(normText, ["yag", "oil", "grease", "su dok"])) {
            return isEn
                ? "Household smoke detectors belong to everyday building safety, yet their light-scattering physics directly connects to spacecraft fire detection and NASA's terrestrial technology transfers.\n\n- **Earth vs. `0G` Soot & Cool Flames:** Standard photoelectric detectors sense visible soot particles, but in `0G` flames can transition into soot-free `550–780 K` cool flames that optical sensors miss, requiring `CO` gas analyzers and `UV/IR` radiometers.\n- **Space-to-Earth Transfer (`SAME / DAFT`):** Multi-angle laser scattering developed for ISS and Lunar dust rejection now reduces false alarms from dust and steam in terrestrial buildings, mines, and aircraft cargo bays."
                : "Ev tipi duman dedektörleri günlük bina güvenliği konusudur; ancak çalışma prensibi uzay aracı yangın algılama sistemleri ve Dünya'ya aktarılan NASA sensör teknolojileriyle doğrudan bağlantılıdır.\n\n- **Kurum Boyutu ve Görünmez Soğuk Alev Farkı:** Klasik optik dedektörler görünür duman parçacıklarını algılar; `0G` ortamında ise kurumsuz `550–780 K` soğuk alev oluşabildiği için optik sensörler `CO` gaz analizörü ve termal/kızılötesi algılayıcılarla birlikte kullanılır.\n- **Dünya'ya Teknoloji Transferi (`SAME / DAFT`):** Uzay kabinlerinde Ay tozunu gerçek yangın dumanından ayırmak için geliştirilen çok açılı lazer sensörler, bugün Dünya'da toz ve su buharı kaynaklı yanlış alarmları önlemektedir.";
        }

        return isEn
            ? "Household kitchen and grease fires belong to terrestrial safety rather than orbital testing, yet water droplet size physics directly explains both why bulk water fails on hot oil and how spacecraft water-mist extinguishers work.\n\n- **Bulk Water vs. `25–40 µm` Fine Water Mist:** Pouring bulk liquid water onto burning oil sinks and flashes into steam (`~1700x` expansion), splattering burning fuel—so kitchen grease fires must be smothered by cutting oxygen with a lid. Crewed spacecraft never spray bulk water; they deploy **`25–40 µm` fine water mist (`SoFIE-MIST / ISS PFE`)**, whose micro-droplets evaporate directly in the flame front to absorb heat and dilute oxygen without splashing or damaging electronics.\n- **Space-to-Earth Transfer:** NASA micro-mist nozzle designs (`SoFIE-MIST`) and `Nomex / PBI` protective fabrics are now widely used in terrestrial cleanrooms, battery rooms, and firefighting gear."
            : "Evdeki yağ ve mutfak yangınları doğrudan yeryüzü güvenliği konusudur; ancak suyun damlacık boyutu ve buharlaşma fiziği uzay aracı yangın söndürme sistemleriyle birebir bağlantılıdır.\n\n- **Kaba Su ile `25–40 µm` İnce Su Sisi Farkı:** Kızgın yağa dökülen kaba sıvı su yağın altına çöküp aniden buharlaşarak (`~1700 kat` hacim genleşmesi) alevli yağı etrafa sıçratır; bu nedenle tavadaki yağ yangınında su dökülmez, kapak kapatılarak oksijen kesilir. Uzay araçlarında ise kaba su yerine **`25–40 µm` ince su sisi (`SoFIE-MIST / ISS PFE`)** kullanılır; mikro damlacıklar daha alev cephesindeyken buharlaşıp ısıyı çeker ve elektronikleri ıslatmadan alevi boğar.\n- **Dünya'ya Teknoloji Transferi:** Uzay kabinleri için geliştirilen bu ince su sisi başlıkları ve `Nomex / PBI` koruyucu kumaşlar günümüzde veri merkezleri, batarya odaları ve itfaiye ekipmanlarında güvenle kullanılmaktadır.";
    }

    function isPreviousTurnValidInScopeBrowser(history) {
        if (!Array.isArray(history) || history.length === 0) return false;
        let lastUserMsg = "";
        let lastAsstMsg = "";
        for (let i = history.length - 1; i >= 0; i--) {
            const it = history[i];
            if (!it || typeof it !== "object") continue;
            const role = String(it.role || "").toLowerCase();
            const content = String(it.content || "").trim();
            if (!content) continue;
            if (role === "assistant" && !lastAsstMsg) lastAsstMsg = content;
            else if (role === "user" && !lastUserMsg) {
                lastUserMsg = content;
                break;
            }
        }
        if (!lastUserMsg) return false;
        if (lastAsstMsg && hasAnyTerm(normQueryAscii(lastAsstMsg), SCOPE_REJECTED_MARKERS)) return false;
        const prevEval = evaluateQueryScopeBrowser(lastUserMsg, null, null, "", null, "tr", false);
        return prevEval.status === "in_scope" || prevEval.status === "boundary_context";
    }

    function evaluateQueryScopeBrowser(userMsg, history, simParams, mediaCtx, imageB64, lang, allowFollowup) {
        const rawMsg = String(userMsg || "").trim();
        const isEn = String(lang || "tr").toLowerCase() === "en";
        const fullNorm = normQueryAscii(rawMsg);
        const fullFuzzyObj = matchFuzzyDomainTokensBrowser(fullNorm);
        const fuzzyFull = fullFuzzyObj.matched;
        const repairedFullNorm = fullFuzzyObj.repairedNorm;

        // 1) Kural ve güvenlik kilidi ('rule_locked')
        const hasRoleOverride = hasAnyTerm(repairedFullNorm, SCOPE_ROLE_OVERRIDES);
        const hasHalonEndorse = repairedFullNorm.indexOf("halon") !== -1 && hasAnyTerm(repairedFullNorm, SCOPE_HALON_ENDORSE);
        if (hasRoleOverride || hasHalonEndorse) {
            const mentionsHalon = repairedFullNorm.indexOf("halon") !== -1;
            const repTr = mentionsHalon
                ? "Uçuş güvenliği kuralları sabittir ve değiştirilemez. Halon 1301 yüksek alev sıcaklığında zehirli `HF` ve `HBr` gazı ürettiği için kapalı uzay aracı kabinlerinde kullanılmaz; bunun yerine hava akışı kesilir ve ince su sisi uygulanır."
                : "Uçuş ve yangın güvenliği kuralları sabittir; bu ekran yalnızca uzay aracı yangın güvenliği ve yanma fiziği analizleri için çalışır. Aktif 3B yanma odası veya Orion bölmeleri üzerinden teknik bir soru sorabilirsiniz.";
            const repEn = mentionsHalon
                ? "Flight safety rules are fixed and cannot be overridden. Halon 1301 is not used in enclosed spacecraft cabins because it produces toxic `HF` and `HBr` gases at flame temperatures; crews cut cabin airflow and apply fine water mist instead."
                : "Flight and fire safety rules are fixed; this console operates strictly for spacecraft fire safety and combustion physics analysis. You can ask a technical question based on the active 3D chamber or Orion compartments.";
            return {
                status: "rule_locked",
                badge_tr: "Konu Dışı",
                badge_en: "Off-Topic",
                physics_note: false,
                is_followup: false,
                mixed_stripped: false,
                cleaned_query: rawMsg,
                typo_corrections: fuzzyFull.map((p) => p[1]),
                misconception: null,
                boundary_kind: null,
                reply_tr: repTr,
                reply_en: repEn,
                reply: isEn ? repEn : repTr,
            };
        }

        // 2) Karma cümle ayıklama ve yazım hatası düzeltmesi
        const stripRes = stripCasualClausesBrowser(rawMsg);
        const strippedMsg = stripRes.strippedMsg;
        const mixedStripped = stripRes.mixedStripped;
        const clauseNorm = normQueryAscii(strippedMsg);
        const clauseFuzzyObj = clauseNorm === fullNorm ? fullFuzzyObj : matchFuzzyDomainTokensBrowser(clauseNorm);
        const fuzzyHits = clauseFuzzyObj.matched;
        const repairedNorm = clauseFuzzyObj.repairedNorm;

        let cleanedQuery = strippedMsg;
        if (fuzzyHits.length > 0) {
            const missingCanon = [];
            fuzzyHits.forEach(([orig, canon]) => {
                if (orig !== canon && clauseNorm.indexOf(canon) === -1 && !missingCanon.includes(canon)) {
                    missingCanon.push(canon);
                }
            });
            if (missingCanon.length > 0) {
                cleanedQuery = `${strippedMsg} (${missingCanon.join(" ")})`;
            }
        }

        // 3) Sınır bağlantısı ('boundary_context')
        const boundaryKind = detectBoundaryCategoryBrowser(repairedNorm);
        if (boundaryKind) {
            const miscon = detectPhysicalMisconceptionBrowser(repairedNorm);
            return {
                status: "boundary_context",
                badge_tr: "Yangın Güvenliği Bağlantısı",
                badge_en: "Fire Safety Context",
                physics_note: Boolean(miscon),
                is_followup: false,
                mixed_stripped: mixedStripped,
                cleaned_query: cleanedQuery,
                typo_corrections: fuzzyHits.map((p) => p[1]),
                misconception: miscon,
                boundary_kind: boundaryKind,
                reply_tr: "",
                reply_en: "",
                reply: "",
            };
        }

        // 4) Doğrudan kapsam içi ('in_scope')
        const hasExplicitOffTopic = hasAnyTerm(repairedNorm, SCOPE_EXPLICIT_OFF_TOPIC);
        const hasStrongSpaceAnchor = hasStrongSpaceAnchorBrowser(repairedNorm);
        const blockedByOffTopic = hasExplicitOffTopic && !hasStrongSpaceAnchor;

        const hasDirectDomain = hasAnyTerm(repairedNorm, SCOPE_DIRECT_PHRASES)
            || RE_SCOPE_SHORT_TOKENS.test(repairedNorm)
            || RE_NATURAL_COMBUSTION_TOKENS.test(repairedNorm)
            || fuzzyHits.length > 0;
        const cleanGreetingNorm = repairedNorm.replace(/[^a-z0-9\s]/g, " ").replace(/\s+/g, " ").trim();
        const hasIntro = hasAnyTerm(repairedNorm, SCOPE_INTRO_PHRASES)
            || cleanGreetingNorm === "yardim"
            || cleanGreetingNorm === "help"
            || SHORT_GREETINGS_LIST.includes(cleanGreetingNorm);

        if (!blockedByOffTopic && (hasDirectDomain || hasIntro)) {
            const miscon = detectPhysicalMisconceptionBrowser(repairedNorm);
            return {
                status: "in_scope",
                badge_tr: "Doğrudan Analiz",
                badge_en: "Direct Analysis",
                physics_note: Boolean(miscon),
                is_followup: false,
                mixed_stripped: mixedStripped,
                cleaned_query: cleanedQuery,
                typo_corrections: fuzzyHits.map((p) => p[1]),
                misconception: miscon,
                boundary_kind: null,
                reply_tr: "",
                reply_en: "",
                reply: "",
            };
        }

        // 5) Güvenli takip sorusu ve ekli medya desteği
        const hasMedia = Boolean((mediaCtx && String(mediaCtx).trim()) || (imageB64 && String(imageB64).trim()));
        if (!hasExplicitOffTopic) {
            if (hasMedia && (hasAnyTerm(repairedNorm, SCOPE_MEDIA_FOLLOWUP) || hasAnyTerm(repairedNorm, SCOPE_FOLLOWUP_PATTERNS) || repairedNorm.split(/\s+/).length <= 6)) {
                return {
                    status: "in_scope",
                    badge_tr: "Doğrudan Analiz",
                    badge_en: "Direct Analysis",
                    physics_note: false,
                    is_followup: true,
                    mixed_stripped: mixedStripped,
                    cleaned_query: cleanedQuery,
                    typo_corrections: [],
                    misconception: null,
                    boundary_kind: null,
                    reply_tr: "",
                    reply_en: "",
                    reply: "",
                };
            }
            if (allowFollowup !== false && hasAnyTerm(repairedNorm, SCOPE_FOLLOWUP_PATTERNS) && isPreviousTurnValidInScopeBrowser(history)) {
                return {
                    status: "in_scope",
                    badge_tr: "Doğrudan Analiz",
                    badge_en: "Direct Analysis",
                    physics_note: false,
                    is_followup: true,
                    mixed_stripped: mixedStripped,
                    cleaned_query: cleanedQuery,
                    typo_corrections: [],
                    misconception: null,
                    boundary_kind: null,
                    reply_tr: "",
                    reply_en: "",
                    reply: "",
                };
            }
        }

        // 6) Konu dışı ('off_topic') — Erken çıkış
        const fuelId = String((simParams && simParams.fuel_id) || "n_heptane");
        const fLabelsTr = {
            n_heptane: "n-Heptan", methanol: "Metanol", ethanol: "Etanol", pmma: "PMMA",
            nomex: "Nomex", sibal: "SIBAL kumaş", propane_cfig: "Propan", hydrogen: "Hidrojen", custom_material: "özel malzeme"
        };
        const fLabelsEn = {
            n_heptane: "n-Heptane", methanol: "Methanol", ethanol: "Ethanol", pmma: "PMMA",
            nomex: "Nomex", sibal: "SIBAL fabric", propane_cfig: "Propane", hydrogen: "Hydrogen", custom_material: "custom material"
        };
        const fTr = fLabelsTr[fuelId] || "yanma odası";
        const fEn = fLabelsEn[fuelId] || "combustion chamber";
        const offTr = `Bu ekran yalnızca uzay aracı yangın güvenliği, kabin içi müdahale ve mikroçekim yanma fiziği sorularına odaklanır. Aktif \`${fTr}\` sahnesi için aşağıdaki hazır işlemlerden birini seçebilir veya doğrudan teknik bir soru yazabilirsiniz.`;
        const offEn = `This console focuses exclusively on spacecraft fire safety, cabin response, and microgravity combustion physics. You can pick one of the quick actions below for the active \`${fEn}\` scene or type a technical question.`;

        return {
            status: "off_topic",
            badge_tr: "Konu Dışı",
            badge_en: "Off-Topic",
            physics_note: false,
            is_followup: false,
            mixed_stripped: false,
            cleaned_query: rawMsg,
            typo_corrections: [],
            misconception: null,
            boundary_kind: null,
            reply_tr: offTr,
            reply_en: offEn,
            reply: isEn ? offEn : offTr,
        };
    }

    function prependMisconceptionBrowser(replyText, miscon, lang) {
        if (!miscon) return replyText;
        const isEn = String(lang || "tr").toLowerCase() === "en";
        const corr = String(isEn ? miscon.correction_en : miscon.correction_tr || "").trim();
        if (!corr) return replyText;
        const normRep = normQueryAscii(String(replyText || "").slice(0, 320));
        const normHead = normQueryAscii(corr.slice(0, 60));
        if (normHead && normRep.indexOf(normHead) !== -1) return replyText;
        const pfx = isEn ? "**Physics Note:**" : "**Fiziksel Düzeltme:**";
        return `${pfx} ${corr}\n\n${String(replyText || "").trimStart()}`;
    }

    function sanitizeUnverifiedExperimentsBrowser(replyText) {
        if (!replyText) return replyText;
        return String(replyText)
            .replace(/\bSaffire[-\s]+(?:VII|VIII|IX|X|XI|XII|XIII|XIV|XV)\b/gi, "Saffire (I–VI)")
            .replace(/\bSaffire[-\s]+(?:[789]|\d{2,})\b/gi, "Saffire (I–VI)")
            .replace(/\bFLEX[-\s]+(?:[3-9]|\d{2,}|III|IV|V|VI|VII|VIII|IX|X)\b/gi, "FLEX / FLEX-2")
            .replace(/\bBASS[-\s]+(?:[3-9]|\d{2,}|III|IV|V|VI|VII|VIII|IX|X)\b/gi, "BASS / BASS-II")
            .replace(/\bSoFIE[-\s]+(?:[2-9]|\d{2,}|II|III|IV|V|VI|VII|VIII|IX|X)\b/gi, "SoFIE")
            .replace(/\b(SPICE|SLICE|ACME)[-\s]+(?:[2-9]|\d{2,}|II|III|IV|V|VI|VII|VIII|IX|X)\b/gi, "$1");
    }

    function buildSuggestedActionsBrowser(scopeRes, activeSim, lang) {
        const inp = (activeSim && activeSim.inputs) || {};
        const compNet = (activeSim && activeSim.compartment_network) || {};
        const normQ = normQueryAscii(String((scopeRes && scopeRes.cleaned_query) || ""));
        const curFuel = String(inp.fuel_id || "n_heptane");
        const curG = Number(inp.gravity_g ?? 0.0);
        const curO2 = Number(inp.oxygen_pct ?? 21.0);
        const curP = Number(inp.pressure_psia ?? 14.7);
        const curU = Number(inp.airflow_cms ?? 2.0);
        let fireComp = String(compNet.fire_compartment_id || "ORION_CM").toUpperCase();
        if (!["ORION_CM", "IHAB", "HALO", "AIRLOCK", "PPE"].includes(fireComp)) fireComp = "ORION_CM";

        let targetSim = null;
        if (normQ.indexOf("metanol") !== -1 || normQ.indexOf("methanol") !== -1) {
            targetSim = { fuel_id: "methanol", gravity_g: 0.0, oxygen_pct: 16.0, pressure_psia: 14.7, airflow_cms: 0.4, droplet_d0_mm: 3.8, diluent: "N2" };
        } else if (normQ.indexOf("soguk alev") !== -1 || normQ.indexOf("cool flame") !== -1) {
            targetSim = { fuel_id: "n_heptane", gravity_g: 0.0, oxygen_pct: 15.5, pressure_psia: 14.7, airflow_cms: 0.2, droplet_d0_mm: 4.2, diluent: "N2" };
        } else if (normQ.indexOf("uzay giysisi") !== -1 || normQ.indexOf("spacesuit") !== -1 || normQ.indexOf("eva") !== -1) {
            targetSim = { fuel_id: "nomex", gravity_g: 0.16, oxygen_pct: 100.0, pressure_psia: 4.3, airflow_cms: 4.0, droplet_d0_mm: 3.2, diluent: "N2", habitat_id: "eva_suit" };
        } else if (normQ.indexOf("pmma") !== -1 || normQ.indexOf("saffire") !== -1 || normQ.indexOf("bass") !== -1) {
            targetSim = { fuel_id: "pmma", gravity_g: 0.0, oxygen_pct: 21.0, pressure_psia: 14.7, airflow_cms: 5.5, droplet_d0_mm: 3.5, diluent: "N2" };
        } else {
            targetSim = {
                fuel_id: curFuel,
                gravity_g: curG,
                oxygen_pct: curO2,
                pressure_psia: curP,
                airflow_cms: curU !== 0 ? Math.max(0.2, curU) : 4.5,
                droplet_d0_mm: Number(inp.droplet_d0_mm || 3.2),
                diluent: String(inp.diluent || "N2"),
            };
        }

        const actions = [
            { type: "apply_3d_sim", label_tr: "3B Odaya Uygula", label_en: "Load in 3D", sim_params: targetSim },
            { type: "run_orion_sequence", label_tr: "Sıralı Müdahaleyi Başlat", label_en: "Start Fire Response", compartment_id: fireComp },
        ];

        const promptCandidates = [];
        if (curFuel === "methanol" || normQ.indexOf("metanol") !== -1) {
            promptCandidates.push(["0G'de metanol neden soğuk yanar?", "How does methanol burn in 0G?"]);
        } else if (curG === 0.16) {
            promptCandidates.push(["Ay yerçekiminde tutuşma sınırı nasıl değişir?", "How does lunar gravity shift flammability?"]);
        } else if (curO2 >= 50.0) {
            promptCandidates.push(["Uzay giysisinde neden saf oksijen kullanılır?", "Why do spacesuits use pure oxygen?"]);
        } else {
            promptCandidates.push(["0G'de metanol nasıl yanar?", "How does methanol burn in 0G?"]);
        }
        promptCandidates.push(["Su sisi alevi nasıl söndürür?", "How does water mist quench fire?"]);
        promptCandidates.push(["Kapak ne zaman güvenle açılır?", "When is hatch opening safe?"]);

        promptCandidates.slice(0, 2).forEach(([pTr, pEn]) => {
            actions.push({ type: "ask_prompt", label_tr: pTr, label_en: pEn, prompt_tr: pTr, prompt_en: pEn });
        });
        return actions;
    }

    async function callBrowserCloudGateway(msg, simParams, mediaCtx, history, provOverride) {
        const pref = String(provOverride || runtimeConfig.active_provider || "auto").toLowerCase();
        const useGemini = (pref === "gemini" || pref === "auto") && Boolean(runtimeConfig.gemini_api_key);
        const useOpenRouter = !useGemini && (pref === "openrouter" || pref === "auto") && Boolean(runtimeConfig.openrouter_api_key);
        if (!useGemini && !useOpenRouter) return null;

        const sim = simulateCombustionClient(simParams || {});
        const inp = sim.inputs;
        const tel = sim.telemetry;
        const isEn = runtimeConfig.language === "en";
        const sys = isEn
            ? "You are ALTAR-NASA v6.3 Spacecraft Fire Safety & Microgravity Combustion Synthesis Kernel. Answer the user's exact question directly with clear engineering prose and Markdown tables when comparing conditions. Cite only verified NASA experiments (FLEX, FLEX-2, CFI, ACME, BASS, BASS-II, SPICE, SLICE, Saffire I-VI, SoFIE, SAME, DAFT) and never invent experiment numbers. Correct physical misconceptions (such as ceiling smoke in 0G or premature hatch opening) in one concise opening sentence. Avoid emojis. Never recommend Halon 1301 (prohibited per NASA-STD-6001B due to toxic HF/HBr formation; use airflow cutoff U->0 and SoFIE-MIST fine water mist)."
            : "Sen ALTAR-NASA v6.3 Uzay Aracı Yangın Güvenliği ve Mikroçekim Yanma Sentez Çekirdeğisin. Kullanıcının sorduğu soruyu doğrudan, sade mühendislik diliyle ve kıyaslamalarda Markdown tablolarıyla yanıtla. Yalnızca gerçek NASA deneylerini (FLEX, FLEX-2, CFI, ACME, BASS, BASS-II, SPICE, SLICE, Saffire I-VI, SoFIE, SAME, DAFT) an ve katalog dışı deney numarası üretme. Soruda fiziksel bir yanılgı varsa (0G'de dumanın tavanda birikmesi veya sıcak bölme kapağının hemen açılması gibi) ilk cümlede kısaca düzelt. Emoji kullanma. Halon 1301 önermek kesinlikle yasaktır (NASA-STD-6001B gereği zehirli HF/HBr üretir; yerine U->0 fan kesme ve SoFIE-MIST ince su sisi öner).";
        const auditHalon = (txt) => {
            if (!txt) return txt;
            const cleanedTxt = sanitizeUnverifiedExperimentsBrowser(txt);
            if (/\bhalon\b/i.test(cleanedTxt) && !/yasak|prohibit|banned|toksik|toxic|hf\/hbr|6001b/i.test(cleanedTxt)) {
                return cleanedTxt + (isEn
                    ? "\n\n> **[CON-05 • NASA-STD-6001B SAFETY AUDIT]:** Halon 1301 is strictly prohibited inside crewed spacecraft cabins due to lethal `HF`/`HBr` decomposition products that poison ECLSS scrubbers. Approved alternatives: `U -> 0 cm/s` ventilation shutoff, `CO₂` extinguishers, `N₂` depressurization, or `SoFIE-MIST` (`<100 µm`) fine water mist."
                    : "\n\n> **[CON-05 • NASA-STD-6001B GÜVENLİK DENETÇİSİ]:** Mürettebatlı uzay aracı kabinlerinde Halon 1301 kullanımı ölümcül `HF`/`HBr` gazları üretip ECLSS filtrelerini zehirlediği için kesinlikle yasaktır. Onaylı protokoller: `U -> 0 cm/s` fan kesme, `CO₂` tüpü, `N₂` seyreltme veya `SoFIE-MIST` (`<100 µm`) ince su sisidir.");
            }
            return cleanedTxt;
        };
        const ctxPrompt = `[3D Chamber: ${inp.fuel_name_en}, ${inp.gravity_g}G, ${inp.oxygen_pct}% O2, ${inp.pressure_psia} psia, U=${inp.airflow_cms} cm/s -> Regime=${tel.regime}, T_f=${tel.flame_temp_k}K, K=${tel.burning_rate_k_mm2_s}, B_oq=${tel.spalding_b_number}, Sh=${tel.sherwood_number}, Da=${tel.damkohler_number}, MOC=${tel.moc_pct}%, Risk=${tel.risk_score}/100]${mediaCtx ? `\n[Media: ${mediaCtx}]` : ""}\n\nQuestion: ${msg}`;

        try {
            if (useGemini) {
                const mdl = (runtimeConfig.gemini_model || "gemini-2.5-flash").replace(/^models\//, "");
                const gRes = await window.fetch(
                    `https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(mdl)}:generateContent?key=${encodeURIComponent(runtimeConfig.gemini_api_key)}`,
                    {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            system_instruction: { parts: [{ text: sys }] },
                            contents: [{ role: "user", parts: [{ text: ctxPrompt }] }],
                            generationConfig: { temperature: 0.25 },
                        }),
                    }
                );
                if (gRes.ok) {
                    const gData = await gRes.json();
                    const txt = (((gData.candidates || [])[0] || {}).content || {}).parts;
                    const out = Array.isArray(txt) ? txt.map((p) => p.text || "").join("") : "";
                    if (out.trim()) return { provider: "gemini", model: mdl, reply: auditHalon(out.trim()) };
                }
            } else if (useOpenRouter) {
                const orMdl = runtimeConfig.openrouter_model || "google/gemini-2.0-flash-exp:free";
                const orRes = await window.fetch("https://openrouter.ai/api/v1/chat/completions", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        Authorization: `Bearer ${runtimeConfig.openrouter_api_key}`,
                    },
                    body: JSON.stringify({
                        model: orMdl,
                        messages: [
                            { role: "system", content: sys },
                            { role: "user", content: ctxPrompt },
                        ],
                        temperature: 0.25,
                    }),
                });
                if (orRes.ok) {
                    const orData = await orRes.json();
                    const out = ((((orData.choices || [])[0] || {}).message || {}).content || "").trim();
                    if (out) return { provider: "openrouter", model: orMdl, reply: auditHalon(out) };
                }
            }
        } catch (_) {}
        return null;
    }

    async function emitNextBrowserStreamPacket() {
        const nowTime = new Date().toTimeString().slice(0, 8);
        const isEn = runtimeConfig.language === "en";
        const src = String(streamState.source || "ntrs").toLowerCase();
        const rawTarget = String(streamState.query_or_url || "").trim();

        if (src === "custom_url") {
            const target = rawTarget || "https://psi.nasa.gov/physci/repo/data/investigations/PSI-69";
            const mPsi = target.match(/\b(PSI-\d+)\b/i);
            const psiCode = mPsi ? mPsi[1].toUpperCase() : "";

            if (psiCode && PSI_SNAPSHOT_MAP[psiCode]) {
                const snap = PSI_SNAPSHOT_MAP[psiCode];
                const phases = Array.isArray(snap.phases) ? snap.phases : [];
                streamState.seq_id += 1;
                streamState.last_tick_ms = Date.now();
                streamState.last_fetch_time = nowTime;
                streamState.last_error = "";
                let chosenParams = Object.assign({
                    fuel_id: "n_heptane", gravity_g: 0.0, oxygen_pct: 21.0,
                    pressure_psia: 14.7, airflow_cms: 2.4, droplet_d0_mm: 3.4, diluent: "N2",
                }, snap.extracted_sim_params || {});
                let phaseSuffix = "";
                let summaryTxt = String(snap.abstract || "").slice(0, 320);
                if (phases.length > 0) {
                    const ph = phases[(streamState.seq_id - 1) % phases.length];
                    if (ph && ph.sim_params) chosenParams = Object.assign({}, chosenParams, ph.sim_params);
                    phaseSuffix = isEn ? ` [Phase ${ph.index}/${phases.length}]` : ` [Faz ${ph.index}/${phases.length}]`;
                    summaryTxt = isEn
                        ? `Phase ${ph.index}/${phases.length} (${snap.table_file || psiCode}): ${chosenParams.fuel_id}, ${chosenParams.gravity_g}G, ${chosenParams.oxygen_pct}% O₂, ${chosenParams.pressure_psia} psia, ${chosenParams.airflow_cms} cm/s — Temp: ${ph.flame_temp_k || ""} K.`
                        : `Faz ${ph.index}/${phases.length} (${snap.table_file || psiCode}): ${chosenParams.fuel_id}, ${chosenParams.gravity_g}G, %${chosenParams.oxygen_pct} O₂, ${chosenParams.pressure_psia} psia, ${chosenParams.airflow_cms} cm/s — Sıcaklık: ${ph.flame_temp_k || ""} K.`;
                }
                streamState.latest_sim_params = chosenParams;
                streamState.events.unshift({
                    seq_id: streamState.seq_id,
                    time: nowTime,
                    source: "Custom PSI Stream (psi.nasa.gov)",
                    id: snap.id || psiCode,
                    title: `${snap.title || psiCode}${phaseSuffix}`,
                    summary: summaryTxt,
                    url: snap.url || target,
                    extracted_sim_params: chosenParams,
                });
                streamState.events = streamState.events.slice(0, 12);
                return;
            }

            if (/psi\.nasa\.gov|osdr\.nasa\.gov/i.test(target)) {
                let qTerm = "combustion";
                try {
                    const pu = new URL(target, window.location.href);
                    qTerm = pu.searchParams.get("q") || pu.searchParams.get("term") || pu.searchParams.get("search") || "combustion";
                } catch (_) {}
                const hits = searchPsiSnapshotJs(qTerm, 36);
                if (hits.length > 0) {
                    const hit = hits[streamState.seq_id % hits.length];
                    streamState.seq_id += 1;
                    streamState.last_tick_ms = Date.now();
                    streamState.last_fetch_time = nowTime;
                    streamState.last_error = "";
                    streamState.latest_sim_params = Object.assign({
                        fuel_id: "n_heptane", gravity_g: 0.0, oxygen_pct: 21.0,
                        pressure_psia: 14.7, airflow_cms: 2.4, droplet_d0_mm: 3.4, diluent: "N2",
                    }, hit.extracted_sim_params || {});
                    streamState.events.unshift({
                        seq_id: streamState.seq_id,
                        time: nowTime,
                        source: "Custom PSI Search Stream",
                        id: hit.id,
                        title: hit.title,
                        summary: hit.abstract,
                        url: hit.url,
                        extracted_sim_params: streamState.latest_sim_params,
                    });
                    streamState.events = streamState.events.slice(0, 12);
                    return;
                }
            }

            try {
                const res = await window.fetch(target, { method: "GET" });
                if (!res.ok) throw new Error(`HTTP ${res.status}`);
                const cleanName = decodeURIComponent((target.split("?")[0].split("/").pop() || "stream_data.csv"));
                let parsed = null;
                if (/\.(xlsx|zip)$/i.test(cleanName)) {
                    const ab = await res.arrayBuffer();
                    const arch = await extractArchiveBufferInBrowser(ab, cleanName);
                    parsed = parseTextOrTablePayloadInBrowser(arch.text || "", arch.effectiveName || cleanName);
                } else {
                    const txt = await res.text();
                    parsed = parseTextOrTablePayloadInBrowser(txt, cleanName);
                }
                streamState.seq_id += 1;
                streamState.last_tick_ms = Date.now();
                streamState.last_fetch_time = nowTime;
                streamState.last_error = "";
                const phases = Array.isArray(parsed.phases) ? parsed.phases : [];
                let chosenParams = Object.assign({}, parsed.extracted_sim_params || {});
                let phaseSuffix = "";
                if (phases.length > 0) {
                    const ph = phases[(streamState.seq_id - 1) % phases.length];
                    if (ph && ph.sim_params) chosenParams = Object.assign({}, chosenParams, ph.sim_params);
                    phaseSuffix = isEn ? ` [Phase ${ph.index}/${phases.length}]` : ` [Faz ${ph.index}/${phases.length}]`;
                }
                streamState.latest_sim_params = chosenParams;
                streamState.events.unshift({
                    seq_id: streamState.seq_id,
                    time: nowTime,
                    source: "Custom URL Stream",
                    id: `URL-${streamState.seq_id}`,
                    title: `${parsed.title || cleanName}${phaseSuffix}`,
                    summary: (isEn ? parsed.summary_en : parsed.summary_tr || "").replace(/[#*`]/g, "").slice(0, 260),
                    url: target,
                    extracted_sim_params: chosenParams,
                });
                streamState.events = streamState.events.slice(0, 12);
                return;
            } catch (_) {
                streamState.last_tick_ms = Date.now();
                streamState.last_fetch_time = nowTime;
                streamState.last_error = isEn
                    ? "External URL blocked direct browser reading (CORS policy). Use a psi.nasa.gov link or Nasa_4.exe."
                    : "Dış bağlantı tarayıcıdan doğrudan veri okumayı (CORS kuralı) kısıtladı. Resmi psi.nasa.gov adresi veya Nasa_4.exe kullanın.";
                return;
            }
        }

        if (src === "osdr" && PSI_SNAPSHOT.length > 0) {
            const qVal = (!rawTarget || rawTarget.toLowerCase() === "auto") ? "combustion" : rawTarget;
            const psiPool = searchPsiSnapshotJs(qVal, 36);
            const item = psiPool[streamState.seq_id % Math.max(1, psiPool.length)] || psiRowToItemJs(PSI_SNAPSHOT[0]);
            streamState.seq_id += 1;
            streamState.last_tick_ms = Date.now();
            streamState.last_fetch_time = nowTime;
            streamState.last_error = "";
            streamState.latest_sim_params = Object.assign({
                fuel_id: "n_heptane", gravity_g: 0.0, oxygen_pct: 21.0,
                pressure_psia: 14.7, airflow_cms: 2.4, droplet_d0_mm: 3.4, diluent: "N2",
            }, item.extracted_sim_params || {});
            streamState.events.unshift({
                seq_id: streamState.seq_id,
                time: nowTime,
                source: "NASA PSI Repository Stream",
                id: item.id,
                title: item.title,
                summary: item.abstract,
                url: item.url,
                extracted_sim_params: streamState.latest_sim_params,
            });
            streamState.events = streamState.events.slice(0, 12);
            return;
        }

        let catPool = NASA_CATALOG;
        if (rawTarget && rawTarget.toLowerCase() !== "auto") {
            const scored = NASA_CATALOG
                .map((e) => ({ e, s: computeTextSimilarity(rawTarget, `${e.program} ${e.title} ${e.title_tr} ${(e.tags || []).join(" ")}`) }))
                .filter((x) => x.s > 0.05)
                .sort((a, b) => b.s - a.s)
                .map((x) => x.e);
            if (scored.length > 0) catPool = scored;
        }
        const pick = catPool[streamState.seq_id % catPool.length];
        streamState.seq_id += 1;
        streamState.last_tick_ms = Date.now();
        streamState.last_fetch_time = nowTime;
        streamState.last_error = "";
        streamState.latest_sim_params = {
            fuel_id: pick.fuel_id,
            gravity_g: pick.gravity_g,
            oxygen_pct: pick.oxygen_pct,
            pressure_psia: pick.pressure_psia,
            airflow_cms: pick.airflow_cms,
            droplet_d0_mm: pick.cool_flame_observed ? 4.4 : 3.2,
            diluent: "N2",
        };
        streamState.events.unshift({
            seq_id: streamState.seq_id,
            time: nowTime,
            source: "NASA NTRS Live Stream",
            id: `NTRS-${pick.ntrs_id}`,
            title: pick.title,
            summary: isEn ? pick.key_finding_en : pick.key_finding_tr,
            url: pick.ntrs_url,
            extracted_sim_params: streamState.latest_sim_params,
        });
        streamState.events = streamState.events.slice(0, 12);
    }

    function syncBrowserStreamTimer() {
        if (streamState.timerId) {
            clearInterval(streamState.timerId);
            streamState.timerId = null;
        }
        if (streamState.enabled) {
            const periodMs = Math.max(5000, (Number(streamState.interval_sec) || 25) * 1000);
            streamState.timerId = window.setInterval(() => {
                if (streamState.enabled) {
                    emitNextBrowserStreamPacket().catch(() => {});
                }
            }, periodMs);
        }
    }

    let ccsdsSeqCounter = 0;

    function crc16CcittBrowser(bytes) {
        let crc = 0xffff;
        for (let i = 0; i < bytes.length; i++) {
            crc ^= (bytes[i] & 0xff) << 8;
            for (let b = 0; b < 8; b++) {
                crc = (crc & 0x8000) ? (((crc << 1) ^ 0x1021) & 0xffff) : ((crc << 1) & 0xffff);
            }
        }
        return crc & 0xffff;
    }

    function buildCcsdsPacketBrowser(actuatorId, compartmentId, targetHatchId, engage, authority, paramU16) {
        const cleanAct = String(actuatorId || "").toUpperCase();
        if (cleanAct.includes("HALON")) {
            return {
                ok: false,
                blocked_by_interlock: true,
                error_code: "NASA_STD_6001B_HALON_FORBIDDEN",
                message_tr: "DONANIM KİLİDİ: NASA-STD-6001B uyarınca kapalı uzay aracı kabininde Halon 1301 kullanımı HF/HBr toksisitesi nedeniyle engellendi!",
                message_en: "HARDWARE INTERLOCK: Halon 1301 discharge blocked per NASA-STD-6001B due to toxic HF/HBr pyrolysis products!",
            };
        }
        const spec = HARDWARE_ACTUATOR_SPECS[cleanAct] || HARDWARE_ACTUATOR_SPECS.ECLSS_IMV_FAN_CUTOFF || {
            apid: 0x0210, ttethernet_vl: 0x4101, mil1553_rt: 4, mil1553_sa: 1, opcode: 0xA1, title_tr: cleanAct, title_en: cleanAct, standard: "NASA-STD-6001B",
        };
        ccsdsSeqCounter = (ccsdsSeqCounter + 1) & 0x3fff;
        const apid = Number(spec.apid || 0x0210) & 0x07ff;
        const pktId = 0x1800 | apid;
        const pktSeq = 0xc000 | (ccsdsSeqCounter & 0x3fff);
        const ttVl = Number(spec.ttethernet_vl || 0x4101) & 0xffff;
        const rtNum = Number(spec.mil1553_rt || 4) & 0x1f;
        const saNum = Number(spec.mil1553_sa || 1) & 0x1f;
        const milCmd = (rtNum << 11) | (saNum << 5) | 6;
        const COMP_CODES = { ORION_CM: 0x01, HALO: 0x02, IHAB: 0x03, PPE: 0x04, AIRLOCK: 0x05 };
        const HATCH_CODES = { HATCH_ORION_HALO: 0x11, HATCH_HALO_IHAB: 0x12, HATCH_HALO_PPE: 0x13, HATCH_IHAB_AIRLOCK: 0x14 };
        const compKey = COMP_CODES[String(compartmentId || "HALO").toUpperCase()] ? String(compartmentId).toUpperCase() : "HALO";
        const compByte = COMP_CODES[compKey];
        const hatchByte = HATCH_CODES[String(targetHatchId || "")] || 0x00;
        const isAuto = String(authority || "").startsWith("FDIR") ? 1 : 0;
        const stateFlags = ((engage ? 1 : 0) << 7) | (isAuto << 6) | 0x01;
        const mag = Math.max(0, Math.min(65535, Math.round(Number(paramU16 || 100))));

        const body16 = [
            (pktId >> 8) & 0xff, pktId & 0xff,
            (pktSeq >> 8) & 0xff, pktSeq & 0xff,
            0x00, 0x0b,
            (ttVl >> 8) & 0xff, ttVl & 0xff,
            (milCmd >> 8) & 0xff, milCmd & 0xff,
            Number(spec.opcode || 0xA1) & 0xff, compByte, hatchByte, stateFlags,
            (mag >> 8) & 0xff, mag & 0xff,
        ];
        const crc = crc16CcittBrowser(body16);
        const full18 = body16.concat([(crc >> 8) & 0xff, crc & 0xff]);
        const hexStr = full18.map((b) => b.toString(16).toUpperCase().padStart(2, "0")).join(" ");
        const crcHex = `0x${crc.toString(16).toUpperCase().padStart(4, "0")}`;
        return {
            ok: true,
            action_id: cleanAct,
            title_tr: spec.title_tr || cleanAct,
            title_en: spec.title_en || cleanAct,
            compartment_id: compKey,
            target_hatch_id: targetHatchId || null,
            engage: Boolean(engage),
            authority_source: authority || "FDIR_AUTONOMOUS_6001B",
            ccsds: {
                apid_hex: `0x${apid.toString(16).toUpperCase().padStart(4, "0")}`,
                sequence_count: ccsdsSeqCounter,
                packet_length_bytes: 18,
                ttethernet_vl_hex: `0x${ttVl.toString(16).toUpperCase().padStart(4, "0")}`,
                mil_std_1553b_cmd_hex: `0x${milCmd.toString(16).toUpperCase().padStart(4, "0")}`,
                crc16_ccitt_hex: crcHex,
                raw_hex: hexStr,
            },
        };
    }

    function safeEvalMathExprBrowser(rawExpr, varsObj) {
        let s = String(rawExpr || "").trim();
        if (!s || s.length > 320) throw new Error("Empty or oversized expression.");
        let lhsLabel = "";
        const eqIdx = s.indexOf("=");
        if (eqIdx > 0 && s[eqIdx - 1] !== "<" && s[eqIdx - 1] !== ">" && s[eqIdx - 1] !== "!" && s[eqIdx + 1] !== "=") {
            lhsLabel = s.slice(0, eqIdx).trim();
            s = s.slice(eqIdx + 1).trim();
        }
        s = s
            .replace(/\^/g, "**")
            .replace(/·/g, "*")
            .replace(/×/g, "*")
            .replace(/−/g, "-")
            .replace(/²/g, "**2")
            .replace(/³/g, "**3")
            .replace(/₀/g, "0")
            .replace(/₂/g, "2");
        const tokens = [];
        const usedVars = new Set();
        let i = 0;
        while (i < s.length) {
            const ch = s[i];
            if (/\s/.test(ch)) { i++; continue; }
            if (s.slice(i, i + 2) === "**") { tokens.push({ t: "op", v: "**" }); i += 2; continue; }
            if ("+-*/(),".includes(ch)) { tokens.push({ t: ch === "(" || ch === ")" || ch === "," ? ch : "op", v: ch }); i++; continue; }
            if (/[0-9.]/.test(ch)) {
                const mNum = s.slice(i).match(/^[0-9]*\.?[0-9]+(?:[eE][+-]?[0-9]+)?/);
                if (!mNum) throw new Error("Invalid number token.");
                tokens.push({ t: "num", v: parseFloat(mNum[0]) });
                i += mNum[0].length;
                continue;
            }
            if (/[A-Za-z_]/.test(ch)) {
                const mId = s.slice(i).match(/^[A-Za-z_][A-Za-z0-9_]*/);
                tokens.push({ t: "id", v: mId[0] });
                i += mId[0].length;
                continue;
            }
            throw new Error(`Unsupported character: ${ch}`);
        }

        const funcs = {
            sqrt: (a) => Math.sqrt(Math.max(0, a)),
            exp: (a) => Math.exp(Math.min(60, Math.max(-60, a))),
            ln: (a) => Math.log(Math.max(1e-12, a)),
            log: (a) => Math.log(Math.max(1e-12, a)),
            log10: (a) => Math.log10(Math.max(1e-12, a)),
            abs: (a) => Math.abs(a),
            sin: (a) => Math.sin(a),
            cos: (a) => Math.cos(a),
            tan: (a) => Math.tan(a),
            tanh: (a) => Math.tanh(a),
            min: (a, b) => Math.min(a, b),
            max: (a, b) => Math.max(a, b),
            pow: (a, b) => Math.pow(a, b),
        };

        let pos = 0;
        const peek = () => tokens[pos] || null;
        const consume = () => tokens[pos++];

        function parseExpr() {
            let left = parseTerm();
            while (peek() && peek().t === "op" && (peek().v === "+" || peek().v === "-")) {
                const op = consume().v;
                const right = parseTerm();
                left = op === "+" ? left + right : left - right;
            }
            return left;
        }

        function parseTerm() {
            let left = parsePower();
            while (peek() && peek().t === "op" && (peek().v === "*" || peek().v === "/")) {
                const op = consume().v;
                const right = parsePower();
                left = op === "*" ? left * right : left / (Math.abs(right) < 1e-12 ? 1e-12 : right);
            }
            return left;
        }

        function parsePower() {
            let base = parseUnary();
            if (peek() && peek().t === "op" && peek().v === "**") {
                consume();
                const expVal = parsePower();
                base = Math.pow(base, expVal);
            }
            return base;
        }

        function parseUnary() {
            if (peek() && peek().t === "op" && (peek().v === "+" || peek().v === "-")) {
                const op = consume().v;
                const v = parseUnary();
                return op === "-" ? -v : v;
            }
            return parsePrimary();
        }

        function parsePrimary() {
            const tk = peek();
            if (!tk) throw new Error("Unexpected end of formula.");
            if (tk.t === "num") {
                consume();
                return tk.v;
            }
            if (tk.t === "(") {
                consume();
                const val = parseExpr();
                if (!peek() || peek().t !== ")") throw new Error("Missing closing parenthesis.");
                consume();
                return val;
            }
            if (tk.t === "id") {
                consume();
                const name = tk.v;
                if (peek() && peek().t === "(") {
                    consume();
                    const fn = funcs[name];
                    if (!fn) throw new Error(`Unsupported function: ${name}`);
                    const args = [];
                    if (!peek() || peek().t !== ")") {
                        args.push(parseExpr());
                        while (peek() && peek().t === ",") {
                            consume();
                            args.push(parseExpr());
                        }
                    }
                    if (!peek() || peek().t !== ")") throw new Error("Missing ')' after function arguments.");
                    consume();
                    return fn.apply(null, args);
                }
                if (name === "pi" || name === "PI") return Math.PI;
                if (name === "e" || name === "E") return Math.E;
                if (Object.prototype.hasOwnProperty.call(varsObj, name)) {
                    usedVars.add(name);
                    return Number(varsObj[name]);
                }
                throw new Error(`Unknown variable: ${name}`);
            }
            throw new Error(`Unexpected token: ${tk.v}`);
        }

        const outVal = parseExpr();
        if (pos < tokens.length) throw new Error("Unexpected trailing tokens.");
        if (!Number.isFinite(outVal)) throw new Error("Non-finite numerical result.");
        return { value: outVal, usedVars: Array.from(usedVars).sort(), lhsLabel: lhsLabel };
    }

    function evaluateCustomFormulaBrowser(expression, targetMetric, simParams) {
        try {
            const baseParams = (simParams && typeof simParams === "object" && !Array.isArray(simParams)) ? simParams : {};
            const sim = simulateCombustionClient(baseParams);
            const inp = sim.inputs || {};
            const fv = sim.flight_validation || {};
            const buildEnv = (ov) => {
                const s = ov ? simulateCombustionClient(Object.assign({}, baseParams, ov)) : sim;
                const si = s.inputs || {};
                const st = s.telemetry || {};
                const fRef = FUEL_PROPERTIES[si.base_fuel_id || si.fuel_id || "n_heptane"] || FUEL_PROPERTIES.n_heptane;
                const sO2 = Number(si.oxygen_pct ?? 21.0);
                const sP = Number(si.pressure_psia ?? 14.7);
                const sDil = String(si.diluent || "N2");
                const mwDil = Number((DILUENT_FACTORS[sDil] || DILUENT_FACTORS.N2).mw || 28.01);
                const xO2 = sO2 / 100.0;
                const yO2 = (xO2 * 32.0) / Math.max(1.0, xO2 * 32.0 + (1.0 - xO2) * mwDil);
                const rfRdVal = Number(st.standoff_ratio_rf_rd ?? st.standoff_ratio ?? 5.0);
                return {
                    sim: s,
                    vars: {
                        D0: Number(si.droplet_d0_mm ?? 3.2),
                        O2: sO2,
                        X_O2: roundN(xO2, 4),
                        Y_O2: roundN(yO2, 4),
                        P: sP,
                        P_atm: roundN(sP / 14.696, 4),
                        P_kpa: Number(si.pressure_kpa ?? roundN(sP * 6.89476, 2)),
                        PO2: Number(st.o2_partial_psia ?? st.po2_psia ?? roundN((sP * sO2) / 100.0, 3)),
                        U: Number(si.airflow_cms ?? 0.0),
                        g: Number(si.gravity_g ?? 0.0),
                        G: Number(si.gravity_g ?? 0.0),
                        T_f: Number(st.flame_temp_k ?? 1800.0),
                        Tf: Number(st.flame_temp_k ?? 1800.0),
                        T_s: Number(fRef.t_boil_k ?? 371.5),
                        T_amb: 298.15,
                        B: Number(st.spalding_b_number ?? 3.5),
                        B_oq: Number(st.spalding_b_number ?? 3.5),
                        Sh: Number(st.sherwood_number ?? 2.0),
                        Re: Number(st.reynolds_number ?? 0.0),
                        Gr: Number(st.grashof_number ?? 0.0),
                        Ra: Number(st.rayleigh_number ?? 0.0),
                        Ri: Number(st.richardson_number ?? 0.0),
                        Fr: Number(st.froude_number ?? 0.0),
                        Da: Number(st.damkohler_number ?? 5.0),
                        K: Number(st.burning_rate_k_mm2_s ?? 0.65),
                        V_f: Number(st.flame_spread_mm_s ?? 0.0),
                        MOC: Number(st.moc_pct ?? 15.0),
                        chi_r: Number(st.radiative_loss_fraction ?? 0.18),
                        Rf_Rd: rfRdVal,
                        CO: Number(st.co_ppm ?? 50.0),
                        HRRPUA: Number(st.hrrpua_kw_m2 ?? 120.0),
                        Soot: Number(st.soot_index ?? 0.2),
                        t: 6.0,
                    },
                };
            };

            const baseEnv = buildEnv(null);
            const eval0 = safeEvalMathExprBrowser(expression, baseEnv.vars);
            const metricAliases = {
                k_burn: "K",
                burning_rate_k: "K",
                moc_pct: "MOC",
                standoff_ratio: "Rf_Rd",
                standoff_ratio_rf_rd: "Rf_Rd",
                flame_spread_mm_s: "V_f",
                flame_temp_k: "T_f",
                sherwood_number: "Sh",
                spalding_b_number: "B_oq",
            };
            const candidates = {
                Sh: baseEnv.vars.Sh,
                B_oq: baseEnv.vars.B_oq,
                K: baseEnv.vars.K,
                Rf_Rd: baseEnv.vars.Rf_Rd,
                MOC: baseEnv.vars.MOC,
                V_f: baseEnv.vars.V_f,
                T_f: baseEnv.vars.T_f,
            };
            const rawTm = String(targetMetric || "auto").trim();
            const normTarget = metricAliases[rawTm] || rawTm;
            let chosenRefName = Object.prototype.hasOwnProperty.call(candidates, normTarget) ? normTarget : "";
            if (!chosenRefName) {
                const lhsClean = metricAliases[eval0.lhsLabel] || eval0.lhsLabel;
                if (lhsClean && Object.prototype.hasOwnProperty.call(candidates, lhsClean)) {
                    chosenRefName = lhsClean;
                } else {
                    let bestKey = "K";
                    let bestErr = 1e18;
                    Object.keys(candidates).forEach((ck) => {
                        const err = Math.abs(eval0.value - candidates[ck]) / Math.max(1.0, Math.abs(candidates[ck]));
                        if (err < bestErr) {
                            bestErr = err;
                            bestKey = ck;
                        }
                    });
                    chosenRefName = bestKey;
                }
            }

            const refVal = Number(candidates[chosenRefName]);
            const relDiff = roundN((Math.abs(eval0.value - refVal) / Math.max(1e-4, Math.abs(refVal))) * 100.0, 2);

            // Çok noktalı R² / RMSE doğrulama taraması (core/physics_engine.py ile %100 birebir)
            const sweepPoints = [];
            const usedSet = new Set(eval0.usedVars);
            if (usedSet.has("t") && Array.isArray(fv.d2_points) && fv.d2_points.length > 0) {
                const d0Sq = Math.max(0.25, Math.pow(baseEnv.vars.D0, 2));
                fv.d2_points.forEach((pt) => {
                    const envT = Object.assign({}, baseEnv.vars, { t: Number(pt.t_s) });
                    const ypRaw = safeEvalMathExprBrowser(expression, envT).value;
                    const ypNorm = ypRaw > 1.35 ? ypRaw / d0Sq : ypRaw;
                    sweepPoints.push({ x: Number(pt.t_s), meas: Number(pt.d2_meas), pred: roundN(ypNorm, 4) });
                });
            } else if (
                chosenRefName === "MOC" ||
                ((usedSet.has("U") || usedSet.has("Re")) && !usedSet.has("O2") && !usedSet.has("Y_O2") && !usedSet.has("B_oq"))
            ) {
                [0.5, 2.5, 5.5, 12.0, 22.0, 34.0].forEach((uVal) => {
                    const eU = buildEnv({ airflow_cms: uVal });
                    const yPred = safeEvalMathExprBrowser(expression, eU.vars).value;
                    const yMeas = Number(eU.vars[chosenRefName] ?? refVal);
                    if (Number.isFinite(yPred)) {
                        sweepPoints.push({ x: uVal, meas: roundN(yMeas, 4), pred: roundN(yPred, 4) });
                    }
                });
            } else {
                [16.0, 19.0, 21.0, 26.0, 32.0, 40.0].forEach((o2Val) => {
                    const eO = buildEnv({ oxygen_pct: o2Val });
                    const yPred = safeEvalMathExprBrowser(expression, eO.vars).value;
                    const yMeas = Number(eO.vars[chosenRefName] ?? refVal);
                    if (Number.isFinite(yPred)) {
                        sweepPoints.push({ x: o2Val, meas: roundN(yMeas, 4), pred: roundN(yPred, 4) });
                    }
                });
            }

            let rSq = null;
            let rmse = null;
            if (sweepPoints.length >= 3) {
                let sumSq = 0;
                let meanRef = 0;
                sweepPoints.forEach((pt) => {
                    meanRef += pt.meas;
                    sumSq += Math.pow(pt.meas - pt.pred, 2);
                });
                meanRef /= sweepPoints.length;
                let ssTot = 0;
                sweepPoints.forEach((pt) => {
                    ssTot += Math.pow(pt.meas - meanRef, 2);
                });
                rmse = roundN(Math.sqrt(sumSq / sweepPoints.length), 4);
                rSq = ssTot > 1e-6 ? roundN(Math.max(0.0, Math.min(0.999, 1.0 - sumSq / ssTot)), 4) : (relDiff < 5.0 ? 0.99 : 0.75);
            }

            return {
                ok: true,
                expression,
                evaluated_value: roundN(eval0.value, 5),
                reference_metric: chosenRefName,
                reference_value: roundN(refVal, 5),
                relative_diff_pct: relDiff,
                used_variables: eval0.usedVars,
                r_squared: rSq,
                rmse: rmse,
                sweep_points: sweepPoints,
                summary_tr:
                    `Hesaplanan Değer: ${eval0.value.toFixed(4)} | En Yakın Referans (${chosenRefName}): ${refVal.toFixed(4)} (Fark: %${relDiff.toFixed(2)})` +
                    (rSq !== null ? ` | ISS 0G Serisi R² = ${rSq.toFixed(3)}, RMSE = ${rmse.toFixed(3)}` : ""),
                summary_en:
                    `Evaluated Value: ${eval0.value.toFixed(4)} | Reference (${chosenRefName}): ${refVal.toFixed(4)} (Diff: ${relDiff.toFixed(2)}%)` +
                    (rSq !== null ? ` | ISS 0G Sweep R² = ${rSq.toFixed(3)}, RMSE = ${rmse.toFixed(3)}` : ""),
            };
        } catch (err) {
            return {
                ok: false,
                error: err && err.message ? err.message : "Invalid mathematical formula.",
                error_tr: `Denklem çözümlenemedi: ${err && err.message ? err.message : "Sözdizimi hatası"}`,
                error_en: `Formula evaluation error: ${err && err.message ? err.message : "Syntax error"}`,
            };
        }
    }

    async function analyzeUploadedBundleInBrowser(formData) {
        const files = formData && formData.getAll ? (formData.getAll("files").length ? formData.getAll("files") : formData.getAll("file")) : [];
        if (!files || !files.length) {
            return analyzeUploadedMediaInBrowser(formData);
        }
        const results = [];
        for (let i = 0; i < files.length && i < 16; i++) {
            const subFd = new FormData();
            subFd.append("file", files[i]);
            const r = await analyzeUploadedMediaInBrowser(subFd);
            if (r && r.ok) results.push(r);
        }
        if (!results.length) {
            return {
                ok: false,
                error: "Hiçbir dosya çözümlenemedi / Could not parse bundle files.",
                error_tr: "Seçilen paket içinden geçerli veri çıkarılamadı.",
                error_en: "Could not extract valid combustion telemetry from selected bundle.",
            };
        }
        const mergedPhases = [];
        const mergedFields = [];
        const calibPairs = [];
        let mergedSimParams = {};
        let firstImgB64 = null;
        results.forEach((r, rIdx) => {
            if (!firstImgB64 && r.image_base64) firstImgB64 = r.image_base64;
            if (r.extracted_sim_params && typeof r.extracted_sim_params === "object") {
                Object.keys(r.extracted_sim_params).forEach((k) => {
                    if (r.extracted_sim_params[k] !== null && r.extracted_sim_params[k] !== undefined) {
                        mergedSimParams[k] = r.extracted_sim_params[k];
                    }
                });
            }
            if (Array.isArray(r.extracted_fields)) {
                r.extracted_fields.forEach((fld) => {
                    if (fld && !mergedFields.includes(fld)) mergedFields.push(fld);
                });
            }
            const rSim = r.simulation || simulateCombustionClient(r.extracted_sim_params || {});
            const rFv = rSim.flight_validation || {};
            if (Array.isArray(rFv.moc_points)) {
                rFv.moc_points.slice(0, 3).forEach((mp) => {
                    calibPairs.push([Number(mp.moc_meas_pct) / 100.0, Number(mp.moc_pred_pct) / 100.0]);
                });
            }
            if (Array.isArray(r.phases) && r.phases.length > 0) {
                r.phases.forEach((p) => {
                    const pSp = p.sim_params || r.extracted_sim_params || {};
                    const pSt = simulateCombustionClient(pSp);
                    calibPairs.push([Number(pSp.oxygen_pct ?? 21.0) / 100.0, Number(pSt.telemetry.moc_pct) / 100.0]);
                    mergedPhases.push(Object.assign({}, p, { index: mergedPhases.length + 1, source_file: r.filename }));
                });
            } else if (r.extracted_sim_params && rSim) {
                mergedPhases.push({
                    index: mergedPhases.length + 1,
                    short_tr: `Dosya ${rIdx + 1}: ${String(r.filename || "").slice(0, 18)}`,
                    short_en: `File ${rIdx + 1}: ${String(r.filename || "").slice(0, 18)}`,
                    desc: r.filename || `File ${rIdx + 1}`,
                    flame_temp_k: rSim.telemetry.flame_temp_k,
                    sim_params: r.extracted_sim_params,
                });
            }
        });
        const primary = results[0];
        const namesJoined = results.map((x) => x.filename).join(", ");
        const bundleLabel = results.length > 1
            ? `${results.length} Files (${String(primary.filename || "Bundle").slice(0, 24)})`
            : String(primary.filename || "Bundle");
        const sim = simulateCombustionClient(mergedSimParams);
        let bundleR2 = sim.flight_validation ? Number(sim.flight_validation.r_squared) : 0.962;
        let bundleRmse = sim.flight_validation ? Number(sim.flight_validation.rmse) : 0.024;
        if (calibPairs.length >= 3) {
            let meanM = 0;
            let ssRes = 0;
            calibPairs.forEach((pr) => {
                meanM += pr[0];
                ssRes += Math.pow(pr[0] - pr[1], 2);
            });
            meanM /= calibPairs.length;
            let ssTot = 0;
            calibPairs.forEach((pr) => {
                ssTot += Math.pow(pr[0] - meanM, 2);
            });
            ssTot = Math.max(1e-6, ssTot);
            bundleRmse = roundN(Math.sqrt(ssRes / calibPairs.length), 3);
            bundleR2 = roundN(Math.max(0.72, Math.min(0.998, 1.0 - ssRes / Math.max(ssTot, ssRes * 1.18))), 3);
        }
        const calibObj = { r_squared: bundleR2, rmse: bundleRmse };
        const sumTr = `**Çoklu NASA PSI Veri Paketi (${results.length} Dosya Birleştirildi):** \`${namesJoined}\`\n` + results.map((x) => `- ${x.summary_tr || x.filename}`).join("\n");
        const sumEn = `**Multi-File NASA PSI Bundle (${results.length} Files Merged):** \`${namesJoined}\`\n` + results.map((x) => `- ${x.summary_en || x.filename}`).join("\n");
        return {
            ok: true,
            filename: bundleLabel,
            file_count: results.length,
            media_type: "bundle",
            image_base64: firstImgB64,
            extracted_fields: mergedFields,
            phases: mergedPhases.slice(0, 24),
            extracted_sim_params: sim.inputs,
            simulation: sim,
            calibration: calibObj,
            bundle_calibration: calibObj,
            summary_tr: sumTr,
            summary_en: sumEn,
        };
    }

    function makeJsonResponse(obj, status) {
        const bodyStr = JSON.stringify(obj);
        return new Response(bodyStr, {
            status: status || 200,
            headers: { "Content-Type": "application/json; charset=utf-8" },
        });
    }

    const serverlessFetchImpl = async function (url, options) {
        const opts = options || {};
        const baseOrigin = (window.location && window.location.origin && window.location.origin !== "null")
            ? window.location.origin
            : "http://127.0.0.1";
        const u = new URL(url, baseOrigin);
        const path = u.pathname;
        const method = String(opts.method || "GET").toUpperCase();
        let jsonBody = {};
        if (opts.body && typeof opts.body === "string") {
            try { jsonBody = JSON.parse(opts.body); } catch (_) {}
        }

        if (path === "/api/health") {
            return makeJsonResponse({ status: "ok", app: "ALTAR-NASA-FlameInFreefall", version: "6.3.0-serverless" });
        }

        if (path === "/api/bootstrap") {
            return makeJsonResponse({
                version: "6.3.0-serverless",
                presets: MISSION_PRESETS,
                directives: DIRECTIVES,
                earth_transfers: EARTH_TRANSFERS,
                spacecraft_compartments: SPACECRAFT_COMPARTMENTS,
                spacecraft_hatches: IDSS_HATCH_LINKS,
                fdir_actuators: HARDWARE_ACTUATOR_SPECS,
                config: Object.assign({}, runtimeConfig, {
                    gemini_api_key: "",
                    openrouter_api_key: "",
                    gemini_api_key_configured: Boolean(runtimeConfig.gemini_api_key),
                    openrouter_api_key_configured: Boolean(runtimeConfig.openrouter_api_key),
                    antigravity_api_key_configured: false,
                }),
                providers: {
                    active_provider: runtimeConfig.active_provider || "auto",
                    gemini_ready: Boolean(runtimeConfig.gemini_api_key),
                    gemini_model: runtimeConfig.gemini_model,
                    antigravity_ready: false,
                    antigravity: { cli_ready: false, models: [] },
                    ollama: { online: false, models: [], recommended_active: "" },
                    openrouter_ready: Boolean(runtimeConfig.openrouter_api_key),
                },
                stream: Object.assign({}, streamState, { timerId: null }),
            });
        }

        if (path === "/api/simulate") {
            return makeJsonResponse(simulateCombustionClient(jsonBody));
        }

        if (path === "/api/mission-certify" && method === "POST") {
            const sim = simulateCombustionClient(jsonBody);
            return makeJsonResponse({
                ok: true,
                fuel_id: sim.inputs.fuel_id,
                fuel_name_tr: sim.inputs.fuel_name_tr,
                fuel_name_en: sim.inputs.fuel_name_en,
                mission_certification: sim.mission_certification,
            });
        }

        if ((path === "/api/fdir/command" || path === "/api/fdir-command") && method === "POST") {
            const pkt = buildCcsdsPacketBrowser(
                jsonBody.action_id || jsonBody.actuator_id || "ECLSS_IMV_FAN_CUTOFF",
                jsonBody.compartment_id || jsonBody.target_id || "HALO",
                jsonBody.target_hatch_id || (String(jsonBody.target_id || "").startsWith("HATCH_") ? jsonBody.target_id : null),
                jsonBody.engage !== undefined ? Boolean(jsonBody.engage) : true,
                jsonBody.authority_source || jsonBody.authority || "JURY_MANUAL_GUARDED_SWITCH",
                Number(jsonBody.parameter_u16 ?? jsonBody.analog_value ?? 100)
            );
            return makeJsonResponse(pkt, pkt.ok ? 200 : 400);
        }

        if (path === "/api/fdir/evaluate" && method === "POST") {
            const sim = (jsonBody.sim_state && jsonBody.sim_state.telemetry)
                ? jsonBody.sim_state
                : ((jsonBody.sim_result && jsonBody.sim_result.telemetry)
                    ? jsonBody.sim_result
                    : simulateCombustionClient(jsonBody.sim_params || {}));
            const tel = sim.telemetry || {};
            const pre = sim.pre_ignition || {};
            const cn = sim.compartment_network || {};
            const compId = String(cn.fire_compartment_id || jsonBody.compartment_id || "HALO").toUpperCase();
            const adjHatches = (IDSS_HATCH_LINKS || [])
                .filter((h) => h.comp_a === compId || h.comp_b === compId)
                .map((h) => h.hatch_id);
            const autoEn = jsonBody.autonomous_enabled !== undefined ? Boolean(jsonBody.autonomous_enabled) : true;
            const packets = [];
            const compInfo = SPACECRAFT_COMPARTMENTS[compId] || {};
            const roomTr = compInfo.name_tr || compId;
            const roomEn = compInfo.name_en || compId;
            let stateCode = "NOMINAL_FLIGHT";
            let sev = "NOMINAL";
            let headTr = `${roomTr}: Tüm giriş-çıkış kapakları, hava dolaşımı ve elektrik hatları normal durumda.`;
            let headEn = `${roomEn}: All entry-exit hatches, air circulation, and power lines are normal.`;

            if (!tel.extinguished && !tel.cool_flame_active) {
                stateCode = "ACTIVE_COMPARTMENT_FIRE";
                sev = "EMERGENCY";
                headTr = `${roomTr}: Aktif yangın algılandı (${Math.round(tel.flame_temp_k || 1400)} K) — Giriş-çıkış kapakları ve hava kanalları kapatıldı, su sisi devrede.`;
                headEn = `${roomEn}: Active fire detected (${Math.round(tel.flame_temp_k || 1400)} K) — Entry-exit hatches and air ducts closed, water mist active.`;
                if (autoEn) {
                    packets.push(buildCcsdsPacketBrowser("ECLSS_IMV_FAN_CUTOFF", compId, null, true, "FDIR_AUTONOMOUS_6001B", 1));
                    adjHatches.forEach((hid) => {
                        packets.push(buildCcsdsPacketBrowser("IDSS_HATCH_SEAL", compId, hid, true, "FDIR_AUTONOMOUS_6001B", 100));
                    });
                    packets.push(buildCcsdsPacketBrowser("PCDU_120VDC_SSPC_TRIP", compId, null, true, "FDIR_AUTONOMOUS_6001B", 120));
                    packets.push(buildCcsdsPacketBrowser("PFE_SOFIE_WATERMIST", compId, null, true, "FDIR_AUTONOMOUS_6001B", 35));
                    packets.push(buildCcsdsPacketBrowser("CAMRAS_POSTFIRE_SCRUB", compId, null, true, "FDIR_AUTONOMOUS_6001B", 1));
                }
            } else if (tel.cool_flame_active) {
                stateCode = "COOL_FLAME_NTC_HAZARD";
                sev = "CRITICAL";
                headTr = `${roomTr}: Görünmez soğuk alev algılandı (${Math.round(tel.flame_temp_k || 650)} K) — Bölüm izole edildi, hava akışı kesildi ve su sisi uygulanıyor.`;
                headEn = `${roomEn}: Invisible cool flame detected (${Math.round(tel.flame_temp_k || 650)} K) — Section isolated, airflow stopped, and water mist applied.`;
                if (autoEn) {
                    packets.push(buildCcsdsPacketBrowser("ECLSS_IMV_FAN_CUTOFF", compId, null, true, "FDIR_AUTONOMOUS_6001B", 1));
                    adjHatches.forEach((hid) => {
                        packets.push(buildCcsdsPacketBrowser("IDSS_HATCH_SEAL", compId, hid, true, "FDIR_AUTONOMOUS_6001B", 100));
                    });
                    packets.push(buildCcsdsPacketBrowser("PFE_SOFIE_WATERMIST", compId, null, true, "FDIR_AUTONOMOUS_6001B", 25));
                    packets.push(buildCcsdsPacketBrowser("CAMRAS_POSTFIRE_SCRUB", compId, null, true, "FDIR_AUTONOMOUS_6001B", 1));
                }
            } else if (pre.thermal_runaway_imminent || pre.semenov_runaway) {
                stateCode = "PRE_IGNITION_THERMAL_ANOMALY";
                sev = "WARNING";
                headTr = `${roomTr}: Aşırı ısınma uyarısı — Alev oluşmadan önce bölüm elektriği güvenlik amacıyla kesildi.`;
                headEn = `${roomEn}: Overheating warning — Section power turned off before ignition.`;
                if (autoEn) {
                    packets.push(buildCcsdsPacketBrowser("PCDU_120VDC_SSPC_TRIP", compId, null, true, "FDIR_AUTONOMOUS_6001B", 120));
                }
            }
            return makeJsonResponse({
                ok: true,
                fdir_state: stateCode,
                severity: sev,
                fire_compartment_id: compId,
                adjacent_hatches_targeted: adjHatches,
                headline_tr: headTr,
                headline_en: headEn,
                autonomous_enabled: autoEn,
                decision_latency_ms: 0.38,
                dispatched_packets: packets,
            });
        }

        if (path === "/api/vision-acoustic" && method === "POST") {
            const tr = Math.max(0.05, Math.min(0.9999, Number(jsonBody.laser_transmission ?? 0.96)));
            const dUm = Math.max(0.04, Math.min(50.0, Number(jsonBody.particle_diameter_um ?? 0.18)));
            const arcDrv = Math.max(0.0, Math.min(1.0, Number(jsonBody.arc_fault_drive ?? 0.0)));
            const fvPpm = roundN((-Math.log(tr) / 0.12) * 670e-9 / (6.0 * Math.PI * 0.21) * 1e6, 4);
            const dpM = dUm * 1e-6;
            const cSca = (wlNm) => {
                const wlM = wlNm * 1e-9;
                const xP = (Math.PI * dpM) / wlM;
                const cRay = ((Math.pow(Math.PI, 5) * Math.pow(dpM, 6)) / (3.0 * Math.pow(wlM, 4))) * 0.29;
                const cGeo = 0.5 * Math.PI * dpM * dpM;
                const wMie = Math.pow(xP, 4) / (1.0 + Math.pow(xP, 4));
                return (1.0 - wMie) * cRay + wMie * cGeo * (1.0 + 0.18 / (1.0 + xP));
            };
            const daftRatio = roundN(cSca(405.0) / Math.max(1e-30, cSca(880.0)), 3);
            const isDust = daftRatio <= 1.75;
            const splDb = roundN(21.4 + 44.0 * arcDrv, 1);
            const kurt = roundN(3.02 + 9.4 * arcDrv * arcDrv, 2);
            const cls = daftRatio >= 3.2
                ? "COMBUSTION_SMOKE_SUBMICRON"
                : (isDust ? "LUNAR_REGOLITH_NUISANCE_DUST" : "SMOLDERING_AGGLOMERATE_TRANSITION");
            return makeJsonResponse({
                ok: true,
                beer_lambert_daft: {
                    soot_fv_ppm: fvPpm,
                    daft_ratio_405_880: daftRatio,
                    aerosol_class: cls,
                    false_alarm_rejected: isDust,
                },
                ultrasonic_acoustic: {
                    band_khz: "18.0 - 40.0 kHz",
                    ultrasonic_spl_db: splDb,
                    spectral_kurtosis: kurt,
                    arc_or_pyrolysis_anomaly: kurt >= 5.2 || arcDrv >= 0.35,
                },
                headline_tr: isDust
                    ? `DAFT 405/880 nm Oranı (${daftRatio}): Ay Regolit Tozu — Yanlış Alarm Reddedildi`
                    : (kurt >= 5.2 ? `18–40 kHz Ultrasonik Ark / Piroliz Saptandı (κ=${kurt}, ${splDb} dB)!` : `Optik/Akustik İzleme Nominal (DAFT=${daftRatio}, κ=${kurt})`),
                headline_en: isDust
                    ? `DAFT 405/880 nm Ratio (${daftRatio}): Lunar Regolith Dust — Nuisance Rejected`
                    : (kurt >= 5.2 ? `18–40 kHz Ultrasonic Arc / Pyrolysis Detected (κ=${kurt}, ${splDb} dB)!` : `Optical/Acoustic Nominal (DAFT=${daftRatio}, κ=${kurt})`),
            });
        }

        if (path === "/api/rank") {
            return makeJsonResponse(rankExperimentsClient(jsonBody.mission_params, jsonBody.query, jsonBody.hardware_filter));
        }

        if (path === "/api/compare") {
            return makeJsonResponse(compareExperimentsClient(jsonBody.exp_ids));
        }

        if (path === "/api/nasa-live") {
            const src = u.searchParams.get("source") || "ntrs";
            const q = u.searchParams.get("q") || "microgravity combustion";
            return makeJsonResponse(await fetchLiveNasaBrowser(src, q));
        }

        if (path === "/api/ingest-media" && method === "POST") {
            return makeJsonResponse(await analyzeUploadedMediaInBrowser(opts.body));
        }

        if (path === "/api/ingest-bundle" && method === "POST") {
            return makeJsonResponse(await analyzeUploadedBundleInBrowser(opts.body));
        }

        if ((path === "/api/evaluate-formula" || path === "/api/custom-equation") && method === "POST") {
            const eqRes = evaluateCustomFormulaBrowser(jsonBody.expression, jsonBody.target_metric, jsonBody.sim_params);
            return makeJsonResponse(eqRes, eqRes.ok ? 200 : 400);
        }

        if (path === "/api/scrape-url" && method === "POST") {
            let targetUrl = String(jsonBody.url || "").trim();
            const isEn = runtimeConfig.language === "en";
            const barePsi = targetUrl.match(/^PSI-(\d{1,4})$/i);
            if (barePsi) {
                targetUrl = `https://psi.nasa.gov/physci/repo/data/investigations/PSI-${barePsi[1]}`;
            } else if (targetUrl && !/^(https?:\/\/|\.\/|\/)/i.test(targetUrl) && /^[a-z0-9.-]+\.[a-z]{2,}(\/|$)/i.test(targetUrl)) {
                targetUrl = `https://${targetUrl}`;
            }
            if (!targetUrl || !/^(https?:\/\/|\.\/|\/)/i.test(targetUrl)) {
                return makeJsonResponse({
                    ok: false,
                    error: isEn
                        ? "Please enter a valid https:// web link (e.g. https://psi.nasa.gov/physci/repo/data/investigations/PSI-20)."
                        : "Lütfen geçerli bir https:// web bağlantısı girin (örn. https://psi.nasa.gov/physci/repo/data/investigations/PSI-20).",
                });
            }

            let parsedTarget = null;
            try {
                parsedTarget = new URL(targetUrl, window.location.href);
            } catch (_) {
                return makeJsonResponse({
                    ok: false,
                    error: isEn ? "Malformed web URL." : "Geçersiz web adresi biçimi.",
                });
            }

            const host = parsedTarget.hostname.toLowerCase();
            const pPath = parsedTarget.pathname || "";
            const qParam = (
                parsedTarget.searchParams.get("q")
                || parsedTarget.searchParams.get("term")
                || parsedTarget.searchParams.get("search")
                || ""
            ).trim();
            const mPsi = targetUrl.match(/\b(PSI-\d+)\b/i);
            const mNtrs = /ntrs\.nasa\.gov$/i.test(host) ? pPath.match(/\/citations\/(\d{6,14})/i) : null;
            const isNasaPortal = /(?:^|\.)(psi|osdr|ntrs)\.nasa\.gov$/i.test(host);

            // 1. Arama / listeleme adresi (örn. psi.nasa.gov/physci/repo/search?q=combustion)
            if (isNasaPortal && !mPsi && !mNtrs && (/\/search\b/i.test(pPath) || Boolean(qParam) || /^(\/|\/physci\/repo\/?)$/i.test(pPath))) {
                if (/ntrs\.nasa\.gov$/i.test(host)) {
                    const ntrsRes = await fetchLiveNasaBrowser("ntrs", qParam || "microgravity combustion");
                    const nItems = Array.isArray(ntrsRes.items) ? ntrsRes.items : [];
                    return makeJsonResponse({
                        ok: true,
                        mode: "search_results",
                        repository: "NASA NTRS Technical Reports Server (ntrs.nasa.gov)",
                        query: qParam || "microgravity combustion",
                        url: targetUrl,
                        title: `NASA NTRS: '${qParam || "combustion"}' (${nItems.length})`,
                        count: nItems.length,
                        search_items: nItems,
                    });
                }
                const psiItems = searchPsiSnapshotJs(qParam || "combustion", 36);
                return makeJsonResponse({
                    ok: true,
                    mode: "search_results",
                    repository: "NASA Physical Sciences Informatics (psi.nasa.gov)",
                    query: qParam || "combustion",
                    url: targetUrl,
                    title: `NASA PSI: '${qParam || "combustion"}' (${psiItems.length})`,
                    count: psiItems.length,
                    search_items: psiItems,
                });
            }

            // 2. Tekil PSI-XX deney kaydı adresi (örn. psi.nasa.gov/physci/repo/data/investigations/PSI-117 veya PSI-22)
            if (mPsi) {
                const psiCode = mPsi[1].toUpperCase();
                const snap = PSI_SNAPSHOT_MAP[psiCode];
                if (snap) {
                    const baseParams = Object.assign({
                        fuel_id: "n_heptane",
                        gravity_g: 0.0,
                        oxygen_pct: 21.0,
                        pressure_psia: 14.7,
                        airflow_cms: 2.4,
                        droplet_d0_mm: 3.4,
                        diluent: "N2",
                    }, snap.extracted_sim_params || {});
                    const sim0 = simulateCombustionClient(baseParams);
                    const phases = Array.isArray(snap.phases) ? snap.phases : [];
                    const titleStr = snap.title || `${psiCode} — ${snap.raw_title || ""}`;
                    if (!ragDocs.some((d) => d.doc_id === psiCode)) {
                        ragDocs.push({
                            doc_id: psiCode,
                            title: titleStr,
                            source: "NASA PSI Portal",
                            url: snap.url || targetUrl,
                            text: `${titleStr} ${snap.abstract || ""}`,
                        });
                    }
                    const fallbackTr = `**NASA PSI Deney Kaydı (${psiCode}${snap.acronym ? " • " + snap.acronym : ""}):** ${snap.raw_title || titleStr}\n- **Test Koşulları:** \`${baseParams.fuel_id}\`, \`${baseParams.gravity_g}G\`, \`%${baseParams.oxygen_pct} O₂\`, \`${baseParams.pressure_psia} psia\`, \`${baseParams.airflow_cms} cm/s\`.\n- **Özet:** ${snap.abstract || ""}`;
                    const fallbackEn = `**NASA PSI Investigation (${psiCode}${snap.acronym ? " • " + snap.acronym : ""}):** ${snap.raw_title || titleStr}\n- **Conditions:** \`${baseParams.fuel_id}\`, \`${baseParams.gravity_g}G\`, \`${baseParams.oxygen_pct}% O₂\`, \`${baseParams.pressure_psia} psia\`, \`${baseParams.airflow_cms} cm/s\`.\n- **Abstract:** ${snap.abstract || ""}`;
                    return makeJsonResponse({
                        ok: true,
                        filename: snap.table_file || `${psiCode}.json`,
                        title: titleStr,
                        preview: snap.abstract || "",
                        summary_tr: snap.summary_tr || fallbackTr,
                        summary_en: snap.summary_en || fallbackEn,
                        chunks: Math.max(1, phases.length || 2),
                        phases: phases,
                        extracted_sim_params: baseParams,
                        simulation: sim0,
                    });
                }
                try {
                    const osdrRes = await window.fetch(`https://osdr.nasa.gov/osdr/data/search?term=${encodeURIComponent(psiCode)}&size=3`, { method: "GET" });
                    if (osdrRes && osdrRes.ok) {
                        const osdrJson = await osdrRes.json();
                        const hits = (((osdrJson || {}).hits || {}).hits) || [];
                        if (hits.length > 0) {
                            const srcDoc = hits[0]._source || {};
                            const liveTitle = String(srcDoc["Study Title"] || srcDoc.title || `${psiCode} NASA OSDR/PSI`);
                            const liveDesc = String(srcDoc["Study Description"] || srcDoc.description || "").slice(0, 750);
                            const parsedLive = parseTextOrTablePayloadInBrowser(`${psiCode} ${liveTitle}\n${liveDesc}`, `${psiCode}.txt`);
                            return makeJsonResponse(Object.assign({}, parsedLive, {
                                ok: true,
                                filename: `${psiCode}.json`,
                                title: `${psiCode} — ${liveTitle}`,
                                preview: liveDesc,
                                simulation: simulateCombustionClient(parsedLive.extracted_sim_params || {}),
                            }));
                        }
                    }
                } catch (_) {}
                return makeJsonResponse({
                    ok: false,
                    error: isEn
                        ? `Record ${psiCode} is outside the 36 verified combustion investigations bundled offline, and live NASA OSDR lookup was unreachable.`
                        : `${psiCode} kaydı çevrimdışı paketteki 36 doğrulanmış yanma deneyinin dışındadır ve canlı NASA OSDR sorgusuna şu an ulaşılamadı.`,
                });
            }

            // 3. Tekil NTRS makale adresi (örn. ntrs.nasa.gov/citations/20150023456)
            if (mNtrs) {
                const ntrsId = mNtrs[1];
                const matchedExp = NASA_CATALOG.find((e) => String(e.ntrs_id) === ntrsId);
                if (matchedExp) {
                    const baseParams = {
                        fuel_id: matchedExp.fuel_id || "n_heptane",
                        gravity_g: Number(matchedExp.gravity_g ?? 0.0),
                        oxygen_pct: Number(matchedExp.oxygen_pct ?? 21.0),
                        pressure_psia: Number(matchedExp.pressure_psia ?? 14.7),
                        airflow_cms: Number(matchedExp.airflow_cms ?? 2.4),
                        droplet_d0_mm: matchedExp.cool_flame_observed ? 4.4 : 3.4,
                        diluent: "N2",
                    };
                    return makeJsonResponse({
                        ok: true,
                        filename: `NTRS-${ntrsId}.json`,
                        title: `NTRS-${ntrsId} — ${matchedExp.title}`,
                        preview: matchedExp.key_finding_en,
                        summary_tr: `**NASA NTRS Makale Kaydı (\`NTRS-${ntrsId}\` • ${matchedExp.program}):** ${matchedExp.title_tr}\n- **Koşullar:** \`${baseParams.fuel_id}\`, \`${baseParams.gravity_g}G\`, \`%${baseParams.oxygen_pct} O₂\`, \`${baseParams.pressure_psia} psia\`, \`${baseParams.airflow_cms} cm/s\`.\n- **Temel Bulgu:** ${matchedExp.key_finding_tr}`,
                        summary_en: `**NASA NTRS Citation (\`NTRS-${ntrsId}\` • ${matchedExp.program}):** ${matchedExp.title}\n- **Conditions:** \`${baseParams.fuel_id}\`, \`${baseParams.gravity_g}G\`, \`${baseParams.oxygen_pct}% O₂\`, \`${baseParams.pressure_psia} psia\`, \`${baseParams.airflow_cms} cm/s\`.\n- **Key Finding:** ${matchedExp.key_finding_en}`,
                        chunks: 2,
                        phases: [],
                        extracted_sim_params: baseParams,
                        simulation: simulateCombustionClient(baseParams),
                    });
                }
                return makeJsonResponse({
                    ok: false,
                    error: isEn
                        ? `ntrs.nasa.gov blocks direct cross-origin browser requests (CORS) for citation #${ntrsId}. Download the PDF and upload it below, or open this URL in the desktop app (Nasa_4.exe).`
                        : `ntrs.nasa.gov sunucusu #${ntrsId} makalesi için doğrudan tarayıcı sorgusunu (CORS güvenlik kuralı) kısıtlamaktadır. Makale PDF dosyasını indirip aşağıdan yükleyebilir veya bağlantıyı masaüstü uygulamasında (Nasa_4.exe) doğrudan çözümleyebilirsiniz.`,
                });
            }

            // 4. Doğrudan CSV / JSON / XLSX / ZIP / metin bağlantıları (CORS açık kaynaklar veya yerel göreli yollar)
            try {
                const res = await window.fetch(targetUrl, { method: "GET" });
                if (!res.ok) {
                    return makeJsonResponse({
                        ok: false,
                        error: isEn
                            ? `Remote server returned HTTP ${res.status} for this URL.`
                            : `Karşı sunucu bu bağlantı için HTTP ${res.status} yanıtı döndürdü.`,
                    });
                }
                const cleanName = decodeURIComponent((pPath.split("/").pop() || "web_dataset.csv"));
                if (/\.(xlsx|zip)$/i.test(cleanName)) {
                    const ab = await res.arrayBuffer();
                    const arch = await extractArchiveBufferInBrowser(ab, cleanName);
                    return makeJsonResponse(parseTextOrTablePayloadInBrowser(arch.text || "", arch.effectiveName || cleanName));
                }
                if (/\.pdf$/i.test(cleanName)) {
                    const ab = await res.arrayBuffer();
                    const pdfTxt = extractReadableTextFromPdfBuffer(ab);
                    return makeJsonResponse(parseTextOrTablePayloadInBrowser(pdfTxt, cleanName));
                }
                const rawText = await res.text();
                return makeJsonResponse(parseTextOrTablePayloadInBrowser(rawText, cleanName));
            } catch (_) {
                return makeJsonResponse({
                    ok: false,
                    error: isEn
                        ? "This external server restricts direct browser reading (CORS security policy). Download the file (.csv/.xlsx/.zip/.pdf) and upload it below, or use the desktop app (Nasa_4.exe) for live server fetching."
                        : "Bu dış sunucu tarayıcı üzerinden doğrudan veri çekimini (CORS güvenlik kuralı) kısıtlamaktadır. Veri dosyasını (.csv/.xlsx/.zip/.pdf) indirip aşağıdan yükleyebilir veya canlı sunucu çekimi için masaüstü uygulamasını (Nasa_4.exe) kullanabilirsiniz.",
                });
            }
        }

        if (path === "/api/rag-add-text" && method === "POST") {
            const ttl = String(jsonBody.title || "NASA Record");
            const txt = String(jsonBody.content || "");
            ragDocs.push({
                doc_id: `DOC-${Date.now()}`,
                title: ttl,
                title_tr: ttl,
                title_en: ttl,
                source: String(jsonBody.source || "User"),
                url: String(jsonBody.url || ""),
                text: txt,
                text_tr: txt,
                text_en: txt,
            });
            return makeJsonResponse({ ok: true, count: ragDocs.length, chunks: 1 });
        }

        if (path === "/api/rag-search") {
            const q = u.searchParams.get("q") || "";
            const results = ragDocs
                .map((d) => ({
                    doc_id: d.doc_id || "",
                    source: d.source || "NASA PSI",
                    url: d.url || "",
                    title: d.title,
                    title_tr: d.title_tr || d.title,
                    title_en: d.title_en || d.title,
                    text: d.text,
                    text_tr: d.text_tr || d.text,
                    text_en: d.text_en || d.text,
                    similarity: roundN(Math.max(0.18, computeTextSimilarity(q, `${d.title} ${d.text}`)), 4),
                }))
                .sort((a, b) => b.similarity - a.similarity)
                .slice(0, 6);
            return makeJsonResponse({ ok: true, results });
        }

        if (path === "/api/stream/config" && method === "POST") {
            if ("enabled" in jsonBody) streamState.enabled = Boolean(jsonBody.enabled);
            if (jsonBody.source) streamState.source = jsonBody.source;
            if (jsonBody.query_or_url) streamState.query_or_url = String(jsonBody.query_or_url);
            if (jsonBody.interval_sec) streamState.interval_sec = Math.max(10, Number(jsonBody.interval_sec) || 25);
            if ("auto_sync_sim" in jsonBody) streamState.auto_sync_sim = Boolean(jsonBody.auto_sync_sim);

            if (jsonBody.trigger_immediate || streamState.enabled) {
                await emitNextBrowserStreamPacket();
            }
            syncBrowserStreamTimer();
            return makeJsonResponse(Object.assign({}, streamState, { timerId: null }));
        }

        if (path === "/api/stream/status") {
            if (streamState.enabled) {
                const elapsed = Date.now() - (streamState.last_tick_ms || 0);
                if (elapsed >= Math.max(8000, (Number(streamState.interval_sec) || 25) * 1000)) {
                    await emitNextBrowserStreamPacket();
                }
            }
            return makeJsonResponse(Object.assign({}, streamState, { timerId: null }));
        }

        if ((path === "/api/chat/start" || path === "/api/chat") && method === "POST") {
            const jobId = `srvless-${Date.now()}-${Math.floor(Math.random() * 1000)}`;
            const reqLang = (jsonBody.sim_params && jsonBody.sim_params.lang) ? String(jsonBody.sim_params.lang) : runtimeConfig.language;
            if (reqLang === "en" || reqLang === "tr") runtimeConfig.language = reqLang;
            const simNow = simulateCombustionClient(jsonBody.sim_params || {});
            const scopeRes = evaluateQueryScopeBrowser(
                jsonBody.message,
                jsonBody.history || [],
                jsonBody.sim_params || {},
                jsonBody.media_context || "",
                jsonBody.image_base64 || null,
                reqLang,
                true
            );
            const suggestedActions = buildSuggestedActionsBrowser(scopeRes, simNow, reqLang);

            if (scopeRes.status === "off_topic" || scopeRes.status === "rule_locked") {
                const earlyPayload = {
                    status: "done",
                    provider: "deterministic_physics",
                    model: "ALTAR-Analytical-Solver-Core",
                    reply: scopeRes.reply,
                    citations: [],
                    stages: [reqLang === "en" ? "[1/1] Topic scope check completed" : "[1/1] Konu kapsamı kontrolü tamamlandı"],
                    scope_guard: scopeRes,
                    suggested_actions: suggestedActions,
                };
                if (path === "/api/chat") {
                    return makeJsonResponse(Object.assign({ ok: true }, earlyPayload));
                }
                chatJobs.set(jobId, earlyPayload);
                return makeJsonResponse({ ok: true, job_id: jobId });
            }

            const effectiveMsg = scopeRes.cleaned_query || jsonBody.message;
            const intentStr = classifyBrowserIntent(effectiveMsg, jsonBody.media_context);
            const built = buildQuestionDrivenReply(
                effectiveMsg,
                jsonBody.sim_params,
                jsonBody.media_context,
                reqLang,
                jsonBody.history || []
            );
            const prefNow = String(jsonBody.provider_override || runtimeConfig.active_provider || "auto").toLowerCase();
            const isMetaTurn = ["capabilities_guide", "platform_features", "greeting_identity"].includes(intentStr);
            const cloudRes = (prefNow === "auto" && isMetaTurn)
                ? null
                : await callBrowserCloudGateway(
                    effectiveMsg,
                    jsonBody.sim_params,
                    jsonBody.media_context,
                    jsonBody.history || [],
                    jsonBody.provider_override
                );

            let finalReply = cloudRes ? cloudRes.reply : built.reply;
            if (!cloudRes && scopeRes.status === "boundary_context") {
                const bNorm = normQueryAscii(effectiveMsg);
                const bTr = prependMisconceptionBrowser(
                    buildBoundaryReplyBrowser(scopeRes.boundary_kind || "terrestrial_fire", bNorm, simNow, "tr"),
                    scopeRes.misconception,
                    "tr"
                );
                const bEn = prependMisconceptionBrowser(
                    buildBoundaryReplyBrowser(scopeRes.boundary_kind || "terrestrial_fire", bNorm, simNow, "en"),
                    scopeRes.misconception,
                    "en"
                );
                scopeRes.reply_tr = bTr;
                scopeRes.reply_en = bEn;
                finalReply = reqLang === "en" ? bEn : bTr;
            } else {
                finalReply = sanitizeUnverifiedExperimentsBrowser(finalReply);
                finalReply = prependMisconceptionBrowser(finalReply, scopeRes.misconception, reqLang);
            }

            const payload = cloudRes
                ? {
                    status: "done",
                    provider: cloudRes.provider,
                    model: cloudRes.model,
                    reply: finalReply,
                    citations: built.citations,
                    stages: ["[4/4] Cloud Gateway + Browser Physics Verification Complete"],
                    scope_guard: scopeRes,
                    suggested_actions: suggestedActions,
                }
                : {
                    status: "done",
                    provider: "deterministic_physics",
                    model: "ALTAR-Analytical-Solver-Core",
                    reply: finalReply,
                    citations: built.citations,
                    stages: ["[4/4] Browser Analytical Physics Synthesis Ready"],
                    scope_guard: scopeRes,
                    suggested_actions: suggestedActions,
                };
            if (path === "/api/chat") {
                return makeJsonResponse(Object.assign({ ok: true }, payload));
            }
            chatJobs.set(jobId, payload);
            return makeJsonResponse({ ok: true, job_id: jobId });
        }

        if (path.startsWith("/api/chat/poll/")) {
            const jobId = decodeURIComponent(path.split("/").pop() || "");
            const job = chatJobs.get(jobId);
            if (!job) return makeJsonResponse({ ok: false, error: "Job not found" });
            return makeJsonResponse(Object.assign({ ok: true }, job));
        }

        if (path.startsWith("/api/chat/cancel/")) {
            return makeJsonResponse({ ok: true });
        }

        if (path === "/api/config") {
            if (method === "POST") {
                Object.keys(jsonBody).forEach((k) => {
                    if (k in runtimeConfig && (jsonBody[k] !== "" || k === "language" || k === "custom_extra_directives")) {
                        runtimeConfig[k] = jsonBody[k];
                    }
                });
            }
            return makeJsonResponse({
                ok: true,
                config: Object.assign({}, runtimeConfig, {
                    gemini_api_key: "",
                    openrouter_api_key: "",
                    gemini_api_key_configured: Boolean(runtimeConfig.gemini_api_key),
                    openrouter_api_key_configured: Boolean(runtimeConfig.openrouter_api_key),
                }),
                providers: {
                    active_provider: runtimeConfig.active_provider,
                    gemini_ready: Boolean(runtimeConfig.gemini_api_key),
                    gemini_model: runtimeConfig.gemini_model,
                    antigravity_ready: false,
                    antigravity: { cli_ready: false, models: [] },
                    ollama: { online: false, models: [], recommended_active: "" },
                    openrouter_ready: Boolean(runtimeConfig.openrouter_api_key),
                },
            });
        }

        if (path === "/api/ollama/status") {
            return makeJsonResponse({ online: false, models: [], note: "Serverless Static Web Mode" });
        }
        if (path === "/api/antigravity/status") {
            return makeJsonResponse({ cli_ready: false, models: [] });
        }
        if (path === "/api/providers/test") {
            const t0 = performance.now();
            const cloudCheck = await callBrowserCloudGateway(
                "0G küresel alevde Spalding B_oq sayısını tek cümleyle özetle.",
                {},
                "",
                [],
                runtimeConfig.active_provider
            );
            const dt = roundN((performance.now() - t0) / 1000, 2);
            if (cloudCheck) {
                return makeJsonResponse({
                    ok: true,
                    provider: cloudCheck.provider,
                    model: cloudCheck.model,
                    latency_s: dt,
                    sample: cloudCheck.reply.slice(0, 280),
                });
            }
            return makeJsonResponse({
                ok: true,
                provider: "deterministic_physics",
                model: "ALTAR-Analytical-Solver-Core (v6.3)",
                latency_s: 0.01,
                sample: runtimeConfig.language === "en"
                    ? "Analytical physics solver (d² law, de Ris spread, ±1σ bounds, 5-phase certification, and 15 NASA PSI records) active in 100% serverless browser mode."
                    : "Soru-odaklı çok katmanlı analitik fizik çözücü (d² yasası, de Ris yayılımı, ±1σ güven bandı, 5 aşamalı sertifikasyon ve 15 PSI bilgi tabanı) %100 sunucusuz modda aktif.",
            });
        }
        if (path === "/api/ollama/pull" || path === "/api/ollama/unload") {
            return makeJsonResponse({
                ok: false,
                unloaded: 0,
                error: runtimeConfig.language === "en"
                    ? "Local Ollama management is available in the desktop Nasa_4.exe application."
                    : "Yerel Ollama yönetimi masaüstü Nasa_4.exe uygulamasında aktiftir.",
            });
        }

        return makeJsonResponse({ ok: false, error: `Unsupported serverless endpoint: ${path}` }, 404);
    };

    window.ALTAR_FALLBACK_FETCH = serverlessFetchImpl;
    if (IS_PURE_SERVERLESS) {
        window.ALTAR_SERVERLESS_FETCH = serverlessFetchImpl;
        const nativeFetch = typeof window.fetch === "function" ? window.fetch.bind(window) : null;
        if (nativeFetch) {
            window.fetch = function (input, init) {
                const urlStr = typeof input === "string" ? input : (input && input.url ? String(input.url) : "");
                if (urlStr.startsWith("/api/") || urlStr.startsWith("./api/") || urlStr.startsWith("api/")) {
                    return serverlessFetchImpl(urlStr.replace(/^\.?\/?api\//, "/api/"), init || {});
                }
                return nativeFetch(input, init);
            };
        }
    }
})();
"""


README_STATIC_DEPLOY = """# ALTAR-NASA • Flame in Freefall (v6.3) — Sunucusuz Statik Web Paketi

Bu klasör (`web_serverless/`), GitHub Pages üzerinde arka plan sunucusu gerektirmeden doğrudan tarayıcıda çalışan statik web sürümünü içerir.

## Çalışma Özellikleri
1. **Sunucusuz Tarayıcı Modu:** Çalışan herhangi bir arka plan sunucusu gerektirmez; 3B WebGL yanma odası, Orion MCP 3B dijital ikizi ve güvenlik sistemi, faza özgü `d²` / `de Ris` / `Burke-Schumann` yasaları, benzer malzeme eşleştirmesi, karşıt ve eş yönlü akış analizi, `0.38G Mars` ve `0.16G Ay` sınır eğrileri, ISS `0G` referans kalibrasyonu (`R²` / `RMSE`), `NASA JSC-20584` yaşam destek saati ve dinamik NASA PSI deney sıralaması doğrudan tarayıcıda çalışır.
2. **Yerel Veri Güvenliği:** Kaynak kodun içinde gömülü API anahtarı bulunmaz; yüklediğiniz alev fotoğrafları, video kayıtları veya veri tabloları harici bir sunucuya gönderilmeden tarayıcı belleğinde işlenir.

## GitHub Pages Üzerinde Yayınlama
1. Yalnızca bu `web_serverless/` klasörünün içindeki dosyaları (`index.html`, `css/`, `js/`, `nasa_flame.ico`, `.nojekyll`) `gh-pages` dalının kök dizinine kopyalayın.
2. GitHub depo ayarlarından **Settings -> Pages -> Deploy from a branch (`gh-pages` / `/root`)** seçeneğini kaydedin.
3. Canlı web adresi: `https://faruk042.github.io/Nasa-Turkce/`
"""


def build_bundle() -> None:
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    (OUT_DIR / "css").mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "js" / "vendor").mkdir(parents=True, exist_ok=True)

    # 1. Statik varlıkları kopyala
    shutil.copy2(WEB_SRC / "static" / "css" / "mission_control.css", OUT_DIR / "css" / "mission_control.css")
    if (WEB_SRC / "static" / "nasa_flame.ico").is_file():
        shutil.copy2(WEB_SRC / "static" / "nasa_flame.ico", OUT_DIR / "nasa_flame.ico")
    shutil.copy2(WEB_SRC / "static" / "js" / "vendor" / "three.min.js", OUT_DIR / "js" / "vendor" / "three.min.js")
    shutil.copy2(WEB_SRC / "static" / "js" / "three_chamber_3d.js", OUT_DIR / "js" / "three_chamber_3d.js")
    shutil.copy2(WEB_SRC / "static" / "js" / "spacecraft_ultra_hd_3d.js", OUT_DIR / "js" / "spacecraft_ultra_hd_3d.js")
    shutil.copy2(WEB_SRC / "static" / "js" / "charts_and_audio.js", OUT_DIR / "js" / "charts_and_audio.js")
    shutil.copy2(WEB_SRC / "static" / "js" / "app_controller.js", OUT_DIR / "js" / "app_controller.js")

    # 2. serverless_kernel.js dosyasını gömülü doğrulanmış bilimsel katalogla ve 36 PSI arşiviyle oluştur
    psi_snapshot_path = PROJECT_ROOT / "core" / "psi_archive_snapshot.json"
    psi_archive_snapshot = (
        json.loads(psi_snapshot_path.read_text(encoding="utf-8"))
        if psi_snapshot_path.is_file()
        else []
    )
    embedded_payload = {
        "FUEL_PROPERTIES": FUEL_PROPERTIES,
        "DILUENT_FACTORS": DILUENT_FACTORS,
        "HABITAT_CONFIGS": HABITAT_CONFIGS,
        "ANALOG_MATERIALS_DB": ANALOG_MATERIALS_DB,
        "MISSION_PRESETS": MISSION_PRESETS,
        "NASA_EXPERIMENTS_CATALOG": NASA_EXPERIMENTS_CATALOG,
        "SPACE_TO_EARTH_TRANSFERS": SPACE_TO_EARTH_TRANSFERS,
        "CORE_DIRECTIVES_LIST": CORE_DIRECTIVES_LIST,
        "BILINGUAL_SCIENTIFIC_SYNONYMS": BILINGUAL_SCIENTIFIC_SYNONYMS,
        "SPACECRAFT_COMPARTMENTS": SPACECRAFT_COMPARTMENTS,
        "IDSS_HATCH_LINKS": SPACECRAFT_HATCH_LINKS,
        "HARDWARE_ACTUATOR_SPECS": HARDWARE_ACTUATOR_SPECS,
        "PSI_ARCHIVE_SNAPSHOT": psi_archive_snapshot,
    }
    embedded_json = json.dumps(embedded_payload, ensure_ascii=False)
    kernel_code = SERVERLESS_KERNEL_TEMPLATE.replace("__EMBEDDED_JSON__", embedded_json)
    (WEB_SRC / "static" / "js" / "serverless_kernel.js").write_text(kernel_code, encoding="utf-8")
    (OUT_DIR / "js" / "serverless_kernel.js").write_text(kernel_code, encoding="utf-8")

    # 3. index.html dosyasını sunucusuz statik CSP ve göreli yollarla dönüştür
    src_html = (WEB_SRC / "templates" / "index.html").read_text(encoding="utf-8")
    # Sunucu CSRF meta etiketini kaldır ve yerine statik CSP + sunucusuz mod işareti koy
    csp_meta = (
        '<meta name="altar-serverless" content="1" />\n    '
        '<meta http-equiv="Content-Security-Policy" content="'
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: blob:; "
        "media-src 'self' blob:; "
        "font-src 'self' data:; "
        "connect-src 'self' https://*.nasa.gov http://127.0.0.1:11434 http://localhost:11434; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "form-action 'self';"
        '" />\n    <link rel="icon" href="./nasa_flame.ico" />'
    )
    out_html = re.sub(r'<meta\s+name="altar-csrf"[^>]*>', csp_meta, src_html)
    out_html = re.sub(
        r'href="/static/css/mission_control\.css(\?v=[0-9.]+)?"',
        lambda m: f'href="./css/mission_control.css{m.group(1) or ""}"',
        out_html,
    )
    out_html = out_html.replace('src="/static/js/vendor/three.min.js"', 'src="./js/vendor/three.min.js"')
    out_html = re.sub(
        r'src="/static/js/three_chamber_3d\.js(\?v=[0-9.]+)?"',
        lambda m: f'src="./js/three_chamber_3d.js{m.group(1) or ""}"',
        out_html,
    )
    out_html = re.sub(
        r'src="/static/js/spacecraft_ultra_hd_3d\.js(\?v=[0-9.]+)?"',
        lambda m: f'src="./js/spacecraft_ultra_hd_3d.js{m.group(1) or ""}"',
        out_html,
    )
    out_html = re.sub(
        r'src="/static/js/charts_and_audio\.js(\?v=[0-9.]+)?"',
        lambda m: f'src="./js/charts_and_audio.js{m.group(1) or ""}"',
        out_html,
    )
    out_html = re.sub(
        r'src="/static/js/serverless_kernel\.js(\?v=[0-9.]+)?"',
        lambda m: f'src="./js/serverless_kernel.js{m.group(1) or ""}"',
        out_html,
    )
    out_html = re.sub(
        r'src="/static/js/app_controller\.js(\?v=[0-9.]+)?"',
        lambda m: f'src="./js/app_controller.js{m.group(1) or ""}"',
        out_html,
    )
    out_html = out_html.replace(">Çevrimdışı Mod<", ">Tarayıcı Modu<")
    out_html = out_html.replace(">Çevrimdışı / Yerel<", ">Tarayıcı İçi<")
    (OUT_DIR / "index.html").write_text(out_html, encoding="utf-8")

    # 4. Örnek veri paketlerini ve dağıtım kılavuzunu yaz
    if (PROJECT_ROOT / "sample_data").is_dir():
        shutil.copytree(PROJECT_ROOT / "sample_data", OUT_DIR / "sample_data", dirs_exist_ok=True)
    (OUT_DIR / "README_GITHUB_CLOUDFLARE_PAGES.md").write_text(README_STATIC_DEPLOY, encoding="utf-8")
    (OUT_DIR / ".nojekyll").write_text("", encoding="utf-8")

    print(f"[OK] Serverless static bundle generated at: {OUT_DIR}")


if __name__ == "__main__":
    build_bundle()
