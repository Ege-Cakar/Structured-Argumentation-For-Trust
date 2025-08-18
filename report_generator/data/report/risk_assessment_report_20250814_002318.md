# Risk Assessment Report
_Generated 2025-08-14 00:23:18_

## Swift Guide Words  
*Version 1 • Author: Life Safety Functional Safety & Code Compliance Expert • Section ID: swift_guide_words_20250813_153308_f1fd2e59*

SWIFT Guide Word Preparation – Integrated Life Safety (code-aware)

Because live cutover must preserve NFPA/UL/EN compliance, deterministic behavior, and AHJ acceptance, a unified guide-word taxonomy is required to structure hazard discovery across all interfaces. Therefore this taxonomy blends canonical SWIFT terms with life‑safety extensions and is to be applied across sensors/AI, FACP/FAPU, networks, HVAC smoke control, IoT/edge, evacuation routing and notification, backup communications, power, time sync, management/logging, and cloud/on‑prem.

Global core (use in combination across categories): No/None; More; Less; As Well As; Part Of; Reverse; Other Than; Early; Late; Faster; Slower.

Timing: Early, Late, Faster, Slower, Jitter, Latency >100 ms, Desync, Missed window.
Quantity/Load: Too Much, Too Little, Burst, Flood, Starvation, Overload, Queue growth.
Quality/Sensing: Degraded, Noisy, Drift, Uncalibrated, Out‑of‑spec, Saturated, Quantization error, Occlusion.
Direction/Addressing: Reverse, Other Than, Wrong Zone, Cross‑Zone, Misrouting, Backflow.
Sequence/Logic: Out‑of‑order, Skipped, Duplicated, Conflicting, Stuck, Latent, Race condition, Deadlock, Interlock bypassed.
Human Factors: Misuse, Overtrust, Undertrust, Fatigue, Training Gap, Bypass Left In, Silenced, Disabled, Permit lapse.
Environment: EMI/EMC, Heat, Smoke, Water, Corrosive, Dust, Vibration, Lighting variance, Temperature extremes.
Interfaces/Integration: Mismatch, Protocol error, Mapping error, Unit error, Unlisted interface, As Well As unintended, Part Of partial, Timebase mismatch.
Power/Pathways: Loss of Power, Brownout, Sag, Transient, Single Point of Failure, Common Cause Failure, Battery end‑of‑life, UPS bypass, Pathway survivability shortfall.
Communications: Loss of Comms, Partitioned Network, Congestion, Jitter, QoS misconfig, Clock source fail, Failover stuck, Multicast storm, Certificate expiry.
Cybersecurity (OT/IT): Tampering, Spoofing, Replay, Denial of Service, Ransomware, Privilege creep, Insecure default, Supply‑chain compromise, Shadow admin.
Data/AI: Model Drift, False Positive, False Negative, Threshold mis‑tuned, Data Poisoning, Concept drift, Unverified Update, Shadow model, Training set bias.
Compliance/Documentation: Unlisted Component, Nonconforming Installation, Unapproved Variance, Documentation Gap, Test coverage gap, Listing invalidated by change, As‑built stale.
Maintenance/Proof Testing: Deferred testing, Proof‑test overdue, Calibration overdue, Obsolescence, Wrong spare, MRO error, Battery maintenance missed.
Change Control/Configuration: Unauthorized change, Version skew, Rollback failure, Config drift, Bypass not removed, MOC incomplete, Time sync source change, License expiry.

Because traceability is mandatory, combine a global core term with a category term per component, then record deviation, plausible causes, consequences, safeguards, and needed actions with code/listing context; specific standard clauses should be verified during analysis. Therefore domain leads should extend with discipline details, for example HVAC damper fail‑positions and pressure zoning, IT/OT VLAN/QoS and PKI lifecycle, fire alarm SLC/notification circuit survivability, AI/Video dataset representativeness and line‑of‑sight, ERRCS/DAS non‑listed path segments, and access control egress unlocking interlocks.

## Swift Step 2 Background Analysis  
*Version 1 • Author: Live Cutover & Commissioning Safety Assurance Expert • Section ID: swift_step_2_background_analysis_20250813_153933_50be06e1*

SWIFT Step 2 – Background Analysis (Live Cutover & Commissioning)

Triggering condition and scope
• Because the site will execute a live cutover and commissioning of an AI-enabled, addressable fire detection and control system across 15 buildings with 10,000+ endpoints, the activity introduces simultaneous configuration, traffic, and control-path changes; therefore this is a campus-scale, time-coupled intervention that must preserve uninterrupted life-safety function.
• Because legacy FACP/BMS, smoke control, mass notification, and backup communications must remain authoritative until acceptance, the cutover necessarily operates in parallel states; therefore bi-directional interactions and event coherency across legacy and new systems are critical constraints.

Regulatory and business drivers
• Because AHJ acceptance and applicable codes/listings require continuous detection, notification, and control during impairments, any gap constitutes noncompliance; therefore commissioning must be staged to avoid loss of coverage and to document equivalency during transitions (actual permit conditions to be verified).
• Because the campus is a zero-downtime data centre and work centre, SLA and asset-protection pressures narrow tolerance for nuisance alarms and latency; therefore decision latency must meet P95 ≤ 100 ms and P99 ≤ 150 ms targets while minimizing AI false positives/negatives during onboarding.

Current state, dependencies, and constraints
• Because the new FAS with AI video analytics, IoT edge mesh, automated evacuation routing, and multi-path comms is installed but not fully cut in, control authority, event routing, and supervision traverse mixed topologies; therefore time sync (PTP/NTP holdover), PKI/cert lifecycle, network QoS/jitter, and addressable loop integrity are gating dependencies.
• Because concurrent IT re-segmentation, HVAC/BMS interface updates, and construction activity are in flight, environment and interface stability cannot be assumed; therefore commissioning windows, occupancy states, generator/UPS conditions, and radio/DAS coverage require coordination and verification.

Assumptions, boundaries, and unknowns
• Because Step 1 guide-word taxonomy (timing, quantity, quality, direction/flow, sequence, state, interface, environment, human factors, security, maintenance, AI/data, compliance) is established, this background frames where deviations could arise without asserting hazards or mitigations.
• The following data are required to finalize scope: authoritative device inventory and mapping, current cause-and-effect matrix, PTP/NTP topology and BMCA policy, QoS budgets and measured latency baselines, PKI enrollment/expiry schedule, AHJ permit conditions, and cutover phasing plan (source verification required).

## Purpose Statement  
*Version 1 • Author: Life Safety Functional Safety & Code Compliance Expert • Section ID: purpose_statement_20250813_154713_d22e425b*

Step 3 – Purpose Statement (code-anchored, SWIFT-aligned)

Because AHJs require continuous code conformity during campus-scale live cutover and operation, and because AI and IT/OT interfaces can jeopardize determinism and listings, our purpose is a defensible, fail‑safe, code‑anchored integration with safety‑critical decisions at or below 100 ms. Therefore we will add governed AI and campus interfaces without compromising UL/EN/NFPA compliance, functional safety, or AHJ acceptance.

• Compliance and listings: Because integration can invalidate listings, we will preserve conformity for detection, control, notification, and smoke control. Therefore AI remains supplemental unless listed, with independent, fail‑safe actuation and documented control scope.

• Deterministic performance: Because timing drives life safety, we will engineer and verify end‑to‑end latency and jitter under worst credible load. Therefore ≤100 ms decisions are maintained with deterministic pathways and assured time sync across on‑prem and cloud edges.

• Availability and survivability: Because downtime creates exposure and noncompliance, we will provide N+1/2N power and communications and code‑appropriate survivable pathways. Therefore core functions sustain ≥99.99% availability with brownout ride‑through and loss‑of‑comms safe states during and after cutover.

• Live cutover governance: Because migration invites human and common‑cause errors, we will use formal MOC/MOP, locked‑out bypasses, staged dual‑running, and rollback. Therefore zero downtime for core life safety is achieved while preserving listing scope and audit traceability.

• Safety, cybersecurity, and interfaces: Because security and cross‑system logic affect safety integrity, we will enforce network segregation, least privilege, signed and rollback‑capable updates, provenance, and AI model governance (drift and false‑alarm bounding). Therefore HVAC smoke control and evacuation routing remain compliant, testable, and auditable with traceable evidence for AHJ review.

## Step 4 Success Criteria Definition  
*Version 1 • Author: Real-Time Edge Computing & Performance Assurance Expert • Section ID: step_4_success_criteria_definition_20250813_155537_33060396*

Step 4 – Success Criteria Definition (Deterministic Performance for Safety-Critical Paths)

Because life safety demands sub-100 ms action during live migration, the following SLOs/SLIs must be met and continuously evidenced.

- End-to-end latency: 99.995% of safety decisions ≤100 ms; p99 ≤80 ms; p95 ≤60 ms; zero uncontrolled deadline misses during cutover windows; evaluated over rolling 30 days and each cutover.

- Stage budgets (p99 at 120% forecast load): ingest ≤15 ms; decode ≤8 ms; inference ≤30 ms; decision bus ≤8 ms; safety logic ≤10 ms; actuation/notify ≤15 ms; residual/jitter buffer ≤14 ms. Breach triggers capacity block or canary rollback while preserving E2E SLOs.

- Jitter and queueing: E2E jitter p95 ≤20 ms; any stage queueing delay p99 ≤10 ms; alert at 75% of thresholds; breach at 100%.

- Time synchronization: PTP Max|offset| ≤1 ms across safety nodes; alert at 0.5 ms sustained >5 s; dual grandmasters with holdover; within-bounds 99.99% of time.

- Failover and loss: Safety service failover ≤1 s from fault detect to healthy; critical-path packet/frame loss <0.1% during switchover; orchestrator prevents rescheduling of safety pods during cutover via PodDisruptionBudgets and taints/tolerations; validated in chaos drills and live cutover.

- Capacity headroom: Sustained CPU/GPU ≥30% headroom; memory WSS ≥25%; critical NIC ≤60%; non-safety agents capped via cgroups/limits to protect SLOs.

- Availability and ordering: Safety-path availability ≥99.99%; critical packet/frame loss <0.1%; out-of-order <0.01% with bounded reordering buffers.

- Measurement and gates: T0 (NIC hardware timestamp) to T6 (actuation ACK) with monotonic clocks; 100% stage SLI coverage via tracing/eBPF, hardware timestamps on ingest, red/black box monitors, and 1 s synthetic probes. Go‑live only after burn‑in at 120% load with all SLOs green; sustain through commissioning and 90 days post go‑live. Burn‑in duration and multiplier may be tuned after initial characterization; actual data would need to be obtained for finalization.

## System Description  
*Version 1 • Author: OT/IIoT Cybersecurity & Real-Time Networking Expert • Section ID: system_description_20250813_160505_19070267*

Step 5 – System Description (integration-focused, latency/availability aligned)

Scope and boundaries
Because life-safety decisions must complete within 100 ms end-to-end, scope covers every path from sensing and analytics to actuation and notification across 15 buildings and 10k+ nodes. Therefore, in-scope elements are the OT/IIoT network fabric, edge compute/gateways, brokers/controllers, identity/PKI, time sync, management/telemetry, monitoring, and backup communications; general IT workloads are out of scope except for defined conduits.

Component inventory
• Endpoints: life-safety detectors/actuators, AI cameras/encoders, environmental sensors.
• Edge compute/gateways: protocol bridging (BACnet/SC, Modbus/TCP, OPC UA), event filtering, edge analytics.
• Brokers/controllers: MQTT/AMQP clusters, evacuation logic, fire panels, interlock controllers.
• Network fabric: access/aggregation/core with DiffServ QoS and TSN profiles (Qbv/Qci) where applied; VRFs/VLANs per zone; redundant campus backbone.
• Identity/PKI: CA, automated enrollment (EST/SCEP), OCSP/CRL services.
• Time sync: dual PTP grandmasters, building boundary clocks, GNSS holdover, NTP tertiary.
• Management/telemetry: SDN controller, configuration/firmware services, SIEM/SOAR, OT IDS.
• Backup links: LTE/5G at building edges; LoRa/radio for low-rate telemetry.

Communication domains and data flows
Because determinism is required, flows are segmented and prioritized to align with SLOs (P95 ≤ 80 ms, P99 ≤ 100 ms; jitter ≤ 10 ms; loss ≤ 0.1%). Therefore, life-safety traffic uses reserved queues and paths distinct from bulk and management.
• Sensor/analytics events → brokers/controllers.
• Controller commands → actuators.
• Occupant/first-responder alarms → notification systems.
• Health/telemetry → monitoring.
• Management/PKI/time sync → services.
A per-segment budget is enforced along sensor → edge → broker → controller → actuator paths.

Interface map
• Messaging/control: MQTT v5 with mTLS; AMQP 1.0.
• Building protocols: BACnet/SC over TLS; Modbus/TCP within secured zones; OPC UA with signed/encrypted policies.
• Access and segmentation: 802.1X/EAP-TLS at the edge; SDN policy with VRFs/VLANs.
• Time: PTPv2 with monitoring; NTP as tertiary.
• Trust services: EST/SCEP enrollment; OCSP stapling and CRL caching at brokers/gateways.
• Management/telemetry: REST/HTTPS APIs, NetFlow/IPFIX, syslog.
• Backup communications: cellular gateways using IPsec/GRE as conduits; LoRa/radio via constrained gateways.

Inputs and outputs
• Inputs: sensor telemetry, video analytics events, device/line health, time/PKI status.
• Outputs: actuator commands, evacuation messaging, BMS/HVAC interlocks, first-responder notifications.

Stakeholders and interconnection points
Because operations span facilities, security, and IT, authoritative interconnections are brokers, BMS/HVAC gateways, SDN controllers, time/PKI services, monitoring/SIEM, and cellular gateways. Therefore, stakeholders include facilities engineering, OT/network security, datacentre operations, AHJ, and vendors/integrators.

## Ai Detection And Analytics Chain  
*Version 1 • Author: AI Fire Detection & Analytics Risk Expert • Section ID: ai_detection_and_analytics_chain_20250813_161723_364e366f*

SWIFT Step 6 – AI detection and analytics chain: risk and hazard identification (focused scope)

1) Timing and quantity: late inference and dropped frames during burst load. Because edge nodes can exceed the under‑100 ms target and networks shed frames under contention, fast‑onset signatures are missed and alarms are delayed; therefore smoke control and evacuation may actuate too late. L=4, I=5, R=20. Current safeguards include conventional addressable detectors and watchdogs. Controls include reserved compute headroom with QoS prioritization, deadline‑aware inference with abstain‑and‑verify, latency‑capped hysteresis, diversified edge nodes, and automatic escalation to non‑AI sensors when video is stale. Detection uses p99.9 latency and frame‑drop telemetry with service‑level alerts; actual site traces are required. Residual L=2, I=5, R=10.

2) Quality and environment: model drift, lookalikes, and adversarial flicker causing false positives. Because dust, steam, glare, and lighting flicker shift the visual distribution and patterns can mimic smoke or flame, the AI may trigger purge and egress erroneously; therefore unsafe airflow, nuisance evacuations, and trust erosion occur. L=4, I=4, R=16. Current safeguards include multi‑sensor confirmation and operator verification. Controls include calibrated confidence with ECE checks, context‑aware dynamic thresholds, abstain‑and‑verify with secondary sensors, online drift detection and environment classifiers, synthetic smoke tests, shadow or canary deployment with acceptance gates, and stream integrity hardening. Detection tracks false‑alarm rate by zone and periodic confusion audits; local data must be obtained. Residual L=2, I=4, R=8.

3) Direction, flow, sequence, and human factors: misrouting, time skew, and partial cutover misconfiguration. Because endpoints can be remapped, clocks can drift, and mixed thresholds can bypass fail‑safe gating, the fusion layer mis‑correlates confidence to zones; therefore spurious commands or missed alarms result. L=3, I=5, R=15. Current safeguards include interlocks and manual override. Controls include mutual‑authentication and source binding, signed configurations and models, sequence numbers with de‑duplication, time sanity checks, configuration linting with two‑person review, and canary cutovers with rollback and traceability. Detection relies on end‑to‑end correlation tests and time‑synchronization monitors. Residual L=2, I=5, R=10.

4) Fail‑safe gating disabled or mis‑tuned between AI and life‑safety actuation. Because AI paths can be routed around NFPA 72 verification or thresholds set too permissive, single‑source analytics can actuate HVAC and evacuation routing; therefore a single false positive propagates to life‑safety actuation. L=3, I=5, R=15. Current safeguards include some interlocks but coverage is uncertain. Controls include hardwired interlocks, two‑out‑of‑n diverse sensing, abstain‑by‑default logic, IEC 61508 safety‑lifecycle proof tests, and UL 268 certified detectors as authoritative inputs. Detection uses periodic functional tests and audits of routing rules. Residual L=1, I=5, R=5.

## Hvac Smoke Control Step6 Hazard Identification  
*Version 1 • Author: HVAC Smoke Control & Life‑Safety Integration Expert • Section ID: hvac_smoke_control_step6_hazard_identification_20250813_162535_57799ca7*

Step 6 – HVAC smoke control hazard identification (complements AI analytics hazards)

1) Guide word: Out-of-Sequence; Component: AHUs, smoke/return dampers, purge. What-if: AHU stops or purge starts before dampers close, drawing smoke into data halls and egress because flow paths invert. Causes: misaligned cause‑and‑effect, >100 ms jitter, time‑sync drift, controller reboot. Existing safeguards: matrix docs, some end‑switches. L 3; I 4; Risk 12 High; Not acceptable. Mitigation: hardwired damper end‑switch permissives to VFD/AHU, local PLC inhibit‑until‑closed, proof‑of‑flow, FSCP takeover dry‑runs. Priority P1; Timeline pre‑cutover.

2) Guide word: More/Less/Drifted; Component: stair pressurization fans, pressure sensors, VFDs, doors. What-if: ΔP undershoots or overshoots so smoke leaks or doors exceed opening‑force limits, impairing egress. Causes: sensor drift/placement, HOA left in Hand, VFD trip on ATS, duct leakage. Safeguards: single sensors, basic alarms. L 3; I 5; Risk 15 High; Not acceptable. Mitigation: dual sensors with voting and auto‑zero, pressure clamps within engineered limits, anti‑windup ramps, door‑force checks, VFD ride‑through and minimum‑on timers, trending with deviation alarms. Priority P1; Timeline pre‑cutover and acceptance.

3) Guide word: Late/Unavailable; Component: FACP→FSCP→BAS paths, BACnet/SC, VLAN/QoS, time sync. What-if: Command propagation exceeds 100 ms or drops during migration, delaying actuation. Causes: QoS/VLAN misconfig, BACnet/SC trust errors, switch failover, storm control, NTP/PTP loss. Safeguards: some hardwired relays. L 3; I 4; Risk 12 High; Not acceptable. Mitigation: UL864/UUKL hardwired interlocks for life‑safety actions, FSCP priority, local DDC fallback, reserved QoS, time‑sync supervision, heartbeat watchdogs, measured latency SLO tests. Priority P1; Timeline pre‑cutover.

4) Guide word: Misplaced/Crossed; Component: fire/smoke dampers, point mapping, end‑switch feedback. What-if: Wrong damper actuates or false feedback indicates open/closed, causing pressure reversal and smoke spread. Causes: terminal mislabeling, BACnet point misbinding, end‑switch failure, inconsistent naming. Safeguards: limited feedback, matrix docs. L 3; I 4; Risk 12 High; Not acceptable. Mitigation: point‑to‑point verification, unique IDs, UUKL mode end‑to‑end tests, mandatory end‑switches on life‑safety dampers, proof‑of‑closure alarms. Priority P1; Timeline pre‑cutover.

5) Guide word: Unavailable/Power; Component: ATS/generator, UPS, VFDs, control power. What-if: ATS transfer trips VFDs and drops pressurization/exhaust for seconds, jeopardizing egress. Causes: ride‑through disabled, DC‑bus undervoltage, controls not on UPS, simultaneous restart inrush. Safeguards: generator, basic restart logic. L 3; I 4; Risk 12 High; Not acceptable. Mitigation: VFD ride‑through/catch‑on‑the‑fly, UPS for controls/network, staggered restarts, emergency power priority, witnessed transfer/black‑start tests. Priority P1; Timeline pre‑cutover.

## Automated Evacuation Routing And Mass Notification Swift Step6  
*Version 1 • Author: Evacuation Modeling & Mass Notification Human Factors Expert • Section ID: automated_evacuation_routing_and_mass_notification_swift_step6_20250813_163515_d69a1e31*

Step 6 SWIFT – Automated Evacuation Routing and Mass Notification (Human Factors Focus)

1) Routing oscillation and counterflow
- Guide words: Direction/Path–Contradictory, Reverse; Timing–Intermittent; Interfaces–Latency, Unsynchronized; Quality–Stale; Human Factors–Cognitive overload.
- Scenario: Re-routes outpace movement, channels disagree, and counterflows form.
- Causes: Stale occupancy map, weak hysteresis, clock drift, missing congestion feedback.
- Consequences: Crush risk, evacuation delay, and ≤100 ms decision-loop breaches.
- Existing controls: Static fallback and AHJ overrides; damping not validated.
- L4, I5, Score 20, Acceptability: Critical.
- Mitigations (P1, pre‑cutover): Enforce hold‑times and hysteresis; degrade to static on low confidence or excess latency; gating and tie‑break logic; precise time sync; congestion sensing; drill‑validated.

2) PAVA intelligibility degraded by smoke-control noise
- Guide words: Quality–Unintelligible, Distorted; Environment–Noise; Interfaces–Prioritization failed; Timing–Duration too short.
- Scenario: Fans and dampers raise noise and reverberation, reducing STI; overlapping pages truncate instructions.
- Causes: Sparse speakers, no bounded AGC, mixed paging paths, no fan‑on profiles.
- Consequences: Messages heard but not understood; hesitation and wrong turns.
- Existing controls: Code audibility and redundancy; STI under load unverified.
- L4, I4, Score 16, Acceptability: Critical.
- Mitigations (P1, before phased activation): Model and measure STI under smoke-control; add speakers or zoning; enable bounded AGC; pre‑record bilingual scripts; synchronize text and mobile; verify ≤1 s ECS latency.

3) Accessibility and refuge communication gaps
- Guide words: Sequence–Omitted; Direction/Path–Blocked; Interfaces–Not connected, Survivability; Human Factors–Mobility and hearing limits; Commissioning–Placeholder data.
- Scenario: Accessible routing omitted on failover; ERRCS or refuge comms drop; door groups mis‑unlock.
- Causes: Incomplete accessibility metadata, radio shadows, and misconfigured groups.
- Consequences: Entrapment, missed assistance requests, and regulatory exposure.
- Existing controls: Code unlocking and strobes; survivability and coverage unverified.
- L3, I5, Score 15, Acceptability: High.
- Mitigations (P1, pre‑cutover with periodic re‑tests): Tag accessible routes; validate refuge and ERRCS coverage and survivability; verify battery autonomy; provision evacuation chairs and training; test door groups and clear widths.

4) Notification congestion and coverage blind spots
- Guide words: Interfaces–Prioritization failed, Lost link, Latency; Timing–Delayed; Quantity–Saturated; Environment–Shielding; Human Factors–Unaware.
- Scenario: Campus load delays mobile or ECS updates while stairwell DAS is weak, so reroutes and alerts arrive late or not at all.
- Causes: Insufficient QoS and preemption, lack of multicast or cell‑broadcast, stairwell coverage gaps, failover untested.
- Consequences: Uneven notification, late egress, and reduced compliance.
- Existing controls: Basic QoS and tones; load and coverage tests incomplete.
- L3, I4, Score 12, Acceptability: High.
- Mitigations (P1, pre‑cutover): Enforce priority QoS and rate limits; enable multicast or cell‑broadcast; map and remediate stairwell DAS; schedule failover and load drills; target ≥99.9% availability.

## Step6 Cyber Rt Networking Hazards  
*Version 1 • Author: OT/IIoT Cybersecurity & Real-Time Networking Expert • Section ID: step6_cyber_rt_networking_hazards_20250813_164453_c5e8a4a1*

Step 6 – Cybersecurity & Real‑Time Networking Hazards (Campus PKI, Time, Brokers, Backup)

Rationale: These hazards target identity, time, and priority, which anchor the ≤100 ms decision SLO and survivability. Because live cutover amplifies load and configuration drift, stability cannot be assumed.

1) PKI/OCSP enrollment storm and revocation path failure
• Guide words: Unauthenticated, Unauthorized, Stale, Overloaded, Starved, Bypassed, Unsafe default.
• What‑if and causes: Live cutover drives mass EST/SCEP enrollments while OCSP/CRL paths lag or are unreachable due to misconfigured mirrors and clock skew.
• Effects: Devices fail mTLS or fall back to insecure trust, therefore spoofed brokers/gateways can inject or legitimate nodes go dark, breaching identity and availability SLOs.
• Safeguards: OCSP stapling; on‑campus OCSP mirrors/CRL caches with expiry alarms; randomized enrollment with rate limits; pre‑staged certs; broker identity pinning; fail‑closed quarantine mode.
• Required data: OCSP/CRL latency and hit rates; CA issuance throughput vs demand; mTLS success ratios under load; cert age distribution (actual data required).

2) PTP offset compromise and desynchronization
• Guide words: Drifted, Desynchronized, Out‑of‑order, Faster, Slower, Spoofed, Partitioned.
• What‑if and causes: Grandmaster fails or is spoofed; boundary clocks run mixed profiles; GNSS loss forces NTP fallback without path authentication.
• Effects: TSN schedules misalign and event ordering breaks, therefore P95/P99 latency and jitter exceed targets and cross‑building correlation degrades.
• Safeguards: Dual authenticated grandmasters with constrained BMCA and hardware timestamping; MACsec on time paths; GNSS holdover; application time‑sanity guardrails.
• Required data: Offset and path‑delay histograms; grandmaster switchover timing; cross‑domain skew; TSN conformance (verification required).

3) QoS priority inversion and MQTT‑AMQP partitioning under storm/failover
• Guide words: More, Burst, Congested, Overloaded, Jittery, Slower, Misrouted, Out‑of‑order, Duplicated, Isolated, Incompatible.
• What‑if and causes: Alarm bursts coincide with 802.1X reauth surges and broker failover onto LTE/5G where DSCP re‑marking, ECMP shifts, and MTU/MSS mismatch trigger fragmentation and redelivery.
• Effects: Priority inversion delays or drops life‑safety commands; duplicated QoS‑1 traffic saturates clients, therefore P99 latency breaches 100 ms and buildings partition logically.
• Safeguards: Strict LLQ with TSN Qbv/Qci and guard bands; broker topic prioritization/backpressure; staggered 802.1X timers; BFD‑pinned paths; validated end‑to‑end MTU/MSS.
• Required data: Per‑class queue drops; P95/P99 latency and jitter; broker redelivery counters; reauth rates; failover switchover time (verification required).

Gaps now closed (additional cutover‑critical hazards)
4) 802.1X/NAC misclassification isolates life‑safety
• Guide words: Unauthorized, Isolated, Misconfigured, Bypassed, Late.
• Because policy errors quarantine devices or down‑shift VLAN/priority during reauth, safety traffic is delayed or blocked, therefore commands miss SLOs and monitoring blind spots emerge.
• Controls/data: Pre‑stage EAP‑TLS allowlists and deterministic port‑profiles; reauth staggering; break‑glass life‑safety VLAN with strict ACLs; RADIUS/EAP failure logs and misclassification counts.

5) Broker split‑brain under WAN partition
• Guide words: Partitioned, Duplicated, Out‑of‑order, Stale, Misrouted.
• Because loss of quorum yields dual leaders and cross‑site reconnects, acknowledgments diverge and messages duplicate or arrive stale, therefore actuators may act inconsistently.
• Controls/data: Quorum‑based clustering with failure‑domain awareness and site affinity; idempotent consumers with de‑dup keys/TTL; partition‑injection test results and duplicate delivery stats.

## Physical Access Egress Step6  
*Version 1 • Author: Physical Security & Egress Control Integration Risk Expert • Section ID: physical_access_egress_step6_20250813_165338_f4aee40a*

Step 6 – Hazard identification: Physical access and egress layer (≤100 ms path). Scope includes door hardware, ACS, interlocks/mantraps, turnstiles and barriers, and elevators with firefighter service.

Hazard 1 – Guide words: Late, Unavailable, Sequence, Conflict, Desync – door release, interlocks, and ACS.
Because some releases still traverse ACS software, APIs, or congested networks, alarm-to-unlock can arrive late or not at all. Therefore interlock bypass may lag unlock and turnstile drop-arms may not clear, creating entrapment. Causes include VLAN or ACL blocks, ACS CPU overload during event storms, lockdown precedence over fire, and PTP or NTP loss that desynchronizes token and heartbeat logic. Effects are delayed egress, relock during an active alarm, and trapped occupants in mantraps. Risk rating is Likelihood 4, Impact 5, giving 20. Verification should timestamp FACP hardwired relay closure to lock power drop and interlock bypass, accepting ≤100 ms local and ≤500 ms cross-system under load; mitigation emphasizes hardwired supervised fire relays with fail‑safe unlock precedence, dual‑path release, safe‑state on time desync, QoS, and explicit ACL whitelisting.

Hazard 2 – Guide words: Unavailable, Degraded, Reverse, Overload – power survivability and fail‑safe behavior.
Because some maglocks or strikes depend on PoE or non‑fire‑tripped supplies, brownouts or midspan failures can keep locks energized or cause relock while the alarm remains latched. Therefore egress can be blocked or oscillate on restoration. Causes include missing supervised fire‑trip inputs, overloaded or shared UPS, and auto‑relock logic on power return. Effects include lock‑in during evacuation or uncontrolled releases that break zones. Risk rating is Likelihood 3, Impact 5, totaling 15. Verification uses staged brownouts and PoE cuts with the alarm held, requiring lock power to drop within ≤100 ms and no relock until the alarm clears; mitigation calls for dedicated UL 294 survivability power with fire trip and fail‑safe hardware at egress points.

Hazard 3 – Guide words: Wrong, Other Than, Conflict, Before/After – elevator recall, stair re‑entry, and barriers.
Because elevator recall, firefighter service, ACS unlocks, and barrier controls are sometimes inconsistently zoned, lobbies and stair re‑entry doors can remain secured and turnstiles or revolving doors can stay engaged. Therefore occupants and responders face blocked lobbies and noncompliant re‑entry. Causes include mismapped recall‑to‑ACS points, interlock logic that does not bypass under Phase I or II, lockdown precedence over recall, and missing barrier brake or drop‑arm triggers. Effects include delayed evacuation, crowding at barriers, and responder access denial. Risk rating is Likelihood 4, Impact 4, resulting in 16. Verification requires integrated Phase I and II drills confirming lobby unlocks, compliant stair re‑entry, and turnstile drop‑arms within ≤100 ms, with cross‑system logs correlated; mitigation defines life‑safety precedence and validates barrier mechanical breakout where applicable.

## Live Cutover Commissioning Hazards  
*Version 1 • Author: Live Cutover & Commissioning Safety Assurance Expert • Section ID: live_cutover_commissioning_hazards_20250813_170300_2d9e1e7e*

Step 6 – Live Cutover & Commissioning Hazard Set (Gap Closure Addendum)

Purpose of this addendum: Close cutover-specific gaps not yet captured by subsystem hazards by explicitly addressing dual-running, authority-of-control, rollback behaviors, test-bypass governance, impairment bridging, and comms rehoming in the T0–T6 window.

A) Voice Evac/Fire Phone authority mis-handoff (building/zone scope)
- Guide words: sequence missing/skipped; state test mode left on; interface mapping error; human factors handover error.
- Deviation/Causes: During dual-run, legacy retains mic/phone priority while new head-end asserts partial control because parity and ownership tokens are misaligned.
- Consequences: Wrong/no tones or announcements; occupant confusion; delayed egress.
- Safeguards/Detection: Single-writer lock per building, keyed physical transfer, pre-flight talk-test, audio loopback and tone presence monitors.
- Risk: L=3, I=4, Priority=12.

B) Monitoring and backup comms rehome failure (DAS/LTE/sat and offsite monitoring)
- Guide words: direction wrong route; interface certificate expired; security credential reuse; state degraded.
- Deviation/Causes: Report paths duplicate or blackhole during switchover because endpoints are rehomed out-of-order or trust stores mismatch.
- Consequences: Missed dispatch or duplicate dispatch; regulatory exposure.
- Safeguards/Detection: Dual-path heartbeats with positive acks, timed enable/disable gates, certificate pinning and expiry alarms, live failover drill.
- Risk: L=3, I=5, Priority=15.

C) Supervision/notification inhibits left active (bypass left-in)
- Guide words: state inhibit active; sequence skipped; quality stale.
- Deviation/Causes: NAC/SLC/waterflow delays widened or suppressed for testing and not auto-cleared under time pressure.
- Consequences: Silent faults and delayed actuation; latency targets exceeded.
- Safeguards/Detection: Auto-expiring inhibits, no-active-inhibits go/no-go gate, inhibitor dashboard with paging, field spot-checks.
- Risk: L=4, I=4, Priority=16.

D) Split smoke-control sequencing under impairment bridging
- Guide words: direction wrong target; sequence out-of-order/race; interface mapping error; state degraded.
- Deviation/Causes: Legacy drives fans while new drives dampers, because bridging slices the matrix across controllers.
- Consequences: Pressure imbalance/recirculation; facility-wide disruption.
- Safeguards/Detection: One sequencer-of-record per zone, one-way idempotent gateway, end-switch and delta-P correlation alarms.
- Risk: L=3, I=5, Priority=15.

E) Latched states across rollback/backout
- Guide words: maintenance rollback failure; sequence partial rollback; state safe-state not reached.
- Deviation/Causes: New-system latches (alarm/evac/smoke mode) persist when reverting, because neutral-state handshake is missing.
- Consequences: Conflicting indications and actuations; extended impairment.
- Safeguards/Detection: Rollback precondition checklist to neutralize latches, power-cycle-to-safe policy where applicable, parity checks pre/post rollback.
- Risk: L=3, I=4, Priority=12.

## Edge Compute Performance Step6 Hazards  
*Version 1 • Author: Real-Time Edge Computing & Performance Assurance Expert • Section ID: edge_compute_performance_step6_hazards_20250813_171121_a8f45323*

Step 6 – Hazard Identification: Real-Time Edge Computing and Performance Assurance

1) Orchestration and scheduling jitter during cutover and alarm storms
Because mixed‑critical pods can be rescheduled or throttled while GC, IRQ migration, or device resets occur, tail latency inflates precisely during alarm bursts. Therefore late, intermittent, and jitter deviations threaten the <100 ms SLO and delay life‑safety actuation.
Risk: L=4, I=4, R=16. Metrics: p99 latency, p95 jitter, failover time, CPU/GPU headroom; actual data would need to be obtained. Acceptance: p99 <80 ms, jitter p95 <20 ms, failover <1 s, headroom ≥30%. Safeguards: PREEMPT_RT, CPU isolation and IRQ/NIC affinity, SCHED_FIFO with priority inheritance, mlock; Guaranteed QoS, taints/PDBs, hot‑standby with readiness gates; GPU persistence/MIG; throttle non‑safety agents. Needed analyses: forced reschedule and storm‑soak with tracing; pass on acceptance.

2) Admission control, backpressure, and queue starvation
Because unbounded queues and flat priorities admit bursty camera and sensor fan‑in, head‑of‑line blocking and allocator thrash emerge. Therefore overflow/underflow and out‑of‑order handling degrade end‑to‑end latency and frame integrity.
Risk: L=4, I=4, R=16. Metrics: per‑stage throughput, queue depth, frame/packet loss; actual data would need to be obtained. Acceptance: critical‑path loss <0.1% and zero deadline misses under load. Safeguards: bounded lock‑free queues, drop‑oldest for non‑safety, priority lanes for life‑safety topics, per‑source shaping and admission control, backpressure‑aware gStreamer caps, zero‑copy DMA, SLO watchdogs with fast abort. Needed analyses: burst and sustained‑storm tests with latency budget conformance checks.

3) Time synchronization drift and timestamp pathologies
Because single points in PTP or NTP fallback without hardware timestamping inject offset and jitter, temporal windows and fusion ordering break. Therefore sequence and quality deviations can cause late or incorrect decisions and false positives.
Risk: L=3, I=4, R=12. Metrics: max|offset|, path delay symmetry, reorder ratios; actual data would need to be obtained. Acceptance: clock offset <1 ms and p99 latency <80 ms during perturbation. Safeguards: dual PTP grandmasters, boundary clocks, NIC HW timestamping, holdover oscillators, offset alarms with safe‑mode policies, monotonic‑clock APIs with offset compensation. Needed analyses: offset injection and out‑of‑order frame tests.

4) Thermal throttling and power/PoE sags
Because rack thermal exceedance or brownout induces CPU/GPU frequency throttling or device resets, processing gaps appear during high‑demand periods. Therefore tail‑latency spikes and failovers may breach safety SLOs.
Risk: L=3, I=4, R=12. Metrics: thermal headroom, throttle events, power quality; actual data would need to be obtained. Acceptance: zero uncontrolled deadline misses during thermal or power perturbations. Safeguards: UPS‑backed nodes, PoE budgeting, proactive derating alerts, fan curves, GPU/CPU thermal guards with graceful degradation. Needed analyses: thermal‑soak and power‑sag fault‑injection with continuous latency tracing.

5) Security‑performance interaction (EDR/logging/telemetry)
Because endpoint security and heavy logging compete for CPU, I/O, and caches, contention amplifies jitter and resource starvation. Therefore benign scans or spikes can act as unintentional denial of service on the inference path.
Risk: L=3, I=3, R=9. Metrics: agent CPU/I/O usage versus latency deltas; actual data would need to be obtained. Acceptance: no measurable impact on p99 latency or jitter under agent activity. Safeguards: cgroups and I/O rate limits, CPU pinning, scan windows, exclude hot paths, staged canaries with perf gates. Needed analyses: A/B with agents enabled during storm tests.

## Functional Safety Code Compliance Step6  
*Version 1 • Author: Life Safety Functional Safety & Code Compliance Expert • Section ID: functional_safety_code_compliance_step6_20250813_172258_21faa80d*

Step 6 – Code‑anchored Functional Safety Hazard Identification (listing scope, gating/precedence, survivability, acceptance/testing)

1) Listing scope and actuation gating
• Guide words: Other Than, Unlisted Component, Misuse, Overtrust, Unverified Update.
• Scenario: Because AI video analytics and some IoT sensors are outside initiating‑device listing scope, their use as primary triggers would violate UL 864/UUKL precedence and NFPA 72 intent. Therefore actuation or release could occur without a listed initiating event and jeopardize listing/AHJ acceptance.
• Actions: Hard‑gate actuation to listed initiating circuits and listed interfaces; treat AI/IoT as supplemental/diagnostics only; enforce change control with documented listing impact analysis; freeze models during acceptance and maintain rollback.

2) Fire alarm precedence vs BAS and cutover bypasses
• Guide words: Reverse, Conflicting, Bypass Left In, Out‑of‑order.
• Scenario: Because BAS forces/overrides and commissioning jumpers can persist, fire alarm commands may be reversed or blocked. Therefore smoke control may fail to start or shut down prematurely, creating code violations and unsafe smoke movement.
• Actions: Implement listed, fail‑safe precedence interfaces with normally‑closed default to fire‑alarm control; supervise damper/fan feedback; dual‑witness removal of bypasses; require BAS lockout/tagout during tests and verify by negative testing with deliberate BAS conflicts.

3) Pathway and power survivability
• Guide words: Less/Degraded, Loss of Power, Common Cause Failure, Single Point of Failure, EMI/Heat/Water.
• Scenario: Because life‑safety signaling is riding shared IT/PoE or co‑located UPS/closets, survivability may not meet required classes under heat, water, or EMI. Therefore notification, smoke control, and routing links can fail when demanded.
• Actions: Map circuits to required survivability class; apply 2‑hour‑rated or equivalently protected routing; provide physically diverse risers and segregated power sources; monitor path integrity; proof‑test brownout ride‑through and endpoint thermal tolerance.

4) Acceptance testing, latency, and sequence integrity
• Guide words: Late, Jitter, Desync, Skipped, Duplicated, Unverified Update.
• Scenario: Because integrated sequences span panels, networks, and edge nodes, congestion and clock drift can breach ≤100 ms decision targets and mis‑order NFPA timing, while unverified updates or leftover test modes hide faults. Therefore notification/control can be delayed or contradictory to egress codes.
• Actions: Define an end‑to‑end deterministic latency budget with time‑sync holdover; instrument tests under worst‑credible load and clock offsets; freeze firmware/config during acceptance; record traces as evidence for AHJ review.

## Step 7 Risk Assessment Cutover Identity Time Priority  
*Version 1 • Author: OT/IIoT Cybersecurity & Real-Time Networking Expert • Section ID: step_7_risk_assessment_cutover_identity_time_priority_20250813_205047_232cebcd*

Step 7: Risk Assessment and Evaluation – Cutover-critical cybersecurity hazards (identity, time, priority)

Ratings use Impact 1–5, Likelihood 1–5, Risk = I×L; acceptability judged against Step 4 targets: P95 ≤80 ms, P99 ≤100 ms, jitter ≤10 ms, loss ≤0.1%, HA ≥99.99%, failover ≤1 s, identity completeness and PKI freshness.

1) PTP desynchronization (Desynchronized, Drifted, Out-of-order)
• Rationale: Because GM failover/reparenting and NTP fallback can push offsets beyond TSN/Qbv gates, therefore timestamps and sequencing break, causing late or out‑of‑order events and SLO breaches. 
• Impact 5; Likelihood 4; Risk 20; Acceptability: Unacceptable. 
• Assumptions: mixed PTP/NTP, limited holdover, multi‑vendor TSN. 
• Data sources: ptp4l/gPTP logs, boundary clock stats, TSN telemetry, latency histograms; actual data would need to be obtained. 
• Deeper analysis: controlled GM failover drills, offset/jitter sweeps under alarm storms, measure out‑of‑order rate into actuator logic.

2) QoS priority inversion (Misrouted, Slower, Jittery, Congested)
• Rationale: Because DSCP rewrite or VLAN mis‑tagging during EVPN/SD‑WAN changes can place life‑safety flows behind video bursts, therefore P99 latency and loss exceed targets and HA is threatened. 
• Impact 4; Likelihood 4; Risk 16; Acceptability: Unacceptable. 
• Assumptions: multivendor DiffServ/TSN with shared links. 
• Data sources: switch queue counters, policer drops, sFlow/IPFIX, broker/edge queue depth, PCAP tags. 
• Deeper analysis: queueing model, synthetic alarm storm with LLQ/TSN validation, Qci policing tests, priority inheritance across tunnels.

3) PKI enrollment/OCSP storm (Overloaded, Starved, Stale, Unauthenticated)
• Rationale: Because mass re‑enrollment and revocation checks can overload RA/CA/OCSP, therefore mTLS handshakes fail or stale status is accepted, degrading identity assurance and adding retry latency. 
• Impact 4; Likelihood 3; Risk 12; Acceptability: Tolerable with controls. 
• Assumptions: partial PKI, online revocation dependence. 
• Data sources: CA/RA throughput, EST/SCEP logs, OCSP cache hits, handshake latency. 
• Deeper analysis: RA/OCSP load tests, CRL caching and OCSP stapling efficacy, cert rotation throughput versus device count.

Gaps to add into Step 7 scope
4) 802.1X/NAC misclassification (Unauthorized, Isolated, Misconfigured)
• Because policy errors can isolate life‑safety endpoints during cutover, therefore alarms and commands miss the ≤100 ms window. Impact 4; Likelihood 3; Risk 12; Acceptability: Tolerable but high priority. Data: NAC decision logs, auth failures; staged audit‑mode tests needed.

5) Broker split‑brain under partition (Partitioned, Stale, Duplicated, Out‑of‑order)
• Because path churn can break quorum and diverge state, therefore duplicates, loss, or delayed redelivery violate latency/loss and HA targets. Impact 5; Likelihood 3; Risk 15; Acceptability: Unacceptable without quorum safeguards. Data: cluster logs, leader election timings; chaos partition tests required.

## Ai Fire Analytics Step7 Risk Assessment  
*Version 1 • Author: AI Fire Detection & Analytics Risk Expert • Section ID: ai_fire_analytics_step7_risk_assessment_20250813_205926_8b591040*

Step 7 – Risk Assessment and Evaluation: AI Fire Detection & Analytics

Because Step 6 exposed AI-specific hazards and Step 4 sets sub‑100 ms and accuracy expectations, this section quantifies top AI risks, justifies ratings, and sets actionable controls.

1) Late inference and frame drops (Guide words: Timing–late/jitter, Quantity–drop, Sequence–out‑of‑order)
Because bursty load and network contention inflate tail latency and shed frames, fast‑onset signatures are missed or delayed; therefore smoke control and evacuation can actuate too late. Ratings: L=4, I=5, R=20; Acceptability: High—mitigate before go‑live. Current safeguards: listed detectors in parallel and stale‑stream watchdogs. Additional controls: compute and QoS headroom, deadline‑aware inference with abstain‑and‑verify, bounded queues with backpressure, temporal consistency checks, and automatic escalation to non‑AI sensors when video is stale. Residual: L=2, I=5, R=10. Data required: p99.9 decision‑latency and frame‑drop traces under alarm storms (verification required).

2) False positives from drift and lookalikes (Guide words: Quality–drifted/biased/adversarial, Environment–haze/glare/flicker)
Because dust, steam, glare, and flicker shift visual distributions, the model elevates spurious alerts; therefore nuisance evacuations and unsafe airflow changes occur. Ratings: L=4, I=4, R=16; Acceptability: High—mitigate before go‑live. Current safeguards: multi‑sensor confirmation and operator review exist but are not quantified. Additional controls: calibrated confidence with reliability diagrams and ECE limits, dynamic thresholds by environment, abstain‑and‑verify with diverse sensors, online drift detectors, adversarial and occlusion robustness tests, and shadow/canary with confusion‑matrix acceptance gates. Residual: L=2, I=4, R=8. Data required: zone‑level false‑alarm rates and periodic confusion audits (actual data needed).

3) Missed detection from occlusion and mis‑tuning (Guide words: Quality–occluded/saturated, Quantity–less, Human factors–mis‑configure)
Because cameras lose line‑of‑sight or thresholds are tightened to suppress nuisance alerts, true events are suppressed; therefore recall degrades below acceptable bounds. Ratings: L=3, I=5, R=15; Acceptability: ALARP with controls. Current safeguards: overlapping coverage and listed detectors provide partial redundancy. Additional controls: placement audits and occlusion checks, synthetic smoke/flame tests per view, minimum recall gates using confusion‑matrix targets before enabling actuation, two‑out‑of‑n voting with diverse modalities, and two‑person review for threshold changes. Residual: L=2, I=5, R=10. Data required: view‑level recall and missed‑detection rates across construction phases.

4) Gating and mapping failures into actuation (Guide words: Direction–misrouted, Sequence/State–wrong state/partial cutover, Quality–stale)
Because AI events can bypass NFPA 72 verification or be misrouted across zones and clocks, single‑source analytics can directly actuate HVAC or evacuation; therefore a lone false or stale event propagates to life‑safety control. Ratings: L=3, I=5, R=15; Acceptability: ALARP with enforced interlocks. Current safeguards: some interlocks exist but coverage is uncertain during cutover. Additional controls: hardwired interlocks and two‑out‑of‑n diverse sensing, abstain‑by‑default when confidence or time sanity checks fail, signed models and configurations with source binding and de‑duplication, and periodic functional tests of routing and zone mappings. Residual: L=1, I=5, R=5. Data required: audited gating rules and time‑sanity failure rates.

Standards alignment: keep AI supplemental unless listed per applicable fire codes and product listings, and apply functional‑safety lifecycle practices; exact clauses require verification.

## Hvac Smoke Control Step7 Risk Assessment  
*Version 1 • Author: HVAC Smoke Control & Life‑Safety Integration Expert • Section ID: hvac_smoke_control_step7_risk_assessment_20250813_210633_71bee02f*

Step 7 Risk Assessment — HVAC Smoke Control & Life-Safety Integration (code‑anchored to sub‑100 ms actuation, pressure zoning integrity, and deterministic sequencing)

1) Late — command path FACP→FSCP→BAS→VFD/dampers. Scenario: Under congestion or failover, propagation exceeds 100 ms, delaying actuation and violating life‑safety precedence. Causes include QoS or VLAN misconfiguration, BACnet routing hops, time sync jitter, and edge analytics gating. Safeguards include hardwired FSCP priority and watchdogs, yet end‑to‑end latency under load remains unverified. L=3, I=4, Risk=12 High; not acceptable against the <100 ms criterion. Probe with worst‑case latency and failover tests using timestamped traces and time sync conformance checks.

2) More — stair pressurization VFD control loop. Scenario: Differential pressure exceeds the 12–50 Pa band, increasing door forces and impairing egress. Causes include sensor drift or placement error, controller overshoot or windup, and stack effects under heat. Safeguards include redundant sensors, setpoint clamps, and mechanical reliefs, but calibration and tuning status need verification. L=3, I=4, Risk=12 High; not acceptable versus pressurization and door‑force limits. Probe with multidoor step tests, calibration checks, and trending under thermal load.

3) Out‑of‑Sequence — AHU isolation and exhaust or purge. Scenario: Exhaust runs or AHU shuts before isolation dampers position, entraining smoke into data halls and egress. Causes include vendor logic mismatch, version control gaps, HOA left in Hand, false end‑switch feedback, and cross‑building routing delay. Safeguards include UUKL interlocks and end‑switch feedback, yet cross‑vendor determinism and fan sequencing priority are unproven. L=3, I=5, Risk=15 High; not acceptable due to egress and critical space risk. Probe with time‑stamped end‑to‑end sequence tests and failover logs.

4) Omitted/Incorrect — damper end‑switch verification. Scenario: End‑switch indicates open while blade is stuck closed, defeating pressure zoning integrity. Causes include mechanical linkage failure, misadjusted limit, or wiring fault post‑cutover. Safeguards include position feedback, but no proof‑of‑flow or ΔP correlation may exist. L=3, I=4, Risk=12 High; not acceptable against zero single‑point failure. Probe with A‑B position versus airflow/ΔP correlation and periodic functional tests.

5) Power/Transient — ATS transfer and VFD ride‑through. Scenario: ATS transfer induces VFD trips and loss of pressurization or exhaust for tens of seconds. Causes include undervoltage ride‑through disabled, DC bus undervoltage, and upstream inrush. Safeguards include generator or UPS, yet VFD settings and sequencing under transfer are unverified. L=3, I=5, Risk=15 High; not acceptable versus required continuous smoke control. Probe with instrumented transfer tests, event logs, and start sequencing verification.

## Evacuation Routing Mass Notification Human Factors Step7  
*Version 1 • Author: Evacuation Modeling & Mass Notification Human Factors Expert • Section ID: evacuation_routing_mass_notification_human_factors_step7_20250813_211712_d2ae5cbb*

SWIFT Step 7 – Evacuation Modeling & Mass Notification Human Factors Risk Assessment (routing, intelligibility, accessibility, safe fallback, live cutover)

Hazard 1: Dynamic routing misdirects due to stale or unsynchronized data
- Guide words: Direction/Path wrong way; Interfaces latency, unsynchronized; Commissioning placeholder. 
- Scenario: Signage directs into smoke because routing used stale inputs while pressurization changed tenability. 
- Causes: Weak freshness checks, mesh jitter, low hysteresis, mis-mapped door groups. 
- Consequences: Exposure and queuing increase; local RSET can exceed ASET; wayfinding errors breach ≤5% target. 
- Existing controls: Static egress, firefighter override; ECS supervision does not validate arrow logic. 
- L=3; I=5; Score=15; Acceptability: High. 
- Analysis needed: End-to-end latency/jitter tests; agent-based egress with time-varying routes; FDS for ASET. 
- Mitigations: Enforce timeouts with fail-safe reversion to static signs, add sensor quorum and hysteresis, validate door-group mapping with fault injection; Priority: P1 pre-cutover.

Hazard 2: PAVA audible but unintelligible under smoke-control noise
- Guide words: Quality unintelligible; Environment noise; Interfaces prioritization failed. 
- Scenario: Fans mask speech so tones are heard but words are not. 
- Causes: Coverage gaps, untuned DSP for fan-on profile, mis-set priority/ducking. 
- Consequences: Pre-movement increases and compliance drops; STI below 0.45–0.50 violates success criteria, lengthening RSET. 
- Existing controls: UL 2572 ECS and survivable pathways; worst-case STI unverified. 
- L=4; I=4; Score=16; Acceptability: Critical. 
- Analysis needed: Acoustic modeling and STIPA with fans operating; ECS latency/priority tests. 
- Mitigations: Add/reposition speakers, dynamic EQ and gain presets tied to fan state, concise multilingual scripts, synchronized arrows; Priority: P1 tuning, P2 hardware.

Hazard 3: Accessibility and LEP gaps in routing and messaging
- Guide words: Human Factors mobility limitations, language barrier; Sequence omitted. 
- Scenario: Routes ignore wheelchair users/refuges; English-only audio in mixed-language zones. 
- Causes: Missing mobility attributes, message mapping errors, unintegrated refuge comms. 
- Consequences: Unsafe paths and non-compliance risks; visual coverage may miss ADA candela. 
- Existing controls: ADA hardware and strobes likely present; coverage and language mapping not verified. 
- L=3; I=4; Score=12; Acceptability: High. 
- Analysis needed: HFMEA for assisted flows, mobility-aware egress modeling, photometrics; actual site data required. 
- Mitigations: Audit ADA/LEP coverage, preload mobility-aware routes and refuge logic, enable haptic/bilingual alerts, drill assistance teams; Priority: P1 audit, P2 drills.

Hazard 4: Out-of-sequence door release and pressurization versus routing updates
- Guide words: Sequence out-of-order; Interfaces unsynchronized; Direction wrong way; Security fail-unsafe. 
- Scenario: Signage updates before doors are unlocked or pressure differentials settle, causing trapping in lobbies and reverse flow. 
- Causes: BACnet/integration delays, door relock on power dips, panel brownouts, missing closed-loop checks. 
- Consequences: Bottlenecks and entrapment; decision loop and signage latency limits are breached. 
- Existing controls: Code-driven fail-safe unlock and elevator recall; no verification that routing waits for ready state. 
- L=3; I=5; Score=15; Acceptability: High. 
- Analysis needed: Time-synchronization and sequence-of-operations tests across ECS–ACS–HVAC; device-state logging. 
- Mitigations: Gate routing on verified door-unlocked and pressure-in-range signals, latch fail-open on loss of power, supervised status feedback to signage, cutover runbooks with step holds; Priority: P1 pre-cutover.

## Access Control Egress Step7 Risk Assessment  
*Version 1 • Author: Physical Security & Egress Control Integration Risk Expert • Section ID: access_control_egress_step7_risk_assessment_20250813_212626_cb94fa87*

Step 7 Risk Assessment – Access Control and Egress Integration (Live Cutover)

Alignment with HVAC/Evac Step 7: We apply the same latency and survivability targets: alarm-to-unlock ≤100 ms (local) and ≤500 ms (cross-system), no relock until alarm reset and HVAC all‑clear, and ride‑through during brownouts.

1) Non-deterministic fire-to-unlock under network/API, NAC churn, partitions, and event storms.
Because partitions and policy churn delay or drop API overrides while storms queue messages, unlock can exceed 100 ms or fail, desynchronizing with smoke control and routing. Risk rating: L=4, I=5, Score 20, High unacceptable. Data/tests: PTP‑correlated FACP‑to‑coil timing, hardwired versus API inventory, ACS queue/drop telemetry, VLAN/ACL fault‑injection and unlock storm; acceptance as above with zero missed releases.

2) Brownout or transfer‑induced relock or reversal during alarm.
Because PoE droop, UPS transfer, or PSU foldback can reboot controllers and re‑energize maglocks, doors may relock mid‑evacuation. Risk rating: L=3, I=5, Score 15, High unacceptable. Data/tests: PSU hold‑up and fire‑trip continuity, PoE midspan behavior, staged sags and current limits; verify sustained unlock through alarm and reassertion within 100 ms.

3) Lockdown and anti‑passback preempting or relocking after fire input.
Because rule precedence and heartbeat timeouts can outrank the override, doors can fail to unlock or relock while alarm persists. Risk rating: L=3, I=5, Score 15, High unacceptable. Data/tests: explicit precedence map and state machine, concurrent fire plus lockdown drills, audit continuity; verify no relock until alarm reset and HVAC all‑clear.

4) Interlocks/mantraps/turnstiles not bypassed before unlock.
Because bypass relays or logic may lag, occupants can be trapped and egress flow blocked. Risk rating: L=3, I=4, Score 12, Medium treat. Data/tests: interlock tables and relay supervision, fire‑while‑interlocked tests; measure bypass‑to‑unlock within 100 ms and mechanical drop times.

5) AI trigger misclassification driving missed or spurious releases.
Because AI can deliver false negatives or positives under drift or spoofing, doors may remain locked or unlock campus‑wide. Risk rating: L=3, I=5, Score 15, High unacceptable. Data/tests: site‑specific ROC and confusion matrix, guarded commissioning with dual‑confirmation and suppression, false release rate monitoring; verify hardwired path always meets latency.

## Step7 Live Cutover Commissioning  
*Version 1 • Author: Live Cutover & Commissioning Safety Assurance Expert • Section ID: step7_live_cutover_commissioning_20250813_213523_f4d33e51*

Step 7 – Risk Assessment (Live Cutover & Commissioning Safety Assurance)

Scope. Quantifies Step 6 hazards from a cutover/commissioning lens and tests acceptability against Step 4 success criteria; flags analyses and go/no‑go gates.

H1: Campus single‑window cutover without isolation
- Guide words: Timing (>100 ms, jitter), Sequence (skipped), Direction (wrong route), State (degraded).
- Hazard: Simultaneous database/SLC changes misroute smoke control and create coverage gaps.
- Consequence vs Step 4: Breaches P95 ≤100 ms/P99 ≤150 ms, 100% smoke control validation, and continuous coverage.
- Safeguards/detection: Parallel run with one‑way gateway; P99 telemetry; supervised circuits.
- Risk: Likelihood 4; Impact 4; Priority 16; Acceptability: unacceptable.
- Required analyses and gates: Building canary; hot‑cutover fault injection; PTP/QoS freeze; time‑boxed soak meeting all Step 4 metrics before expanding beyond the canary.

H2: Unphased PKI/NAC identity change and PTP drift
- Guide words: Interface (certificate/API), Security (unauthorized change), Timing (clock drift, >100 ms), Quantity (flood).
- Hazard: Mass reauth and grandmaster loss induce control‑plane contention and event ordering errors.
- Consequence vs Step 4: Threatens supervision uptime and latency targets; risks missed or missequenced alarms.
- Safeguards/detection: Shadow trust store; NAC maintenance mode; PTP holdover alarms.
- Risk: Likelihood 3; Impact 4; Priority 12; Acceptability: unacceptable.
- Required analyses and gates: NAC reauth load test; BMCA/holdover drill; jitter budget verification with P95/P99 monitoring; identity/time freeze aligned to change window.

H3: Rollback failure and test/inhibit left active
- Guide words: Sequence (missing step), State (inhibit active, safe‑state not reached), Maintenance (rollback failure).
- Hazard: Orphaned addresses and lingering inhibits silently impair detection/control.
- Consequence vs Step 4: Jeopardizes 0 missed verified alarms and ≥99.95% supervision.
- Safeguards/detection: Automated pre‑flight; inhibit timers; orphan detection.
- Risk: Likelihood 3; Impact 4; Priority 12; Acceptability: unacceptable.
- Required analyses and gates: Timed backout drills; golden‑image/firmware checksum; dual‑control approvals at rollback gates.

H4: Inadequate soak and backout timing
- Guide words: Timing (too short/too long), Human (time pressure), Sequence (out‑of‑order).
- Hazard: Short soak misses intermittent latency spikes; expired backout window strands defects overnight.
- Consequence vs Step 4: Breaches nuisance‑alarm limit and latency targets; latent coverage gaps.
- Safeguards/detection: Real‑time P95/P99 dashboards; anomaly alerts.
- Risk: Likelihood 3; Impact 3; Priority 9; Acceptability: conditionally acceptable only with defined gates.
- Required analyses and gates: Soak‑duration sizing via traffic modeling; pre‑announced backout cutoff; dynamic fire watch during any impairment.

Net judgment. A broad single‑window cutover and unphased identity/time changes are not acceptable without staged proofs, freezes, and soak/rollback gates tied to Step 4 metrics.

## Edge Compute Performance Step7  
*Version 1 • Author: Real-Time Edge Computing & Performance Assurance Expert • Section ID: edge_compute_performance_step7_20250813_214313_c353ce1e*

Step 7 – Risk Assessment: Real-Time Edge Computing & Performance Assurance (identity, time, priority)

This layer bridges OT/IIoT and AI assessments because compute-side contention can erase network QoS gains; therefore we quantify deadline and jitter risks at the edge.

• GPU/CPU priority inversion, saturation, and thermal throttling
Because safety inference shares accelerators/cores and may enter throttled states, cross-tenant bursts cause tail latency beyond the deadline miss budget. Therefore p99 latency and jitter can breach targets despite adequate average throughput. Rating: L4, I4, R16 (unacceptable pre-mitigation). Metrics: risk of p99 >80 ms, jitter p95 >20 ms, headroom <30%; pass/fail: projected fail without isolation data; actual tail distributions required. Needed tests: schedulability and interference profiling under burst and heat. Mitigations: CPU isolation and SCHED_FIFO/RR for safety threads; cgroups hard caps for background agents; GPU MIG/exclusive profiles; pin performance states and disable deep C-states on safety cores.

• Identity-to-QoS drift and policy enforcement gap
Because PriorityClass/Network QoS are not automatically bound to kernel/GPU schedulers, identity-governed pods can run with equal or higher effective priority. Therefore hidden contention paths appear during cutover. Rating: L3, I4, R12. Metrics: divergence between declared QoS and actual CPU shares/GPU occupancy; pass/fail: unproven mapping. Needed tests: policy-to-runtime audit with tracing. Mitigations: admission controller to enforce serviceAccount→cgroup/priority→GPU profile mapping; topic/partition ACLs; pre-deploy conformance gates.

• Time sync degradation and temporal-window breakage
Because PTP holdover and timestamp offload mismatches desynchronize event time, pipelines reorder or stall. Therefore E2E decisions can exceed 100 ms while monitors under-report. Rating: L3, I4, R12. Metrics: risk of sync error >1 ms; out-of-order rate; pass/fail: unverified. Needed tests: PTP failover drills and holdover drift measurement. Mitigations: dual grandmasters, hardware timestamping, monotonic-clock budgeting with alarms on |offset|≥1 ms.

• Backpressure and bounded-queue misconfiguration
Because unbounded/drop-tail buffers create head-of-line blocking, burstiness amplifies jitter. Therefore backlog violates the 100 ms path. Rating: L4, I4, R16. Metrics: queue depth tails, frame/packet loss vs 0.1% SLO; pass/fail: configuration unknown. Needed tests: service-vs-arrival envelope and burst soak. Mitigations: bounded lock-free queues with priority-aware drop, zero-copy paths, per-stage quotas and feedback to capture.

• Orchestrator-induced cold starts/failover jitter
Because rescheduling and image pulls add startup latency, safety pods may miss deadlines during maintenance. Therefore failover time expands. Rating: L3, I4, R12. Metrics: restart to ready time vs <1 s target; pass/fail: TBD. Needed tests: disruption and node-drain drills. Mitigations: PodDisruptionBudgets, taints/tolerations, hot-standby with pre-pulled images and fast health checks.

## Life Safety Functional Safety Code Compliance Step7  
*Version 1 • Author: Functional Safety & Code Compliance Expert • Section ID: life_safety_functional_safety_code_compliance_step7_20250813_215312_29c4bcff*

Step 7 — Risk Assessment (Life Safety Functional Safety & Code Compliance)
Scale: Likelihood 1–5; Impact 1–5; threshold ≥12 intolerable. Focus: listings/approvals, single-fault tolerance, supervised pathways, precedence logic, ≤100 ms timing.

1) Unlisted actuation / precedence breach (guide: Other Than, Unlisted, Conflicting)
Because AI/IoT analytics are not listed initiating devices and dynamic MNS/evac logic can invert fire-alarm precedence, direct actuation or mis-prioritization breaches code. Therefore AHJ rejection or unsafe action/missed alarm is credible.
Rating: L3, I5, Score 15. Quantify: confirm listings and precedence matrix; characterize AI false positive/negative rates. Mitigations: hardwired primacy to UL-listed FA/SC devices (UL 864/2572/UUKL), AI as supplemental gate only, pre-approved cause-and-effect; target score <12 after test.

2) Determinism and timing drift (guide: Latency >100 ms, Desync)
Because shared networks and time-sync drift add nondeterminism, safety decisions can exceed 100 ms and sequences violate required timings. Therefore delayed notification/control is possible.
Rating: L3, I4, Score 12. Quantify: worst-case latency/jitter percentiles and sync bounds under load/fault. Mitigations: segregated deterministic life-safety paths, bounded time source, admission control, watchdog/fail-safe timeouts.

3) Survivability and single-fault violations (guide: Single Point of Failure, Unsupervised Pathway)
Because shared UPS/PoE, non–2-hour pathways, or unsupervised segments create common-cause loss, one fault can silence detection/notification/smoke control. Therefore single-fault and survivability requirements may be breached.
Rating: L4, I5, Score 20. Quantify: availability/fault-tree analysis, survivability map, supervision coverage, bypass audit. Mitigations: 2-hour pathways where required, 2N/N+1 listed power segregation, continuous supervision, cutover permits and independent restoration checks.

4) Change-control and listing integrity (guide: Unverified Update, Documentation Gap)
Because unvetted firmware/config changes alter listings or cause-effect, migration updates can invalidate approvals or mis-actuate. Therefore compliance and safety are at risk.
Rating: L3, I4, Score 12. Verify: vendor listing impact statements; offline regression. Mitigations: formal MOC with listing review, version lock/rollback, staged NFPA 72 integrated tests before go-live.

## Ot Iiot Networking Step8  
*Version 1 • Author: OT/IIoT Cybersecurity & Real-Time Networking Expert • Section ID: ot_iiot_networking_step8_20250813_220159_61c2410f*

Step 8 – Risk Mitigation Recommendations (OT/IIoT Cybersecurity & Real-Time Networking; NAC/PTP/QoS focus)

These P1 controls directly enforce Step 4 targets and retire Step 7 High/Critical items concentrated on priority determinism, time integrity, and identity continuity during live cutover.

1) Deterministic priority plane (QoS/TSN)
Because life‑safety must preempt, implement auditable DSCP EF for life‑safety events, LLQ strict‑priority at every hop, TSN Qbv/Qci where supported, WRED disabled for EF, storm control, and verified VLAN‑to‑queue mappings; preserve DSCP and normalize MTU/MSS across WAN/VPN and LTE/5G. Since misrouting and congestion drive jitter and loss, add policy‑based routing for life‑safety conduits and enforce BACnet segmentation to contain broadcasts. Validate with alarm‑storm plus broker failover and cutover drills; demonstrate P95 ≤80 ms, P99 ≤100 ms, jitter ≤10 ms, loss ≤0.1%, failover ≤1 s, and track p99.9 and queue depth. Addresses Misrouted, Slower, Burst, Jittery, Congested, Out‑of‑order. Aligns with DiffServ, IEEE 802.1Qbv/Qci.

2) Resilient and secure time (PTP)
Because event ordering and control loops depend on tight sync, deploy dual independent PTP grandmasters with GNSS and holdover, boundary clocks per building, explicit BMCA priorities, domain isolation, ACLs on PTP multicast, and MACsec on time segments; keep NTP tertiary and exclude PTP from cellular paths. Since desync is silent, continuously monitor offset/jitter and asymmetry with alerting within one minute. Validate by forced GM failover and asymmetry injection; verify ordering under peak. Addresses Drifted, Desynchronized, Out‑of‑order, Spoofed, Corrupted. Aligns with IEEE 1588v2/802.1AS.

3) Identity‑driven access with cutover‑safe NAC
Because misclassification can isolate life‑safety devices, enforce 802.1X EAP‑TLS with automated enrollment and short‑lived certs, on‑site OCSP stapling and CRL caching, and microsegmentation with protocol allowlists; enable NAC maintenance mode that fails open only to a restricted life‑safety VLAN. Since outages are probable during migration, test RADIUS loss, profiling errors, and switch reloads; prove 100% life‑safety reachability, certificate issuance/rotation within 24 hours, and NAC fault MTTR ≤15 minutes. Addresses Unauthorized, Unauthenticated, Bypassed, Isolated, Misconfigured, Stale. Aligns with IEC 62443, NIST SP 800‑82.

4) Gap closures essential to de‑risk cutover
Because identity and priority depend on underpinning services, deploy active‑active broker/controller HA with fast convergence and DoS‑resilient fronting, PKI with EST enrollment, offline root and HSM‑backed issuing CAs, and BACnet/SC segmentation to reduce broadcast. Since backup links can skew latency, enforce DSCP preservation and MSS clamp on LTE/5G, and exclude PTP from cellular routing. Validate with failover drills; actual throughput and cache hit rates require collection during pilots. Addresses Overloaded, Partitioned, Incompatible, Unsafe default, Stale.

Data required for acceptance: audited device‑to‑queue maps, per‑hop latency and jitter distributions, PTP offset/jitter trends, OCSP/CRL availability, and failover timings; exact figures to be obtained from lab and building‑level pilots.

## Ai Fire Analytics Step8 Mitigations  
*Version 1 • Author: AI Fire Detection & Analytics Risk Expert • Section ID: ai_fire_analytics_step8_mitigations_20250813_221010_97b74696*

Step 8 – AI Fire Detection & Predictive Analytics: enforceable mitigations, tests, and commissioning gates

Because Step 7 exposed unacceptable AI-driven actuation risks, we anchor controls in hardwired primacy, time integrity, and safe fallback so that HVAC, access/egress, and evacuation only act on trustworthy signals. Therefore the items below translate hazards into design requirements, acceptance tests, and go-live gates aligned with NFPA 72, UL 268, and functional safety practices (IEC 61508).

• Dual-confirmation gating with hardwired primacy is required because AI false positives under glare/steam can misdrive smoke control and messaging (Guide words: Quality, Environment, Human, Sequence). Design: two-of-N with listed detectors/manual stations primary; AI contributes only when confidence is calibrated (ECE-bounded), with abstain, temporal hysteresis, rate limits, per-zone alarm budgets, and interlocks that block AI-only actuation. Tests/gates: site shadow-mode ROC against Step 4 targets, nuisance-injection and HIL validation, zero uncontrolled evacuations in commissioning. Ratings: Baseline L5 I5 R25; Residual L3 I4 R12, justified by diversity and interlocks; Priority immediate; Effort moderate.

• Time-integrity and freshness enforcement is mandatory because stale, duplicated, or misrouted streams after switch migrations cause wrong sequencing (Guide words: Timing, Direction/Flow, Quantity). Design: PTP lock gating, per-message time windows, monotonic timestamps and sequence numbers, duplicate/stale drops, camera health telemetry and watchdogs; hold commands unless time-integrity is green. Tests/gates: chaos time-sync breaks, induced frame drops, duplicate MQTT, verify abstain-and-fallback and 99.9th percentile latency <100 ms. Ratings: Baseline L4 I4 R16; Residual L2 I4 R8; Priority immediate; Effort moderate.

• Model governance, drift control, and commissioning mode are essential because construction dust, relighting, and threshold tweaks shift error tradeoffs (Guide words: Quality, Environment, Human, Sequence). Design: signed artifacts, canary plus shadow with rollback, online drift and ECE monitors, periodic synthetic-smoke revalidation, bounded dynamic thresholds, human-in-the-loop for low confidence, and adversarial/spoofing resilience (secure transport, integrity checks, device attestation, flicker tests). Tests/gates: acceptable ECE and shadow concordance, capped nuisance budget, zero uncontrolled evacuations. Ratings: Baseline L4 I4 R16; Residual L3 I4 R12; Priority high; Effort moderate-high.

• Tail-latency and overload control at the edge is needed because event storms and hot paths inflate inference beyond <100 ms, masking fast-onset flame (Guide words: Timing, Quantity, Sequence). Design: capacity headroom, admission control, priority lanes for life-safety, backpressure, circuit breakers, watchdog-triggered safe fallback to detector-only logic, and stateless restart to known-safe. Tests/gates: soak and burst tests to 99.9th latency target with graceful degradation demonstrated. Ratings: Baseline L4 I4 R16; Residual L2 I4 R8; Priority high; Effort moderate.

Note: Ratings are expert estimates pending site data; acceptance requires site-specific validation per the above gates.

## Evacuation Human Factors Step8 Mitigations  
*Version 1 • Author: Evacuation Modeling & Mass Notification Human Factors Expert • Section ID: evacuation_human_factors_step8_mitigations_20250813_222657_72d3c456*

Step 8 Mitigations — Evacuation Routing, Mass Notification, Human Factors (targets Step 7 Critical/High)

Hazard 1: PAVA intelligibility collapse under smoke‑control noise.
Guide word: Quality/Performance – Unintelligible. Because smoke‑control fans elevate broadband noise and reverberation, SPL may be adequate while STI fails; therefore intelligibility collapses under load. Scenario: During fan‑on pressurization, messages are audible but below STI criteria. Causes: fan noise, door‑leak turbulence, reverberation, untuned AGC/EQ. Consequences: misunderstanding, delayed egress, re‑entry. Existing controls: ECS verified fan‑off only; confirmation pending. Ratings: L=4, I=5, Score=20 (Critical). Mitigations: P1 pre‑cutover run fan‑on STIPA in representative zones against success criteria (STI ≥ 0.50 or ≥ 0.45, per space); retune EQ/AGC, add distributed speakers to raise SNR, simplify bilingual scripts. P1 during cutover monitor noise and switch to short imperative prerecorded phrases; if STI below target, favor tone plus simple bilingual callouts. P2 post‑cutover add acoustic treatment or micro‑zoning if needed.

Hazard 2: Dynamic routing misdirection from stale or conflicting data.
Guide word: Direction/Path – Wrong way. Because stale, conflicting, or lagged inputs can invert optimal paths, ungated updates can misdirect; therefore occupants may be steered into smoke or congestion. Scenario: Dynamic signs or mobile prompts contradict safe egress. Causes: sensor latency/loss, ungated arrows, absent hysteresis. Consequences: crowding, exposure, compliance decay. Existing controls: static egress; dynamic signs supervised status TBD. Ratings: L=3, I=4, Score=12 (High). Mitigations: P1 pre‑cutover implement ready‑to‑route gating with routing hysteresis‑quorum and freshness checks; publish only wheelchair‑safe paths and otherwise auto‑route to refuge with two‑way confirmation; verify bilingual accessibility coverage for voice, text, pictograms, and strobes. Set reroute damping with dwell matched to human reaction time plus a rate‑limit and oscillation breaker; meet ECS ≤ 1 s and signage ≤ 2 s. P1 during cutover supervised reversion to static fallback signage on staleness with visible “static mode” and congruent PAVA/mobile messaging. P2 post validation suites for arrow logic and drills to tune thresholds; exact damping parameters require field data.

Hazard 3: Out‑of‑order sequencing with door release and pressurization.
Guide word: Sequence/Logic – Out‑of‑order. Because route messaging can precede door unlock or stair pressurization without state feedback, egress can stall; therefore entrapment risk increases. Scenario: Route announced before unlock/pressurization, or after reclosure. Causes: unsynchronized interfaces, missing latency budgets, absent state feedback. Consequences: stalled flow, entrapment, abandonment. Existing controls: recall and door release present; linkage to signage unclear. Ratings: L=3, I=5, Score=15 (High). Mitigations: P1 pre‑cutover enforce cross‑system ready‑to‑route gate confirming door unlock, stair pressure within tolerance, and survivable power before route messaging; keep safety‑critical signaling within the 100 ms budget. P1 during if handshake breaches budget or states disagree, freeze dynamic guidance and issue nearest‑exit generics. P2 post time‑stamped cutover tests, rollback, and AHJ override freeze.

## Hvac Smoke Control Step8  
*Version 1 • Author: HVAC Smoke Control & Life-Safety Integration Expert • Section ID: hvac_smoke_control_step8_20250813_223703_7a72c214*

Step 8 – Risk Mitigation Recommendations: HVAC Smoke Control & Life-Safety Integration

1) Deterministic life-safety command chain (UUKL priority)
Because BACnet-only paths can miss sub-100 ms and fail under storms, implement hardwired FACP/FSCP relays to life-safety PLCs, VFDs, and dampers with UUKL interlocks and latching manual reset. Therefore enforce a ready-to-route handshake: confirm door release/unlock and safe stair door contacts before pressurization ramp; supervise with heartbeat and timestamped acknowledgments. Block non-life-safety writes to UUKL points; apply QoS/VLAN isolation for monitoring-only; maintain time sync and watchdogs. Priority: Highest. Owners: Fire alarm, controls, electrical. Timeline: wiring/logic pre-cutover; dry run by T-2 weeks. Dependencies: FSCP wiring, panel I/O capacity, BACnet ACLs.

2) Stable pressurization and safe sequencing
Because over/under-pressurization impairs egress or spreads smoke, deploy redundant differential pressure sensors with selection/voting and auto-zero checks. Therefore implement a stair delta‑P clamp at 12–50 Pa with soft-start VFD ramps to respect door force limits. Require end-switch proof‑of‑closure before fan start, proof‑of‑flow after start, and verify fail-safe damper positions. Sequence: door release/ready-to-route → smoke damper actions/exhaust enable → AHU shutdown → pressurization fan start → clamp control. Priority: High. Owners: Mechanical, controls. Timeline: logic and calibration pre‑cutover; 30‑day soak trending. Dependencies: sensor placement, calibration tools.

3) Power ride-through and controlled restarts
Because ATS transfers can trip VFDs and drop pressurization, enable VFD ride‑through, undervoltage tolerance, and controlled restart ramps. Therefore provide UPS for controllers/sensors/FSCP and critical network segments; add brownout detection with restart inhibit, minimum on/off timers, and smoke-control fault bypass per design. Priority: High. Owners: Electrical, controls. Timeline: pre‑cutover integrated electrical tests; witnessed transfers. Dependencies: generator vendor, ATS window, VFD parameters.

4) Cutover safety governance
Because live migration increases misconfiguration and AI false triggers, enforce permits-to-work, change freeze on UUKL points, positive isolation of non‑essential automation, version-controlled cause‑and‑effect, and rollback. Therefore conduct witnessed UUKL functional tests and weekly end‑to‑end latency checks; maintain on‑site fire watch during risky windows. Priority: High. Owners: Commissioning, facilities, IT/OT. Timeline: throughout cutover and 30‑day soak. Note: actual latency and door‑force data must be obtained during testing.

## Physical Security Egress Step 8  
*Version 1 • Author: Physical Security & Egress Control Integration Risk Expert • Section ID: physical_security_egress_step_8_20250813_224527_8fb86718*

Step 8 – Risk Mitigation Recommendations: Physical Security & Egress Control Integration

1) Life‑safety precedence, supervised egress mapping, and FSCP priority
Because network/API paths cannot guarantee sub‑100 ms or listing, the FACP must directly release egress at the edge; therefore use supervised UL 294/864 relays per door as primary with ACS/API as secondary, with mantrap/turnstile bypass, stair re‑entry compliance, and FSCP override priority that defeats lockdown. Guide words: Late, Reverse, Bypass, Conflict. Risk: Delayed/failed unlock from network or policy conflict L=4 I=5 Score=20; residual L=1 I=4 Score=4. Verification: door‑level alarm‑to‑de‑energize ≤100 ms local, ≤500 ms cross‑system; 100% door coverage mapped and witnessed; FSCP override wins in all scenarios.

2) Survivable power and transfer‑tested ride‑through
Because fail‑safe relies on correct de‑energization and continuity, provide dedicated UL 294 PSUs with fire‑trip, supervised outputs, and door‑strike power transfer that defaults to unlock; therefore avoid PoE‑only for life‑safety locks, add local listed power, micro‑UPS, and periodic load/battery tests. Guide words: Power Unavailable, Degraded, Overload, Reverse. Risk: Lock‑in from power anomaly L=3 I=5 Score=15; residual L=1 I=5 Score=5. Verification: mains pull, PoE midspan drop, and UPS transfer tests; measure coil de‑energize time; inhibit relock while any alarm active.

3) Deterministic sequencing for interlocks, turnstiles, elevators, and stair re‑entry
Because mis‑sequence can trap occupants, the mantrap controller shall receive FACP bypass to fail open safely, turnstiles drop arms, elevator Phase I recall engages while card readers are shunted, and stair re‑entry unlocks as required campus‑wide; therefore anti‑tailgate and lockdown rules are suppressed during alarm. Guide words: Sequence, Wrong, Other Than, Conflict. Risk: Entrapment from mis‑sequence L=3 I=4 Score=12; residual L=1 I=4 Score=4. Verification: scripted drills validate order and timing under smoke control; end‑to‑end path timing captured.

4) Live‑cutover guards and edge determinism
Because change windows create event storms and desync, edge controllers must latch fire state and ignore heartbeats, safe‑state on NTP/PTP loss, and rate‑limit non‑life‑safety; therefore dual‑path release (hardwired + API), QoS/ACL allow‑lists for overrides, and AI unlocks only in supervised test mode. Guide words: Quantity, Desync, False Positive/Negative, Intermittent. Risk: Relock during alarm L=3 I=4 Score=12; residual L=1 I=4 Score=4. Risk: AI false unlock L=3 I=3 Score=9; residual L=1 I=3 Score=3. Verification: inject time loss, ACL blocks, and floods; KPI targets: ≥99.99% release availability; median ≤100 ms local, ≤500 ms cross; 100% release auditability.

Resources and schedule: licensed electricians plus ACS/fire technicians; AHJ witnessing; duration on the order of weeks per building—actual data would need to be obtained via site survey.

## Live Cutover Commissioning Safety Assurance Step8  
*Version 1 • Author: Live Cutover & Commissioning Safety Assurance Expert • Section ID: live_cutover_commissioning_safety_assurance_step8_20250813_225251_f55e2f0e*

Step 8 Mitigations – Live Cutover & Commissioning Safety Assurance (SWIFT-linked)

1) Dual-control gated MOP, supervised bypass, and go/no-go with rollback
- Why this is needed: Mis-sequencing and inhibits left on elevate life-safety exposure during live work; therefore procedural rigor must neutralize Sequence and State hazards.
- Hazards addressed (guide words): Sequence (skipped, out-of-order), State (inhibit active, fail-open), Human Factors (handover error), Security (unauthorized change).
- Controls: Dual-authorization MOP with hold points and witnessed sign-offs; permit-to-work for any override; time-bounded supervised bypass with auto-expiry, annunciation, and dynamic fire watch; preflight gates requiring supervision uptime ≥ proposed threshold, ready-to-route handshakes, shadow-mode AI stability, and staged rollback assets.
- Rollback triggers: Any coverage loss, P95 latency exceeding 100 ms, failed handshake, or unexpected alarm storm.
- Risk rating: Now L4 I4 = 16; Target L2 I3 = 6. Priority High.
- Owners and timing: Cutover Manager, AHJ/Owner rep, FLS Lead; schedule freeze and rehearsal required; exact dates to be confirmed per window.

2) Parallel run with one-way gateways, hardwired precedence, deterministic swap
- Why this is needed: Continuous coverage demands functional redundancy while preventing cross-talk; therefore Direction/Flow and Timing risks require engineered isolation and determinism.
- Hazards addressed: Direction/Flow (wrong target, wrong route), Timing (>100 ms, jitter), Quantity (duplicate, flood), Interface (mapping error).
- Controls: Legacy primary; new system in shadow via one-way event gateways; hardwired precedence for notification and smoke control; hardened time sync (PTP profile selection, GNSS holdover, BMCA tuning) and QoS with P99 monitors and alarms; endpoint enrollment gates with whitelists and rate limiting; canary then segmented cutover with reversible windows and ready-to-route confirmations.
- Risk rating: Now L5 I4 = 20; Target L2 I4 = 8. Priority High.
- Owners and timing: FLS Engineer, Network Lead, Controls Lead; per-building windows after canary; schedule to be confirmed.

3) Proven rollback and survivability with witnessed integrated tests
- Why this is needed: Survivability and recoverability control catastrophic outcomes; therefore Maintenance and Security hazards must be closed before decommissioning legacy.
- Hazards addressed: Maintenance (rollback failure, firmware mismatch), Security (unsigned firmware), Interface (certificate expired), Environment (EMI), Backup comms impairment.
- Controls: Golden configuration and version pinning with signed artifacts; offline-tested rollback media and timed checkpoints; validated spares; exercised backup comms (DAS, LTE, satellite); witnessed IST/SAT/FACT and cause-and-effect pass criteria prior to legacy decommissioning.
- Risk rating: Now L3 I5 = 15; Target L2 I3 = 6. Priority High.
- Owners and timing: QA/Config Manager, Security Lead, Comms Lead; artifact freeze and start-of-window failover test; immediate backout on criteria miss.

## Real Time Edge Performance Controls Gap Addendum  
*Version 1 • Author: Real-Time Edge Performance Assurance Expert • Section ID: real_time_edge_performance_controls_gap_addendum_20250813_230004_ac21de45*

Step 8 – Gap Addendum: Real‑Time Edge Performance Controls (deterministic <100 ms)

1) Data‑plane I/O determinism and NIC scheduling. Because Linux defaults (irqbalance, GRO/LRO, qdisc, NAPI budget) add jitter, tails rise under storms. Therefore dedicate RX/TX cores, pin IRQ/RPS/XPS, bound interrupt coalescing, prefer host‑networking or SR‑IOV for safety pods, and use zero‑copy paths (e.g., AF_XDP/DPDK where feasible); set qdisc to latency‑friendly with DSCP mapping aligned to safety QoS. So packet/frame loss stays <0.1% and stage latency fits p99 <80 ms, jitter p95 <20 ms. Risk: pre L4 I4 R16; post L2 I3 R6. Validate with sustained line‑rate and mixed‑burst generators; actual NIC/NAPI metrics need to be obtained.

2) GC/allocator and per‑frame allocation control. Because GC pauses and heap fragmentation drive p99.9 spikes, safety code must avoid managed pauses. Therefore move hot path to non‑GC languages or real‑time GC modes, pre‑allocate pools/ring buffers, use fixed‑size message structs, and pin a known allocator; forbid per‑frame malloc/new. So inference and ingest threads remain below budgets under load. Risk: pre L4 I4 R16; post L2 I2 R4. Validate via allocation tracing and pause profiling; pass gate is zero GC in critical sections.

3) Container runtime and cgroup throttling guards. Because CFS quota throttling and sidecar hops insert periodic stalls, tails appear despite CPU pinning. Therefore use cpusets with quota‑throttle disabled for RT pods, SCHED_FIFO with RLIMIT_RTPRIO, minimal sidecars, host‑networking for safety paths, and isolate containerd/telemetry on non‑RT cores. So sched delay shrinks and no uncontrolled deadline misses occur. Risk: pre L3 I4 R12; post L2 I2 R4. Evidence: throttled_time≈0 and bounded context switches; actual values require measurement.

4) Thermal/power throttling prevention with PTP‑locked scheduling. Because DVFS and thermal derating silently slow compute, tails surge during cutover. Therefore lock CPU governor to performance, set fixed GPU clocks, monitor throttle flags, and trigger backpressure‑safe degradation before throttling; keep UPS/PoE margins and thermal headroom. So p99 remains <80 ms while PTP‑stamped stages preserve ordering. Risk: pre L3 I5 R15; post L2 I3 R6. Validate with thermal soak and brownout simulation; obtain throttle telemetry.

5) Tail‑latency SLO observability and enforcement. Because budgets must be enforced at runtime, not just designed, monitoring must drive control. Therefore implement per‑stage SLOs and p99.9 tracking with budget‑kill/late‑drop, eBPF scheduling delay tracing, synthetic probes, and ready‑to‑route gates; integrate with blue‑green/canary perf gates. So 99.995% <100 ms and zero uncontrolled misses during cutover. Risk: pre L4 I4 R16; post L2 I3 R6. Tests: chaos/latency injection and multi‑day soak; exact durations TBD.

Administrative hooks: change freeze on safety nodes, AHJ‑witnessed failover drills, and safety‑case traceability tying these controls to life‑safety codes. Effort: medium overall; sprint‑level planning TBD.

## Life Safety Functional Safety Code Compliance Step 8  
*Version 1 • Author: Functional Safety & Code Compliance Expert • Section ID: life_safety_functional_safety_code_compliance_step_8_20250813_230812_c73fbe95*

Step 8 Mitigations – Life Safety Functional Safety & Code Compliance

• UUKL hardwired primacy, survivability, and safe states (Loss of Comms, Desync, Single/Common Cause). Because network-only control can fail non-deterministically, require all safety-critical initiating-to-output chains to traverse UL 864-listed FACP/FAPU with UUKL-listed I/O; network overlays are non-authoritative. Therefore provide code-required pathway survivability, fully supervised circuits, and segregated N+1/2N power with brownout ride-through; on loss of supervision drive to a documented safe-state truth table (smoke control to design-safe modes, releasing inhibited, egress unlocked, notification local-only if networks fail).

• Listings boundary and change control (Unlisted Component, Documentation Gap). Because listings and approvals are invalidated by unverified elements, publish a listing boundary matrix mapping each component/interface to its UL/EN category and acceptance method. Therefore block unlisted items in safety-critical paths absent formal variance; enforce MOC with dual approval, configuration baselines, secure boot and signed firmware; trigger reacceptance testing whenever listed behavior could change.

• AI/IoT as supplemental with two-of-N gating and safe-degrade (Model Drift, False Pos/Neg, Unverified Update). Because algorithms are not within life-safety listings, designate AI as supplemental; require two-of-N or cross-technology confirmation for actuation and route early warning to pre-alarm. Therefore mandate offline validation on representative datasets, signed and rollback-capable releases, proof-test intervals, and live KPIs that auto-quarantine AI on drift/nuisance; if processing exceeds the 100 ms budget, treat AI as advisory only.

• Performance and timing enforcement (Latency >100 ms, Jitter, Time Desync). Because deterministic timing is a safety requirement, define an end-to-end latency/jitter budget and instrument time-stamped acceptance tests; require PTP/NTP with holdover and alarms on desync; apply QoS and rate limiting; if budget is exceeded, degrade to local hardwired control.

• AHJ-governed commissioning and cutover (Bypass Left In, Out-of-order). Because acceptance, survivability, and timing must be demonstrated, implement scripted, repeatable tests with captured timings; schedule AHJ-witnessed events pre-cutover, at cutover, and post-change. Therefore use expiring bypass permits with supervision and removal checkouts; stage parallel hardwired continuity before migration; define freeze windows and a rollback plan. Resourcing: FPE lead, OEM panel tech, network engineer, commissioning agent; final schedule and durations require site verification.

## Objective Achievement Assessment  
*Version 1 • Author: Live Cutover & Commissioning Safety Assurance Expert • Section ID: objective_achievement_assessment_20250813_231911_6fa12a5a*

Step 9 – Objective Achievement Assessment (Cutover-focused)

Alignment to Purpose and Success Criteria
Because Step 3/4 demand uninterrupted life-safety and strict SLOs, Step 8 mitigations are necessary but insufficient without witnessed, campus-representative proofs. Therefore acceptance will rely on the following gates, each traceable to guide words and risk ratings.

Residual risks, evidence gaps, and acceptance gates
1) Timing/jitter during load and failover (Timing: >100 ms, jitter, timeout; Sequence: race). Risk L3, I4, Priority 12. Gate 1: demonstrate P95 ≤100 ms, P99 ≤150 ms under 10k-endpoint simulated traffic with grandmaster loss, link flap, and controller failover; continuous P99 telemetry and packet capture required (actual data to be obtained).
2) Correct cause-and-effect routing for smoke control and mass notification (Interface: mapping error; Direction: wrong route; Sequence: out-of-order). Risk L2, I5, Priority 10. Gate 2: witnessed IST/FACT for each critical AHU/damper and notification zone using device stimulators; signed as-built exports and hash-locked release packages.
3) Safe-state, AI behavior, and rollback reliability (State: inhibit active/degraded; Quality: misclassified; Maintenance: rollback failure). Risks: State L3 I4 P12; AI L3 I3 P9; Rollback L2 I4 P8. Gate 3: 24 h shadow-run meeting ≤1 nuisance alarm/24 h, zero missed verified alarms, auto-expiring inhibits verified, and timed rollback dry-run with complete audit trail.
4) Backup comms continuity across DAS/LTE/satellite (Interface: certificate expired; Environment: EMI/power loss; Security: unauthorized change). Risk L2, I4, Priority 8. Gate 4: end-to-end failover drills for radios and MNS across at least two buildings, including UPS transfer and DAS amplifier outage.

Acceptability and Go/No-Go
Because residual risks exceed tolerance without evidence, declare Conditional Go for one canary building once Gates 1–4 pass locally under dynamic fire watch. Therefore Campus-wide remains No-Go until multi-building replication achieves Step 4 SLOs with independent witnessing.

Prioritized actions and owners
High: Gate 1 (Network Eng, Controls); Gate 2 (Controls, Commissioning Agent); Gate 3 (Operations, AI Lead, Change Manager); Gate 4 (Radio/DAS Lead). Medium: campus traffic simulation, comms failover red-team, AI threshold Monte Carlo, digital-twin latency modeling.

Confidence and residual risk
Confidence is Moderate now because campus-scale proofs are pending. Confidence becomes High after all gates are witnessed and residual risks are shown ALARP against Step 4 tolerances.

