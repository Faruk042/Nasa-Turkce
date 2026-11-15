/* ============================================================================
 * ALTAR-NASA v6.3 — Realistic Artemis Orion MPCV + Airbus ESM 3D Digital Twin,
 * Cutaway Compartment Explorer, True 3D Perspective Cabin Camera (Optical +
 * Radiometric LWIR Ironbow + Split View), Autonomous Threshold FDIR & 0G Cooling.
 * Strict CSP Compliant ('self', zero inline scripts, zero emojis).
 * ============================================================================ */
(function () {
    "use strict";

    const COMPARTMENT_ORDER = ["ORION_CM", "HALO", "IHAB", "AIRLOCK", "PPE"];

    const ROOM_DEFS = {
        ORION_CM: {
            idx: 0,
            camCode: "01",
            short_tr: "Komuta",
            short_en: "Command",
            tab_tr: "Komuta Bölümü",
            tab_en: "Command Deck",
            name_tr: "Komuta Bölümü (Kokpit)",
            name_en: "Command Deck (Cockpit)",
            hatches: ["HATCH_ORION_HALO"],
            firePos3d: [0.18, 0.92, 0.28],
            cutawayY: 0.94,
            cutawayR: 0.88,
            cutawayH: 0.36,
            camFocus: { yaw: 0.08, pitch: 0.18, dist: 4.55, px: 0.0, py: 0.88 },
            fire3dRoomPos: [-0.52, -0.05, -0.45],
            equipHeatPos: [-0.58, -0.08, -0.52],
        },
        IHAB: {
            idx: 2,
            camCode: "02",
            short_tr: "Yaşam",
            short_en: "Living",
            tab_tr: "Yaşam Bölümü",
            tab_en: "Living Bay",
            name_tr: "Mürettebat Yaşam Bölümü",
            name_en: "Crew Living Bay",
            hatches: ["HATCH_HALO_IHAB", "HATCH_IHAB_AIRLOCK"],
            firePos3d: [-0.22, 0.46, 0.32],
            cutawayY: 0.46,
            cutawayR: 1.28,
            cutawayH: 0.42,
            camFocus: { yaw: -0.08, pitch: 0.12, dist: 4.75, px: 0.0, py: 0.44 },
            fire3dRoomPos: [0.56, 0.02, -0.48],
            equipHeatPos: [0.62, 0.05, -0.55],
        },
        HALO: {
            idx: 1,
            camCode: "03",
            short_tr: "Güç",
            short_en: "Power",
            tab_tr: "Güç ve Elektronik",
            tab_en: "Power & Avionics",
            name_tr: "Güç ve Elektronik Bölümü",
            name_en: "Power & Avionics Bay",
            hatches: ["HATCH_ORION_HALO", "HATCH_HALO_IHAB", "HATCH_HALO_PPE"],
            firePos3d: [0.24, -0.34, 0.26],
            cutawayY: -0.38,
            cutawayR: 0.98,
            cutawayH: 0.44,
            camFocus: { yaw: 0.10, pitch: 0.06, dist: 4.85, px: 0.0, py: -0.36 },
            fire3dRoomPos: [-0.66, 0.08, -0.38],
            equipHeatPos: [-0.72, 0.12, -0.42],
        },
        AIRLOCK: {
            idx: 3,
            camCode: "04",
            short_tr: "Tünel",
            short_en: "Tunnel",
            tab_tr: "Kenetlenme Tüneli",
            tab_en: "Docking Tunnel",
            name_tr: "Kenetlenme ve Geçiş Tüneli",
            name_en: "Docking & Transfer Tunnel",
            hatches: ["HATCH_IHAB_AIRLOCK"],
            firePos3d: [0.0, 1.54, 0.14],
            cutawayY: 1.54,
            cutawayR: 0.44,
            cutawayH: 0.42,
            camFocus: { yaw: 0.05, pitch: 0.24, dist: 4.15, px: 0.0, py: 1.48 },
            fire3dRoomPos: [0.34, -0.10, -0.55],
            equipHeatPos: [0.38, -0.06, -0.60],
        },
        PPE: {
            idx: 4,
            camCode: "05",
            short_tr: "Hava",
            short_en: "Air",
            tab_tr: "Hava Ünitesi",
            tab_en: "Air & Life Support",
            name_tr: "Yaşam Destek ve Hava Ünitesi",
            name_en: "Life Support & Air Bay",
            hatches: ["HATCH_HALO_PPE"],
            firePos3d: [-0.20, -1.04, 0.26],
            cutawayY: -1.04,
            cutawayR: 0.98,
            cutawayH: 0.54,
            camFocus: { yaw: -0.10, pitch: -0.06, dist: 4.95, px: 0.0, py: -0.98 },
            fire3dRoomPos: [-0.52, -0.02, -0.50],
            equipHeatPos: [-0.58, 0.02, -0.56],
        },
    };

    // 256-entry Radiometric LWIR Ironbow Lookup Table (RGB)
    const IRONBOW_LUT = (function buildIronbowLut() {
        const stops = [
            { t: 0.00, c: [6, 4, 24] },
            { t: 0.18, c: [38, 12, 88] },
            { t: 0.36, c: [106, 23, 126] },
            { t: 0.54, c: [182, 52, 88] },
            { t: 0.72, c: [238, 114, 36] },
            { t: 0.88, c: [252, 202, 48] },
            { t: 1.00, c: [255, 253, 228] },
        ];
        const lut = new Uint8Array(256 * 3);
        for (let i = 0; i < 256; i++) {
            const x = i / 255;
            let s0 = stops[0];
            let s1 = stops[stops.length - 1];
            for (let k = 0; k < stops.length - 1; k++) {
                if (x >= stops[k].t && x <= stops[k + 1].t) {
                    s0 = stops[k];
                    s1 = stops[k + 1];
                    break;
                }
            }
            const f = (x - s0.t) / Math.max(1e-5, s1.t - s0.t);
            lut[i * 3] = Math.round(s0.c[0] + (s1.c[0] - s0.c[0]) * f);
            lut[i * 3 + 1] = Math.round(s0.c[1] + (s1.c[1] - s0.c[1]) * f);
            lut[i * 3 + 2] = Math.round(s0.c[2] + (s1.c[2] - s0.c[2]) * f);
        }
        return lut;
    })();

    class SpacecraftUltraHDStudio {
        constructor(options) {
            this.opts = options || {};
            this.apiFetch = this.opts.apiFetch || window.fetch.bind(window);
            this.onHardwareStateChange = this.opts.onHardwareStateChange || null;
            this.onRequestAiCopilot = this.opts.onRequestAiCopilot || null;
            this.getLang = this.opts.getLang || (() => "tr");

            this.canvas = document.getElementById("sc-gl-canvas");
            this.pipCanvas = document.getElementById("sc-pip-canvas");
            if (!this.canvas) return;

            this.gl =
                this.canvas.getContext("webgl", {
                    antialias: true,
                    alpha: false,
                    powerPreference: "high-performance",
                    premultipliedAlpha: false,
                }) || this.canvas.getContext("experimental-webgl");

            if (!this.gl) {
                console.warn("WebGL unavailable for Orion MCP 3D Studio; running state & control kernel without WebGL.");
            }
            this.pipCtx = this.pipCanvas ? this.pipCanvas.getContext("2d", { willReadFrequently: true }) : null;

            this.rooms = {};
            COMPARTMENT_ORDER.forEach((cid) => {
                this.rooms[cid] = {
                    entryClosed: false,
                    airClosed: false,
                    powerCut: false,
                    airScrub: false,
                    manualFire: null, // null = follow simulation in fireOriginCid, true = forced fire test, false = stopped
                    mistLatched: false,
                    mistAnim: 0.0,
                    hatchAnim: 0.0,
                    ventAnim: 0.0,
                    tempC: 21.0,
                    coLocal: 1.0,
                    coreTempK: 294.15,
                    reignitedAlertUntil: 0.0,
                };
            });

            this.state = {
                active: false,
                hullMode: "exterior", // "exterior" | "cutaway"
                sectionFocusMode: "hull", // "exterior" | "cutaway" | "room"
                zoneIdx: 0, // Default: ORION_CM
                fireOriginCid: "ORION_CM",
                camVisible: true,
                cameraMode: "optical", // "optical" | "thermal" | "split"
                aiAuto: true,
                autoThreshold: 65,
                autoCountdownActive: false,
                autoCountdownTotal: 5.5,
                autoCountdownRem: 0.0,
                autoCountdownRoom: null,
                autoStepMask: 0,
                manualSequenceActive: false,
                lastSeqTickMs: performance.now(),
                autoOverrideLatched: false,
                showSpace: true,
                simExtinguished: false,
                coolFlame: false,
                gravityG: 0.0,
                oxygenPct: 21.0,
                autoignitionTempK: 660.0,
                flameTempK: 1920,
                coPpm: 85,
                simRiskScore: 45,
                fire: 0.0,
                dpKpa: 0.0,
                hatchForceKn: 0.0,
                smokeLeakGs: 0.0,
                fedTotal: 0.0,
                autoOrbit: true,
                webcamStream: null,
                webcamVideo: null,
                webcamProbeCanvas: null,
                webcamPrevLuma: null,
                webcamMetrics: { brightnessPct: 0, flickerPct: 0, flameCandidate: false },
                lastTabSyncT: 0,
            };

            this.cam = {
                yaw: 0.54,
                pitch: 0.16,
                dist: 7.25,
                px: 0,
                py: 0.08,
                tYaw: 0.54,
                tPitch: 0.16,
                tDist: 7.25,
                tPx: 0,
                tPy: 0.08,
                lerp: false,
                drag: false,
                btn: 0,
                lx: 0,
                ly: 0,
            };

            this.lastT = performance.now();
            if (this.gl) {
                this._initWebGLResources();
                this._initInterior3DScene();
            }
            this._bindUIControls();
            this._updateLocalizedHeader();
            this._startLoop();
        }

        getCompartmentId() {
            return COMPARTMENT_ORDER[this.state.zoneIdx] || "ORION_CM";
        }

        _getActiveRoom() {
            return this.rooms[this.getCompartmentId()];
        }

        _isRoomFireActive(cid) {
            const rm = this.rooms[cid];
            if (!rm || rm.mistLatched || rm.mistAnim > 0.08) return false;
            if (rm.manualFire === true) return true;
            if (rm.manualFire === false) return false;
            return cid === this.state.fireOriginCid && !this.state.simExtinguished;
        }

        _hasAdjacentSmokeIngress(cid) {
            if (this._isRoomFireActive(cid)) return false;
            const rm = this.rooms[cid];
            if (!rm || rm.entryClosed) return false;
            const myHatches = ROOM_DEFS[cid] ? ROOM_DEFS[cid].hatches || [] : [];
            return COMPARTMENT_ORDER.some((otherCid) => {
                if (otherCid === cid || !this._isRoomFireActive(otherCid)) return false;
                const otherRm = this.rooms[otherCid];
                if (otherRm && otherRm.entryClosed) return false;
                const otherHatches = ROOM_DEFS[otherCid] ? ROOM_DEFS[otherCid].hatches || [] : [];
                return myHatches.some((h) => otherHatches.includes(h));
            });
        }

        _computeRoomPostFireStats(cid) {
            const rm = this.rooms[cid];
            const burning = this._isRoomFireActive(cid);
            const tCore = rm ? rm.coreTempK : 294.15;
            const tAuto = Math.max(520.0, this.state.autoignitionTempK || 650.0);
            const o2Factor = Math.min(1.45, Math.max(0.35, (this.state.oxygenPct || 21.0) / 21.0));
            const rawTherm = Math.max(0.0, (tCore - 335.0) / Math.max(80.0, tAuto - 335.0));
            const ventBonus = rm && rm.airClosed ? 0.65 : 1.0;
            const riskPct = burning
                ? Math.min(99, Math.round(Math.max(65, this.state.simRiskScore)))
                : Math.min(96, Math.round(Math.pow(rawTherm, 1.15) * 100.0 * o2Factor * ventBonus));

            // Cooling time constant to safe 338 K (~65 C)
            const gVal = this.state.gravityG || 0.0;
            const mistOn = rm && (rm.mistLatched || rm.mistAnim > 0.05);
            const tauCool = mistOn ? 18.0 : (gVal < 0.05 ? 92.0 : (gVal < 0.4 ? 54.0 : 34.0));
            let safeSec = 0;
            if (burning) {
                safeSec = Math.round(tauCool * 1.45);
            } else if (tCore > 338.15) {
                const ratio = (tCore - 294.15) / (338.15 - 294.15);
                safeSec = Math.max(1, Math.round(tauCool * Math.log(Math.max(1.02, ratio))));
            }
            return {
                coreTempK: tCore,
                coreTempC: tCore - 273.15,
                reignitionRiskPct: riskPct,
                safeReentrySec: safeSec,
            };
        }

        _checkFlashReignitionOnO2Reentry(cid) {
            const rm = this.rooms[cid];
            if (!rm || this._isRoomFireActive(cid)) return false;
            // In microgravity/low-G, if hot smoldering core > 525 K (~252 C) receives fresh cabin O2 prematurely, flash re-ignition occurs
            if (rm.coreTempK >= 525.0 && (this.state.oxygenPct || 21.0) >= 15.0) {
                rm.mistLatched = false;
                rm.mistAnim = 0.0;
                rm.manualFire = true;
                rm.reignitedAlertUntil = performance.now() * 0.001 + 9.0;
                this.state.fireOriginCid = cid;
                this.state.autoOverrideLatched = false;
                return true;
            }
            return false;
        }

        setHullMode(mode) {
            const clean = mode === "cutaway" ? "cutaway" : "exterior";
            this.state.hullMode = clean;
            this.state.sectionFocusMode = clean;
            this.state.autoOrbit = clean === "exterior";
            this.cam.lerp = true;
            if (clean === "cutaway") {
                this.cam.tYaw = 0.04;
                this.cam.tPitch = 0.14;
                this.cam.tDist = 6.15;
                this.cam.tPx = 0.0;
                this.cam.tPy = 0.14;
            } else {
                this.cam.tYaw = 0.54;
                this.cam.tPitch = 0.16;
                this.cam.tDist = 7.25;
                this.cam.tPx = 0.0;
                this.cam.tPy = 0.08;
            }
            this._syncOrionSectionButtons();
        }

        focusSection(zoneIdx) {
            const z = Math.max(0, Math.min(COMPARTMENT_ORDER.length - 1, Number(zoneIdx) || 0));
            this.state.zoneIdx = z;
            this.state.hullMode = "cutaway";
            this.state.sectionFocusMode = "room";
            this.state.autoOrbit = false;
            const cid = COMPARTMENT_ORDER[z] || "ORION_CM";
            const cf = (ROOM_DEFS[cid] || ROOM_DEFS.ORION_CM).camFocus;
            this.cam.lerp = true;
            this.cam.tYaw = cf.yaw;
            this.cam.tPitch = cf.pitch;
            this.cam.tDist = cf.dist;
            this.cam.tPx = cf.px;
            this.cam.tPy = cf.py;

            if (!this.state.camVisible) {
                this.state.camVisible = true;
                const ws = document.getElementById("sc-lower-workspace");
                if (ws) ws.classList.remove("cam-collapsed");
            }
            this._updateLocalizedHeader();
            this._syncOrionSectionButtons();
            if (this.onHardwareStateChange) this.onHardwareStateChange();
        }

        _syncOrionSectionButtons() {
            const isEn = this.getLang() === "en";
            document.querySelectorAll(".orion-sec-btn").forEach((btn) => {
                const hullAttr = btn.dataset.hull;
                const zFocus = btn.dataset.zoneFocus;
                if (hullAttr === "exterior") {
                    btn.textContent = isEn ? "Outer Hull" : "Dış Gövde";
                    btn.classList.toggle("active", this.state.sectionFocusMode === "exterior");
                } else if (hullAttr === "cutaway") {
                    btn.textContent = isEn ? "Cutaway" : "İç Kesit";
                    btn.classList.toggle("active", this.state.sectionFocusMode === "cutaway");
                } else if (zFocus !== undefined) {
                    const zIdx = Number(zFocus);
                    const cid = COMPARTMENT_ORDER[zIdx] || "ORION_CM";
                    const def = ROOM_DEFS[cid];
                    if (def) {
                        btn.textContent = isEn ? def.short_en : def.short_tr;
                    }
                    btn.classList.toggle("active", this.state.sectionFocusMode === "room" && this.state.zoneIdx === zIdx);
                    btn.classList.toggle("sec-fire", this._isRoomFireActive(cid));
                }
            });
        }

        _stopWebcam() {
            if (this.state.webcamStream) {
                this.state.webcamStream.getTracks().forEach((tr) => tr.stop());
                this.state.webcamStream = null;
            }
            this.state.webcamVideo = null;
            this.state.webcamPrevLuma = null;
        }

        _collectAllSealedHatches() {
            const set = new Set();
            COMPARTMENT_ORDER.forEach((cid) => {
                if (this.rooms[cid] && this.rooms[cid].entryClosed) {
                    (ROOM_DEFS[cid].hatches || []).forEach((h) => set.add(h));
                }
            });
            return Array.from(set);
        }

        getSimulationOverrides() {
            const fireCid = COMPARTMENT_ORDER.find((c) => this._isRoomFireActive(c)) || this.state.fireOriginCid || this.getCompartmentId();
            const rm = this.rooms[fireCid];
            return {
                fire_compartment_id: fireCid,
                sealed_hatches: this._collectAllSealedHatches(),
                imv_fan_cutoff: Boolean(rm && rm.airClosed),
                water_mist_active: Boolean(rm && (rm.mistLatched || rm.mistAnim > 0.08 || rm.manualFire === false)),
                avionics_fault_watts: 0.0,
            };
        }

        setActive(visible) {
            this.state.active = Boolean(visible);
            if (this.state.active) {
                this.resize();
                this._updateLocalizedHeader();
                this._syncOrionSectionButtons();
            } else {
                this._stopWebcam();
            }
        }

        resize() {
            if (!this.canvas || !this.gl) return;
            const ssaa = Math.min(Math.max(window.devicePixelRatio || 1, 1.75), 2.25);
            const cw = Math.max(320, Math.floor((this.canvas.clientWidth || 760) * ssaa));
            const ch = Math.max(240, Math.floor((this.canvas.clientHeight || 455) * ssaa));
            if (this.canvas.width !== cw || this.canvas.height !== ch) {
                this.canvas.width = cw;
                this.canvas.height = ch;
            }
        }

        _triggerAutonomousCountdownIfNeeded() {
            if (!this.state.aiAuto || this.state.autoOverrideLatched || this.state.autoCountdownActive) return;
            const fireCid = COMPARTMENT_ORDER.find((c) => this._isRoomFireActive(c));
            if (!fireCid) return;
            const rm = this.rooms[fireCid];
            if (!rm) return;
            const effectiveRisk = rm.manualFire === true ? Math.max(75, this.state.simRiskScore) : this.state.simRiskScore;
            if (effectiveRisk >= this.state.autoThreshold) {
                this.state.manualSequenceActive = false;
                this.state.autoCountdownActive = true;
                this.state.autoCountdownTotal = 5.5;
                this.state.autoCountdownRem = 5.5;
                this.state.autoCountdownRoom = fireCid;
                this.state.autoStepMask = 0;
                this.state.lastSeqTickMs = performance.now();
            }
        }

        triggerFullSequentialIntervention(compartmentId, startDemoFireIfIdle = true) {
            const targetCid = COMPARTMENT_ORDER.includes(compartmentId) ? compartmentId : this.getCompartmentId();
            const zIdx = COMPARTMENT_ORDER.indexOf(targetCid);
            if (zIdx >= 0) {
                this.state.zoneIdx = zIdx;
            }
            const rm = this.rooms[targetCid];
            if (!rm) return false;

            if (!this.state.camVisible) {
                this.state.camVisible = true;
                const ws = document.getElementById("sc-lower-workspace");
                if (ws) ws.classList.remove("cam-collapsed");
            }

            rm.airClosed = false;
            rm.powerCut = false;
            rm.entryClosed = false;
            rm.mistLatched = false;
            rm.mistAnim = 0.0;
            rm.airScrub = false;

            if (startDemoFireIfIdle !== false && !this._isRoomFireActive(targetCid)) {
                rm.manualFire = true;
                this.state.fireOriginCid = targetCid;
            }

            this.state.autoOverrideLatched = false;
            this.state.manualSequenceActive = true;
            this.state.autoCountdownActive = true;
            this.state.autoCountdownTotal = 5.5;
            this.state.autoCountdownRem = 5.5;
            this.state.autoCountdownRoom = targetCid;
            this.state.autoStepMask = 0;
            this.state.lastSeqTickMs = performance.now();

            this._updateLocalizedHeader();
            this._renderCountdownBanner();
            this._syncManualButtonStates();
            this._renderLivePhysicsTelemetry();
            if (this.onHardwareStateChange) this.onHardwareStateChange();
            return true;
        }

        cancelAutonomousSequence() {
            this.state.autoCountdownActive = false;
            this.state.manualSequenceActive = false;
            this.state.autoCountdownRem = 0.0;
            this.state.autoOverrideLatched = true;
            this._syncManualButtonStates();
            this._renderCountdownBanner();
            this._renderLivePhysicsTelemetry();
        }

        _advanceSequenceByWallClock() {
            const nowMs = performance.now();
            const prevMs = this.state.lastSeqTickMs || nowMs;
            this.state.lastSeqTickMs = nowMs;
            if (!this.state.autoCountdownActive) return;
            const dt = Math.min(0.25, Math.max(0.0, (nowMs - prevMs) / 1000.0));
            if (dt > 0.0) {
                this._stepAutonomousSequence(dt);
            }
        }

        _stepAutonomousSequence(dt) {
            if (!this.state.autoCountdownActive) {
                this._renderCountdownBanner();
                return;
            }
            const cid = this.state.autoCountdownRoom || this.getCompartmentId();
            const rm = this.rooms[cid];
            const isManualRun = Boolean(this.state.manualSequenceActive);
            const mistStepDone = Boolean(this.state.autoStepMask & 8);

            if (!rm || (!isManualRun && !this.state.aiAuto) || (!isManualRun && !mistStepDone && !this._isRoomFireActive(cid))) {
                this.state.autoCountdownActive = false;
                this.state.manualSequenceActive = false;
                this._syncManualButtonStates();
                this._renderCountdownBanner();
                return;
            }

            this.state.autoCountdownRem = Math.max(0.0, this.state.autoCountdownRem - dt);
            const rem = this.state.autoCountdownRem;
            let stateChanged = false;

            // 5-Step Sequential Fire Response (~5.5 s total):
            // 1/5 Closing Air Vents -> 2/5 Cutting Bay Power -> 3/5 Sealing Entry Hatch -> 4/5 Spraying Water Mist -> 5/5 Scrubbing Cabin Air
            if (rem <= 4.4 && !(this.state.autoStepMask & 1)) {
                this.state.autoStepMask |= 1;
                if (!rm.airClosed) {
                    rm.airClosed = true;
                    this.dispatchHardwareCommand("ECLSS_IMV_FAN_CUTOFF", true, null, 1);
                    stateChanged = true;
                }
            }
            if (rem <= 3.3 && !(this.state.autoStepMask & 2)) {
                this.state.autoStepMask |= 2;
                if (!rm.powerCut) {
                    rm.powerCut = true;
                    this.dispatchHardwareCommand("PCDU_120VDC_SSPC_TRIP", true, null, 120);
                    stateChanged = true;
                }
            }
            if (rem <= 2.2 && !(this.state.autoStepMask & 4)) {
                this.state.autoStepMask |= 4;
                if (!rm.entryClosed) {
                    rm.entryClosed = true;
                    const h0 = (ROOM_DEFS[cid].hatches || [])[0] || "HATCH_ORION_HALO";
                    this.dispatchHardwareCommand("IDSS_HATCH_SEAL", true, h0, 100);
                    stateChanged = true;
                }
            }
            if (rem <= 1.1 && !(this.state.autoStepMask & 8)) {
                this.state.autoStepMask |= 8;
                rm.mistAnim = 1.0;
                rm.mistLatched = true;
                rm.manualFire = false;
                this.dispatchHardwareCommand("PFE_SOFIE_WATERMIST", true, null, 35);
                stateChanged = true;
            }
            if (rem <= 0.0 && !(this.state.autoStepMask & 16)) {
                this.state.autoStepMask |= 16;
                rm.airScrub = true;
                this.state.autoCountdownActive = false;
                this.state.manualSequenceActive = false;
                this.dispatchHardwareCommand("CAMRAS_POSTFIRE_SCRUB", true, null, 1);
                stateChanged = true;
            }

            if (stateChanged) {
                this._syncManualButtonStates();
                this._renderLivePhysicsTelemetry();
                if (this.onHardwareStateChange) this.onHardwareStateChange();
            }
            this._renderCountdownBanner();
        }

        _renderCountdownBanner() {
            const box = document.getElementById("sc-auto-countdown-box");
            if (!box) return;
            const isEn = this.getLang() === "en";
            const txtEl = document.getElementById("sc-auto-countdown-text");
            const cancelBtn = document.getElementById("sc-btn-cancel-auto");
            if (cancelBtn) {
                cancelBtn.textContent = isEn ? "Manual Override" : "Manuel Devral";
            }
            if (!this.state.autoCountdownActive) {
                box.style.display = "none";
                if (txtEl) txtEl.textContent = "";
                return;
            }
            box.style.display = "flex";
            const total = this.state.autoCountdownTotal || 5.5;
            const rem = this.state.autoCountdownRem;
            const cid = this.state.autoCountdownRoom || this.getCompartmentId();
            const def = ROOM_DEFS[cid] || ROOM_DEFS.ORION_CM;
            const rName = isEn ? def.short_en : def.short_tr;

            let stepLabel = "";
            if (rem > 4.4) {
                stepLabel = isEn ? "1/5 Closing Air Vents" : "1/5 Hava Kanalları Kapatılıyor";
            } else if (rem > 3.3) {
                stepLabel = isEn ? "2/5 Cutting Bay Power" : "2/5 Bölüm Elektriği Kesiliyor";
            } else if (rem > 2.2) {
                stepLabel = isEn ? "3/5 Sealing Entry Hatch" : "3/5 Giriş Kapağı Kilitleniyor";
            } else if (rem > 1.1) {
                stepLabel = isEn ? "4/5 Spraying Water Mist" : "4/5 Su Sisi Sıkılıyor";
            } else {
                stepLabel = isEn ? "5/5 Scrubbing Cabin Air" : "5/5 Kabin Havası Temizleniyor";
            }

            const modeTitle = this.state.manualSequenceActive
                ? (isEn ? "Fire Response" : "Sıralı Müdahale")
                : (isEn ? "Auto-Protection" : "Otonom Koruma");

            if (txtEl) {
                txtEl.textContent = isEn
                    ? `${modeTitle} (${rName}) • ${rem.toFixed(1)} s — ${stepLabel}`
                    : `${modeTitle} (${rName}) • ${rem.toFixed(1)} sn — ${stepLabel}`;
            }
            const fillEl = document.getElementById("sc-auto-countdown-fill");
            if (fillEl) {
                const pct = Math.max(0, Math.min(100, ((total - rem) / total) * 100));
                fillEl.style.width = `${pct.toFixed(1)}%`;
            }
        }

        syncFromSimulation(simData) {
            if (!simData || !simData.telemetry) return;
            const tel = simData.telemetry;
            const inp = simData.inputs || {};
            const cn = simData.compartment_network || {};
            const tox = cn.multi_gas_toxicology || {};
            const pfc = simData.post_fire_cooling || {};

            const wasExtinguished = this.state.simExtinguished;
            this.state.simExtinguished = Boolean(tel.extinguished);
            this.state.coolFlame = Boolean(tel.cool_flame_active);
            this.state.gravityG = Number(inp.gravity_g ?? 0.0);
            this.state.oxygenPct = Number(inp.oxygen_pct ?? 21.0);
            this.state.autoignitionTempK = Number(pfc.autoignition_temp_k || 650.0);
            this.state.flameTempK = Number(tel.flame_temp_k || 294);
            this.state.coPpm = Number(tel.co_ppm || 1);
            this.state.simRiskScore = Number(tel.risk_score || 15);
            this.state.dpKpa = Number(cn.overpressure_kpa || 0);
            this.state.hatchForceKn = Number(cn.max_hatch_force_kn || 0);
            this.state.smokeLeakGs = Number(cn.total_intermodule_smoke_g_s || 0);
            this.state.fedTotal = Number(tox.fed_total || 0);

            if (wasExtinguished && !this.state.simExtinguished) {
                this.state.autoOverrideLatched = false;
            }

            this._triggerAutonomousCountdownIfNeeded();
            this._syncManualButtonStates();
            this._renderLivePhysicsTelemetry();
            if (this.state.active) {
                this._evaluateBackendFdir(simData);
            }
        }

        _buildHumanStatusBanner() {
            const isEn = this.getLang() === "en";
            const cid = this.getCompartmentId();
            const def = ROOM_DEFS[cid] || ROOM_DEFS.ORION_CM;
            const rm = this.rooms[cid];
            const roomName = isEn ? def.name_en : def.name_tr;
            const fireNow = this._isRoomFireActive(cid);
            const smokeIn = this._hasAdjacentSmokeIngress(cid);
            const pf = this._computeRoomPostFireStats(cid);
            const tempC = Math.round(rm.tempC || (fireNow ? Math.max(45, this.state.flameTempK - 273.15) : 21));
            const fullSealed = rm.entryClosed && rm.airClosed;
            const nowSec = performance.now() * 0.001;

            if (rm.reignitedAlertUntil > nowSec) {
                return {
                    sev: "EMERGENCY",
                    text: isEn
                        ? `Flash Re-Ignition in ${roomName}: Hot 0G core (${Math.round(pf.coreTempC)} °C) received fresh O₂ before safe cooling clearance.`
                        : `Yeniden Tutuşma Uyarısı — ${roomName}: Sıcak 0G çekirdek (${Math.round(pf.coreTempC)} °C) soğumadan temiz O₂ girdiği için alev yeniden parladı.`,
                };
            }
            if (!fireNow && pf.coreTempK > 345.0) {
                return {
                    sev: "CAUTION",
                    text: isEn
                        ? `${roomName}: Flame suppressed; 0G core cooling in progress (T_core: ${Math.round(pf.coreTempC)} °C, safe entry in ${pf.safeReentrySec} s). Keep sealed.`
                        : `${roomName}: Alev söndürüldü; 0G sıcak çekirdek soğuyor (T_core: ${Math.round(pf.coreTempC)} °C, güvenli giriş: ${pf.safeReentrySec} sn). Kapağı kapalı tutun.`,
                };
            }
            if (rm.mistAnim > 0.08 || (!fireNow && tempC > 26)) {
                return {
                    sev: "CAUTION",
                    text: isEn
                        ? `${roomName}: Fine water mist cooling active (${tempC} °C) — compartment temperature decaying safely.`
                        : `${roomName}: Su sisi soğutması devrede (${tempC} °C) — bölüm sıcaklığı güvenli seviyeye düşürülüyor.`,
                };
            }
            if (fireNow) {
                if (this.state.autoOverlayMsg) {
                    return { sev: "EMERGENCY", text: this.state.autoOverlayMsg };
                }
                if (fullSealed) {
                    return {
                        sev: "EMERGENCY",
                        text: isEn
                            ? `Alert — ${roomName}: Fire active (${tempC} °C). Entry-exit hatches and air vents closed to block smoke spread.`
                            : `Uyarı — ${roomName}: Aktif yangın algılandı (${tempC} °C). Duman geçişini önlemek için kapak ve hava kanalları kapatıldı.`,
                    };
                }
                return {
                    sev: "EMERGENCY",
                    text: isEn
                        ? `Alert — ${roomName}: Fire active (${tempC} °C). Isolate room hatches/vents or trigger water mist.`
                        : `Uyarı — ${roomName}: Aktif yangın algılandı (${tempC} °C). Odayı kapatarak veya su sisi çalıştırarak müdahale edin.`,
                };
            }
            if (smokeIn) {
                return {
                    sev: "WARNING",
                    text: isEn
                        ? `Caution — ${roomName}: No local fire (${tempC} °C), but smoke is entering from an unsealed adjacent bay. Close hatch.`
                        : `Dikkat — ${roomName}: Bu odada alev yok (${tempC} °C), ancak komşu bölümden duman sızıyor. Kapağı kapatın.`,
                };
            }
            if (fullSealed) {
                return {
                    sev: "WARNING",
                    text: isEn
                        ? `${roomName} is isolated: Entry-exit doors and air inlet-outlet vents are closed (${tempC} °C).`
                        : `${roomName} izole edildi: Giriş-çıkış bağlantıları ve hava giriş-çıkış kanalları kapalı (${tempC} °C).`,
                };
            }
            if (rm.entryClosed || rm.airClosed) {
                const partTr = rm.entryClosed ? "giriş-çıkış kapağı kapalı, hava kanalı açık" : "hava giriş-çıkışı kapalı, kapak açık";
                const partEn = rm.entryClosed ? "entry-exit hatch closed, air vents open" : "air vents closed, hatch open";
                return {
                    sev: "CAUTION",
                    text: isEn
                        ? `${roomName}: Safe (${tempC} °C) — ${partEn}.`
                        : `${roomName}: Güvenli durumda (${tempC} °C) — ${partTr}.`,
                };
            }
            return {
                sev: "NOMINAL",
                text: isEn
                    ? `${roomName} is normal (${tempC} °C). Entry-exit connections and air inlet-outlet vents are open.`
                    : `${roomName} güvenli durumda (${tempC} °C). Giriş-çıkış kapakları ve hava giriş-çıkış kanalları açık.`,
            };
        }

        _renderLivePhysicsTelemetry() {
            const isEn = this.getLang() === "en";
            const cid = this.getCompartmentId();
            const rm = this.rooms[cid];
            const fireNow = this._isRoomFireActive(cid);
            const pf = this._computeRoomPostFireStats(cid);

            const elPhys = document.getElementById("sc-stat-phys");
            const elSmoke = document.getElementById("sc-stat-smoke");
            const elIso = document.getElementById("sc-stat-isolation");
            const elReign = document.getElementById("sc-stat-reignition");
            const elReent = document.getElementById("sc-stat-reentry");
            const banner = document.getElementById("sc-fdir-banner");

            const shownDp = fireNow ? this.state.dpKpa : 0.0;
            if (elPhys) {
                elPhys.textContent = `+${shownDp.toFixed(2)} kPa`;
                elPhys.style.color = shownDp > 1.5 ? "#fbbf24" : "#6ee7b7";
            }
            if (elSmoke) {
                if (rm.entryClosed) {
                    elSmoke.textContent = isEn ? "Blocked (Hatch Closed)" : "Engellendi (Kapak Kapalı)";
                    elSmoke.style.color = "#34d399";
                } else if (fireNow && this.state.smokeLeakGs > 0.02) {
                    elSmoke.textContent = `${this.state.smokeLeakGs.toFixed(2)} g/s`;
                    elSmoke.style.color = "#fb7185";
                } else {
                    elSmoke.textContent = isEn ? "None (0.00 g/s)" : "Yok (0.00 g/s)";
                    elSmoke.style.color = "#6ee7b7";
                }
            }
            if (elIso) {
                if (rm.entryClosed && rm.airClosed) {
                    elIso.textContent = isEn ? "Room Fully Sealed" : "Oda Tamamen Kapalı";
                    elIso.style.color = "#fbbf24";
                } else if (rm.entryClosed) {
                    elIso.textContent = isEn ? "Hatch Closed • Air Open" : "Kapak Kapalı • Hava Açık";
                    elIso.style.color = "#fcd34d";
                } else if (rm.airClosed) {
                    elIso.textContent = isEn ? "Hatch Open • Air Closed" : "Kapak Açık • Hava Kapalı";
                    elIso.style.color = "#fcd34d";
                } else {
                    elIso.textContent = isEn ? "Hatch & Air Open" : "Kapak ve Hava Açık";
                    elIso.style.color = "#6ee7b7";
                }
            }
            if (elReign) {
                const cDeg = Math.round(pf.coreTempC);
                elReign.textContent = isEn
                    ? `${cDeg} °C (${pf.reignitionRiskPct}%)`
                    : `${cDeg} °C (%${pf.reignitionRiskPct})`;
                elReign.style.color = pf.reignitionRiskPct >= 45 ? "#fb7185" : (pf.reignitionRiskPct >= 15 ? "#fbbf24" : "#6ee7b7");
            }
            if (elReent) {
                if (pf.safeReentrySec <= 0) {
                    elReent.textContent = isEn ? "Safe (0 s)" : "Güvenli (0 sn)";
                    elReent.style.color = "#34d399";
                } else {
                    elReent.textContent = isEn ? `${pf.safeReentrySec} s wait` : `${pf.safeReentrySec} sn bekle`;
                    elReent.style.color = pf.safeReentrySec > 40 ? "#fb7185" : "#fbbf24";
                }
            }
            if (banner) {
                const st = this._buildHumanStatusBanner();
                banner.textContent = st.text;
                banner.dataset.severity = st.sev;
            }
        }

        async _evaluateBackendFdir(simData) {
            clearTimeout(this._fdirTimer);
            this._fdirTimer = setTimeout(async () => {
                try {
                    const compId = this.getCompartmentId();
                    const fireNow = this._isRoomFireActive(compId);
                    const isTherm = this.state.cameraMode === "thermal" || this.state.cameraMode === "split";
                    const vaPayload = {
                        compartment_id: compId,
                        camera_mode: isTherm ? "MWIR_3_5UM" : "OPTICAL_CHEMILUM",
                        optical_blue_chemilum: this.state.coolFlame ? 0.02 : (fireNow ? 0.55 : 0.04),
                        optical_soot_lum: this.state.coolFlame ? 0.0 : (fireNow ? 0.38 : 0.02),
                        mwir_peak_temp_k: fireNow ? this.state.flameTempK : 294.15,
                        mwir_dt_dt_k_s: fireNow ? 9.4 : 0.1,
                        co_ppm: fireNow ? this.state.coPpm : 1.0,
                        laser_transmission: fireNow && !this.state.coolFlame ? 0.78 : 0.985,
                        particle_diameter_um: 0.16,
                        arc_fault_drive: 0.0,
                    };
                    await this.apiFetch("/api/fdir/evaluate", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            sim_state: simData,
                            vision_acoustic: vaPayload,
                            autonomous_enabled: this.state.aiAuto,
                        }),
                    });
                } catch (_) {
                    /* graceful offline continuity */
                }
            }, 150);
        }

        async dispatchHardwareCommand(actionId, engage, targetHatchId, paramU16) {
            const compId = this.getCompartmentId();
            try {
                const res = await this.apiFetch("/api/fdir/command", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        action_id: actionId,
                        compartment_id: compId,
                        target_hatch_id: targetHatchId || null,
                        engage: Boolean(engage),
                        authority_source: "CREW_SAFETY_CONSOLE",
                        parameter_u16: paramU16 || 100,
                    }),
                });
                return await res.json();
            } catch (_) {
                return null;
            }
        }

        /* ====================================================================
         * 1. EXTERIOR & CUTAWAY ORION MPCV + AIRBUS ESM WEBGL ENGINE
         * ==================================================================== */
        _initWebGLResources() {
            const gl = this.gl;
            const extDeriv = gl.getExtension("OES_standard_derivatives");
            const extUint = gl.getExtension("OES_element_index_uint");
            const extAniso =
                gl.getExtension("EXT_texture_filter_anisotropic") ||
                gl.getExtension("WEBKIT_EXT_texture_filter_anisotropic");
            this.maxAniso = extAniso ? Math.min(16, gl.getParameter(extAniso.MAX_TEXTURE_MAX_ANISOTROPY_EXT)) : 1;

            const mkHdTex = (w, h, fn, ws, wt) => {
                const c = document.createElement("canvas");
                c.width = w;
                c.height = h;
                const ctx = c.getContext("2d");
                ctx.imageSmoothingEnabled = true;
                ctx.imageSmoothingQuality = "high";
                fn(ctx, w, h);
                const t = gl.createTexture();
                gl.bindTexture(gl.TEXTURE_2D, t);
                gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, c);
                gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, ws || gl.REPEAT);
                gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, wt || gl.REPEAT);
                gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR);
                gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
                if (extAniso) {
                    gl.texParameterf(gl.TEXTURE_2D, extAniso.TEXTURE_MAX_ANISOTROPY_EXT, this.maxAniso);
                }
                gl.generateMipmap(gl.TEXTURE_2D);
                return t;
            };

            const drawNasaMeatball = (ctx, cx, cy, R) => {
                ctx.save();
                ctx.fillStyle = "#0B3D91";
                ctx.beginPath();
                ctx.arc(cx, cy, R, 0, Math.PI * 2);
                ctx.fill();
                ctx.strokeStyle = "#ffffff";
                ctx.lineWidth = R * 0.055;
                ctx.beginPath();
                ctx.ellipse(cx, cy, R * 0.82, R * 0.28, -0.45, 0, Math.PI * 2);
                ctx.stroke();
                ctx.strokeStyle = "#FC3D21";
                ctx.lineWidth = R * 0.13;
                ctx.lineCap = "round";
                ctx.lineJoin = "round";
                ctx.beginPath();
                ctx.moveTo(cx - R * 0.76, cy + R * 0.32);
                ctx.lineTo(cx + R * 0.18, cy - R * 0.54);
                ctx.lineTo(cx + R * 0.70, cy + R * 0.36);
                ctx.stroke();
                ctx.fillStyle = "#ffffff";
                ctx.font = `900 ${Math.round(R * 0.50)}px Arial, sans-serif`;
                ctx.textAlign = "center";
                ctx.textBaseline = "middle";
                ctx.fillText("NASA", cx, cy + R * 0.06);
                ctx.restore();
            };

            // Authentic Artemis Orion MPCV Backshell Texture:
            // Matte-white forward bay thermal collar + metallic silver/charcoal AETB-8 thermal tile grid
            this.texOrionArtemisSilverHD = mkHdTex(2048, 2048, (ctx, w, h) => {
                // Upper forward bay white thermal blanket collar
                ctx.fillStyle = "#EEF2F7";
                ctx.fillRect(0, 0, w, 520);
                ctx.fillStyle = "#CBD5E1";
                ctx.fillRect(0, 502, w, 22);

                // Metallic silver-coated AETB-8 thermal protection tiles (Artemis flight standard)
                let s = 2026;
                const rnd = () => {
                    s = (s * 16807) % 2147483647;
                    return (s - 1) / 2147483646;
                };
                const tw = 88;
                const th = 58;
                for (let y = 524; y < h; y += th) {
                    const off = (Math.floor(y / th) % 2) * 44;
                    for (let x = -44; x < w + 44; x += tw) {
                        const v = rnd();
                        const baseLum = Math.round(146 + v * 46);
                        const coolShift = Math.round(v * 10);
                        ctx.fillStyle = `rgb(${baseLum - 4},${baseLum},${baseLum + 6 + coolShift})`;
                        ctx.fillRect(x + off, y, tw - 2, th - 2);
                        ctx.strokeStyle = "rgba(30, 41, 59, 0.42)";
                        ctx.lineWidth = 2;
                        ctx.strokeRect(x + off, y, tw - 2, th - 2);
                    }
                }

                // Subtle RCS & umbilical dark reinforced tile patches
                ctx.fillStyle = "#334155";
                ctx.fillRect(260, 740, 120, 76);
                ctx.fillRect(1180, 740, 120, 76);

                // Authentic insignia on white forward bay collar
                drawNasaMeatball(ctx, 430, 265, 96);
                ctx.fillStyle = "#1E293B";
                ctx.font = "800 104px Arial, sans-serif";
                ctx.textAlign = "center";
                ctx.fillText("ORION", 1040, 298);

                // US Flag
                const fx = 1460;
                const fy = 195;
                const fw = 228;
                const fh = 132;
                for (let st = 0; st < 13; st++) {
                    ctx.fillStyle = st % 2 === 0 ? "#B91C1C" : "#F8FAFC";
                    ctx.fillRect(fx, fy + (st * fh) / 13, fw, fh / 13 + 1);
                }
                ctx.fillStyle = "#1E3A8A";
                ctx.fillRect(fx, fy, fw * 0.42, fh * (7 / 13));

                // ESA Patch
                ctx.fillStyle = "#0F4C81";
                ctx.beginPath();
                ctx.arc(1855, 265, 72, 0, Math.PI * 2);
                ctx.fill();
                ctx.fillStyle = "#F8FAFC";
                ctx.font = "bold 48px Arial, sans-serif";
                ctx.fillText("esa", 1855, 279);
            });

            // Authentic Airbus European Service Module (ESM) White/Silver Radiator Panel Texture
            this.texEsmRadiatorHD = mkHdTex(2048, 2048, (ctx, w, h) => {
                ctx.fillStyle = "#E9EEF5";
                ctx.fillRect(0, 0, w, h);

                // Fine horizontal ammonia/glycol radiator fluid tubes
                ctx.strokeStyle = "rgba(100, 116, 139, 0.28)";
                ctx.lineWidth = 3;
                for (let y = 90; y < h - 90; y += 46) {
                    ctx.beginPath();
                    ctx.moveTo(40, y);
                    ctx.lineTo(w - 40, y);
                    ctx.stroke();
                }

                // Vertical manifold headers & brushed aluminum frame borders
                ctx.fillStyle = "#CBD5E1";
                ctx.fillRect(0, 0, 68, h);
                ctx.fillRect(w - 68, 0, 68, h);
                ctx.fillRect(0, 0, w, 74);
                ctx.fillRect(0, h - 74, w, 74);

                ctx.fillStyle = "#0B3D91";
                ctx.fillRect(68, 980, w - 136, 30);
                drawNasaMeatball(ctx, 440, 560, 102);
                ctx.fillStyle = "#1E293B";
                ctx.font = "800 104px Arial, sans-serif";
                ctx.textAlign = "center";
                ctx.fillText("ARTEMIS  ESM", 1260, 595);
            });

            this.texEarthHD = mkHdTex(
                2048,
                1024,
                (ctx, w, h) => {
                    const g = ctx.createLinearGradient(0, 0, 0, h);
                    g.addColorStop(0.0, "#0b2559");
                    g.addColorStop(0.16, "#093a8c");
                    g.addColorStop(0.5, "#062c73");
                    g.addColorStop(0.84, "#093a8c");
                    g.addColorStop(1.0, "#0b2559");
                    ctx.fillStyle = g;
                    ctx.fillRect(0, 0, w, h);

                    const continents = [
                        { pts: [[260, 220], [440, 190], [560, 290], [510, 440], [390, 490], [310, 390]], col: "#1e6b3a", hi: "#8a6d3b" },
                        { pts: [[470, 510], [590, 540], [640, 690], [560, 840], [490, 790], [450, 620]], col: "#166534", hi: "#4d7c0f" },
                        { pts: [[930, 210], [1140, 185], [1230, 275], [1160, 355], [970, 345]], col: "#2f6f3e", hi: "#a16207" },
                        { pts: [[960, 380], [1190, 395], [1280, 540], [1190, 745], [1045, 730], [955, 535]], col: "#b47b38", hi: "#ca8a04" },
                        { pts: [[1210, 195], [1620, 180], [1760, 320], [1670, 470], [1430, 485], [1260, 365]], col: "#1f6f43", hi: "#926c35" },
                        { pts: [[1580, 620], [1765, 610], [1815, 735], [1675, 790], [1565, 720]], col: "#b86b2b", hi: "#eab308" },
                    ];
                    continents.forEach((c) => {
                        ctx.save();
                        ctx.beginPath();
                        c.pts.forEach(([px, py], i) => (i === 0 ? ctx.moveTo(px, py) : ctx.lineTo(px, py)));
                        ctx.closePath();
                        ctx.lineJoin = "round";
                        ctx.strokeStyle = "rgba(14, 165, 233, 0.36)";
                        ctx.lineWidth = 26;
                        ctx.stroke();
                        ctx.fillStyle = c.col;
                        ctx.fill();
                        ctx.clip();
                        ctx.fillStyle = c.hi;
                        ctx.globalAlpha = 0.48;
                        ctx.beginPath();
                        ctx.ellipse(c.pts[1][0], c.pts[2][1], 130, 75, 0.35, 0, Math.PI * 2);
                        ctx.fill();
                        ctx.restore();
                    });

                    const pg = ctx.createLinearGradient(0, 0, 0, 88);
                    pg.addColorStop(0, "rgba(248, 250, 252, 0.95)");
                    pg.addColorStop(1, "rgba(226, 232, 240, 0.0)");
                    ctx.fillStyle = pg;
                    ctx.fillRect(0, 0, w, 88);

                    const sg = ctx.createLinearGradient(0, h - 92, 0, h);
                    sg.addColorStop(0, "rgba(226, 232, 240, 0.0)");
                    sg.addColorStop(1, "rgba(248, 250, 252, 0.95)");
                    ctx.fillStyle = sg;
                    ctx.fillRect(0, h - 92, w, 92);

                    for (let i = 0; i < 120; i++) {
                        const cx = (i * 173 + 60) % w;
                        const cy = 75 + ((i * 139) % (h - 150));
                        const rw = 85 + (i % 5) * 42;
                        const rh = 11 + (i % 4) * 6;
                        const cg = ctx.createRadialGradient(cx, cy, 4, cx, cy, rw);
                        cg.addColorStop(0, "rgba(255, 255, 255, 0.58)");
                        cg.addColorStop(0.55, "rgba(241, 245, 249, 0.25)");
                        cg.addColorStop(1, "rgba(255, 255, 255, 0.0)");
                        ctx.save();
                        ctx.translate(cx, cy);
                        ctx.rotate(((i % 7) - 3) * 0.08);
                        ctx.scale(1, rh / rw);
                        ctx.fillStyle = cg;
                        ctx.beginPath();
                        ctx.arc(0, 0, rw, 0, Math.PI * 2);
                        ctx.fill();
                        ctx.restore();
                    }
                },
                gl.REPEAT,
                gl.CLAMP_TO_EDGE
            );

            const VS = `
                attribute vec3 aPos, aNorm;
                attribute vec2 aUv;
                uniform mat4 uProj, uView, uModel;
                varying vec3 vWorld, vNorm, vLocal;
                varying vec2 vUv;
                void main() {
                    vec4 wp = uModel * vec4(aPos, 1.0);
                    vWorld = wp.xyz;
                    vLocal = aPos;
                    vNorm = mat3(uModel) * aNorm;
                    vUv = aUv;
                    gl_Position = uProj * uView * wp;
                }
            `;

            const FS = `
                ${extDeriv ? "#extension GL_OES_standard_derivatives : enable" : ""}
                precision highp float;
                varying vec3 vWorld, vNorm, vLocal;
                varying vec2 vUv;
                uniform sampler2D uTex;
                uniform float uUseTex, uMatType, uMet, uRg, uIrid, uEm, uAl, uSatGain, uFirePow;
                uniform vec3 uTint, uCam, uFirePos;

                float hash21(vec2 p) {
                    p = fract(p * vec2(234.34, 435.345));
                    p += dot(p, p + 34.23);
                    return fract(p.x * p.y);
                }

                vec2 voronoiFoil(vec2 x) {
                    vec2 n = floor(x), f = fract(x);
                    float d1 = 8.0, d2 = 8.0, id = 0.0;
                    for (int j = -1; j <= 1; j++) {
                        for (int i = -1; i <= 1; i++) {
                            vec2 g = vec2(float(i), float(j));
                            vec2 o = vec2(hash21(n + g), hash21(n + g + 17.3));
                            vec2 r = g - f + o;
                            float d = dot(r, r);
                            if (d < d1) { d2 = d1; d1 = d; id = o.x; }
                            else if (d < d2) { d2 = d; }
                        }
                    }
                    return vec2(clamp((sqrt(d2) - sqrt(d1)) * 2.8, 0.0, 1.0), id);
                }

                vec3 thinFilm(float c) {
                    return 0.5 + 0.5 * cos(6.28318 * ((1.0 - c) * 1.15 + vec3(0.0, 0.33, 0.67)));
                }

                vec3 rgb2hsv(vec3 c) {
                    vec4 K = vec4(0.0, -1.0 / 3.0, 2.0 / 3.0, -1.0);
                    vec4 p = mix(vec4(c.bg, K.wz), vec4(c.gb, K.xy), step(c.b, c.g));
                    vec4 q = mix(vec4(p.xyw, c.r), vec4(c.r, p.yzx), step(p.x, c.r));
                    float d = q.x - min(q.w, q.y);
                    float e = 1.0e-10;
                    return vec3(abs(q.z + (q.w - q.y) / (6.0 * d + e)), d / (q.x + e), q.x);
                }

                vec3 hsv2rgb(vec3 c) {
                    vec4 K = vec4(1.0, 2.0 / 3.0, 1.0 / 3.0, 3.0);
                    vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www);
                    return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);
                }

                vec3 gradeNaturalPBR(vec3 hdr, float satGain) {
                    vec3 mapped = (hdr * (2.51 * hdr + 0.03)) / (hdr * (2.43 * hdr + 0.59) + 0.14);
                    vec3 srgb = pow(clamp(mapped, 0.0, 1.0), vec3(1.0 / 2.2));
                    vec3 hsv = rgb2hsv(srgb);
                    hsv.y = clamp(hsv.y * satGain, 0.0, 0.92);
                    return clamp(hsv2rgb(hsv), 0.0, 1.0);
                }

                void main() {
                    if (uMatType > 5.5) {
                        vec3 dir = normalize(vLocal);
                        vec3 spaceBg = mix(vec3(0.005, 0.011, 0.028), vec3(0.012, 0.030, 0.068), pow(clamp(dir.y * 0.5 + 0.5, 0.0, 1.0), 1.8));
                        vec2 sUv = vec2(atan(dir.z, dir.x) * 95.0, dir.y * 160.0);
                        vec2 cell = floor(sUv), fr = fract(sUv) - 0.5;
                        float rnd = hash21(cell);
                        float star = rnd > 0.970 ? smoothstep(0.22, 0.02, length(fr)) * (0.55 + 1.4 * fract(rnd * 91.7)) : 0.0;
                        vec3 starCol = rnd > 0.99 ? vec3(1.0, 0.88, 0.62) : (rnd > 0.98 ? vec3(0.72, 0.88, 1.0) : vec3(0.95));
                        gl_FragColor = vec4(clamp(spaceBg + starCol * star, 0.0, 1.0), 1.0);
                        return;
                    }

                    vec4 tx = texture2D(uTex, vUv);
                    vec3 baseSrgb = uUseTex > 0.5 ? (tx.rgb * uTint) : uTint;
                    float matMet = uMet;
                    float matRg = uRg;
                    float procH = 0.5;

                    if (uMatType < 0.5 && uUseTex > 0.5) {
                        vec2 g = abs(fract(vUv * vec2(18.0, 14.0)) - 0.5);
                        float seam = smoothstep(0.47, 0.495, max(g.x, g.y));
                        baseSrgb *= (1.0 - seam * 0.14);
                        procH = 1.0 - seam;
                    } else if (uMatType > 0.5 && uMatType < 1.5) {
                        // Subtle aerospace Kapton MLI gold foil (recessed bays/collars)
                        vec2 vf = voronoiFoil(vUv * 16.0);
                        vec2 vf2 = voronoiFoil(vUv * 36.0 + 3.7);
                        float crease = vf.x * 0.70 + vf2.x * 0.30;
                        vec3 deepGold = vec3(0.66, 0.44, 0.12);
                        vec3 warmGold = vec3(0.86, 0.66, 0.24);
                        vec3 specGold = vec3(0.95, 0.82, 0.46);
                        baseSrgb = mix(deepGold, warmGold, smoothstep(0.08, 0.58, crease));
                        baseSrgb = mix(baseSrgb, specGold, smoothstep(0.68, 0.98, crease) * 0.55) * uTint;
                        procH = crease;
                        matMet = 0.86;
                        matRg = mix(0.32, 0.17, crease);
                    } else if (uMatType > 1.5 && uMatType < 2.5) {
                        // Authentic dark navy/anthracite GaAs X-Wing photovoltaic solar cells
                        vec2 cUv = vUv * vec2(18.0, 9.0);
                        vec2 f = fract(cUv);
                        float border = step(0.93, f.x) + step(0.94, f.y);
                        float silverBus = (f.y > 0.88 && f.y < 0.93 && f.x > 0.22 && f.x < 0.78) ? 1.0 : 0.0;
                        float finger = step(0.96, fract(f.x * 6.0)) * (1.0 - border);
                        vec3 cellCol = mix(vec3(0.05, 0.10, 0.20), vec3(0.08, 0.16, 0.30), f.y);
                        cellCol = mix(cellCol, vec3(0.58, 0.66, 0.76), finger * 0.26);
                        if (silverBus > 0.5) { cellCol = vec3(0.76, 0.80, 0.86); matMet = 0.88; matRg = 0.18; }
                        else if (border > 0.5) { cellCol = vec3(0.08, 0.10, 0.14); matMet = 0.25; matRg = 0.48; }
                        else { matMet = 0.62; matRg = 0.16; }
                        baseSrgb = cellCol;
                        procH = border > 0.5 ? 0.15 : 0.85;
                    } else if (uMatType > 3.5 && uMatType < 4.5) {
                        // Realistic C/SiC & Columbium AJ10-190 OMS-E Engine Bell Nozzle (charcoal-titanium metallic)
                        float y = clamp(vUv.y, 0.0, 1.0);
                        vec3 throatCol = vec3(0.54, 0.56, 0.60);
                        vec3 midCol = vec3(0.24, 0.26, 0.30);
                        vec3 skirtCol = vec3(0.14, 0.16, 0.19);
                        vec3 noz = y < 0.35 ? mix(throatCol, midCol, y / 0.35) : mix(midCol, skirtCol, (y - 0.35) / 0.65);
                        float flute = sin(vUv.x * 140.0) * 0.5 + 0.5;
                        float stiffRing = step(0.86, fract(y * 7.0));
                        baseSrgb = noz * (0.90 + 0.16 * flute) + vec3(0.08) * stiffRing;
                        procH = flute;
                        matMet = 0.84;
                        matRg = 0.26;
                    } else if (uMatType > 4.5 && uMatType < 5.5) {
                        // Authentic AVCOAT Ablative Heatshield (charcoal-umber phenolic honeycomb blocks)
                        vec2 bUv = vUv * vec2(34.0, 24.0);
                        vec2 id = floor(bUv), f = fract(bUv);
                        float v = hash21(id);
                        float seam = step(0.91, f.x) + step(0.91, f.y);
                        vec3 tile = mix(vec3(0.24, 0.18, 0.15), vec3(0.36, 0.26, 0.20), v);
                        baseSrgb = seam > 0.5 ? vec3(0.16, 0.13, 0.11) : tile;
                        procH = seam > 0.5 ? 0.2 : 0.8;
                        matMet = 0.10;
                        matRg = 0.62;
                    }

                    vec3 albedo = pow(clamp(baseSrgb, 0.0, 1.2), vec3(2.2));
                    vec3 N = normalize(vNorm);
                    if (!gl_FrontFacing) N = -N;

                    ${
                        extDeriv
                            ? `
                    if (uMatType < 5.5) {
                        vec3 dpx = dFdx(vWorld), dpy = dFdy(vWorld);
                        vec3 r1 = cross(dpy, N), r2 = cross(N, dpx);
                        float det = dot(dpx, r1);
                        float bmpAmt = (uMatType > 0.5 && uMatType < 1.5) ? 0.32 : 0.14;
                        if (abs(det) > 1e-8) {
                            N = normalize(abs(det) * N - bmpAmt * sign(det) * (dFdx(procH) * r1 + dFdy(procH) * r2));
                        }
                    }
                    `
                            : ""
                    }

                    vec3 V = normalize(uCam - vWorld);
                    vec3 L = normalize(vec3(0.68, 0.54, 0.50));
                    vec3 H = normalize(V + L);

                    float NL = max(dot(N, L), 0.0);
                    float NV = max(dot(N, V), 0.02);
                    float NH = max(dot(N, H), 0.0);
                    float VH = max(dot(V, H), 0.0);

                    float rg = clamp(matRg, 0.08, 0.92);
                    float a = rg * rg, a2 = a * a;
                    float dn = NH * NH * (a2 - 1.0) + 1.0;
                    float D = a2 / max(0.00018, 3.14159 * dn * dn);

                    vec3 F0 = mix(vec3(0.035), albedo, matMet);
                    if (uIrid > 0.01) F0 = mix(F0, thinFilm(NV), uIrid * 0.45);
                    vec3 F = F0 + (1.0 - F0) * pow(1.0 - VH, 5.0);

                    float k = (rg + 1.0) * (rg + 1.0) / 8.0;
                    float G = (NV / (NV * (1.0 - k) + k)) * (NL / (NL * (1.0 - k) + k));
                    vec3 spec = (D * F * G) / max(0.025, 4.0 * NV * NL);

                    float diffKeep = mix(1.0, 0.35, matMet);
                    vec3 direct = (diffKeep * albedo / 3.14159 + spec) * vec3(3.45, 3.40, 3.35) * NL;

                    vec3 L2 = normalize(vec3(-0.65, -0.42, 0.62));
                    vec3 bounce = albedo * (0.28 + 0.46 * max(dot(N, L2), 0.0)) * 0.52;

                    vec3 R = reflect(-V, N);
                    float skyGrad = clamp(R.y * 0.5 + 0.5, 0.0, 1.0);
                    vec3 studioEnv = mix(vec3(0.62, 0.70, 0.82), vec3(0.98, 0.98, 0.96), skyGrad);
                    vec3 F_env = F0 + (max(vec3(1.0 - rg), F0) - F0) * pow(1.0 - NV, 5.0);
                    vec3 envRefl = studioEnv * F_env * mix(0.08, 1.15, matMet) * (1.0 - rg * 0.55);

                    vec3 selfRim = albedo * pow(1.0 - NV, 4.0) * 0.25;

                    vec3 fireGlow = vec3(0.0);
                    if (uFirePow > 0.01) {
                        vec3 dF = uFirePos - vWorld;
                        fireGlow = vec3(2.1, 0.55, 0.08) * (uFirePow / (dot(dF, dF) + 0.14)) * max(dot(N, normalize(dF)), 0.28) * (albedo + vec3(0.10));
                    }

                    vec3 hdr = albedo * 0.18 + bounce + envRefl + selfRim + direct + fireGlow + albedo * uEm;
                    gl_FragColor = vec4(gradeNaturalPBR(hdr, uSatGain), uAl);
                }
            `;

            const compile = (tp, src) => {
                const s = gl.createShader(tp);
                gl.shaderSource(s, src);
                gl.compileShader(s);
                return s;
            };

            this.prog = gl.createProgram();
            gl.attachShader(this.prog, compile(gl.VERTEX_SHADER, VS));
            gl.attachShader(this.prog, compile(gl.FRAGMENT_SHADER, FS));
            gl.linkProgram(this.prog);
            gl.useProgram(this.prog);

            this.U = {};
            ["aPos", "aNorm", "aUv"].forEach((k) => {
                this.U[k] = gl.getAttribLocation(this.prog, k);
            });
            [
                "uProj", "uView", "uModel", "uTex", "uUseTex", "uMatType",
                "uTint", "uMet", "uRg", "uIrid", "uEm", "uAl", "uSatGain",
                "uCam", "uFirePos", "uFirePow",
            ].forEach((k) => {
                this.U[k] = gl.getUniformLocation(this.prog, k);
            });

            const toGpu = (pos, norm, uv, idx) => {
                const mk = (arr, tgt, Ctor) => {
                    const b = gl.createBuffer();
                    gl.bindBuffer(tgt, b);
                    gl.bufferData(tgt, new Ctor(arr), gl.STATIC_DRAW);
                    return b;
                };
                const u32 = extUint && pos.length / 3 > 65000;
                return {
                    p: mk(pos, gl.ARRAY_BUFFER, Float32Array),
                    n: mk(norm, gl.ARRAY_BUFFER, Float32Array),
                    u: mk(uv, gl.ARRAY_BUFFER, Float32Array),
                    i: mk(idx, gl.ELEMENT_ARRAY_BUFFER, u32 ? Uint32Array : Uint16Array),
                    tp: u32 ? gl.UNSIGNED_INT : gl.UNSIGNED_SHORT,
                    c: idx.length,
                };
            };

            const buildLathe = (pts, segs, cutDeg = 0, uRep = 1.0, startOffsetRad = 0.0) => {
                const pos = [];
                const norm = [];
                const uv = [];
                const idx = [];
                const span = ((360 - cutDeg) * Math.PI) / 180;
                const stR = startOffsetRad + (cutDeg * 0.5 * Math.PI) / 180;
                for (let m = 0; m < pts.length; m++) {
                    const p0 = pts[m];
                    const p1 = pts[(m + 1) % pts.length];
                    const dr = p1.r - p0.r;
                    const dy = p1.y - p0.y;
                    const ln = Math.hypot(dr, dy) || 1;
                    const nr = -dy / ln;
                    const ny = dr / ln;
                    const bv = pos.length / 3;
                    for (let s = 0; s <= segs; s++) {
                        const t = s / segs;
                        const th = stR + t * span;
                        const c = Math.cos(th);
                        const sn = Math.sin(th);
                        [p0, p1].forEach((pt) => {
                            pos.push(c * pt.r, pt.y, sn * pt.r);
                            norm.push(c * nr, ny, sn * nr);
                            uv.push((1.0 - t) * uRep, pt.v);
                        });
                    }
                    for (let s = 0; s < segs; s++) {
                        const i0 = bv + s * 2;
                        idx.push(i0, i0 + 1, i0 + 2, i0 + 2, i0 + 1, i0 + 3);
                    }
                }
                return toGpu(pos, norm, uv, idx);
            };

            const buildSphere = (lat, lon) => {
                const p = [];
                const n = [];
                const u = [];
                const ix = [];
                for (let y = 0; y <= lat; y++) {
                    for (let x = 0; x <= lon; x++) {
                        const v = y / lat;
                        const u0 = x / lon;
                        const ph = v * Math.PI;
                        const th = u0 * Math.PI * 2;
                        const nx = -Math.cos(th) * Math.sin(ph);
                        const ny = Math.cos(ph);
                        const nz = Math.sin(th) * Math.sin(ph);
                        p.push(nx, ny, nz);
                        n.push(nx, ny, nz);
                        u.push(u0, v);
                    }
                }
                for (let y = 0; y < lat; y++) {
                    for (let x = 0; x < lon; x++) {
                        const a = y * (lon + 1) + x;
                        const b = a + lon + 1;
                        ix.push(a, b, a + 1, b, b + 1, a + 1);
                    }
                }
                return toGpu(p, n, u, ix);
            };

            const buildBell = (r0, r1, h, segs) => {
                const p = [];
                const n = [];
                const u = [];
                const ix = [];
                for (let j = 0; j <= 18; j++) {
                    const v = j / 18;
                    const y = (0.5 - v) * h;
                    const r = r0 + (r1 - r0) * Math.pow(v, 0.68);
                    for (let i = 0; i <= segs; i++) {
                        const u0 = i / segs;
                        const a = u0 * Math.PI * 2;
                        p.push(Math.cos(a) * r, y, Math.sin(a) * r);
                        n.push(Math.cos(a) * 0.92, 0.35, Math.sin(a) * 0.92);
                        u.push(u0, v);
                    }
                }
                for (let j = 0; j < 18; j++) {
                    for (let i = 0; i < segs; i++) {
                        const a = j * (segs + 1) + i;
                        const b = a + segs + 1;
                        ix.push(a, b, a + 1, b, b + 1, a + 1);
                    }
                }
                return toGpu(p, n, u, ix);
            };

            const buildBox = () => {
                const p = [];
                const n = [];
                const u = [];
                const ix = [];
                const f = [
                    { n: [0, 0, 1], v: [[-0.5, -0.5, 0.5], [0.5, -0.5, 0.5], [0.5, 0.5, 0.5], [-0.5, 0.5, 0.5]] },
                    { n: [0, 0, -1], v: [[0.5, -0.5, -0.5], [-0.5, -0.5, -0.5], [-0.5, 0.5, -0.5], [0.5, 0.5, -0.5]] },
                    { n: [0, 1, 0], v: [[-0.5, 0.5, 0.5], [0.5, 0.5, 0.5], [0.5, 0.5, -0.5], [-0.5, 0.5, -0.5]] },
                    { n: [0, -1, 0], v: [[-0.5, -0.5, -0.5], [0.5, -0.5, -0.5], [0.5, -0.5, 0.5], [-0.5, -0.5, 0.5]] },
                    { n: [1, 0, 0], v: [[0.5, -0.5, 0.5], [0.5, -0.5, -0.5], [0.5, 0.5, -0.5], [0.5, 0.5, 0.5]] },
                    { n: [-1, 0, 0], v: [[-0.5, -0.5, -0.5], [-0.5, -0.5, 0.5], [-0.5, 0.5, 0.5], [-0.5, 0.5, -0.5]] },
                ];
                f.forEach((fc, fi) => {
                    const b = fi * 4;
                    const uv = [[0, 1], [1, 1], [1, 0], [0, 0]];
                    fc.v.forEach((pt, k) => {
                        p.push(...pt);
                        n.push(...fc.n);
                        u.push(...uv[k]);
                    });
                    ix.push(b, b + 1, b + 2, b, b + 2, b + 3);
                });
                return toGpu(p, n, u, ix);
            };

            const cmProfile = [
                { r: 0.56, y: 0.68, v: 0.04 },
                { r: 1.62, y: -0.58, v: 0.96 },
                { r: 1.50, y: -0.58, v: 0.96 },
                { r: 0.48, y: 0.68, v: 0.04 },
            ];
            const cylProfile = [
                { r: 1.0, y: 0.5, v: 0.02 },
                { r: 1.0, y: -0.5, v: 0.98 },
                { r: 0.93, y: -0.5, v: 0.98 },
                { r: 0.93, y: 0.5, v: 0.02 },
            ];
            // Sealed solid cylindrical disc / bulkhead plate
            const discProfile = [
                { r: 0.0, y: 0.5, v: 0.0 },
                { r: 1.0, y: 0.5, v: 1.0 },
                { r: 1.0, y: -0.5, v: 1.0 },
                { r: 0.0, y: -0.5, v: 0.0 },
            ];
            // Conical Crew Module Adapter (CMA) bridging CM heatshield rim (r=1.52) to ESM top ring (r=1.18)
            const cmaProfile = [
                { r: 1.50, y: 0.22, v: 0.05 },
                { r: 1.18, y: -0.22, v: 0.95 },
                { r: 1.10, y: -0.22, v: 0.95 },
                { r: 1.40, y: 0.22, v: 0.05 },
            ];

            // Cutaway opening faces +Z (camera at yaw ~ 0 looks straight into +Z)
            // In buildLathe, angle theta=PI/2 is +Z, so startOffsetRad = PI/2 centers the cutaway wedge toward +Z!
            this.M = {
                sph: buildSphere(36, 52),
                box: buildBox(),
                bell: buildBell(0.16, 0.46, 0.78, 44),
                vernier: buildBell(0.032, 0.095, 0.22, 20),
                disc: buildLathe(discProfile, 56, 0, 1.0),
                orionCm: buildLathe(cmProfile, 64, 0, 1.0),
                orionCmCut: buildLathe(cmProfile, 56, 132, 0.65, Math.PI * 0.5 + 2.15),
                cmaRing: buildLathe(cmaProfile, 60, 0, 1.0),
                cmaRingCut: buildLathe(cmaProfile, 52, 132, 0.65, Math.PI * 0.5),
                avcoat: buildLathe(
                    [
                        { r: 0.0, y: -0.22, v: 0.05 },
                        { r: 0.98, y: -0.17, v: 0.55 },
                        { r: 1.63, y: -0.01, v: 0.95 },
                        { r: 1.63, y: 0.08, v: 0.98 },
                        { r: 0.0, y: 0.08, v: 0.05 },
                    ],
                    64,
                    0,
                    1.0
                ),
                cyl: buildLathe(cylProfile, 56, 0, 1.0),
                cylCut: buildLathe(cylProfile, 48, 132, 0.65, Math.PI * 0.5),
            };
        }

        _mm(a, b) {
            const o = new Float32Array(16);
            for (let c = 0; c < 4; c++) {
                for (let r = 0; r < 4; r++) {
                    o[c * 4 + r] =
                        a[r] * b[c * 4] +
                        a[4 + r] * b[c * 4 + 1] +
                        a[8 + r] * b[c * 4 + 2] +
                        a[12 + r] * b[c * 4 + 3];
                }
            }
            return o;
        }

        _trs(tx, ty, tz, rx, ry, rz, sx, sy, sz) {
            const cx = Math.cos(rx);
            const sxr = Math.sin(rx);
            const cy = Math.cos(ry);
            const syr = Math.sin(ry);
            const cz = Math.cos(rz);
            const szr = Math.sin(rz);
            return this._mm(
                new Float32Array([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, tx, ty, tz, 1]),
                this._mm(
                    new Float32Array([cy, 0, -syr, 0, 0, 1, 0, 0, syr, 0, cy, 0, 0, 0, 0, 1]),
                    this._mm(
                        new Float32Array([1, 0, 0, 0, 0, cx, sxr, 0, 0, -sxr, cx, 0, 0, 0, 0, 1]),
                        this._mm(
                            new Float32Array([cz, szr, 0, 0, -szr, cz, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]),
                            new Float32Array([sx, 0, 0, 0, 0, sy, 0, 0, 0, 0, sz, 0, 0, 0, 0, 1])
                        )
                    )
                )
            );
        }

        _draw(m, mat, o = {}) {
            const gl = this.gl;
            const U = this.U;
            gl.uniformMatrix4fv(U.uModel, false, mat);
            if (o.tex) {
                gl.activeTexture(gl.TEXTURE0);
                gl.bindTexture(gl.TEXTURE_2D, o.tex);
                gl.uniform1i(U.uTex, 0);
                gl.uniform1f(U.uUseTex, 1.0);
            } else {
                gl.uniform1f(U.uUseTex, 0.0);
            }
            gl.uniform1f(U.uMatType, o.mt ?? 0.0);
            gl.uniform3fv(U.uTint, o.tint || [1, 1, 1]);
            gl.uniform1f(U.uMet, o.met ?? 0.12);
            gl.uniform1f(U.uRg, o.rg ?? 0.28);
            gl.uniform1f(U.uIrid, o.irid ?? 0.0);
            gl.uniform1f(U.uEm, o.em ?? 0.0);
            gl.uniform1f(U.uAl, o.al ?? 1.0);
            [
                ["p", U.aPos, 3],
                ["n", U.aNorm, 3],
                ["u", U.aUv, 2],
            ].forEach(([k, l, s]) => {
                gl.bindBuffer(gl.ARRAY_BUFFER, m[k]);
                gl.enableVertexAttribArray(l);
                gl.vertexAttribPointer(l, s, gl.FLOAT, false, 0, 0);
            });
            gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, m.i);
            gl.drawElements(gl.TRIANGLES, m.c, m.tp, 0);
        }

        _renderOrionCutawayInterior(t) {
            const M = this.M;
            const gl = this.gl;
            const activeCid = this.getCompartmentId();

            // Central pressurized crew/utility spine
            this._draw(M.cyl, this._trs(0, 0.92, 0, 0, 0, 0, 0.24, 1.28, 0.24), {
                tint: [0.62, 0.68, 0.76],
                met: 0.65,
                rg: 0.28,
            });

            COMPARTMENT_ORDER.forEach((cid) => {
                const def = ROOM_DEFS[cid];
                const rm = this.rooms[cid];
                const isSel = cid === activeCid;
                const isFire = this._isRoomFireActive(cid);
                const isSealed = rm && rm.entryClosed && rm.airClosed;
                const pulse = 0.65 + 0.35 * Math.sin(t * 7.5);

                // Structural deck floor disc
                const deckTint = isFire
                    ? [0.95, 0.32, 0.12]
                    : (isSealed ? [0.85, 0.62, 0.16] : (isSel ? [0.22, 0.68, 0.94] : [0.46, 0.53, 0.62]));
                this._draw(
                    M.disc,
                    this._trs(0, def.cutawayY - def.cutawayH * 0.46, 0, 0, 0, 0, def.cutawayR, 0.045, def.cutawayR),
                    {
                        tint: deckTint,
                        met: 0.55,
                        rg: 0.28,
                        em: isFire ? 0.85 * pulse : (isSel ? 0.32 : 0.04),
                    }
                );

                // 3D Internal Equipment Representation inside Cutaway
                if (cid === "ORION_CM") {
                    // Two crew seats + MFD console inside Command Deck
                    [-0.32, 0.32].forEach((sx) => {
                        this._draw(M.box, this._trs(sx, def.cutawayY - 0.04, 0.12, -0.35, 0, 0, 0.26, 0.18, 0.30), {
                            tint: [0.76, 0.34, 0.14],
                            met: 0.18,
                            rg: 0.52,
                        });
                    });
                    this._draw(M.box, this._trs(0, def.cutawayY + 0.08, 0.36, 0.28, 0, 0, 0.54, 0.16, 0.06), {
                        tint: rm.powerCut ? [0.10, 0.14, 0.20] : [0.14, 0.68, 0.95],
                        met: 0.45,
                        rg: 0.18,
                        em: rm.powerCut ? 0.0 : 0.55,
                    });
                } else if (cid === "IHAB") {
                    // Crew habitat bunks + SoFIE rack
                    [-0.58, 0.58].forEach((rx, idx) => {
                        this._draw(M.box, this._trs(rx, def.cutawayY, 0.10, 0, 0, 0, 0.34, 0.30, 0.42), {
                            tint: idx === 0 ? [0.82, 0.86, 0.92] : [0.22, 0.34, 0.50],
                            met: 0.35,
                            rg: 0.36,
                        });
                    });
                } else if (cid === "HALO") {
                    // Power distribution & SSPC racks + gold harness
                    [-0.48, 0.48].forEach((rx) => {
                        this._draw(M.box, this._trs(rx, def.cutawayY, 0.12, 0, 0, 0, 0.32, 0.34, 0.36), {
                            tint: [0.16, 0.22, 0.32],
                            met: 0.62,
                            rg: 0.26,
                            em: rm.powerCut ? 0.0 : 0.14,
                        });
                    });
                } else if (cid === "PPE") {
                    // Composite O2/N2 spherical tanks + CAMRAS scrubbers
                    [-0.44, 0.44].forEach((tx, ti) => {
                        this._draw(M.sph, this._trs(tx, def.cutawayY, 0.18, 0, 0, 0, 0.22, 0.22, 0.22), {
                            tint: ti === 0 ? [0.16, 0.52, 0.34] : [0.18, 0.38, 0.68],
                            met: 0.58,
                            rg: 0.24,
                        });
                    });
                } else if (cid === "AIRLOCK") {
                    // Internal hatch ring
                    this._draw(M.disc, this._trs(0, def.cutawayY, 0, 0, 0, 0, 0.36, 0.04, 0.36), {
                        tint: [0.74, 0.78, 0.84],
                        met: 0.72,
                        rg: 0.22,
                    });
                }

                // Live 3D Fire Sphere inside Cutaway Compartment if Active
                if (isFire) {
                    gl.enable(gl.BLEND);
                    gl.blendFunc(gl.SRC_ALPHA, gl.ONE);
                    gl.depthMask(false);
                    const fp = def.firePos3d;
                    const rFlame = 0.13 + 0.03 * Math.sin(t * 14.0);
                    this._draw(M.sph, this._trs(fp[0] * 0.65, def.cutawayY + 0.02, 0.24, 0, 0, 0, rFlame, rFlame, rFlame), {
                        tint: this.state.coolFlame ? [0.55, 0.32, 0.95] : [1.0, 0.48, 0.08],
                        em: 2.8,
                        al: 0.85,
                    });
                    gl.depthMask(true);
                    gl.disable(gl.BLEND);
                }
            });
        }

        _renderOrionMcp(t) {
            const M = this.M;
            const isCut = this.state.hullMode === "cutaway";
            const yCm = 0.72;
            const yEsm = -0.92;
            const anyWindowFire = COMPARTMENT_ORDER.some((c) => this._isRoomFireActive(c));

            // Realistic aerospace material palette (zero neon colors)
            const TITANIUM_DARK = [0.22, 0.25, 0.30];
            const ALUMINUM_BRUSHED = [0.82, 0.85, 0.90];
            const THERMAL_WHITE = [0.92, 0.94, 0.97];
            const RCS_GRAPHITE = [0.18, 0.20, 0.24];

            // 1. Sealed NASA Docking System (NDS) Tunnel & Closed Metallic Pressure Hatch Cap (fixes open top pit)
            const yDock = yCm + 0.86;
            this._draw(isCut ? M.cylCut : M.cyl, this._trs(0, yDock, 0, 0, 0, 0, 0.54, 0.34, 0.54), {
                tint: THERMAL_WHITE,
                met: 0.24,
                rg: 0.36,
            });
            // Upper titanium NDS docking ring collar
            this._draw(M.cyl, this._trs(0, yDock + 0.21, 0, 0, 0, 0, 0.52, 0.10, 0.52), {
                tint: ALUMINUM_BRUSHED,
                met: 0.78,
                rg: 0.20,
            });
            // Sealed Metallic NDS Pressure Hatch Lid + Center Equalization Hub (completely closes top opening)
            this._draw(M.disc, this._trs(0, yDock + 0.245, 0, 0, 0, 0, 0.50, 0.045, 0.50), {
                tint: [0.68, 0.72, 0.78],
                met: 0.76,
                rg: 0.22,
            });
            this._draw(M.disc, this._trs(0, yDock + 0.275, 0, 0, 0, 0, 0.22, 0.035, 0.22), {
                tint: TITANIUM_DARK,
                met: 0.82,
                rg: 0.24,
            });
            // 12 Realistic NDS Capture Guide Petals & Striker Latches
            for (let i = 0; i < 12; i++) {
                const a = (i / 12) * Math.PI * 2;
                this._draw(M.box, this._trs(Math.cos(a) * 0.49, yDock + 0.275, Math.sin(a) * 0.49, 0, -a, 0, 0.075, 0.045, 0.045), {
                    tint: i % 3 === 0 ? [0.84, 0.68, 0.26] : TITANIUM_DARK,
                    met: 0.72,
                    rg: 0.24,
                });
            }
            // Optical Navigation / Star Tracker Sensor Box on Forward Bay
            this._draw(M.box, this._trs(0.42, yDock + 0.05, 0.40, 0, 0.78, 0, 0.12, 0.11, 0.12), {
                tint: TITANIUM_DARK,
                met: 0.75,
                rg: 0.20,
            });

            // 2. Orion Crew Module Conical Backshell (Metallic Silver AETB-8 Tiles + White Forward Bay Collar)
            this._draw(isCut ? M.orionCmCut : M.orionCm, this._trs(0, yCm, 0, 0, 2.15, 0, 1, 1, 1), {
                tex: this.texOrionArtemisSilverHD,
                mt: 0,
                met: 0.52,
                rg: 0.24,
            });

            // Cockpit Windows (only draw windows not inside cutaway opening)
            [-0.48, -0.16, 0.16, 0.48].forEach((wa) => {
                if (isCut && Math.abs(wa) < 0.6) return;
                const rW = 1.01;
                const wy = yCm + 0.18;
                this._draw(M.box, this._trs(Math.sin(wa) * rW, wy, Math.cos(wa) * rW, -0.56, wa, 0, 0.22, 0.16, 0.07), {
                    tint: THERMAL_WHITE,
                    met: 0.22,
                    rg: 0.30,
                });
                this._draw(M.box, this._trs(Math.sin(wa) * (rW + 0.018), wy, Math.cos(wa) * (rW + 0.018), -0.56, wa, 0, 0.17, 0.11, 0.05), {
                    tint: anyWindowFire ? [1.0, 0.38, 0.06] : [0.16, 0.24, 0.34],
                    met: 0.88,
                    rg: 0.08,
                    em: anyWindowFire ? 1.8 : 0.08,
                });
            });

            // 3. AVCOAT Ablative Heatshield + Seamless Conical Crew Module Adapter (CMA) + Umbilical Fairing
            // (Eliminates the floating gap between CM y=0.14 and ESM top y=-0.20)
            this._draw(M.avcoat, this._trs(0, yCm - 0.58, 0, 0, 0, 0, 1, 1, 1), { mt: 5 });

            // Conical CMA Adapter Ring seamlessly joining CM Heatshield (y=+0.08) to ESM Forward Bulkhead (y=-0.22)
            this._draw(isCut ? M.cmaRingCut : M.cmaRing, this._trs(0, -0.05, 0, 0, 0, 0, 1, 1, 1), {
                tint: [0.86, 0.89, 0.93],
                met: 0.34,
                rg: 0.32,
            });
            // Recessed Gold Kapton MLI Thermal Collar Strip at CMA-ESM Interface
            this._draw(isCut ? M.cylCut : M.cyl, this._trs(0, -0.19, 0, 0, 0, 0, 1.185, 0.09, 1.185), {
                mt: 1,
                tint: [0.95, 0.92, 0.86],
            });
            // Starboard CM-to-ESM Umbilical Fairing Tunnel (bridges CM side directly into ESM upper ring without gap)
            this._draw(M.box, this._trs(1.28, 0.04, 0.0, 0, 0, 0.42, 0.18, 0.68, 0.28), {
                tint: THERMAL_WHITE,
                met: 0.30,
                rg: 0.30,
            });

            // 4. Airbus European Service Module (ESM) Core, Sealed Top/Aft Bulkheads, White/Silver Radiators & Quad RCS
            // Seal Top Bulkhead of ESM
            this._draw(M.disc, this._trs(0, yEsm + 0.71, 0, 0, 0, 0, 1.17, 0.04, 1.17), {
                tint: [0.72, 0.76, 0.82],
                met: 0.65,
                rg: 0.28,
            });
            // ESM Structural Cylinder (Gold MLI under-layer visible in collar seams)
            this._draw(isCut ? M.cylCut : M.cyl, this._trs(0, yEsm, 0, 0, 0, 0, 1.17, 1.44, 1.17), {
                mt: 1,
                tint: [0.94, 0.90, 0.82],
            });

            // 8 Curved/Faceted White-Silver Airbus ESM Radiator Panels (skip front 2 panels in Cutaway mode)
            for (let p = 0; p < 8; p++) {
                const a = (p / 8) * Math.PI * 2;
                if (isCut && Math.cos(a) > 0.45) continue;
                const rP = 1.225;
                this._draw(M.box, this._trs(Math.sin(a) * rP, yEsm + 0.01, Math.cos(a) * rP, 0, a, 0, 0.74, 1.18, 0.038), {
                    tex: this.texEsmRadiatorHD,
                    mt: 0,
                    met: 0.22,
                    rg: 0.26,
                });
            }

            // 4 Quad Reaction Control System (RCS) Pods in Realistic White/Graphite Housing
            for (let r = 0; r < 4; r++) {
                const a = (r / 4) * Math.PI * 2 + Math.PI / 8;
                if (isCut && Math.cos(a) > 0.55) continue;
                const rp = 1.24;
                this._draw(M.box, this._trs(Math.sin(a) * rp, yEsm + 0.58, Math.cos(a) * rp, 0, a, 0, 0.24, 0.14, 0.18), {
                    tint: THERMAL_WHITE,
                    met: 0.28,
                    rg: 0.30,
                });
                this._draw(M.box, this._trs(Math.sin(a) * (rp + 0.03), yEsm + 0.58, Math.cos(a) * (rp + 0.03), 0, a, 0, 0.14, 0.07, 0.12), {
                    tint: RCS_GRAPHITE,
                    met: 0.72,
                    rg: 0.24,
                });
            }

            // 5. Sealed Aft Engine Heatshield Bulkhead Plate (Fixes open hollow bottom cylinder!)
            const yAftPlate = yEsm - 0.72;
            this._draw(M.disc, this._trs(0, yAftPlate, 0, 0, 0, 0, 1.175, 0.06, 1.175), {
                tint: [0.58, 0.62, 0.68],
                met: 0.74,
                rg: 0.26,
            });
            // Aft gimbal thermal boot ring around main engine mount
            this._draw(M.disc, this._trs(0, yAftPlate - 0.04, 0, 0, 0, 0, 0.42, 0.06, 0.42), {
                mt: 1,
                tint: [0.88, 0.84, 0.76],
            });

            // AJ10-190 OMS-E Main Engine Bell Nozzle (Dark C/SiC metallic, mounted flush to closed aft bulkhead, ZERO fake plume!)
            this._draw(M.bell, this._trs(0, yAftPlate - 0.42, 0, 0, 0, 0, 1, 1, 1), { mt: 4 });

            // 8 Aerojet R-4D-11 Auxiliary Thrusters mounted cleanly on the closed Aft Bulkhead Ring
            for (let v = 0; v < 8; v++) {
                const a = (v / 8) * Math.PI * 2;
                this._draw(
                    M.vernier,
                    this._trs(Math.cos(a) * 0.88, yAftPlate - 0.13, Math.sin(a) * 0.88, 0.10 * Math.sin(a), 0, -0.10 * Math.cos(a), 1, 1, 1),
                    { tint: TITANIUM_DARK, met: 0.78, rg: 0.24 }
                );
            }

            // 6. 4 Airbus X-Wing Dark Photovoltaic Solar Arrays (Gimbaled carbon-fiber yokes + 3 hinged panels per wing)
            for (let w = 0; w < 4; w++) {
                const a = (w / 4) * Math.PI * 2 + Math.PI / 4;
                const cA = Math.cos(a);
                const sA = Math.sin(a);
                // Carbon-titanium deployment yoke arm
                this._draw(M.box, this._trs(cA * 1.54, yEsm + 0.08, sA * 1.54, 0, -a, 0, 0.58, 0.075, 0.095), {
                    tint: TITANIUM_DARK,
                    met: 0.68,
                    rg: 0.28,
                });
                [2.32, 3.32, 4.32].forEach((d, si) => {
                    this._draw(
                        M.box,
                        this._trs(cA * d, yEsm + 0.08 + si * 0.03, sA * d, 0.30, -a, 0.03, 0.94, 0.026, 0.66),
                        { mt: 2, irid: 0.12 }
                    );
                });
            }

            // 7. Render Internal 5-Compartment Cutaway Decks when Cutaway is active
            if (isCut) {
                this._renderOrionCutawayInterior(t);
            }
        }

        /* ====================================================================
         * 2. TRUE 3D PERSPECTIVE CABIN CAMERA ENGINE (window.THREE)
         * ==================================================================== */
        _initInterior3DScene() {
            this.interior3D = null;
            const THREE = window.THREE;
            if (!THREE || !this.pipCanvas) return;

            try {
                const w = this.pipCanvas.width || 520;
                const h = this.pipCanvas.height || 292;
                const renderer = new THREE.WebGLRenderer({
                    antialias: true,
                    alpha: false,
                    preserveDrawingBuffer: true,
                });
                renderer.setSize(w, h, false);
                renderer.setClearColor(0x111a2b, 1);

                const scene = new THREE.Scene();
                scene.fog = new THREE.FogExp2(0x0f172a, 0.065);

                const camera = new THREE.PerspectiveCamera(56, w / h, 0.08, 20.0);
                camera.position.set(0.0, 0.34, 2.25);
                camera.lookAt(0.0, -0.04, -1.35);

                // Cabin Lights
                const ambLight = new THREE.AmbientLight(0xdbeafe, 0.68);
                scene.add(ambLight);
                const mainLight = new THREE.PointLight(0xf8fafc, 0.95, 9.0);
                mainLight.position.set(0.0, 0.95, 0.45);
                scene.add(mainLight);
                const backLight = new THREE.PointLight(0xbae6fd, 0.48, 7.0);
                backLight.position.set(0.0, 0.65, -1.65);
                scene.add(backLight);
                const emergLight = new THREE.PointLight(0xef4444, 0.0, 7.5);
                emergLight.position.set(0.0, 0.88, 0.15);
                scene.add(emergLight);
                const fireLight = new THREE.PointLight(0xff7b1a, 0.0, 7.0);
                scene.add(fireLight);

                // Shared Spacecraft Octagonal/Curved Cabin Shell
                const matWall = new THREE.MeshStandardMaterial({ color: 0xcbd5e1, roughness: 0.58, metalness: 0.22 });
                const matRib = new THREE.MeshStandardMaterial({ color: 0x334155, roughness: 0.42, metalness: 0.62 });
                const matFloor = new THREE.MeshStandardMaterial({ color: 0x1e293b, roughness: 0.65, metalness: 0.38 });
                const matDark = new THREE.MeshStandardMaterial({ color: 0x0f172a, roughness: 0.5, metalness: 0.4 });
                const matBlueRail = new THREE.MeshStandardMaterial({ color: 0x0284c7, roughness: 0.28, metalness: 0.72 });
                const matLedStrip = new THREE.MeshBasicMaterial({ color: 0xe0f2fe });

                const shellGroup = new THREE.Group();
                scene.add(shellGroup);

                // Floor, Ceiling, Side Walls, Angled Chamfers, and Rear Bulkhead
                const floor = new THREE.Mesh(new THREE.BoxGeometry(3.1, 0.08, 4.6), matFloor);
                floor.position.set(0, -0.98, -0.1);
                shellGroup.add(floor);

                // Anti-skid floor grid strips
                for (let gz = -1.8; gz <= 1.4; gz += 0.55) {
                    const fRib = new THREE.Mesh(new THREE.BoxGeometry(2.6, 0.015, 0.04), matRib);
                    fRib.position.set(0, -0.935, gz);
                    shellGroup.add(fRib);
                }

                const ceiling = new THREE.Mesh(new THREE.BoxGeometry(3.1, 0.08, 4.6), matWall);
                ceiling.position.set(0, 1.12, -0.1);
                shellGroup.add(ceiling);

                const leftWall = new THREE.Mesh(new THREE.BoxGeometry(0.08, 2.15, 4.6), matWall);
                leftWall.position.set(-1.46, 0.08, -0.1);
                shellGroup.add(leftWall);

                const rightWall = new THREE.Mesh(new THREE.BoxGeometry(0.08, 2.15, 4.6), matWall);
                rightWall.position.set(1.46, 0.08, -0.1);
                shellGroup.add(rightWall);

                // Angled upper hull chamfers (authentic spacecraft pressure hull octagon feel)
                [-1, 1].forEach((side) => {
                    const cham = new THREE.Mesh(new THREE.BoxGeometry(0.62, 0.06, 4.6), matWall);
                    cham.position.set(side * 1.18, 0.88, -0.1);
                    cham.rotation.z = -side * 0.68;
                    shellGroup.add(cham);

                    const led = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.025, 3.8), matLedStrip);
                    led.position.set(side * 0.82, 1.06, -0.15);
                    shellGroup.add(led);
                });

                // Structural aluminum frames along Z
                [-1.95, -0.95, 0.05, 1.05].forEach((rz) => {
                    const topBeam = new THREE.Mesh(new THREE.BoxGeometry(2.85, 0.07, 0.08), matRib);
                    topBeam.position.set(0, 1.06, rz);
                    shellGroup.add(topBeam);
                    [-1.40, 1.40].forEach((rx) => {
                        const post = new THREE.Mesh(new THREE.BoxGeometry(0.08, 2.04, 0.08), matRib);
                        post.position.set(rx, 0.06, rz);
                        shellGroup.add(post);
                    });
                });

                // Rear Bulkhead Wall with Central Hatch Frame & Corridor Depth
                const rearLeft = new THREE.Mesh(new THREE.BoxGeometry(0.98, 2.15, 0.12), matWall);
                rearLeft.position.set(-0.98, 0.08, -2.15);
                shellGroup.add(rearLeft);
                const rearRight = new THREE.Mesh(new THREE.BoxGeometry(0.98, 2.15, 0.12), matWall);
                rearRight.position.set(0.98, 0.08, -2.15);
                shellGroup.add(rearRight);
                const rearTop = new THREE.Mesh(new THREE.BoxGeometry(1.04, 0.68, 0.12), matWall);
                rearTop.position.set(0.0, 0.82, -2.15);
                shellGroup.add(rearTop);

                const corridorBack = new THREE.Mesh(new THREE.BoxGeometry(1.12, 1.55, 0.08), matDark);
                corridorBack.position.set(0.0, -0.22, -2.55);
                shellGroup.add(corridorBack);

                // Hatch Frame & Animated Dual Sliding Pressure Doors
                const hatchFrameMat = new THREE.MeshStandardMaterial({ color: 0x475569, roughness: 0.35, metalness: 0.72 });
                const hatchDoorMat = new THREE.MeshStandardMaterial({ color: 0x64748b, roughness: 0.32, metalness: 0.76 });
                const matLatch = new THREE.MeshStandardMaterial({ color: 0xf59e0b, roughness: 0.3, metalness: 0.65 });
                const hatchStatusMat = new THREE.MeshBasicMaterial({ color: 0x10b981 });

                const hFrameTop = new THREE.Mesh(new THREE.BoxGeometry(1.08, 0.08, 0.16), hatchFrameMat);
                hFrameTop.position.set(0, 0.50, -2.12);
                shellGroup.add(hFrameTop);
                [-0.51, 0.51].forEach((hx) => {
                    const hfSide = new THREE.Mesh(new THREE.BoxGeometry(0.07, 1.46, 0.16), hatchFrameMat);
                    hfSide.position.set(hx, -0.22, -2.12);
                    shellGroup.add(hfSide);
                });

                const hatchStatusLed = new THREE.Mesh(new THREE.BoxGeometry(0.36, 0.05, 0.04), hatchStatusMat);
                hatchStatusLed.position.set(0, 0.58, -2.06);
                shellGroup.add(hatchStatusLed);

                const hatchLeft = new THREE.Mesh(new THREE.BoxGeometry(0.49, 1.40, 0.07), hatchDoorMat);
                hatchLeft.position.set(-0.68, -0.22, -2.16);
                shellGroup.add(hatchLeft);

                const hatchRight = new THREE.Mesh(new THREE.BoxGeometry(0.49, 1.40, 0.07), hatchDoorMat);
                hatchRight.position.set(0.68, -0.22, -2.16);
                shellGroup.add(hatchRight);

                const latchGroup = new THREE.Group();
                [-0.08, -0.36].forEach((ly) => {
                    const lb = new THREE.Mesh(new THREE.BoxGeometry(0.22, 0.05, 0.09), matLatch);
                    lb.position.set(0, ly, -2.13);
                    latchGroup.add(lb);
                });
                latchGroup.visible = false;
                shellGroup.add(latchGroup);

                // 3D Ceiling/Bulkhead Air Inlet & Outlet Louvers
                const ventSlats = [];
                const ventFrameMat = new THREE.MeshStandardMaterial({ color: 0x334155, roughness: 0.4, metalness: 0.65 });
                const ventSlatMat = new THREE.MeshStandardMaterial({ color: 0x7dd3fc, roughness: 0.32, metalness: 0.55 });
                [-0.96, 0.96].forEach((vx) => {
                    const vBox = new THREE.Mesh(new THREE.BoxGeometry(0.50, 0.28, 0.08), ventFrameMat);
                    vBox.position.set(vx, 0.80, -2.08);
                    shellGroup.add(vBox);
                    for (let s = 0; s < 4; s++) {
                        const slat = new THREE.Mesh(new THREE.BoxGeometry(0.44, 0.045, 0.04), ventSlatMat);
                        slat.position.set(vx, 0.89 - s * 0.06, -2.05);
                        shellGroup.add(slat);
                        ventSlats.push(slat);
                    }
                });

                // 5 Authentic 3D Room Equipment Groups
                const roomGroups = {};
                const poweredEmissives = [];

                // --- ROOM 1: ORION_CM (Command Deck / Cockpit) ---
                const grpCm = new THREE.Group();
                const matSeatPad = new THREE.MeshStandardMaterial({ color: 0xc2410c, roughness: 0.62, metalness: 0.12 });
                const matSeatFrame = new THREE.MeshStandardMaterial({ color: 0x94a3b8, roughness: 0.35, metalness: 0.78 });
                const matMfdScreen = new THREE.MeshStandardMaterial({
                    color: 0x0284c7,
                    emissive: 0x0ea5e9,
                    emissiveIntensity: 0.75,
                    roughness: 0.18,
                    metalness: 0.25,
                });
                poweredEmissives.push({ mat: matMfdScreen, baseHex: 0x0ea5e9, baseInt: 0.75 });

                // Two 3D inclined Orion crew seats
                [-0.68, 0.68].forEach((sx, si) => {
                    const seat = new THREE.Group();
                    seat.position.set(sx, -0.46, -0.35);
                    seat.rotation.y = si === 0 ? 0.24 : -0.24;
                    const backRest = new THREE.Mesh(new THREE.BoxGeometry(0.46, 0.68, 0.09), matSeatPad);
                    backRest.position.set(0, 0.24, -0.14);
                    backRest.rotation.x = -0.28;
                    seat.add(backRest);
                    const headRest = new THREE.Mesh(new THREE.BoxGeometry(0.28, 0.18, 0.09), matSeatFrame);
                    headRest.position.set(0, 0.62, -0.24);
                    headRest.rotation.x = -0.28;
                    seat.add(headRest);
                    const pan = new THREE.Mesh(new THREE.BoxGeometry(0.46, 0.09, 0.44), matSeatPad);
                    pan.position.set(0, -0.06, 0.08);
                    seat.add(pan);
                    const legStrut = new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.07, 0.44, 12), matSeatFrame);
                    legStrut.position.set(0, -0.30, 0.02);
                    seat.add(legStrut);
                    // Rotational hand controller armrest
                    const arm = new THREE.Mesh(new THREE.BoxGeometry(0.08, 0.06, 0.34), matSeatFrame);
                    arm.position.set(si === 0 ? 0.26 : -0.26, 0.10, 0.10);
                    seat.add(arm);
                    const stick = new THREE.Mesh(new THREE.CylinderGeometry(0.022, 0.03, 0.14, 10), matDark);
                    stick.position.set(si === 0 ? 0.26 : -0.26, 0.18, 0.22);
                    seat.add(stick);
                    grpCm.add(seat);
                });

                // Hanging 3-Unit Glass Cockpit MFD Flight Console (Honeywell DU-1310 style)
                const mfdConsole = new THREE.Group();
                mfdConsole.position.set(-0.56, 0.12, -0.82);
                mfdConsole.rotation.y = 0.28;
                mfdConsole.rotation.x = 0.22;
                const mfdBezel = new THREE.Mesh(new THREE.BoxGeometry(0.98, 0.36, 0.08), matDark);
                mfdConsole.add(mfdBezel);
                [-0.31, 0.0, 0.31].forEach((mx) => {
                    const scr = new THREE.Mesh(new THREE.BoxGeometry(0.26, 0.24, 0.02), matMfdScreen);
                    scr.position.set(mx, 0.02, 0.045);
                    mfdConsole.add(scr);
                });
                const strutL = new THREE.Mesh(new THREE.CylinderGeometry(0.025, 0.025, 0.92, 10), matSeatFrame);
                strutL.position.set(-0.34, 0.56, -0.05);
                mfdConsole.add(strutL);
                const strutR = new THREE.Mesh(new THREE.CylinderGeometry(0.025, 0.025, 0.92, 10), matSeatFrame);
                strutR.position.set(0.34, 0.56, -0.05);
                mfdConsole.add(strutR);
                grpCm.add(mfdConsole);

                // Side viewport window & blue handrail
                const winFrame = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.36, 0.48), matSeatFrame);
                winFrame.position.set(1.40, 0.36, -0.65);
                grpCm.add(winFrame);
                const winGlass = new THREE.Mesh(
                    new THREE.BoxGeometry(0.03, 0.26, 0.38),
                    new THREE.MeshStandardMaterial({ color: 0x082f49, emissive: 0x0369a1, emissiveIntensity: 0.35, roughness: 0.1 })
                );
                winGlass.position.set(1.38, 0.36, -0.65);
                grpCm.add(winGlass);
                const railCm = new THREE.Mesh(new THREE.CylinderGeometry(0.022, 0.022, 0.85, 10), matBlueRail);
                railCm.position.set(1.32, 0.05, -0.25);
                grpCm.add(railCm);
                roomGroups.ORION_CM = grpCm;
                scene.add(grpCm);

                // --- ROOM 2: IHAB (Crew Living Bay) ---
                const grpIhab = new THREE.Group();
                const matCtbBag = new THREE.MeshStandardMaterial({ color: 0xf1f5f9, roughness: 0.72, metalness: 0.06 });
                const matRackBody = new THREE.MeshStandardMaterial({ color: 0x334155, roughness: 0.42, metalness: 0.58 });
                const matSofieGlass = new THREE.MeshStandardMaterial({
                    color: 0x0c4a6e,
                    emissive: 0x0284c7,
                    emissiveIntensity: 0.45,
                    roughness: 0.15,
                    metalness: 0.3,
                });
                poweredEmissives.push({ mat: matSofieGlass, baseHex: 0x0284c7, baseInt: 0.45 });

                // Left: Modular Crew Sleep Bunks & White Nomex CTB Stowage Bags
                const bunkRack = new THREE.Mesh(new THREE.BoxGeometry(0.55, 1.58, 1.35), matRackBody);
                bunkRack.position.set(-1.12, -0.14, -0.65);
                grpIhab.add(bunkRack);
                for (let r = 0; r < 2; r++) {
                    for (let c = 0; c < 2; c++) {
                        const bag = new THREE.Mesh(new THREE.BoxGeometry(0.18, 0.44, 0.52), matCtbBag);
                        bag.position.set(-0.82, -0.45 + r * 0.62, -0.95 + c * 0.62);
                        grpIhab.add(bag);
                        const strap = new THREE.Mesh(new THREE.BoxGeometry(0.19, 0.05, 0.53), matBlueRail);
                        strap.position.set(-0.82, -0.45 + r * 0.62, -0.95 + c * 0.62);
                        grpIhab.add(strap);
                    }
                }

                // Right: Galley Warmer + SoFIE Combustion Science Rack + Zero-G Ergometer Frame
                const sofieRack = new THREE.Mesh(new THREE.BoxGeometry(0.56, 1.54, 0.92), matSeatFrame);
                sofieRack.position.set(1.10, -0.16, -0.72);
                grpIhab.add(sofieRack);
                const sofieWin = new THREE.Mesh(new THREE.BoxGeometry(0.05, 0.42, 0.48), matSofieGlass);
                sofieWin.position.set(0.81, 0.14, -0.72);
                grpIhab.add(sofieWin);

                // Exercise Ergometer Frame in foreground right
                const ergoBase = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.09, 0.58, 12), matSeatFrame);
                ergoBase.position.set(0.72, -0.66, 0.25);
                grpIhab.add(ergoBase);
                const ergoWheel = new THREE.Mesh(
                    new THREE.TorusGeometry(0.18, 0.035, 10, 24),
                    new THREE.MeshStandardMaterial({ color: 0xf59e0b, roughness: 0.35, metalness: 0.65 })
                );
                ergoWheel.position.set(0.72, -0.42, 0.25);
                ergoWheel.rotation.y = Math.PI * 0.5;
                grpIhab.add(ergoWheel);

                [-0.78, 0.78].forEach((rx) => {
                    const hBar = new THREE.Mesh(new THREE.CylinderGeometry(0.022, 0.022, 1.25, 10), matBlueRail);
                    hBar.rotation.x = Math.PI * 0.5;
                    hBar.position.set(rx, 0.52, -0.55);
                    grpIhab.add(hBar);
                });
                roomGroups.IHAB = grpIhab;
                scene.add(grpIhab);

                // --- ROOM 3: HALO (Power & Avionics Bay) ---
                const grpHalo = new THREE.Group();
                const matServerRack = new THREE.MeshStandardMaterial({ color: 0x1e293b, roughness: 0.38, metalness: 0.68 });
                const matBattery = new THREE.MeshStandardMaterial({ color: 0x1d4ed8, roughness: 0.34, metalness: 0.52 });
                const matKapton = new THREE.MeshStandardMaterial({ color: 0xd97706, roughness: 0.28, metalness: 0.78 });
                const matAvLed = new THREE.MeshStandardMaterial({
                    color: 0x22c55e,
                    emissive: 0x22c55e,
                    emissiveIntensity: 0.9,
                });
                poweredEmissives.push({ mat: matAvLed, baseHex: 0x22c55e, baseInt: 0.9 });

                [-1.08, 1.08].forEach((rx, side) => {
                    const pduRack = new THREE.Mesh(new THREE.BoxGeometry(0.58, 1.68, 1.48), matServerRack);
                    pduRack.position.set(rx, -0.10, -0.62);
                    grpHalo.add(pduRack);

                    for (let b = 0; b < 4; b++) {
                        const blade = new THREE.Mesh(new THREE.BoxGeometry(0.05, 0.24, 1.24), matSeatFrame);
                        blade.position.set(rx + (side === 0 ? 0.30 : -0.30), -0.56 + b * 0.34, -0.62);
                        grpHalo.add(blade);
                        const ledBar = new THREE.Mesh(new THREE.BoxGeometry(0.02, 0.04, 0.85), matAvLed);
                        ledBar.position.set(rx + (side === 0 ? 0.33 : -0.33), -0.50 + b * 0.34, -0.62);
                        grpHalo.add(ledBar);
                    }
                    // Gold Kapton cable harness conduit
                    const cable = new THREE.Mesh(new THREE.CylinderGeometry(0.045, 0.045, 1.65, 12), matKapton);
                    cable.position.set(rx + (side === 0 ? 0.24 : -0.24), -0.08, 0.22);
                    grpHalo.add(cable);
                });
                // Li-ion Battery Bank on lower deck
                [-0.52, 0.52].forEach((bx) => {
                    const bat = new THREE.Mesh(new THREE.BoxGeometry(0.36, 0.26, 0.62), matBattery);
                    bat.position.set(bx, -0.80, -0.45);
                    grpHalo.add(bat);
                });
                roomGroups.HALO = grpHalo;
                scene.add(grpHalo);

                // --- ROOM 4: AIRLOCK (Docking & Transfer Tunnel) ---
                const grpAirlock = new THREE.Group();
                const matSuitWhite = new THREE.MeshStandardMaterial({ color: 0xf8fafc, roughness: 0.55, metalness: 0.1 });
                const matGoldVisor = new THREE.MeshStandardMaterial({ color: 0xfbbf24, roughness: 0.14, metalness: 0.92 });
                const matYellowRail = new THREE.MeshStandardMaterial({ color: 0xeab308, roughness: 0.3, metalness: 0.65 });

                // Circular tunnel structural rings
                [-1.55, -0.85, -0.15, 0.55].forEach((tz) => {
                    const ring = new THREE.Mesh(new THREE.TorusGeometry(1.16, 0.055, 12, 32), matSeatFrame);
                    ring.position.set(0, 0.04, tz);
                    grpAirlock.add(ring);
                });

                // Stowed 3D EVA Spacesuit (Hard Upper Torso + Gold-Visor Helmet) on right bulkhead mount
                const suitGroup = new THREE.Group();
                suitGroup.position.set(0.86, -0.12, -0.62);
                suitGroup.rotation.y = -0.42;
                const torso = new THREE.Mesh(new THREE.CylinderGeometry(0.22, 0.19, 0.56, 16), matSuitWhite);
                suitGroup.add(torso);
                const plssPack = new THREE.Mesh(new THREE.BoxGeometry(0.36, 0.50, 0.20), matSuitWhite);
                plssPack.position.set(0, 0.02, -0.20);
                suitGroup.add(plssPack);
                const helmet = new THREE.Mesh(new THREE.SphereGeometry(0.17, 20, 16), matSuitWhite);
                helmet.position.set(0, 0.42, 0.0);
                suitGroup.add(helmet);
                const visor = new THREE.Mesh(new THREE.SphereGeometry(0.155, 18, 14), matGoldVisor);
                visor.position.set(0, 0.42, 0.045);
                suitGroup.add(visor);
                grpAirlock.add(suitGroup);

                // Pressure equalization manifold on left wall + EVA translation handrails
                const eqPanel = new THREE.Mesh(new THREE.BoxGeometry(0.16, 0.62, 0.54), matRackBody);
                eqPanel.position.set(-1.05, 0.04, -0.68);
                grpAirlock.add(eqPanel);
                [-0.86, 0.86].forEach((rx) => {
                    const yRail = new THREE.Mesh(new THREE.CylinderGeometry(0.025, 0.025, 1.85, 10), matYellowRail);
                    yRail.rotation.x = Math.PI * 0.5;
                    yRail.position.set(rx, 0.42, -0.55);
                    grpAirlock.add(yRail);
                });
                roomGroups.AIRLOCK = grpAirlock;
                scene.add(grpAirlock);

                // --- ROOM 5: PPE (Air & Life Support Bay) ---
                const grpPpe = new THREE.Group();
                const matO2Tank = new THREE.MeshStandardMaterial({ color: 0x15803d, roughness: 0.34, metalness: 0.48 });
                const matN2Tank = new THREE.MeshStandardMaterial({ color: 0x0369a1, roughness: 0.34, metalness: 0.48 });
                const matValveRed = new THREE.MeshStandardMaterial({ color: 0xdc2626, roughness: 0.35, metalness: 0.55 });

                // Twin vertical brushed-steel CAMRAS CO2 Scrubber Cylinders (Left)
                [-0.95, -0.52].forEach((cx) => {
                    const scrubCyl = new THREE.Mesh(new THREE.CylinderGeometry(0.17, 0.17, 1.32, 20), matSeatFrame);
                    scrubCyl.position.set(cx, -0.22, -0.68);
                    grpPpe.add(scrubCyl);
                    const capTop = new THREE.Mesh(new THREE.SphereGeometry(0.17, 18, 12), matRackBody);
                    capTop.position.set(cx, 0.44, -0.68);
                    grpPpe.add(capTop);
                    const valve = new THREE.Mesh(new THREE.TorusGeometry(0.07, 0.018, 8, 16), matValveRed);
                    valve.position.set(cx, 0.12, -0.49);
                    grpPpe.add(valve);
                });

                // Composite Overwrapped O2 & N2 Pressure Vessels (Right)
                const o2Vessel = new THREE.Mesh(new THREE.SphereGeometry(0.30, 24, 18), matO2Tank);
                o2Vessel.position.set(0.88, 0.18, -0.68);
                grpPpe.add(o2Vessel);
                const n2Vessel = new THREE.Mesh(new THREE.SphereGeometry(0.30, 24, 18), matN2Tank);
                n2Vessel.position.set(0.88, -0.46, -0.68);
                grpPpe.add(n2Vessel);

                // Overhead insulated ECLSS Air Ducts
                const mainDuct = new THREE.Mesh(new THREE.CylinderGeometry(0.11, 0.11, 2.2, 16), matCtbBag);
                mainDuct.rotation.z = Math.PI * 0.5;
                mainDuct.position.set(0.0, 0.72, -0.85);
                grpPpe.add(mainDuct);
                roomGroups.PPE = grpPpe;
                scene.add(grpPpe);

                // --- 3D Fire, Cool-Flame & Smoke Group ---
                const fireGroup = new THREE.Group();
                const matCoreWhite = new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.95 });
                const matMidOrange = new THREE.MeshBasicMaterial({ color: 0xfb923c, transparent: true, opacity: 0.72 });
                const matOuterBlue = new THREE.MeshBasicMaterial({ color: 0x2563eb, transparent: true, opacity: 0.48 });
                const coreSph = new THREE.Mesh(new THREE.SphereGeometry(0.12, 20, 16), matCoreWhite);
                const midSph = new THREE.Mesh(new THREE.SphereGeometry(0.21, 22, 18), matMidOrange);
                const outerSph = new THREE.Mesh(new THREE.SphereGeometry(0.31, 24, 18), matOuterBlue);
                fireGroup.add(coreSph, midSph, outerSph);

                const smokePuffs = [];
                const matSmoke = new THREE.MeshLambertMaterial({ color: 0x64748b, transparent: true, opacity: 0.26 });
                for (let sp = 0; sp < 6; sp++) {
                    const puff = new THREE.Mesh(new THREE.SphereGeometry(0.18 + sp * 0.03, 12, 10), matSmoke);
                    fireGroup.add(puff);
                    smokePuffs.push(puff);
                }
                fireGroup.visible = false;
                scene.add(fireGroup);

                // --- 3D Ceiling SoFIE-MIST Nozzles & Spray Cones ---
                const mistGroup = new THREE.Group();
                const matMistCone = new THREE.MeshBasicMaterial({
                    color: 0xbae6fd,
                    transparent: true,
                    opacity: 0.30,
                    depthWrite: false,
                });
                [-0.62, 0.62].forEach((nx) => {
                    const noz = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.06, 0.10, 12), matSeatFrame);
                    noz.position.set(nx, 1.02, -0.45);
                    shellGroup.add(noz);
                    const cone = new THREE.Mesh(new THREE.ConeGeometry(0.68, 1.95, 20, 1, true), matMistCone);
                    cone.position.set(nx * 0.65, 0.05, -0.45);
                    mistGroup.add(cone);
                });

                const mistCount = 140;
                const mistPos = new Float32Array(mistCount * 3);
                for (let i = 0; i < mistCount; i++) {
                    mistPos[i * 3] = (Math.random() - 0.5) * 2.2;
                    mistPos[i * 3 + 1] = -0.9 + Math.random() * 1.9;
                    mistPos[i * 3 + 2] = -1.6 + Math.random() * 2.0;
                }
                const mistGeo = new THREE.BufferGeometry();
                mistGeo.setAttribute("position", new THREE.BufferAttribute(mistPos, 3));
                const matMistPts = new THREE.PointsMaterial({
                    color: 0xe0f2fe,
                    size: 0.035,
                    transparent: true,
                    opacity: 0.75,
                });
                const mistParticles = new THREE.Points(mistGeo, matMistPts);
                mistGroup.add(mistParticles);
                mistGroup.visible = false;
                scene.add(mistGroup);

                this.interior3D = {
                    THREE,
                    renderer,
                    scene,
                    camera,
                    ambLight,
                    mainLight,
                    backLight,
                    emergLight,
                    fireLight,
                    matLedStrip,
                    hatchLeft,
                    hatchRight,
                    latchGroup,
                    hatchStatusMat,
                    ventSlats,
                    ventSlatMat,
                    roomGroups,
                    poweredEmissives,
                    fireGroup,
                    coreSph,
                    midSph,
                    outerSph,
                    matCoreWhite,
                    matMidOrange,
                    matOuterBlue,
                    matSmoke,
                    smokePuffs,
                    mistGroup,
                    matMistCone,
                    matMistPts,
                    mistGeo,
                    projVec: new THREE.Vector3(),
                };
            } catch (err) {
                console.warn("Interior 3D camera fallback notice:", err);
                this.interior3D = null;
            }
        }

        _project3DToPip(x, y, z, w, h) {
            const i3 = this.interior3D;
            if (!i3) return { x: w * 0.5, y: h * 0.5 };
            i3.projVec.set(x, y, z).project(i3.camera);
            return {
                x: (i3.projVec.x * 0.5 + 0.5) * w,
                y: (-i3.projVec.y * 0.5 + 0.5) * h,
            };
        }

        _applyRadiometricThermalPass(ctx, w, h, splitMode, hotspotScreen, equipScreen, tAmbC, tHotspotC, powerCut, smokeIn) {
            const startX = splitMode ? Math.floor(w * 0.5) : 0;
            const spanW = w - startX;
            if (spanW <= 0) return;

            const img = ctx.getImageData(startX, 0, spanW, h);
            const d = img.data;
            const scaleMinC = 18.0;
            const scaleMaxC = Math.max(120.0, Math.min(1850.0, tHotspotC > 55 ? tHotspotC * 1.08 : 140.0));
            const invSpan = 1.0 / Math.max(20.0, scaleMaxC - scaleMinC);

            const hx = hotspotScreen.x;
            const hy = hotspotScreen.y;
            const ex = equipScreen.x;
            const ey = equipScreen.y;
            const hotDelta = Math.max(0.0, tHotspotC - tAmbC);
            const hotRadSq = Math.max(480.0, Math.min(8200.0, 900.0 + hotDelta * 4.6));
            const equipDelta = powerCut ? 1.5 : 19.5;
            const equipRadSq = 2400.0;

            for (let py = 0; py < h; py++) {
                const rowOff = py * spanW * 4;
                for (let px = 0; px < spanW; px++) {
                    const gx = startX + px;
                    const idx = rowOff + px * 4;
                    const lum = (0.299 * d[idx] + 0.587 * d[idx + 1] + 0.114 * d[idx + 2]) / 255.0;

                    // Base hull & 3D object geometric contour signature around cabin ambient temperature
                    let pixTempC = tAmbC + (lum - 0.35) * 14.0;

                    // Powered 3D avionics/console heat signature (disappears when power is cut!)
                    const dex = gx - ex;
                    const dey = py - ey;
                    const eqG = Math.exp(-(dex * dex + dey * dey) / equipRadSq);
                    pixTempC += equipDelta * eqG * (0.65 + 0.55 * lum);

                    // Smoke plume warm ceiling layer if adjacent smoke enters
                    if (smokeIn && py < h * 0.45) {
                        pixTempC += (1.0 - py / (h * 0.45)) * 28.0;
                    }

                    // Active 0G flame, cool flame (NTC), or post-fire hot 0G core radiometric hotspot
                    if (hotDelta > 2.0) {
                        const dhx = gx - hx;
                        const dhy = py - hy;
                        const distSq = dhx * dhx + dhy * dhy;
                        const coreG = Math.exp(-distSq / (hotRadSq * 0.24));
                        const haloG = Math.exp(-distSq / hotRadSq);
                        pixTempC += hotDelta * (0.68 * coreG + 0.36 * haloG);
                    }

                    const normT = Math.max(0.0, Math.min(1.0, (pixTempC - scaleMinC) * invSpan));
                    const lutIdx = Math.min(255, Math.max(0, Math.round(normT * 255))) * 3;
                    d[idx] = IRONBOW_LUT[lutIdx];
                    d[idx + 1] = IRONBOW_LUT[lutIdx + 1];
                    d[idx + 2] = IRONBOW_LUT[lutIdx + 2];
                }
            }
            ctx.putImageData(img, startX, 0);

            // Split-View divider line & labels
            const isEn = this.getLang() === "en";
            if (splitMode) {
                ctx.strokeStyle = "rgba(56, 189, 248, 0.88)";
                ctx.lineWidth = 2;
                ctx.beginPath();
                ctx.moveTo(startX, 0);
                ctx.lineTo(startX, h);
                ctx.stroke();

                ctx.fillStyle = "rgba(4, 9, 20, 0.76)";
                ctx.fillRect(startX - 58, 14, 52, 18);
                ctx.fillRect(startX + 6, 14, 62, 18);
                ctx.fillStyle = "#bae6fd";
                ctx.font = "bold 9.5px Segoe UI, sans-serif";
                ctx.fillText(isEn ? "OPTICAL" : "OPTİK", startX - 52, 26);
                ctx.fillStyle = "#fde047";
                ctx.fillText("LWIR IR", startX + 12, 26);
            }

            // Radiometric LWIR Colorbar on right margin
            const cbX = w - 20;
            const cbY = 40;
            const cbW = 8;
            const cbH = h - 84;
            ctx.fillStyle = "rgba(4, 9, 20, 0.78)";
            ctx.fillRect(cbX - 34, cbY - 14, 46, cbH + 28);
            for (let y = 0; y < cbH; y++) {
                const frac = 1.0 - y / Math.max(1, cbH - 1);
                const li = Math.round(frac * 255) * 3;
                ctx.fillStyle = `rgb(${IRONBOW_LUT[li]},${IRONBOW_LUT[li + 1]},${IRONBOW_LUT[li + 2]})`;
                ctx.fillRect(cbX, cbY + y, cbW, 1.5);
            }
            ctx.strokeStyle = "rgba(226,232,240,0.6)";
            ctx.lineWidth = 1;
            ctx.strokeRect(cbX, cbY, cbW, cbH);
            ctx.fillStyle = "#fef08a";
            ctx.font = "bold 9px Consolas, monospace";
            ctx.textAlign = "right";
            ctx.fillText(`${Math.round(scaleMaxC)}°C`, cbX - 3, cbY + 7);
            ctx.fillStyle = "#cbd5e1";
            ctx.fillText(`${Math.round(scaleMinC)}°C`, cbX - 3, cbY + cbH);
            ctx.textAlign = "left";

            // Dynamic T_max Hotspot Crosshair Reticle
            const targetPt = hotDelta > 5.0 ? hotspotScreen : equipScreen;
            const peakC = hotDelta > 5.0 ? Math.round(tHotspotC) : Math.round(tAmbC + equipDelta);
            const peakK = Math.round(peakC + 273.15);
            if (!splitMode || targetPt.x >= startX - 18) {
                const rx = Math.max(startX + 14, Math.min(w - 64, targetPt.x));
                const ry = Math.max(28, Math.min(h - 38, targetPt.y));
                ctx.strokeStyle = peakC >= 120 ? "#fde047" : "#38bdf8";
                ctx.lineWidth = 1.4;
                ctx.beginPath();
                ctx.arc(rx, ry, 9, 0, Math.PI * 2);
                ctx.moveTo(rx - 14, ry);
                ctx.lineTo(rx - 5, ry);
                ctx.moveTo(rx + 5, ry);
                ctx.lineTo(rx + 14, ry);
                ctx.moveTo(rx, ry - 14);
                ctx.lineTo(rx, ry - 5);
                ctx.moveTo(rx, ry + 5);
                ctx.lineTo(rx, ry + 14);
                ctx.stroke();

                const tagTxt = `T_max: ${peakC}°C (${peakK}K)`;
                const tagW = 122;
                const tagX = Math.min(w - tagW - 44, Math.max(startX + 6, rx + 12));
                const tagY = Math.max(18, ry - 16);
                ctx.fillStyle = "rgba(4, 9, 20, 0.84)";
                ctx.fillRect(tagX, tagY, tagW, 17);
                ctx.fillStyle = peakC >= 120 ? "#fde047" : "#bae6fd";
                ctx.font = "bold 9.5px Consolas, monospace";
                ctx.fillText(tagTxt, tagX + 4, tagY + 12);
            }
        }

        _drawLiveRoomCamera(t) {
            if (!this.pipCtx || !this.pipCanvas || !this.state.camVisible) return;
            const ctx = this.pipCtx;
            const w = this.pipCanvas.width;
            const h = this.pipCanvas.height;
            const isEn = this.getLang() === "en";
            const cid = this.getCompartmentId();
            const def = ROOM_DEFS[cid] || ROOM_DEFS.ORION_CM;
            const rm = this.rooms[cid];
            const camMode = this.state.cameraMode; // "optical" | "thermal" | "split"
            const irFull = camMode === "thermal";
            const irSplit = camMode === "split";
            const fireNow = this._isRoomFireActive(cid);
            const smokeIn = this._hasAdjacentSmokeIngress(cid);
            const pf = this._computeRoomPostFireStats(cid);
            const fireAmp = fireNow ? Math.max(0.35, this.state.fire) : this.state.fire;
            const usingWebcam = Boolean(this.state.webcamVideo && this.state.webcamVideo.readyState >= 2);

            if (usingWebcam) {
                if (!this.state.webcamProbeCanvas) {
                    const pc = document.createElement("canvas");
                    pc.width = 96;
                    pc.height = 54;
                    this.state.webcamProbeCanvas = pc;
                }
                const pc = this.state.webcamProbeCanvas;
                const pctx = pc.getContext("2d", { willReadFrequently: true });
                pctx.drawImage(this.state.webcamVideo, 0, 0, pc.width, pc.height);
                const img = pctx.getImageData(0, 0, pc.width, pc.height);
                const d = img.data;
                const nPix = pc.width * pc.height;
                if (!this.state.webcamPrevLuma || this.state.webcamPrevLuma.length !== nPix) {
                    this.state.webcamPrevLuma = new Float32Array(nPix);
                }
                let lumaSum = 0;
                let flickerSum = 0;
                let warmFlamePix = 0;
                let blueCorePix = 0;
                let maxLum = 0;
                let maxPx = 48;
                let maxPy = 27;
                for (let i = 0, p = 0; p < nPix; p++, i += 4) {
                    const r = d[i];
                    const g = d[i + 1];
                    const b = d[i + 2];
                    const lum = 0.299 * r + 0.587 * g + 0.114 * b;
                    lumaSum += lum;
                    if (lum > maxLum) {
                        maxLum = lum;
                        maxPx = p % pc.width;
                        maxPy = Math.floor(p / pc.width);
                    }
                    flickerSum += Math.abs(lum - this.state.webcamPrevLuma[p]);
                    this.state.webcamPrevLuma[p] = lum;
                    if (r > 195 && g > 95 && b < 155 && r > b * 1.45 && r >= g) {
                        warmFlamePix++;
                    } else if (b > 190 && g > 140 && r < 145 && b > r * 1.35) {
                        blueCorePix++;
                    }
                }
                const brightPct = Math.min(100, Math.round((lumaSum / (nPix * 255)) * 100));
                const flickPct = Math.min(100, Math.round((flickerSum / (nPix * 36)) * 100));
                const flameFrac = (warmFlamePix + blueCorePix * 0.8) / nPix;
                this.state.webcamMetrics = {
                    brightnessPct: brightPct,
                    flickerPct: flickPct,
                    flameCandidate: flameFrac > 0.012 && flickPct >= 4,
                };
                ctx.drawImage(this.state.webcamVideo, 0, 0, w, h);
                if (irFull || irSplit) {
                    const hs = { x: (maxPx / pc.width) * w, y: (maxPy / pc.height) * h };
                    const estC = this.state.webcamMetrics.flameCandidate ? 860 : 36;
                    this._applyRadiometricThermalPass(ctx, w, h, irSplit, hs, hs, 24, estC, false, false);
                }
            } else if (this.interior3D) {
                // Render Real 3D Perspective Cabin Interior Scene via Three.js
                const i3 = this.interior3D;
                COMPARTMENT_ORDER.forEach((k) => {
                    if (i3.roomGroups[k]) {
                        i3.roomGroups[k].visible = k === cid;
                    }
                });

                // Subtle authentic cabin security camera micro-sway
                i3.camera.position.set(Math.sin(t * 0.45) * 0.035, 0.34 + Math.cos(t * 0.35) * 0.015, 2.25);
                i3.camera.lookAt(0.0, -0.04, -1.35);
                i3.camera.updateMatrixWorld();

                // Update 3D Lighting & Powered Equipment State
                if (rm.powerCut) {
                    i3.ambLight.intensity = 0.18;
                    i3.mainLight.intensity = 0.08;
                    i3.backLight.intensity = 0.06;
                    i3.emergLight.intensity = 0.72 + 0.18 * Math.sin(t * 4.5);
                    i3.matLedStrip.color.setHex(0x7f1d1d);
                    i3.poweredEmissives.forEach((pe) => {
                        pe.mat.emissiveIntensity = 0.0;
                    });
                } else {
                    i3.ambLight.intensity = 0.68;
                    i3.mainLight.intensity = 0.96;
                    i3.backLight.intensity = 0.48;
                    i3.emergLight.intensity = fireAmp > 0.08 ? (0.45 + 0.35 * Math.sin(t * 8.0)) : 0.0;
                    i3.matLedStrip.color.setHex(fireAmp > 0.08 ? 0xfb923c : 0xe0f2fe);
                    i3.poweredEmissives.forEach((pe, idx) => {
                        const pulse = idx === 2 ? (Math.sin(t * 6.0) > -0.2 ? 1.0 : 0.35) : 1.0;
                        pe.mat.emissive.setHex(pe.baseHex);
                        pe.mat.emissiveIntensity = pe.baseInt * pulse;
                    });
                }

                // Update 3D Sliding Hatch Doors & Locking Bars
                const openOffset = 0.68 - 0.435 * rm.hatchAnim;
                i3.hatchLeft.position.x = -openOffset;
                i3.hatchRight.position.x = openOffset;
                i3.latchGroup.visible = rm.hatchAnim > 0.78;
                i3.hatchStatusMat.color.setHex(rm.entryClosed ? 0xef4444 : 0x10b981);

                // Update 3D Ceiling Air Vent Louvers
                const bladeRot = rm.ventAnim * 1.42;
                i3.ventSlats.forEach((slat) => {
                    slat.rotation.x = bladeRot;
                });
                i3.ventSlatMat.color.setHex(rm.airClosed ? 0xf59e0b : 0x7dd3fc);

                // Update 3D Spherical / Wake Fire & Smoke Cloud at Room's Authentic Equipment Fault Coordinates
                const fPos3 = def.fire3dRoomPos;
                if (fireAmp > 0.03) {
                    i3.fireGroup.visible = true;
                    i3.fireGroup.position.set(
                        fPos3[0] + Math.sin(t * 2.4) * 0.02,
                        fPos3[1] + Math.cos(t * 1.9) * 0.02,
                        fPos3[2]
                    );
                    const sc = (0.72 + 0.68 * fireAmp) * (1.0 + 0.06 * Math.sin(t * 14.0));
                    i3.coreSph.scale.setScalar(sc);
                    i3.midSph.scale.setScalar(sc * 1.08);
                    i3.outerSph.scale.setScalar(sc * 1.15);

                    if (this.state.coolFlame) {
                        // Cool flame NTC (550-750 K): barely visible in optical camera!
                        i3.matCoreWhite.opacity = 0.06;
                        i3.matMidOrange.opacity = 0.0;
                        i3.matOuterBlue.color.setHex(0x8b5cf6);
                        i3.matOuterBlue.opacity = 0.10;
                        i3.matSmoke.opacity = 0.05;
                        i3.fireLight.intensity = 0.08;
                    } else {
                        i3.matCoreWhite.opacity = 0.95;
                        i3.matMidOrange.opacity = 0.72;
                        i3.matOuterBlue.color.setHex(0x2563eb);
                        i3.matOuterBlue.opacity = 0.48;
                        i3.matSmoke.opacity = 0.28;
                        i3.fireLight.color.setHex(0xff7b1a);
                        i3.fireLight.position.set(fPos3[0], fPos3[1] + 0.15, fPos3[2] + 0.25);
                        i3.fireLight.intensity = 1.65 * fireAmp;
                    }
                    i3.smokePuffs.forEach((pfMesh, si) => {
                        const ang = t * 0.65 + si * 1.04;
                        pfMesh.position.set(
                            Math.cos(ang) * (0.22 + si * 0.04),
                            0.18 + Math.sin(ang * 1.3) * 0.12 + (this.state.gravityG > 0.05 ? si * 0.06 : 0.0),
                            Math.sin(ang) * 0.16
                        );
                    });
                } else {
                    i3.fireGroup.visible = false;
                    i3.fireLight.intensity = 0.0;
                }

                // Update 3D Ceiling SoFIE-MIST Spray Cones & Droplets
                if (rm.mistAnim > 0.02) {
                    i3.mistGroup.visible = true;
                    i3.matMistCone.opacity = 0.28 * rm.mistAnim;
                    i3.matMistPts.opacity = 0.82 * rm.mistAnim;
                    const arr = i3.mistGeo.attributes.position.array;
                    for (let k = 0; k < arr.length; k += 3) {
                        arr[k + 1] -= 0.055;
                        if (arr[k + 1] < -0.92) arr[k + 1] = 0.98;
                    }
                    i3.mistGeo.attributes.position.needsUpdate = true;
                } else {
                    i3.mistGroup.visible = false;
                }

                // Fog density reacts to adjacent or local smoke
                i3.scene.fog.density = fireAmp > 0.1 && !this.state.coolFlame ? 0.11 : (smokeIn ? 0.13 : 0.055);

                i3.renderer.render(i3.scene, i3.camera);
                ctx.drawImage(i3.renderer.domElement, 0, 0, w, h);

                // Apply Radiometric LWIR Ironbow Pass in Thermal or Split Mode
                if (irFull || irSplit) {
                    const hs2d = this._project3DToPip(fPos3[0], fPos3[1], fPos3[2], w, h);
                    const eq3 = def.equipHeatPos;
                    const eq2d = this._project3DToPip(eq3[0], eq3[1], eq3[2], w, h);
                    const peakHotC = fireNow
                        ? Math.max(85.0, this.state.flameTempK - 273.15)
                        : Math.max(rm.tempC, pf.coreTempC);
                    this._applyRadiometricThermalPass(
                        ctx,
                        w,
                        h,
                        irSplit,
                        hs2d,
                        eq2d,
                        rm.tempC || 21.0,
                        peakHotC,
                        rm.powerCut,
                        smokeIn
                    );
                }
            }

            // Security Camera Lens Vignette, Reticle Corners & Telemetry Overlay
            const vig = ctx.createRadialGradient(w * 0.5, h * 0.5, w * 0.30, w * 0.5, h * 0.5, w * 0.65);
            vig.addColorStop(0, "rgba(0,0,0,0)");
            vig.addColorStop(1, "rgba(2,6,18,0.42)");
            ctx.fillStyle = vig;
            ctx.fillRect(0, 0, w, h);

            ctx.strokeStyle = "rgba(226, 232, 240, 0.45)";
            ctx.lineWidth = 1.5;
            const m = 10;
            const cl = 14;
            [
                [m, m + cl, m, m, m + cl, m],
                [w - m - cl, m, w - m, m, w - m, m + cl],
                [m, h - m - cl, m, h - m, m + cl, h - m],
                [w - m - cl, h - m, w - m, h - m, w - m, h - m - cl],
            ].forEach(([x0, y0, x1, y1, x2, y2]) => {
                ctx.beginPath();
                ctx.moveTo(x0, y0);
                ctx.lineTo(x1, y1);
                ctx.lineTo(x2, y2);
                ctx.stroke();
            });

            const now = new Date();
            const clockStr = now.toTimeString().slice(0, 8);
            ctx.fillStyle = "rgba(4, 9, 20, 0.74)";
            ctx.fillRect(14, 14, 152, 20);
            ctx.fillStyle = "#e2e8f0";
            ctx.font = "bold 10.5px Consolas, monospace";
            ctx.fillText(`CAM-${def.camCode}  ${clockStr}`, 20, 28);

            const stBadge = isEn
                ? `Hatch: ${rm.entryClosed ? "CLOSED" : "OPEN"} | Air: ${rm.airClosed ? "CLOSED" : "OPEN"}`
                : `Kapak: ${rm.entryClosed ? "KAPALI" : "AÇIK"} | Hava: ${rm.airClosed ? "KAPALI" : "AÇIK"}`;
            ctx.fillStyle = "rgba(4, 9, 20, 0.76)";
            ctx.fillRect(14, h - 32, 226, 19);
            ctx.fillStyle = rm.entryClosed && rm.airClosed ? "#fcd34d" : "#bae6fd";
            ctx.font = "bold 10px Segoe UI, sans-serif";
            ctx.fillText(stBadge, 20, h - 19);

            // Update bottom status bar
            const tEl = document.getElementById("sc-pip-temp");
            const dEl = document.getElementById("sc-pip-detect");
            if (usingWebcam) {
                const wm = this.state.webcamMetrics;
                if (tEl) {
                    tEl.textContent = isEn
                        ? `Light: ${wm.brightnessPct}% • Flicker: ${wm.flickerPct}%`
                        : `Işık: %${wm.brightnessPct} • Titreşim: %${wm.flickerPct}`;
                }
                if (dEl) {
                    if (wm.flameCandidate) {
                        dEl.textContent = isEn ? "Status: Optical Flame" : "Durum: Alev Titreşimi";
                        dEl.style.color = "#fb7185";
                    } else {
                        dEl.textContent = isEn ? "Status: Live Optical" : "Durum: Canlı Optik";
                        dEl.style.color = "#38bdf8";
                    }
                }
            } else {
                const shownC = Math.round(rm.tempC || (fireNow ? Math.max(45, this.state.flameTempK - 273.15) : 21));
                const shownCo = Math.round(rm.coLocal || (fireNow ? this.state.coPpm : 1));
                if (tEl) {
                    tEl.textContent = isEn
                        ? `Temp: ${shownC} °C • CO: ${shownCo} ppm`
                        : `Sıcaklık: ${shownC} °C • CO: ${shownCo} ppm`;
                }
                if (dEl) {
                    if (!fireNow && pf.coreTempK > 345.0) {
                        dEl.textContent = isEn
                            ? `0G Core: ${Math.round(pf.coreTempC)} °C (${pf.safeReentrySec} s)`
                            : `0G Çekirdek: ${Math.round(pf.coreTempC)} °C (${pf.safeReentrySec} sn)`;
                        dEl.style.color = "#fbbf24";
                    } else if (rm.mistAnim > 0.08 || (!fireNow && shownC > 26)) {
                        dEl.textContent = isEn ? "Status: Cooling" : "Durum: Soğutuluyor";
                        dEl.style.color = "#67e8f9";
                    } else if (fireNow) {
                        dEl.textContent = this.state.coolFlame
                            ? (isEn ? "Status: Cool Flame" : "Durum: Soğuk Alev")
                            : (isEn ? "Status: Fire Alert" : "Durum: Yangın Uyarısı");
                        dEl.style.color = "#fb7185";
                    } else if (smokeIn) {
                        dEl.textContent = isEn ? "Status: Smoke Leak" : "Durum: Duman Sızıntısı";
                        dEl.style.color = "#fbbf24";
                    } else if (rm.entryClosed && rm.airClosed) {
                        dEl.textContent = isEn ? "Status: Room Closed" : "Durum: Bölüm Kapalı";
                        dEl.style.color = "#fcd34d";
                    } else {
                        dEl.textContent = isEn ? "Status: Safe" : "Durum: Güvenli";
                        dEl.style.color = "#34d399";
                    }
                }
            }
        }

        /* ====================================================================
         * 3. MAIN ANIMATION LOOP & UI CONTROLS
         * ==================================================================== */
        _startLoop() {
            if (!this._seqInterval) {
                this._seqInterval = setInterval(() => {
                    this._advanceSequenceByWallClock();
                }, 80);
            }
            const step = (now) => {
                const dt = Math.min(0.05, (now - this.lastT) / 1000);
                this.lastT = now;
                if (this.state.active && this.gl) {
                    this._renderFrame(now * 0.001, dt);
                }
                requestAnimationFrame(step);
            };
            requestAnimationFrame(step);
        }

        _renderFrame(t, dt) {
            const gl = this.gl;
            const U = this.U;
            const cam = this.cam;

            this._advanceSequenceByWallClock();

            if (cam.lerp) {
                cam.yaw += (cam.tYaw - cam.yaw) * 0.10;
                cam.pitch += (cam.tPitch - cam.pitch) * 0.10;
                cam.dist += (cam.tDist - cam.dist) * 0.10;
                cam.px += (cam.tPx - cam.px) * 0.10;
                cam.py += (cam.tPy - cam.py) * 0.10;
                if (
                    Math.hypot(cam.tYaw - cam.yaw, cam.tPitch - cam.pitch, cam.tDist - cam.dist) < 0.004 &&
                    Math.hypot(cam.tPx - cam.px, cam.tPy - cam.py) < 0.004
                ) {
                    cam.lerp = false;
                }
            } else if (this.state.autoOrbit && !cam.drag) {
                cam.yaw += dt * 0.12;
            }

            const gVal = this.state.gravityG || 0.0;
            COMPARTMENT_ORDER.forEach((cid) => {
                const rm = this.rooms[cid];
                rm.hatchAnim += ((rm.entryClosed ? 1 : 0) - rm.hatchAnim) * 0.14;
                rm.ventAnim += ((rm.airClosed ? 1 : 0) - rm.ventAnim) * 0.14;
                if (rm.mistAnim > 0) {
                    rm.mistAnim = Math.max(0, rm.mistAnim - dt * 0.22);
                }
                const burning = this._isRoomFireActive(cid);
                const smokeIn = this._hasAdjacentSmokeIngress(cid);
                const targetC = burning
                    ? Math.max(48, this.state.flameTempK - 273.15)
                    : (smokeIn ? 26.0 : 21.0);
                const rateC = burning ? 2.4 : (rm.mistAnim > 0.05 ? 1.75 : 0.55);
                rm.tempC += (targetC - rm.tempC) * Math.min(1.0, dt * rateC);

                // Physical 0G Core Thermal Inertia & Cooling Dynamics
                if (burning) {
                    const targetCoreK = Math.max(630.0, Math.min(960.0, this.state.flameTempK * 0.48));
                    rm.coreTempK += (targetCoreK - rm.coreTempK) * Math.min(1.0, dt * 1.35);
                } else {
                    const mistActive = rm.mistLatched || rm.mistAnim > 0.05;
                    const tauCool = mistActive ? 18.0 : (gVal < 0.05 ? 92.0 : (gVal < 0.4 ? 54.0 : 34.0));
                    rm.coreTempK += (294.15 - rm.coreTempK) * Math.min(1.0, dt / tauCool);
                }

                const targetCo = burning
                    ? Math.max(8, this.state.coPpm)
                    : (rm.airScrub ? 0.0 : (smokeIn ? 24.0 : 1.0));
                const rateCo = burning ? 2.2 : (rm.airScrub ? 1.8 : 0.45);
                rm.coLocal += (targetCo - rm.coLocal) * Math.min(1.0, dt * rateCo);
            });

            if (t - this.state.lastTabSyncT > 0.25) {
                this.state.lastTabSyncT = t;
                this._refreshRoomTabBadges();
                this._syncOrionSectionButtons();
                this._renderLivePhysicsTelemetry();
            }

            const anyFireCid = COMPARTMENT_ORDER.find((c) => this._isRoomFireActive(c)) || null;
            const activeCid = this.getCompartmentId();
            const targetFire = this._isRoomFireActive(activeCid)
                ? Math.min(1.0, Math.max(0.38, this.state.simRiskScore / 85.0))
                : 0.0;
            this.state.fire += (targetFire - this.state.fire) * 0.10;

            this.resize();
            gl.useProgram(this.prog);
            gl.viewport(0, 0, this.canvas.width, this.canvas.height);
            gl.clearColor(0.008, 0.016, 0.038, 1.0);
            gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
            gl.enable(gl.DEPTH_TEST);
            gl.disable(gl.CULL_FACE);

            const ex = cam.px + cam.dist * Math.cos(cam.pitch) * Math.sin(cam.yaw);
            const ey = cam.py + cam.dist * Math.sin(cam.pitch);
            const ez = cam.dist * Math.cos(cam.pitch) * Math.cos(cam.yaw);

            const f = 1 / Math.tan((38 * Math.PI) / 360);
            const asp = this.canvas.width / Math.max(1, this.canvas.height);
            const nf = 1 / (0.1 - 160);
            gl.uniformMatrix4fv(
                U.uProj,
                false,
                new Float32Array([f / asp, 0, 0, 0, 0, f, 0, 0, 0, 0, 160.1 * nf, -1, 0, 0, 32 * nf, 0])
            );

            let zx = ex - cam.px;
            let zy = ey - cam.py;
            let zz = ez;
            const zl = Math.hypot(zx, zy, zz) || 1;
            zx /= zl;
            zy /= zl;
            zz /= zl;
            let xx = zz;
            const xy = 0;
            let xz = -zx;
            const xl = Math.hypot(xx, xy, xz) || 1;
            xx /= xl;
            xz /= xl;
            const yx = zy * xz;
            const yy = zz * xx - zx * xz;
            const yz = -zy * xx;
            gl.uniformMatrix4fv(
                U.uView,
                false,
                new Float32Array([
                    xx, yx, zx, 0,
                    0, yy, zy, 0,
                    xz, yz, zz, 0,
                    -(xx * ex + xz * ez), -(yx * ex + yy * ey + yz * ez), -(zx * ex + zy * ey + zz * ez), 1,
                ])
            );

            const glowCid = anyFireCid || activeCid;
            const glowAmp = anyFireCid ? Math.min(1.0, Math.max(0.42, this.state.simRiskScore / 85.0)) : 0.0;
            const fPos = (ROOM_DEFS[glowCid] || ROOM_DEFS.ORION_CM).firePos3d;
            gl.uniform3fv(U.uCam, [ex, ey, ez]);
            gl.uniform1f(U.uSatGain, 1.06); // Natural realistic NASA aerospace PBR grading
            gl.uniform3fv(U.uFirePos, fPos);
            gl.uniform1f(U.uFirePow, glowAmp * 1.25);

            if (this.state.showSpace) {
                gl.depthMask(false);
                this._draw(this.M.sph, this._trs(ex, ey, ez, 0, 0, 0, 74, 74, 74), { mt: 6 });
                gl.depthMask(true);
                this._draw(this.M.sph, this._trs(-15.5, -6.2, -26.0, 0.25, t * 0.03, -0.15, 6.8, 6.8, 6.8), {
                    tex: this.texEarthHD,
                    mt: 0,
                    met: 0.08,
                    rg: 0.34,
                    em: 0.10,
                });
                gl.enable(gl.BLEND);
                gl.blendFunc(gl.SRC_ALPHA, gl.ONE);
                this._draw(this.M.sph, this._trs(-15.5, -6.2, -26.0, 0, 0, 0, 7.15, 7.15, 7.15), {
                    tint: [0.08, 0.48, 0.92],
                    em: 1.1,
                    al: 0.22,
                });
                gl.disable(gl.BLEND);
            }

            this._renderOrionMcp(t);
            this._drawLiveRoomCamera(t);
        }

        _refreshRoomTabBadges() {
            const isEn = this.getLang() === "en";
            document.querySelectorAll(".sc-room-tab").forEach((btn) => {
                const zIdx = Number(btn.dataset.zone);
                const zCid = COMPARTMENT_ORDER[zIdx] || "ORION_CM";
                const zDef = ROOM_DEFS[zCid];
                const zRm = this.rooms[zCid];
                const tC = Math.round(zRm ? zRm.tempC : 21);
                if (zDef) {
                    const baseLbl = isEn ? zDef.short_en : zDef.short_tr;
                    btn.textContent = `${baseLbl} • ${tC}°C`;
                }
                btn.classList.toggle("active", zIdx === this.state.zoneIdx);
                btn.classList.toggle("room-sealed", Boolean(zRm && zRm.entryClosed && zRm.airClosed));
                btn.classList.toggle("room-fire", this._isRoomFireActive(zCid));
            });
        }

        _updateCameraModeButtons() {
            const isEn = this.getLang() === "en";
            const m = this.state.cameraMode;
            const optBtn = document.getElementById("sc-btn-cam-optical");
            const irBtn = document.getElementById("sc-btn-ir-mode");
            const splBtn = document.getElementById("sc-btn-cam-split");
            const wcBtn = document.getElementById("sc-btn-webcam");

            if (optBtn) {
                optBtn.textContent = isEn ? "Optical" : "Optik";
                optBtn.classList.toggle("active", m === "optical" && !this.state.webcamStream);
            }
            if (irBtn) {
                irBtn.textContent = isEn ? "Thermal" : "Termal";
                irBtn.classList.toggle("active", m === "thermal");
            }
            if (splBtn) {
                splBtn.textContent = isEn ? "Split" : "Bölünmüş";
                splBtn.classList.toggle("active", m === "split");
            }
            if (wcBtn) {
                wcBtn.textContent = this.state.webcamStream
                    ? (isEn ? "Close Webcam" : "Kamerayı Kapat")
                    : (isEn ? "Webcam" : "Web Kamera");
                wcBtn.classList.toggle("active", Boolean(this.state.webcamStream));
            }
        }

        _updateLocalizedHeader() {
            const isEn = this.getLang() === "en";
            const cid = this.getCompartmentId();
            const def = ROOM_DEFS[cid] || ROOM_DEFS.ORION_CM;

            const pLbl = document.getElementById("sc-pip-label");
            if (pLbl) {
                pLbl.textContent = isEn
                    ? `REC • ${def.short_en}`
                    : `KAYIT • ${def.short_tr}`;
            }

            this._refreshRoomTabBadges();
            this._syncOrionSectionButtons();
            this._updateCameraModeButtons();

            const camMainBtn = document.getElementById("sc-btn-cam-toggle");
            if (camMainBtn) {
                camMainBtn.textContent = this.state.camVisible
                    ? (isEn ? "Hide Camera" : "Kamerayı Gizle")
                    : (isEn ? "Room Camera" : "Oda Kamerası");
                camMainBtn.classList.toggle("active", this.state.camVisible);
            }

            const threshVal = document.getElementById("sc-val-auto-thresh");
            if (threshVal) {
                threshVal.textContent = isEn
                    ? `Risk ≥ ${this.state.autoThreshold}`
                    : `Risk ≥ ${this.state.autoThreshold}`;
            }

            const setTxt = (id, tr, en) => {
                const el = document.getElementById(id);
                if (el) el.textContent = isEn ? en : tr;
            };
            setTxt("sc-lbl-dp", "Bölüm Basınç Farkı:", "Room Pressure Delta:");
            setTxt("sc-lbl-smoke", "Diğer Odalara Duman:", "Inter-Room Smoke:");
            setTxt("sc-lbl-air", "Bağlantı Durumu:", "Isolation State:");
            setTxt("sc-lbl-reign", "0G Çekirdek / Tutuşma:", "0G Core / Re-Ignition:");
            setTxt("sc-lbl-reentry", "Güvenli Giriş Süresi:", "Safe Re-Entry Time:");
            setTxt("sc-lbl-auto", "Otonom Koruma Eşiği:", "Auto-Protection Threshold:");
            setTxt("sc-btn-mist", "Su Sisi Söndürücü", "Water Mist Suppressor");
            setTxt("sc-btn-ai-copilot", "Bölümü Raporla", "Analyze Room");

            this._renderCountdownBanner();
            this._syncManualButtonStates();
            this._renderLivePhysicsTelemetry();
        }

        _syncManualButtonStates() {
            const isEn = this.getLang() === "en";
            const cid = this.getCompartmentId();
            const rm = this.rooms[cid];
            const fireNow = this._isRoomFireActive(cid);
            const fullClosed = rm.entryClosed && rm.airClosed;

            const bIso = document.getElementById("sc-btn-isolate-room");
            const bDoor = document.getElementById("sc-btn-hatch");
            const bFan = document.getElementById("sc-btn-fan");
            const bFire = document.getElementById("sc-btn-fire-toggle");
            const bSspc = document.getElementById("sc-btn-sspc");
            const bCamras = document.getElementById("sc-btn-camras");
            const bFullSeq = document.getElementById("sc-btn-full-sequence");

            if (bIso) {
                bIso.textContent = fullClosed
                    ? (isEn ? "Reopen Entire Room" : "Bölümü Yeniden Aç")
                    : (isEn ? "Close & Isolate Room" : "Bölümü Tamamen Kapat");
                bIso.classList.toggle("engaged", fullClosed);
            }
            if (bDoor) {
                bDoor.textContent = rm.entryClosed
                    ? (isEn ? "Open Entry-Exit Hatch" : "Giriş-Çıkış Kapağını Aç")
                    : (isEn ? "Close Entry-Exit Hatch" : "Giriş-Çıkış Kapağını Kapat");
                bDoor.classList.toggle("engaged", rm.entryClosed);
            }
            if (bFan) {
                bFan.textContent = rm.airClosed
                    ? (isEn ? "Open Air Inlet-Outlet" : "Hava Giriş-Çıkışını Aç")
                    : (isEn ? "Close Air Inlet-Outlet" : "Hava Giriş-Çıkışını Kapat");
                bFan.classList.toggle("engaged", rm.airClosed);
            }
            if (bFire) {
                bFire.textContent = fireNow
                    ? (isEn ? "Stop Fire" : "Yangını Durdur")
                    : (isEn ? "Start Fire Test" : "Yangın Testi Başlat");
                bFire.classList.toggle("engaged", fireNow);
            }
            if (bSspc) {
                bSspc.textContent = rm.powerCut
                    ? (isEn ? "Restore Room Power" : "Bölüm Elektriğini Aç")
                    : (isEn ? "Cut Room Power" : "Bölüm Elektriğini Kes");
                bSspc.classList.toggle("engaged", rm.powerCut);
            }
            if (bCamras) {
                bCamras.textContent = rm.airScrub
                    ? (isEn ? "Air Cleaning On" : "Hava Temizleme Açık")
                    : (isEn ? "Clean Cabin Air" : "Havayı Temizle");
                bCamras.classList.toggle("engaged", rm.airScrub);
            }
            if (bFullSeq) {
                bFullSeq.textContent = this.state.autoCountdownActive
                    ? (isEn ? "Response Active..." : "Müdahale Sürüyor...")
                    : (isEn ? "Auto Response" : "Sıralı Müdahale");
                bFullSeq.classList.toggle("engaged", Boolean(this.state.autoCountdownActive));
            }

            this._refreshRoomTabBadges();
        }

        _bindUIControls() {
            const canvas = this.canvas;
            canvas.addEventListener("contextmenu", (e) => e.preventDefault());
            canvas.addEventListener("pointerdown", (e) => {
                this.cam.drag = true;
                this.cam.lerp = false;
                this.state.autoOrbit = false;
                this.cam.btn = e.button;
                this.cam.lx = e.clientX;
                this.cam.ly = e.clientY;
                canvas.setPointerCapture(e.pointerId);
            });
            canvas.addEventListener("pointermove", (e) => {
                if (!this.cam.drag) return;
                const dx = e.clientX - this.cam.lx;
                const dy = e.clientY - this.cam.ly;
                this.cam.lx = e.clientX;
                this.cam.ly = e.clientY;
                if (this.cam.btn === 2) {
                    this.cam.px -= dx * 0.006;
                    this.cam.py += dy * 0.006;
                } else {
                    this.cam.yaw -= dx * 0.0075;
                    this.cam.pitch = Math.max(-1.4, Math.min(1.4, this.cam.pitch + dy * 0.0075));
                }
            });
            canvas.addEventListener("pointerup", () => {
                this.cam.drag = false;
            });
            canvas.addEventListener(
                "wheel",
                (e) => {
                    e.preventDefault();
                    this.cam.lerp = false;
                    this.cam.dist = Math.max(2.6, Math.min(15.0, this.cam.dist + e.deltaY * 0.005));
                },
                { passive: false }
            );

            const bindEl = (id, ev, fn) => {
                const el = document.getElementById(id);
                if (el) el.addEventListener(ev, fn);
            };

            // Orion Viewport Mode Bar Section & Cutaway Buttons
            document.querySelectorAll(".orion-sec-btn").forEach((btn) => {
                btn.addEventListener("click", () => {
                    if (btn.dataset.hull) {
                        this.setHullMode(btn.dataset.hull);
                    } else if (btn.dataset.zoneFocus !== undefined) {
                        this.focusSection(Number(btn.dataset.zoneFocus));
                    }
                });
            });

            bindEl("sc-btn-cam-toggle", "click", () => {
                this.state.camVisible = !this.state.camVisible;
                const ws = document.getElementById("sc-lower-workspace");
                if (ws) ws.classList.toggle("cam-collapsed", !this.state.camVisible);
                this._updateLocalizedHeader();
            });

            document.querySelectorAll(".sc-room-tab").forEach((btn) => {
                btn.addEventListener("click", () => {
                    this.state.zoneIdx = Number(btn.dataset.zone) || 0;
                    if (!this.state.camVisible) {
                        this.state.camVisible = true;
                        const ws = document.getElementById("sc-lower-workspace");
                        if (ws) ws.classList.remove("cam-collapsed");
                    }
                    if (this.state.hullMode === "cutaway") {
                        this.state.sectionFocusMode = "room";
                        const cid = this.getCompartmentId();
                        const cf = (ROOM_DEFS[cid] || ROOM_DEFS.ORION_CM).camFocus;
                        this.cam.lerp = true;
                        this.cam.tYaw = cf.yaw;
                        this.cam.tPitch = cf.pitch;
                        this.cam.tDist = cf.dist;
                        this.cam.tPx = cf.px;
                        this.cam.tPy = cf.py;
                    }
                    this._updateLocalizedHeader();
                    if (this.onHardwareStateChange) this.onHardwareStateChange();
                });
            });

            bindEl("sc-chk-ai-auto", "change", (e) => {
                this.state.aiAuto = Boolean(e.target.checked);
                if (!this.state.aiAuto && !this.state.manualSequenceActive) {
                    this.state.autoCountdownActive = false;
                    this._renderCountdownBanner();
                } else if (this.state.aiAuto) {
                    this.state.autoOverrideLatched = false;
                    this._triggerAutonomousCountdownIfNeeded();
                }
            });

            bindEl("sc-inp-auto-thresh", "input", (e) => {
                this.state.autoThreshold = Number(e.target.value) || 65;
                this.state.autoOverrideLatched = false;
                this._updateLocalizedHeader();
                this._triggerAutonomousCountdownIfNeeded();
            });

            bindEl("sc-btn-cancel-auto", "click", () => {
                this.cancelAutonomousSequence();
            });

            // 4 Camera Modes: Optical | Thermal | Split | Webcam
            bindEl("sc-btn-cam-optical", "click", () => {
                this.state.cameraMode = "optical";
                this._updateCameraModeButtons();
            });
            bindEl("sc-btn-ir-mode", "click", () => {
                this.state.cameraMode = this.state.cameraMode === "thermal" ? "optical" : "thermal";
                this._updateCameraModeButtons();
            });
            bindEl("sc-btn-cam-split", "click", () => {
                this.state.cameraMode = this.state.cameraMode === "split" ? "optical" : "split";
                this._updateCameraModeButtons();
            });

            bindEl("sc-btn-isolate-room", "click", async () => {
                const cid = this.getCompartmentId();
                const rm = this.rooms[cid];
                const sealNow = !(rm.entryClosed && rm.airClosed);
                rm.entryClosed = sealNow;
                rm.airClosed = sealNow;
                if (!sealNow) {
                    this._checkFlashReignitionOnO2Reentry(cid);
                }
                this._syncManualButtonStates();
                this._renderLivePhysicsTelemetry();
                const h0 = (ROOM_DEFS[cid].hatches || [])[0] || "HATCH_ORION_HALO";
                await this.dispatchHardwareCommand("IDSS_HATCH_SEAL", sealNow, h0, 100);
                await this.dispatchHardwareCommand("ECLSS_IMV_FAN_CUTOFF", sealNow, null, 1);
                if (this.onHardwareStateChange) this.onHardwareStateChange();
            });

            bindEl("sc-btn-hatch", "click", async () => {
                const cid = this.getCompartmentId();
                const rm = this.rooms[cid];
                rm.entryClosed = !rm.entryClosed;
                if (!rm.entryClosed) {
                    this._checkFlashReignitionOnO2Reentry(cid);
                }
                this._syncManualButtonStates();
                this._renderLivePhysicsTelemetry();
                const h0 = (ROOM_DEFS[cid].hatches || [])[0] || "HATCH_ORION_HALO";
                await this.dispatchHardwareCommand("IDSS_HATCH_SEAL", rm.entryClosed, h0, 100);
                if (this.onHardwareStateChange) this.onHardwareStateChange();
            });

            bindEl("sc-btn-fan", "click", async () => {
                const cid = this.getCompartmentId();
                const rm = this.rooms[cid];
                rm.airClosed = !rm.airClosed;
                if (!rm.airClosed) {
                    this._checkFlashReignitionOnO2Reentry(cid);
                }
                this._syncManualButtonStates();
                this._renderLivePhysicsTelemetry();
                await this.dispatchHardwareCommand("ECLSS_IMV_FAN_CUTOFF", rm.airClosed, null, 1);
                if (this.onHardwareStateChange) this.onHardwareStateChange();
            });

            bindEl("sc-btn-fire-toggle", "click", async () => {
                const cid = this.getCompartmentId();
                const rm = this.rooms[cid];
                const starting = !this._isRoomFireActive(cid);
                rm.mistLatched = false;
                rm.manualFire = starting;
                if (starting) {
                    this.state.fireOriginCid = cid;
                    this.state.autoOverrideLatched = false;
                    this._triggerAutonomousCountdownIfNeeded();
                } else {
                    this.state.autoCountdownActive = false;
                    this._renderCountdownBanner();
                }
                this._syncManualButtonStates();
                this._renderLivePhysicsTelemetry();
                if (this.onHardwareStateChange) this.onHardwareStateChange();
            });

            bindEl("sc-btn-mist", "click", async () => {
                const cid = this.getCompartmentId();
                const rm = this.rooms[cid];
                rm.mistAnim = 1.0;
                rm.mistLatched = true;
                rm.manualFire = false;
                this.state.autoCountdownActive = false;
                this._renderCountdownBanner();
                this._syncManualButtonStates();
                this._renderLivePhysicsTelemetry();
                await this.dispatchHardwareCommand("PFE_SOFIE_WATERMIST", true, null, 35);
                if (this.onHardwareStateChange) this.onHardwareStateChange();
            });

            bindEl("sc-btn-sspc", "click", async () => {
                const cid = this.getCompartmentId();
                const rm = this.rooms[cid];
                rm.powerCut = !rm.powerCut;
                this._syncManualButtonStates();
                this._renderLivePhysicsTelemetry();
                await this.dispatchHardwareCommand("PCDU_120VDC_SSPC_TRIP", rm.powerCut, null, 120);
                if (this.onHardwareStateChange) this.onHardwareStateChange();
            });

            bindEl("sc-btn-full-sequence", "click", () => {
                this.triggerFullSequentialIntervention(this.getCompartmentId(), true);
            });

            bindEl("sc-btn-camras", "click", async () => {
                const cid = this.getCompartmentId();
                const rm = this.rooms[cid];
                rm.airScrub = !rm.airScrub;
                this._syncManualButtonStates();
                this._renderLivePhysicsTelemetry();
                await this.dispatchHardwareCommand("CAMRAS_POSTFIRE_SCRUB", rm.airScrub, null, 1);
            });

            bindEl("sc-btn-webcam", "click", async () => {
                if (this.state.webcamStream) {
                    this._stopWebcam();
                    this._updateLocalizedHeader();
                    return;
                }
                if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) return;
                try {
                    const stream = await navigator.mediaDevices.getUserMedia({ video: { width: 480, height: 270 } });
                    const vid = document.createElement("video");
                    vid.srcObject = stream;
                    vid.muted = true;
                    vid.playsInline = true;
                    await vid.play();
                    this.state.webcamStream = stream;
                    this.state.webcamVideo = vid;
                    this._updateLocalizedHeader();
                } catch (_) {
                    /* graceful fallback to 3D cabin camera if permission denied */
                }
            });

            bindEl("sc-btn-ai-copilot", "click", () => {
                if (this.onRequestAiCopilot) {
                    const cid = this.getCompartmentId();
                    const def = ROOM_DEFS[cid] || ROOM_DEFS.ORION_CM;
                    const label = this.getLang() === "en" ? def.name_en : def.name_tr;
                    this.onRequestAiCopilot(cid, label);
                }
            });
        }
    }

    window.SpacecraftUltraHDStudio = SpacecraftUltraHDStudio;
})();
