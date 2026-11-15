# -*- coding: utf-8 -*-
"""
ALTAR-NASA v6.3 Deterministik FDIR (Fault Detection, Isolation, and Recovery) Otonom Müdahale Motoru
ve Gerçek Uzay Aracı Donanım Veri Yolu (CCSDS 133.0-B-2 + TTEthernet SAE AS6802 + MIL-STD-1553B) Üreteci.

Mimari Ayrım (Sıfır "AI Wrapper" Prensibi):
1) Birincil Milisaniye Güvenlik Katmanı: Deterministik NASA-STD-6001B FDIR Durum Makinesi (< 1 ms).
   Fiziksel/kimyasal eşikler (Semenov ψ, Frank-Kamenetskii δ, MWIR dT/dt, DAFT duman/toz oranı, ΔP ve FED)
   aşıldığında dil modelini beklemeden donanım komutlarını üretir; Halon 1301'i donanımsal olarak engeller.
2) İkincil Bilimsel Yardımcı Pilot (Seçili AI Motoru): FDIR kararını ve fiziksel kök nedeni PSI literatürüyle yorumlar.
3) Üçüncül Jüri Korumalı Manuel Donanım Anahtarları (Guarded Switches): İstenen aktüatöre doğrudan gerçek
   CCSDS Space Packet (APID + SeqCount + CRC-16-CCITT 0x1021), TTEthernet Virtual Link ve MIL-STD-1553B çerçevesi yollar.
"""

from __future__ import annotations

import socket
import struct
import threading
import time
from typing import Any, Dict, List, Optional

from core.compartment_network import SPACECRAFT_COMPARTMENTS, SPACECRAFT_HATCH_LINKS

_SEQ_LOCK = threading.Lock()
_APID_SEQ_COUNTERS: Dict[int, int] = {}
_COMMAND_HISTORY: List[Dict[str, Any]] = []

COMPARTMENT_ENUM: Dict[str, int] = {
    "ORION_CM": 0x01,
    "HALO": 0x02,
    "IHAB": 0x03,
    "PPE": 0x04,
    "AIRLOCK": 0x05,
}

HATCH_ENUM: Dict[str, int] = {
    "HATCH_ORION_HALO": 0x11,
    "HATCH_HALO_IHAB": 0x12,
    "HATCH_HALO_PPE": 0x13,
    "HATCH_IHAB_AIRLOCK": 0x14,
}

HARDWARE_ACTUATOR_SPECS: Dict[str, Dict[str, Any]] = {
    "IDSS_HATCH_SEAL": {
        "apid": 0x0210,
        "ttethernet_vl": 0x4101,
        "mil1553_rt": 4,
        "mil1553_sa": 1,
        "opcode": 0xA1,
        "title_tr": "IDSS Bölmeler Arası Motorlu Kapak İzolasyonu",
        "title_en": "IDSS Inter-Module Motorized Bulkhead Hatch Seal",
        "standard": "IDSS Rev-F / NASA-STD-6001B",
        "subsystem": "STRUCTURAL_ECLSS_ISOLATION",
    },
    "ECLSS_IMV_FAN_CUTOFF": {
        "apid": 0x0214,
        "ttethernet_vl": 0x4102,
        "mil1553_rt": 6,
        "mil1553_sa": 2,
        "opcode": 0xB2,
        "title_tr": "ECLSS IMV & Kabin Havalandırma Fan Kesme (U → 0 cm/s)",
        "title_en": "ECLSS IMV & Cabin HVAC Fan Cutoff (U → 0 cm/s)",
        "standard": "NASA-STD-6001B Step-1",
        "subsystem": "ECLSS_VENTILATION",
    },
    "PCDU_120VDC_SSPC_TRIP": {
        "apid": 0x0218,
        "ttethernet_vl": 0x4104,
        "mil1553_rt": 9,
        "mil1553_sa": 4,
        "opcode": 0xC4,
        "title_tr": "120V DC PCDU Katı-Hal Güç Kesici (SSPC) Bara İzolasyonu",
        "title_en": "120V DC PCDU Solid-State Power Controller (SSPC) Bus Trip",
        "standard": "SSP 30482 / Gateway EPS",
        "subsystem": "EPS_PCDU_120VDC",
    },
    "PFE_SOFIE_WATERMIST": {
        "apid": 0x0220,
        "ttethernet_vl": 0x4108,
        "mil1553_rt": 11,
        "mil1553_sa": 5,
        "opcode": 0xD8,
        "title_tr": "SoFIE-MIST İnce Su Sisi (25–40 µm) / CO₂ Söndürme Deşarjı",
        "title_en": "SoFIE-MIST Fine Water Mist (25–40 µm) / CO₂ PFE Discharge",
        "standard": "NTRS-20200000361 • Halon 1301 YASAK",
        "subsystem": "FIRE_SUPPRESSION_PFE",
    },
    "CAMRAS_POSTFIRE_SCRUB": {
        "apid": 0x0228,
        "ttethernet_vl": 0x4110,
        "mil1553_rt": 14,
        "mil1553_sa": 7,
        "opcode": 0xE5,
        "title_tr": "CAMRAS / Katalitik CO & Asit Gazı Kabin Temizleme Döngüsü",
        "title_en": "CAMRAS / Catalytic CO & Acid-Gas Post-Fire Scrubbing Loop",
        "standard": "NASA JSC-20584 SMAC Recovery",
        "subsystem": "ECLSS_ARS_SCRUBBER",
    },
}


def compute_crc16_ccitt(data: bytes, poly: int = 0x1021, init_val: int = 0xFFFF) -> int:
    """CCSDS 133.0-B-2 & ECSS-E-ST-70-41C standart 16-bit CRC-CCITT (0x1021, başlangıç 0xFFFF)."""
    crc = init_val & 0xFFFF
    for byte in data:
        crc ^= (byte & 0xFF) << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ poly) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc & 0xFFFF


def _next_seq_count(apid: int) -> int:
    with _SEQ_LOCK:
        cur = _APID_SEQ_COUNTERS.get(apid, 0)
        _APID_SEQ_COUNTERS[apid] = (cur + 1) & 0x3FFF
        return cur


def build_ccsds_hardware_packet(
    action_id: str,
    compartment_id: str = "HALO",
    target_hatch_id: Optional[str] = None,
    engage: bool = True,
    authority_source: str = "FDIR_AUTONOMOUS",
    parameter_u16: int = 100,
    udp_loopback_port: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Gerçek CCSDS 133.0-B-2 Telecommand Space Packet + TTEthernet VL + MIL-STD-1553B Komut Kelimesi üretir.
    Paket Yapısı (Toplam 18 Bayt):
      - Byte 0..1 : CCSDS Packet ID -> Version(000) | Type(1=TC) | SecHdr(1) | APID(11-bit)
      - Byte 2..3 : CCSDS Packet Seq Control -> SeqFlags(11=Unsegmented) | SeqCount(14-bit)
      - Byte 4..5 : CCSDS Packet Data Length -> (Toplam Uygulama Verisi + CRC Uzunluğu - 1) = 11 (12 bayt)
      - Byte 6..7 : TTEthernet SAE AS6802 Virtual Link ID (uint16 big-endian)
      - Byte 8..9 : MIL-STD-1553B Command Word -> (RT<<11) | (T/R=0<<10) | (SA<<5) | WordCount(6)
      - Byte 10   : Donanım Opcode (0xA1..0xE5)
      - Byte 11   : Bölme Kodu (ORION_CM=0x01 .. AIRLOCK=0x05)
      - Byte 12   : Hedef Kapak Kodu (0x00 veya 0x11..0x14)
      - Byte 13   : Durum Bayrağı -> bit7: Engage(1/0), bit6: Autonomous(1)/Manual(0), bit0: HalonInterlockBlocked(1)
      - Byte 14..15: Sayısal Parametre (örn. su sisi darbe süresi s veya SSPC kanal maskesi, uint16)
      - Byte 16..17: CRC-16-CCITT (0x1021) Doğrulama Özeti
    """
    if action_id.upper() in ("HALON_1301", "HALON_DISCHARGE"):
        return {
            "ok": False,
            "blocked_by_interlock": True,
            "error_code": "NASA_STD_6001B_HALON_FORBIDDEN",
            "message_tr": "DONANIM KİLİDİ: NASA-STD-6001B uyarınca kapalı uzay aracı kabininde Halon 1301 kullanımı HF/HBr toksisitesi nedeniyle engellendi!",
            "message_en": "HARDWARE INTERLOCK: Halon 1301 discharge blocked per NASA-STD-6001B due to toxic HF/HBr pyrolysis products!",
        }

    spec = HARDWARE_ACTUATOR_SPECS.get(action_id, HARDWARE_ACTUATOR_SPECS["ECLSS_IMV_FAN_CUTOFF"])
    comp_key = compartment_id if compartment_id in COMPARTMENT_ENUM else "HALO"
    comp_byte = COMPARTMENT_ENUM[comp_key]
    hatch_byte = HATCH_ENUM.get(target_hatch_id or "", 0x00)

    apid = int(spec["apid"]) & 0x07FF
    seq_count = _next_seq_count(apid)

    # CCSDS Primary Header (6 Bytes)
    # Version=0 (3b), Type=1 TC (1b), SecHdr=1 (1b) -> 0b0001_1000_0000_0000 = 0x1800
    pkt_id = 0x1800 | apid
    # SeqFlags=3 (0b11 unsegmented) -> 0xC000
    pkt_seq_ctrl = 0xC000 | (seq_count & 0x3FFF)

    tt_vl = int(spec["ttethernet_vl"]) & 0xFFFF
    rt_addr = int(spec["mil1553_rt"]) & 0x1F
    sub_addr = int(spec["mil1553_sa"]) & 0x1F
    word_count = 6
    mil1553_cmd_word = (rt_addr << 11) | (0 << 10) | (sub_addr << 5) | word_count

    is_auto = 1 if authority_source.startswith("FDIR") else 0
    state_flags = ((1 if engage else 0) << 7) | (is_auto << 6) | 0x01  # bit0=1: Halon hardware lock active
    try:
        param_raw = 100 if (parameter_u16 is None or isinstance(parameter_u16, bool)) else int(float(parameter_u16))
    except (TypeError, ValueError, OverflowError):
        param_raw = 100
    param_clamped = max(0, min(65535, param_raw))

    # Uygulama alanı (10 bayt) + CRC16 (2 bayt) = 12 bayt -> CCSDS length field = 12 - 1 = 11
    ccsds_data_len = 12 - 1
    header_and_body = struct.pack(
        ">HHHHHBBBBH",
        pkt_id,
        pkt_seq_ctrl,
        ccsds_data_len,
        tt_vl,
        mil1553_cmd_word,
        int(spec["opcode"]) & 0xFF,
        comp_byte,
        hatch_byte,
        state_flags,
        param_clamped,
    )
    crc16 = compute_crc16_ccitt(header_and_body)
    full_packet = header_and_body + struct.pack(">H", crc16)
    hex_spaced = " ".join(f"{b:02X}" for b in full_packet)
    ascii_serial = (
        f"$ALTAR,TC,{action_id},{comp_key},{target_hatch_id or 'NONE'},"
        f"{1 if engage else 0},{authority_source},0x{crc16:04X}*\r\n"
    )

    udp_dispatched = False
    udp_port_clean: Optional[int] = None
    if udp_loopback_port is not None and not isinstance(udp_loopback_port, bool):
        try:
            udp_port_clean = int(float(udp_loopback_port))
        except (TypeError, ValueError, OverflowError):
            udp_port_clean = None
    if udp_port_clean is not None and 1024 <= udp_port_clean <= 65535:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.settimeout(0.05)
                sock.sendto(full_packet, ("127.0.0.1", udp_port_clean))
                udp_dispatched = True
        except OSError:
            udp_dispatched = False

    record = {
        "ok": True,
        "timestamp_utc_ms": int(time.time() * 1000),
        "action_id": action_id,
        "title_tr": spec["title_tr"],
        "title_en": spec["title_en"],
        "standard": spec["standard"],
        "subsystem": spec["subsystem"],
        "compartment_id": comp_key,
        "target_hatch_id": target_hatch_id,
        "engage": bool(engage),
        "authority_source": authority_source,
        "ccsds": {
            "apid_hex": f"0x{apid:04X}",
            "sequence_count": seq_count,
            "packet_length_bytes": len(full_packet),
            "ttethernet_vl_hex": f"0x{tt_vl:04X}",
            "mil_std_1553b_cmd_hex": f"0x{mil1553_cmd_word:04X}",
            "crc16_ccitt_hex": f"0x{crc16:04X}",
            "raw_hex": hex_spaced,
            "webserial_ascii_frame": ascii_serial.strip(),
        },
        "udp_loopback_dispatched": udp_dispatched,
    }
    with _SEQ_LOCK:
        _COMMAND_HISTORY.append(record)
        if len(_COMMAND_HISTORY) > 60:
            del _COMMAND_HISTORY[:-60]
    return record


def get_adjacent_hatches_for_compartment(compartment_id: str) -> List[str]:
    """Yangın çıkan bölmeyi komşu modüllerden (örn. Orion <-> HALO <-> I-HAB) izole edecek IDSS kapaklarını döndürür."""
    comp_key = compartment_id if compartment_id in SPACECRAFT_COMPARTMENTS else "HALO"
    hatches: List[str] = []
    for h_meta in SPACECRAFT_HATCH_LINKS:
        if comp_key in (h_meta.get("comp_a"), h_meta.get("comp_b")):
            hatches.append(str(h_meta["hatch_id"]))
    return hatches


def evaluate_fdir_autonomous_state(
    sim_state: Dict[str, Any],
    vision_acoustic: Optional[Dict[str, Any]] = None,
    autonomous_enabled: bool = True,
    ai_engine_label: str = "Deterministik FDIR + Bilimsel Yardımcı Pilot",
) -> Dict[str, Any]:
    """
    Milisaniye ölçekli deterministik FDIR değerlendirmesi yapar:
    - Ön-tutuşma aviyonik ısınma (Semenov ψ >= 1 / Frank-Kamenetskii δ >= δ_cr) veya 18–40 kHz ultrasonik arkta
      yangın çıkmadan önce 120V DC SSPC barasını ve IMV fanını keser.
    - Görünmez Soğuk Alev (540–780 K NTC) veya Aktif Sıcak Alev saptandığında komşu IDSS kapaklarını kapatır,
      IMV fanını durdurur, SoFIE-MIST ince su sisini ateşler ve CAMRAS temizleme döngüsünü hazırlar.
    """
    t0 = time.perf_counter()
    tel = sim_state.get("telemetry", {})
    pre = sim_state.get("pre_ignition", {})
    comp_net = sim_state.get("compartment_network", {})

    fire_comp = str(comp_net.get("fire_compartment_id", "HALO"))
    regime = str(tel.get("regime", "HOT_SPHERICAL_0G"))
    extinguished = bool(tel.get("extinguished", False))
    cool_flame = bool(tel.get("cool_flame_active", False))
    flame_temp_k = float(tel.get("flame_temp_k", 298.15))
    co_ppm = float(tel.get("co_ppm", 1.0))

    thermal_runaway = bool(pre.get("thermal_runaway_imminent", False))
    semenov_psi = float(pre.get("semenov_psi", 0.0))
    fk_delta = float(pre.get("frank_kamenetskii_delta", 0.0))

    delta_p_pa = float(comp_net.get("overpressure_kpa", 0.0)) * 1000.0
    fed_total = float((comp_net.get("multi_gas_toxicology") or {}).get("fed_total", 0.0))

    va_state = str((vision_acoustic or {}).get("detection_state", "NOMINAL_CLEAR"))
    nuisance_dust = va_state == "NUISANCE_DUST_REJECTED"
    ultrasonic_arc = va_state == "PRE_IGNITION_ULTRASONIC_ARC_OUTGAS"

    adjacent_hatches = get_adjacent_hatches_for_compartment(fire_comp)
    recommended_actions: List[Dict[str, Any]] = []
    auto_packets: List[Dict[str, Any]] = []

    comp_info = SPACECRAFT_COMPARTMENTS.get(fire_comp, {})
    comp_tr = str(comp_info.get("name_tr") or fire_comp)
    comp_en = str(comp_info.get("name_en") or fire_comp)
    temp_c = round(flame_temp_k - 273.15)

    if nuisance_dust and extinguished:
        fdir_state = "NUISANCE_DUST_SUPPRESSED"
        severity = "NOMINAL"
        headline_tr = f"{comp_tr}: Kabin içi toz parçacıkları duman olarak algılanmadı, kapaklar ve hava kanalları açık."
        headline_en = f"{comp_en}: Cabin dust rejected as non-fire particulate; hatches and air vents remain open."
    elif not extinguished and not cool_flame:
        fdir_state = "ACTIVE_COMPARTMENT_FIRE"
        severity = "EMERGENCY"
        headline_tr = (
            f"Uyarı — {comp_tr}: Aktif yangın tespit edildi ({temp_c} °C). "
            f"Dumanın yayılmasını önlemek için giriş-çıkış kapakları ve hava kanalları kapatılıyor, su sisi hazır."
        )
        headline_en = (
            f"Alert — {comp_en}: Active fire detected ({temp_c} °C). "
            f"Closing entry-exit hatches and air vents to contain smoke; water mist ready."
        )
        recommended_actions = [
            {"action_id": "ECLSS_IMV_FAN_CUTOFF", "compartment_id": fire_comp, "target_hatch_id": None, "param": 1},
            *[
                {"action_id": "IDSS_HATCH_SEAL", "compartment_id": fire_comp, "target_hatch_id": hid, "param": 100}
                for hid in adjacent_hatches
            ],
            {"action_id": "PCDU_120VDC_SSPC_TRIP", "compartment_id": fire_comp, "target_hatch_id": None, "param": 120},
            {"action_id": "PFE_SOFIE_WATERMIST", "compartment_id": fire_comp, "target_hatch_id": None, "param": 35},
            {"action_id": "CAMRAS_POSTFIRE_SCRUB", "compartment_id": fire_comp, "target_hatch_id": None, "param": 1},
        ]
    elif cool_flame or va_state == "INVISIBLE_COOL_OR_H2_FLAME_MWIR":
        fdir_state = "COOL_FLAME_NTC_HAZARD"
        severity = "CRITICAL"
        headline_tr = (
            f"Kritik Uyarı — {comp_tr}: Gözle görünmeyen düşük sıcaklıklı soğuk alev algılandı ({temp_c} °C, CO {co_ppm:.0f} ppm). "
            f"Bölüm kapakları ve hava giriş-çıkışı kapatılıyor."
        )
        headline_en = (
            f"Critical Alert — {comp_en}: Invisible low-temperature cool flame detected ({temp_c} °C, CO {co_ppm:.0f} ppm). "
            f"Sealing room hatches and air vents."
        )
        recommended_actions = [
            {"action_id": "ECLSS_IMV_FAN_CUTOFF", "compartment_id": fire_comp, "target_hatch_id": None, "param": 1},
            *[
                {"action_id": "IDSS_HATCH_SEAL", "compartment_id": fire_comp, "target_hatch_id": hid, "param": 100}
                for hid in adjacent_hatches
            ],
            {"action_id": "PFE_SOFIE_WATERMIST", "compartment_id": fire_comp, "target_hatch_id": None, "param": 25},
            {"action_id": "CAMRAS_POSTFIRE_SCRUB", "compartment_id": fire_comp, "target_hatch_id": None, "param": 1},
        ]
    elif thermal_runaway or ultrasonic_arc:
        fdir_state = "PRE_IGNITION_THERMAL_ANOMALY"
        severity = "WARNING"
        headline_tr = (
            f"Önleyici Uyarı — {comp_tr}: Elektronik aşırı ısınma algılandı. "
            f"Yangın çıkmadan bölüm elektriği ve hava akışı güvenli moda alındı."
        )
        headline_en = (
            f"Preventive Warning — {comp_en}: Avionics overheating detected. "
            f"Section power and airflow isolated before ignition."
        )
        recommended_actions = [
            {"action_id": "PCDU_120VDC_SSPC_TRIP", "compartment_id": fire_comp, "target_hatch_id": None, "param": 120},
            {"action_id": "ECLSS_IMV_FAN_CUTOFF", "compartment_id": fire_comp, "target_hatch_id": None, "param": 1},
        ]
    elif co_ppm >= 25.0 or fed_total >= 0.05:
        fdir_state = "POST_FIRE_CAMRAS_SCRUB"
        severity = "CAUTION"
        headline_tr = f"{comp_tr}: Kabin havasında karbonmonoksit ({co_ppm:.0f} ppm) izleniyor, hava temizleme devrede."
        headline_en = f"{comp_en}: Residual carbon monoxide ({co_ppm:.0f} ppm) monitored; air scrubbing active."
        recommended_actions = [
            {"action_id": "CAMRAS_POSTFIRE_SCRUB", "compartment_id": fire_comp, "target_hatch_id": None, "param": 1},
        ]
    else:
        fdir_state = "NOMINAL_FLIGHT"
        severity = "NOMINAL"
        headline_tr = f"{comp_tr}: Tüm değerler güvenli aralıkta, giriş-çıkış kapakları ve hava kanalları açık."
        headline_en = f"{comp_en}: All readings normal; entry-exit hatches and air vents are open."

    if autonomous_enabled and recommended_actions:
        for item in recommended_actions:
            pkt = build_ccsds_hardware_packet(
                action_id=item["action_id"],
                compartment_id=item["compartment_id"],
                target_hatch_id=item["target_hatch_id"],
                engage=True,
                authority_source="FDIR_AUTONOMOUS_6001B",
                parameter_u16=int(item["param"]),
            )
            auto_packets.append(pkt)

    latency_ms = round((time.perf_counter() - t0) * 1000.0, 3)

    copilot_note_tr = (
        f"Birincil donanım güvenliği deterministik `NASA-STD-6001B FDIR` durum makinesi tarafından `{latency_ms:.3f} ms` içinde "
        f"yürütüldü (`{len(auto_packets)}` adet `CCSDS 133.0-B-2` telekomut paketi). Seçili yardımcı pilot (`{ai_engine_label}`) "
        f"`{regime}` rejiminin kök neden analizini ve `PSI / SoFIE` kanıt izlenebilirliğini salt-okunur katmanda sağlar."
    )
    copilot_note_en = (
        f"Primary life-safety hardware isolation executed by deterministic `NASA-STD-6001B FDIR` in `{latency_ms:.3f} ms` "
        f"(`{len(auto_packets)}` `CCSDS 133.0-B-2` telecommand packets). Selected Co-Pilot (`{ai_engine_label}`) provides "
        f"read-only root-cause kinetic & `PSI / SoFIE` evidence synthesis."
    )

    return {
        "ok": True,
        "fdir_state": fdir_state,
        "severity": severity,
        "autonomous_enabled": autonomous_enabled,
        "decision_latency_ms": latency_ms,
        "fire_compartment_id": fire_comp,
        "adjacent_hatches_targeted": adjacent_hatches,
        "headline_tr": headline_tr,
        "headline_en": headline_en,
        "architecture_separation": {
            "primary_safety_layer": "NASA-STD-6001B Deterministic Avionics FDIR (< 1 ms)",
            "secondary_advisory_layer": f"Read-Only Scientific AI Co-Pilot ({ai_engine_label})",
            "tertiary_override_layer": "Jury Guarded Manual Hardware Switches (CCSDS + TTEthernet + MIL-STD-1553B)",
            "halon_1301_hardware_interlock": "LOCKED_FORBIDDEN",
            "note_tr": copilot_note_tr,
            "note_en": copilot_note_en,
        },
        "recommended_actions": recommended_actions,
        "dispatched_packets": auto_packets,
        "actuator_catalog": HARDWARE_ACTUATOR_SPECS,
        "recent_command_history": list(_COMMAND_HISTORY[-12:]),
    }
