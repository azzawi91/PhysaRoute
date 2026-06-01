// =============================================================================
// Copyright (c) 2026 Mustafa Mazzawi.  All rights reserved.
//
// This file is part of the PhysaRoute reference implementation accompanying
// the manuscript "PhysaRoute: Slime-Mold-Inspired Adaptive Routing for
// Energy-Efficient and Reliable Wireless Body Area Networks in Healthcare IoT"
// (IEEE Internet of Things Journal, under review).
//
// All rights reserved.  No part of this file may be copied, redistributed, or
// reused without the prior written permission of the author.  See LICENSE for
// the full terms.  Contact: mazzawi1991@gmail.com
// =============================================================================
// Main builder for the PhysaRoute manuscript.
// Composes the .docx file by stitching together front matter, body sections,
// figures, tables, and references.

const fs = require("fs");
const H = require("./build_paper_part1.js");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, LevelFormat, HeadingLevel, WidthType, ShadingType,
  BorderStyle, PageNumber, Footer, Header,
  run, it, bd, sub, sup, p, pf, h1, h2, h3, eq, bullet, caption,
  tableCell, image,
} = H;

// ===========================================================================
// FRONT MATTER
// ===========================================================================

const titlePara = new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { before: 0, after: 200 },
  children: [
    new TextRun({
      text: "PhysaRoute: Slime-Mold–Inspired Adaptive Routing for Energy-Efficient and Reliable Wireless Body Area Networks in Healthcare IoT",
      font: H.FONT, size: 32, bold: true,
    }),
  ],
});
const authorPara = new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { after: 80 },
  children: [
    new TextRun({ text: "Mustafa Mazzawi", font: H.FONT, size: 24 }),
  ],
});
const affilPara = new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { after: 200 },
  children: [
    new TextRun({ text: "[Affiliation], Email: mazzawi1991@gmail.com",
                  font: H.FONT, size: 20, italics: true }),
  ],
});

const abstractHead = new Paragraph({
  spacing: { before: 120, after: 60 },
  children: [new TextRun({ text: "Abstract—", font: H.FONT, size: 20, bold: true, italics: true })],
});

const ABSTRACT_TEXT =
  "Wireless Body Area Networks (WBANs) are the connective tissue of contemporary " +
  "healthcare Internet-of-Things (IoT) deployments, ferrying physiological telemetry " +
  "from on-body sensors to clinical endpoints. Yet the fabric they ride on is hostile: " +
  "patient mobility, postural shadowing, time-varying body losses, and severe energy " +
  "budgets jointly erode the reliability, latency and lifetime guarantees that " +
  "life-critical applications demand. Conventional table-driven and on-demand routing " +
  "protocols, as well as recent metaheuristic schemes, treat path discovery as a " +
  "static optimization problem and re-converge slowly when the body channel changes. " +
  "This paper proposes PhysaRoute, an adaptive WBAN routing protocol whose update " +
  "rule is borrowed from the foraging behavior of the acellular slime mold Physarum " +
  "polycephalum. Each candidate link is modeled as a biological tube with a scalar " +
  "conductance that grows under sustained, healthy flow and decays under disuse, " +
  "channel degradation, or energy depletion. A multi-objective fitness term blends " +
  "expected residual energy, packet delivery probability, body-shadowing risk, and " +
  "criticality-weighted delay; the resulting reinforcement-and-pruning dynamic " +
  "converges to a sparse, near-optimal multi-path overlay without a global view of " +
  "the network. We derive a Lyapunov-based convergence bound, characterize the " +
  "protocol's communication and computational complexity, and evaluate PhysaRoute " +
  "on a 12-node WBAN testbed model against AODV, M-ATTEMPT, an ACO baseline and a " +
  "PSO baseline across mobility, energy, latency and throughput regimes. PhysaRoute " +
  "improves average packet delivery ratio by 13.6% over AODV and 6.2% over the " +
  "strongest baseline, extends time-to-first-node-death by 1.96× over M-ATTEMPT and " +
  "1.45× over PSO, reduces end-to-end latency by 30–56%, and increases aggregate " +
  "throughput by 25.8%. A clinical case study on intensive-care telemetry shows " +
  "that the protocol meets the IEEE 11073-10101 timing envelope for high-acuity " +
  "vital signs while simultaneously stretching battery service intervals from days " +
  "to weeks. The results suggest that bio-inspired reinforcement-and-pruning " +
  "dynamics are a credible substrate for the next generation of safety-critical " +
  "healthcare IoT.";

const abstractBody = new Paragraph({
  alignment: AlignmentType.JUSTIFIED,
  spacing: { after: 200, line: 240 },
  children: [
    new TextRun({ text: "Abstract—", font: H.FONT, size: 20, bold: true, italics: true }),
    new TextRun({ text: ABSTRACT_TEXT, font: H.FONT, size: 20 }),
  ],
});

const indexTerms = new Paragraph({
  alignment: AlignmentType.JUSTIFIED,
  spacing: { after: 240, line: 240 },
  children: [
    new TextRun({ text: "Index Terms—", font: H.FONT, size: 20, bold: true, italics: true }),
    new TextRun({
      text: "Wireless body area networks, Internet of Things for healthcare, " +
            "bio-inspired routing, Physarum polycephalum, slime mold computing, " +
            "energy-efficient protocols, adaptive networks, remote patient monitoring, " +
            "intensive-care telemetry.",
      font: H.FONT, size: 20,
    }),
  ],
});

// ===========================================================================
// I. INTRODUCTION
// ===========================================================================

const intro = [
  h1("Introduction", "I"),
  pf(bd("R"), run("emote and continuous monitoring of patient physiology has moved from a research curiosity to a clinical line item. The combination of low-power wireless radios, miniaturized biosensors, and cloud-side machine learning has produced a new operating model in which the patient — not the bed, the ward, or the hospital — is the unit of observation. The narrow band of technology that makes this possible is the "), it("Wireless Body Area Network"), run(" (WBAN), a personal-area mesh of on-body or in-body sensors that report to a wearable gateway, which in turn relays into the broader healthcare Internet of Things (IoT) [1]–[3]. The WBAN is therefore the first hop in nearly every cyber-physical chain that touches a contemporary patient.")),
  p("From a networking standpoint, however, the body is a singularly hostile substrate. Tissue absorbs the 2.4 GHz ISM band aggressively, and even small postural changes — a turned shoulder, a folded arm, a roll in bed — produce transient shadowing events that can drop link gains by 25–40 dB in milliseconds [4]. Patient motion forces continual topology change. Sensor batteries are measured in milliamp-hours rather than watt-hours; a single avoidable retransmission can shorten service life by hours. And the data riding on top of these links is, by definition, safety-critical: a missed VT alarm, a delayed glucose excursion, a corrupted ECG complex can all end in patient harm."),
  p("Routing protocols designed for general-purpose ad-hoc networks fit the WBAN environment poorly. AODV-class on-demand schemes [5] re-discover paths after every disruption, paying a control-plane tax that the body channel renews more frequently than the protocol can absorb. Cluster-head schemes such as LEACH [6] and its WBAN-tuned descendants amortize energy across nodes but assume a degree of topological stationarity that body-worn radios do not possess. Recent metaheuristic approaches — ant colony optimization (ACO) [7], particle swarm optimization (PSO) [8], grey wolf optimization, whale optimization — improve on energy and lifetime metrics, yet they almost universally treat route selection as a one-shot global search whose output is re-invoked on demand, rather than as an ongoing, locally driven process. The mismatch is structural: body channels do not produce occasional disruptions to be repaired, they produce continuous fluctuation to be tracked."),
  p("This paper takes a different starting point. We turn to the foraging behavior of an organism that has solved an analogous problem for hundreds of millions of years: ", it("Physarum polycephalum"), ", an acellular slime mold whose plasmodial body forms a network of protoplasmic tubes between food sources. As Tero ", it("et al."), " famously showed [9], when the food sources are arranged in the geometry of a city's commuter rail stations, the slime mold reorganizes its tubes into a topology that is statistically indistinguishable from the engineered rail network — and in some cases, more cost-efficient. The mechanism is local, distributed, adaptive, and tolerant of damage: tubes that carry sustained flow thicken, while idle tubes thin and disappear. There is no central controller; there is no global view; there is only a continuous, biology-inspired trade between reinforcement and pruning."),
  p("The core argument of this paper is that this trade — formalized as a discrete-time conductance dynamic over candidate WBAN links — is exactly the right substrate for routing under the body channel. Reinforcement-and-pruning gracefully tracks shadowing without re-running discovery; multi-objective conductance updates entangle energy, reliability, body-shadowing risk and criticality-weighted delay into a single scalar that does not require auction-style coordination; and the mathematics are stable enough to admit a Lyapunov convergence argument."),
  p("We propose PhysaRoute, a routing protocol for healthcare WBANs whose contributions are:"),
  bullet("A formal mapping from Physarum tube dynamics to WBAN link selection that preserves the slime mold's reinforcement/pruning semantics while making the update law executable in fractions of a millisecond on commodity ARM Cortex-M0 microcontrollers."),
  bullet("A multi-objective fitness function that fuses expected residual energy, predicted packet delivery probability under body shadowing, hop-count cost, and clinical criticality of the source node, allowing a single scalar to reflect both network-engineering and patient-safety concerns."),
  bullet("A convergence proof based on a Lyapunov potential constructed over the conductance vector, together with a closed-form upper bound on the number of iterations required to reach an ε-optimal sparse overlay."),
  bullet("An open-source simulation harness and a 12-node WBAN evaluation that compares PhysaRoute against AODV, M-ATTEMPT, an ACO-WBAN baseline and a PSO-Energy baseline across packet delivery ratio, residual energy, end-to-end latency, network lifetime, and aggregate throughput."),
  bullet("A clinical case study on intensive-care continuous telemetry that quantifies the gain in safety-relevant metrics — alarm latency, missed-event probability, and battery service interval — when PhysaRoute replaces a state-of-the-art metaheuristic baseline."),
  p("The remainder of the paper is organized as follows. Section II reviews related work on WBAN routing, bio-inspired networking, and slime mold computing. Section III gives the biological background needed to understand the proposed update rule. Section IV formalizes the system model. Section V develops the PhysaRoute protocol, including pseudocode and design rationale. Section VI provides convergence and complexity analyses. Section VII describes the simulation methodology, Section VIII reports the empirical results, and Section IX presents the ICU clinical case study. Section X discusses limitations and Section XI concludes."),
];

// ===========================================================================
// II. RELATED WORK
// ===========================================================================
const related = [
  h1("Related Work", "II"),
  h2("A. Routing in Wireless Body Area Networks"),
  pf("WBAN routing has matured along two broadly parallel tracks. The first track adapts general-purpose ad-hoc and sensor-network protocols — AODV [5], DSR, LEACH [6], DSDV — to the body channel by adding energy-aware metrics and link-quality estimators. M-ATTEMPT [10] is the canonical example: it constructs an energy-efficient multi-hop tree to a single sink, using residual energy and hop count as the link cost, and switches to direct transmission for time-critical traffic. SIMPLE [11] extends this with a fitness-function-based forwarder selection, and iM-SIMPLE adds on-demand routing for emergency packets. THE-FAME and EERR offer further refinements but inherit the same architectural assumption: a static decision phase followed by a deterministic data phase."),
  p("The second track is purpose-built for body-channel dynamics. Cooperative routing schemes such as Co-LAEEBA [12] and ATTEMPT exploit antenna diversity and relay cooperation to fight postural shadowing, while opportunistic protocols defer the choice of next hop until a packet is ready to forward. Quality-of-service-aware schemes such as DARE-IoT [13] segment traffic into criticality classes and route each class differently. None, to our knowledge, treat routing as a continuous biological reinforcement process."),
  h2("B. Bio-Inspired and Metaheuristic Routing"),
  pf("Bio-inspired metaheuristics have been a fertile source of ad-hoc and IoT routing schemes for two decades. ACO-based protocols [7], [14] use pheromone deposition by virtual ants to bias path selection toward routes that have recently delivered packets successfully. PSO-based protocols [8], [15] cast routing as a swarm-intelligence search over possible cluster-head assignments or path encodings, optimizing a fitness function that typically blends energy and distance. More recent work has applied the grey wolf optimizer (GWO), the whale optimization algorithm (WOA), the artificial bee colony, and a long tail of newer metaheuristics to WBAN cluster-head selection and path planning [16]–[19]."),
  p("The methodological pattern is consistent: an offline optimizer is run periodically over a global view of the network, and its output is downloaded to the data plane until the next optimization cycle. This pattern works well when the network topology changes on a timescale longer than the optimization cycle, but the body channel violates that assumption. PhysaRoute differs by integrating the optimization into the data-forwarding loop itself: each successfully delivered packet updates the conductance of the links it traversed, so the fitness landscape and the path selection co-evolve in real time."),
  h2("C. Slime Mold Computing"),
  pf("Physarum polycephalum has been studied as a substrate for distributed computation since Nakagaki ", it("et al."), " demonstrated maze-solving in 2000 [20]. Tero ", it("et al."), " gave the canonical mathematical model in 2010 [9], showing that a system of tubes whose conductance is updated by a sigmoidal function of the flow they carry converges, under suitable boundary conditions, to networks that resemble the Tokyo rail system. The model has since been applied to the Steiner tree problem, transport network design [21], reinforcement learning [22], optical computing, and bio-engineering. In the networking literature, Physarum-inspired routing has appeared in the context of static wireless sensor networks [23], [24], software-defined networks [25], and unmanned aerial vehicle swarms [26]; in each case the application has emphasized topology design rather than continuous adaptation under hostile, fast-changing channels."),
  p("To our knowledge, PhysaRoute is the first protocol to (i) extend the Physarum dynamic to mobile, energy-asymmetric, safety-critical body-area networks; (ii) augment the conductance update with a multi-objective fitness term that includes patient criticality; (iii) prove convergence under the resulting non-stationary boundary conditions; and (iv) report a quantified evaluation on a clinical scenario."),
  h2("D. Healthcare IoT Architectures"),
  pf("On the systems side, healthcare IoT has consolidated around a three-tier architecture — intra-body sensors, on-body or near-body gateways, and cloud-side analytics — with growing interest in fog and edge intermediaries [27], [28]. Reference architectures from the IEEE 11073 family [29] standardize device semantics, and HL7 FHIR has emerged as the dominant data format on the wire. Concerns about end-to-end privacy, integrity, and resilience have driven proposals for blockchain-anchored audit trails [30], federated learning for edge inference [31], and zero-trust security models [32]. PhysaRoute does not displace any of this; it slots beneath the FHIR/IEEE 11073 application stack as a Tier-1 routing layer and remains compatible with TLS-terminated, FHIR-emitting edge gateways."),
];

// ===========================================================================
// III. BACKGROUND: PHYSARUM POLYCEPHALUM
// ===========================================================================
const background = [
  h1("Background: Physarum Polycephalum and the Tube Model", "III"),
  pf("Physarum polycephalum is a unicellular eukaryote whose vegetative phase, the plasmodium, can grow to span several square meters of substrate while remaining a single coordinated cytoplasmic mass. When food sources are placed at scattered points in its environment, the plasmodium responds by extending protoplasmic tubes between them. Cytoplasm is shuttled through the tubes by rhythmic peristaltic contractions; nutrients and chemical signals diffuse along the same routes."),
  p("The empirical regularity that makes the organism interesting to network science is the way its tube morphology evolves over hours-to-days timescales. Tubes that carry consistent, high-flux protoplasmic flow thicken and become more conductive; tubes that carry little or no flow thin and eventually vanish. The asymptotic morphology, given a fixed set of food sources, is a sparse, low-redundancy network that simultaneously optimizes total tube cost, average path length between food sources, and fault tolerance against tube cuts."),
  p("Tero ", it("et al."), " formalized this behavior with the following model [9]. Let the candidate tube graph be ", it("G = (V, E)"), " with food sources ", it("s"), sub("1"), run(", "), it("s"), sub("2"), run(", … and let "), it("D"), sub("ij"), run(" denote the time-varying conductance of the tube on edge "), it("(i, j)"), run(", "), it("L"), sub("ij"), run(" its length, and "), it("Q"), sub("ij"), run(" the protoplasmic flow it carries. Pressure "), it("p"), sub("i"), run(" at node "), it("i"), run(" is determined by Kirchhoff's current law:")),
  eq("Σ (D_ij / L_ij) (p_i − p_j) = I_i,    where I_i = +I_0 at the source, −I_0 at the sink, 0 elsewhere", 1),
  pf("and the conductance evolves as"),
  eq("d D_ij / d t = f(|Q_ij|) − μ D_ij,", 2),
  pf("where ", it("f(·)"), run(" is a monotone, sigmoidal reinforcement function and "), it("μ"), run(" is a decay rate. The flow itself is the consequence of the pressure solution: "), it("Q"), sub("ij"), run(" = ("), it("D"), sub("ij"), run(" / "), it("L"), sub("ij"), run(") ("), it("p"), sub("i"), run(" − "), it("p"), sub("j"), run("). Tero "), it("et al."), run(" showed that this dynamic is provably convergent for a wide class of "), it("f"), run(" and produces sparse, near-optimal Steiner-like topologies.")),
  p("Three properties of the model are particularly relevant to WBAN routing. ", bd("First"), run(", the dynamic is fully local: the update at edge "), it("(i, j)"), run(" depends only on the flow that edge carries and on its own conductance. "), bd("Second"), run(", the dynamic is naturally fault-tolerant: if a tube is cut, flow is automatically rerouted through whichever surviving tubes have the highest conductance, and the conductance values then re-equilibrate. "), bd("Third"), run(", the dynamic produces a sparse, low-redundancy network: in the asymptote, only the tubes that carry flow survive. The first property maps onto the distributed nature of WBAN routing; the second onto body-shadowing recovery; the third onto the need to keep the active multi-path overlay small enough that a low-power microcontroller can maintain it.")),
];

// ===========================================================================
// IV. SYSTEM MODEL
// ===========================================================================
const sysmodel = [
  h1("System Model and Problem Formulation", "IV"),
  h2("A. Network and Topology"),
  pf("We consider a single WBAN comprising ", it("N"), run(" body-worn sensor nodes "), it("V = {v"), sub("1"), it(", …, v"), sub("N"), it("}"), run(" and a gateway / sink node "), it("g"), run(" worn on the patient's belt or wrist. Each sensor periodically generates physiological data (e.g., ECG, SpO"), sub("2"), run(", glucose, motion) and must deliver it to "), it("g"), run(", which then relays out of the body via Bluetooth Low Energy or Wi-Fi to the wider healthcare IoT. Sensors may communicate directly with "), it("g"), run(" or multi-hop through other sensors. The candidate communication graph "), it("G = (V ∪ {g}, E)"), run(" contains an edge "), it("(i, j)"), run(" whenever the long-term-average received signal strength between "), it("i"), run(" and "), it("j"), run(" exceeds a sensitivity threshold "), it("γ"), sub("min"), run(".")),
  h2("B. Channel Model"),
  pf("We adopt the IEEE 802.15.6 channel model CM3 (on-body to on-body, 2.4 GHz). The instantaneous path loss between nodes ", it("i"), run(" and "), it("j"), run(" is")),
  eq("PL_ij(t) = PL_0 + 10 n_p log10(d_ij(t) / d_0) + S_ij(t)", 3),
  pf("where ", it("PL"), sub("0"), run(" is the reference path loss at "), it("d"), sub("0"), run(" = 0.1 m, "), it("n"), sub("p"), run(" ≈ 3.4 is the path-loss exponent for on-body propagation, "), it("d"), sub("ij"), run(" is the geodesic Euclidean distance between the body-mounted sensors, and "), it("S"), sub("ij"), run(" is a log-normal shadowing term whose standard deviation rises sharply during motion. The packet success probability on edge "), it("(i, j)"), run(" given a transmit power "), it("P"), sub("tx"), run(" is approximated as")),
  eq("P_succ(i,j) = (1 − BER(SNR_ij))^L_pkt", 4),
  pf("with the bit error rate (BER) determined by the physical layer. The protocol layer treats ", it("P"), sub("succ"), run("(i,j) as a measured quantity, exponentially smoothed over a window "), it("W"), run(".")),
  h2("C. Energy Model"),
  pf("Each node has initial energy reserve ", it("E"), sub("0"), run(" (typically 4–10 J for a button-cell-powered sensor). The energy consumed in transmitting an "), it("L"), sub("pkt"), run("-bit packet over distance "), it("d"), run(" is")),
  eq("E_tx(L_pkt, d) = L_pkt (E_elec + ε_amp d^k)", 5),
  pf("where ", it("E"), sub("elec"), run(" ≈ 50 nJ/bit is the electronic transceiver cost per bit and "), it("ε"), sub("amp"), run(" "), it("d"), sup("k"), run(" is the amplifier cost, with "), it("k"), run(" ∈ {2, 4} depending on whether the link is in free-space or multipath regime. Reception of an "), it("L"), sub("pkt"), run("-bit packet costs "), it("E"), sub("rx"), run(" = "), it("L"), sub("pkt"), it(" E"), sub("elec"), run(". Idle listening and the radio start-up energy are folded into a per-second baseline "), it("E"), sub("idle"), run(". A node is declared dead when its residual energy drops below "), it("E"), sub("min"), run(".")),
  h2("D. Traffic Model and Criticality"),
  pf("Each sensor ", it("v"), sub("i"), run(" generates packets with mean rate "), it("λ"), sub("i"), run(" and is associated with a clinical criticality coefficient "), it("c"), sub("i"), run(" ∈ [0, 1] inherited from the data type — ECG carries higher "), it("c"), run(" than activity counts. Criticality enters the routing decision through the fitness function in Section V.")),
  h2("E. Optimization Objective"),
  pf("Let ", it("R"), run(" denote the set of multi-hop routes from sensors to the sink. We seek a routing assignment that maximizes a linear combination of normalized expected lifetime "), it("L̃"), run(", normalized aggregate delivery ratio "), it("D̃"), run(", and normalized criticality-weighted timely-delivery rate "), it("T̃"), run(":")),
  eq("max  J(R) = w_1 L̃(R) + w_2 D̃(R) + w_3 T̃(R)", 6),
  pf("subject to per-link energy and rate constraints. The weights ", it("w"), sub("k"), run(" are deployment-time policy parameters; in the simulations of Section VIII we use "), it("w"), sub("1"), run(" = 0.4, "), it("w"), sub("2"), run(" = 0.4, "), it("w"), sub("3"), run(" = 0.2, which we found to dominate alternative settings on a small grid search. Solving (6) globally is NP-hard for "), it("|V|"), run(" beyond toy sizes; the contribution of PhysaRoute is to provide a distributed, biology-inspired update rule that converges to a high-quality feasible solution in milliseconds.")),
];

// ===========================================================================
// V. PHYSAROUTE PROTOCOL
// ===========================================================================
const protocol = [
  h1("The PhysaRoute Protocol", "V"),
  h2("A. Overview"),
  pf("PhysaRoute maintains, for each candidate edge ", it("(i, j)"), run(" in the WBAN, a scalar conductance "), it("D"), sub("ij"), run(" ∈ ["), it("D"), sub("min"), run(", 1] that summarizes the edge's recent contribution to successful, energy-efficient packet delivery. Every "), it("τ"), run(" milliseconds, each node updates the conductance of its own outgoing edges using only locally observable quantities (packet acknowledgments, residual energy, RSSI, neighbour battery hints piggybacked on the link layer). When a packet is to be forwarded, the next-hop selection uses a softmax over conductances, biased by the multi-objective fitness term. The protocol therefore has no separate route-discovery phase; reinforcement and routing co-occur on every packet.")),
  h3("Fig. 1.  (a) Physarum tubes reorganise toward food sources by reinforcing high-flux paths and pruning idle ones. (b) The same dynamic, applied to a WBAN, biases packet flow onto a sparse overlay of high-conductance links from sensors to the gateway."),
  image("fig_concept_analogy.png", 460, 210),
  caption("Fig. 1.  Slime-mold–to–WBAN analogy."),
  h2("B. Conductance Update Rule"),
  pf("Let ", it("Φ"), sub("ij"), run("(t) denote the observed normalized flow over edge "), it("(i, j)"), run(" in the most recent update window — operationally, the count of successfully acknowledged packets that traversed "), it("(i, j)"), run(" divided by the count of attempted packet transmissions. The update rule is")),
  eq("D_ij(t+1) = (1 − μ) D_ij(t) + α F_ij(t) ψ(Φ_ij(t))", 7),
  pf("where ", it("μ"), run(" ∈ (0, 1) is the decay rate, "), it("α"), run(" > 0 is the learning rate, "), it("F"), sub("ij"), run("(t) ∈ [0, 1] is the multi-objective fitness term defined in (8), and "), it("ψ"), run(" is the sigmoidal reinforcement function ψ(x) = x"), sup("γ"), run(" / (1 + x"), sup("γ"), run("), with "), it("γ"), run(" ≥ 1 a non-linearity exponent. Edges with "), it("D"), sub("ij"), run(" ≤ "), it("D"), sub("min"), run(" are pruned from the active overlay until they are re-discovered by a periodic exploration probe.")),
  h2("C. Multi-Objective Fitness"),
  pf("The multi-objective fitness term is the central design lever of PhysaRoute. It folds four signals that a body-channel routing protocol must respect into a single bounded scalar:"),
  eq("F_ij(t) = β_1 R_j(t) + β_2 P̂_succ(i,j)(t) + β_3 (1 − Ŝ_ij(t)) + β_4 c_j", 8),
  pf("where ", it("R"), sub("j"), run("(t) is the normalized residual energy of the next-hop neighbour, "), it("P̂"), sub("succ"), run("(i,j)(t) is the smoothed packet success probability on the link, "), it("Ŝ"), sub("ij"), run("(t) ∈ [0, 1] is an estimate of the probability that the link will enter a deep shadowing event in the next window (computed from a short-horizon AR(1) predictor over RSSI), and "), it("c"), sub("j"), run(" is the criticality coefficient of the source node. The weights "), it("β"), sub("k"), run(" satisfy Σ "), it("β"), sub("k"), run(" = 1 and may be re-tuned per traffic class. "), it("F"), sub("ij"), run(" is bounded in [0, 1] by construction.")),
  h2("D. Pressure Allocation and Forwarding"),
  pf("Forwarding is decoupled from learning. Given a packet arriving at node ", it("i"), run(" destined for the sink "), it("g"), run(", node "), it("i"), run(" computes a forwarding probability over its current neighbours "), it("N(i)"), run(" using a softmax over conductances:")),
  eq("π(j | i) = exp(D_ij / θ) / Σ_{k ∈ N(i)} exp(D_ik / θ)", 9),
  pf("where ", it("θ"), run(" > 0 is a temperature parameter that controls the exploration / exploitation trade. Small "), it("θ"), run(" yields near-deterministic forwarding to the strongest-conductance neighbour; large "), it("θ"), run(" produces broader randomization and is useful early in protocol life or after an emergency restart. We use "), it("θ"), run(" = 0.1 in evaluation, with a brief startup phase at "), it("θ"), run(" = 0.5 for the first 30 packets per source.")),
  h2("E. Exploration Probes"),
  pf("Pure reinforcement-and-pruning will eventually starve the active overlay of alternative paths. To maintain the protocol's resilience to channel changes that occur after the slime mold has converged, every node periodically (every ", it("τ"), sub("explore"), run(" ≈ 30 s) emits a single exploration probe to a random pruned neighbour. If the probe is acknowledged, the neighbour's conductance is reset to "), it("D"), sub("min"), run(" + ε so it re-enters the active set. This mirrors the well-documented behavior of physarum, which periodically extrudes new pseudopodia even into directions that previously yielded no nutrient.")),
  h2("F. Pseudocode"),
  pf("Algorithm 1 summarizes the per-node operation of PhysaRoute. The algorithm is invoked twice per update window: once on packet arrival (forwarding) and once on window expiry (conductance update)."),
  // Algorithm pseudocode rendered as a monospace-styled paragraph block
  new Paragraph({
    spacing: { before: 120, after: 120 },
    border: { top: { style: BorderStyle.SINGLE, size: 6, color: "000000" } },
    children: [new TextRun({ text: "Algorithm 1   PhysaRoute (per-node)", font: H.FONT, size: 18, bold: true })],
  }),
  new Paragraph({ children: [new TextRun({ text: "1:  Input: candidate neighbours N(i), parameters μ, α, β, θ, τ, τ_explore", font: "Courier New", size: 18 })] }),
  new Paragraph({ children: [new TextRun({ text: "2:  Initialize D_ij ← 0.5  for all j ∈ N(i)", font: "Courier New", size: 18 })] }),
  new Paragraph({ children: [new TextRun({ text: "3:  for every packet p arriving at i destined for g do", font: "Courier New", size: 18 })] }),
  new Paragraph({ children: [new TextRun({ text: "4:    compute π(j|i) ∝ exp(D_ij / θ) over active N(i)", font: "Courier New", size: 18 })] }),
  new Paragraph({ children: [new TextRun({ text: "5:    sample next-hop j* ~ π(·|i); transmit p to j*", font: "Courier New", size: 18 })] }),
  new Paragraph({ children: [new TextRun({ text: "6:    if ACK received then increment Φ_ij*; else increment failure count", font: "Courier New", size: 18 })] }),
  new Paragraph({ children: [new TextRun({ text: "7:  end for", font: "Courier New", size: 18 })] }),
  new Paragraph({ children: [new TextRun({ text: "8:  every τ ms (window expiry):", font: "Courier New", size: 18 })] }),
  new Paragraph({ children: [new TextRun({ text: "9:    for each j ∈ N(i) do", font: "Courier New", size: 18 })] }),
  new Paragraph({ children: [new TextRun({ text: "10:     update F_ij ← β_1 R_j + β_2 P̂_succ + β_3 (1 − Ŝ_ij) + β_4 c_j", font: "Courier New", size: 18 })] }),
  new Paragraph({ children: [new TextRun({ text: "11:     update D_ij ← (1 − μ) D_ij + α F_ij ψ(Φ_ij)", font: "Courier New", size: 18 })] }),
  new Paragraph({ children: [new TextRun({ text: "12:     if D_ij < D_min then mark j as pruned", font: "Courier New", size: 18 })] }),
  new Paragraph({ children: [new TextRun({ text: "13:   end for", font: "Courier New", size: 18 })] }),
  new Paragraph({ children: [new TextRun({ text: "14:   every τ_explore: send exploration probe to random pruned neighbour", font: "Courier New", size: 18 })] }),
  new Paragraph({
    spacing: { after: 120 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: "000000" } },
    children: [new TextRun({ text: "15: end every", font: "Courier New", size: 18 })],
  }),
  h2("G. Architecture and Integration"),
  pf("Fig. 2 places PhysaRoute in the broader healthcare IoT stack. The protocol occupies the routing sub-layer between the IEEE 802.15.6 MAC and the application-level FHIR/IEEE 11073 envelope. Conductance state is held entirely on the sensor side; the gateway needs only to ACK packets and to occasionally redistribute the criticality coefficients ", it("c"), sub("j"), run(" if a clinician changes the patient acuity level. End-to-end security is unchanged: PhysaRoute does not see clear-text payloads and is compatible with the AES-128 link-layer encryption already mandated by 802.15.6.")),
  image("fig_architecture.png", 460, 240),
  caption("Fig. 2.  System architecture: PhysaRoute as a tier-2 routing layer below an FHIR / IEEE 11073 application envelope and above the IEEE 802.15.6 MAC."),
  h2("H. Notation Summary"),
  pf("Table I summarizes the symbols used throughout this section and the next."),
];

// ----- Notation table (Table I) ------------------------------------------------
const TBL_WIDTH = 9000;
const colW1 = [1700, 7300];

function notationRow(sym, desc) {
  return new TableRow({
    children: [tableCell(sym, { width: colW1[0], italics: true }),
               tableCell(desc, { width: colW1[1] })],
  });
}
const tableNotation = new Table({
  width: { size: TBL_WIDTH, type: WidthType.DXA },
  columnWidths: colW1,
  rows: [
    new TableRow({
      children: [tableCell("Symbol", { width: colW1[0], header: true }),
                 tableCell("Meaning", { width: colW1[1], header: true })],
    }),
    notationRow("N",          "Number of body-worn sensor nodes"),
    notationRow("g",          "Gateway / sink node"),
    notationRow("D_ij",       "Conductance of edge (i, j); analogue of Physarum tube thickness"),
    notationRow("Φ_ij",       "Observed normalized flow over edge (i, j) in last window"),
    notationRow("F_ij",       "Multi-objective fitness term for edge (i, j)"),
    notationRow("R_j",        "Normalized residual energy of next-hop j"),
    notationRow("P̂_succ",    "Smoothed packet success probability"),
    notationRow("Ŝ_ij",       "Predicted shadowing probability"),
    notationRow("c_j",        "Clinical criticality coefficient of node j"),
    notationRow("μ, α",       "Conductance decay and learning rates"),
    notationRow("β_k",        "Fitness mixing weights, Σβ_k = 1"),
    notationRow("θ",          "Softmax temperature for forwarding"),
    notationRow("τ, τ_explore","Update window and exploration period"),
  ],
});
const captionTable1 = new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { before: 80, after: 200 },
  children: [new TextRun({ text: "Table I.  Notation used throughout the paper.", font: H.FONT, size: 18, italics: true })],
});

// ===========================================================================
// VI. THEORETICAL ANALYSIS
// ===========================================================================
const analysis = [
  h1("Theoretical Analysis", "VI"),
  h2("A. Convergence"),
  pf("We sketch a Lyapunov argument that the conductance vector ", it("D"), run("(t) ∈ [0, 1]"), sup("|E|"), run(" converges to a fixed point of the update (7) under quasi-stationary channel conditions. Define the potential function")),
  eq("V(D) = (1/2) Σ_{(i,j) ∈ E} (D_ij* − D_ij)^2", 10),
  pf("where ", it("D"), sub("ij"), run("* is the fixed point implicitly defined by "), it("D"), sub("ij"), run("* = (α/μ) "), it("F"), sub("ij"), run(" "), it("ψ"), run("("), it("Φ"), sub("ij"), run("("), it("D"), run("*)). Since "), it("ψ"), run(" is monotone, "), it("F"), sub("ij"), run(" is bounded in [0, 1], and "), it("μ"), run(" > 0, the right-hand side of (7) is a contraction with Lipschitz constant ("), it("1 − μ"), run(") + "), it("αL"), sub("ψ"), run(", where "), it("L"), sub("ψ"), run(" is the Lipschitz constant of ψ. Choosing "), it("α < μ / L"), sub("ψ"), run(" ensures "), it("V"), run("("), it("D"), run("(t+1)) ≤ ρ "), it("V"), run("("), it("D"), run("(t)) for some ρ ∈ (0, 1), so convergence is geometric.")),
  p("The number of iterations to reach an ε-neighborhood of ", it("D"), run("* is therefore "), it("O"), run("(log(1/ε) / log(1/ρ)). For our default parameters (μ = 0.05, α = 0.02, "), it("L"), sub("ψ"), run(" ≈ 1, ε = 10"), sup("−3"), run(") this evaluates to roughly 70 update windows, which at "), it("τ"), run(" = 100 ms is 7 s — an order of magnitude faster than typical posture-change events.")),
  h2("B. Communication and Computational Complexity"),
  pf("Per update window, each node performs ", it("O"), run("(|"), it("N"), run("("), it("i"), run(")|) arithmetic operations to refresh "), it("F"), sub("ij"), run(" and "), it("D"), sub("ij"), run(". The dominant per-packet cost is the softmax sample, which is also "), it("O"), run("(|"), it("N"), run("("), it("i"), run(")|). For the typical WBAN of "), it("N"), run(" = 8–12 nodes, |"), it("N"), run("("), it("i"), run(")| ≤ 5, so the per-packet cost is dozens of ARM cycles. PhysaRoute introduces no broadcast traffic beyond what ACK and exploration probes already consume; its control overhead is "), it("O"), run("(N) per "), it("τ"), sub("explore"), run(", versus "), it("O"), run("(N"), sup("2"), run(") for AODV under churn.")),
  h2("C. Stability Under Boundary Drift"),
  pf("In the WBAN setting the boundary conditions of the Physarum dynamic — the ", it("F"), sub("ij"), run(" terms — drift in time as residual energy decays and shadowing patterns evolve. The contraction argument above survives this drift provided that the rate of change of "), it("F"), sub("ij"), run(" is small relative to (1 − ρ). Empirically, the worst-case drift induced by a postural change is ≈ 0.3 in "), it("Ŝ"), sub("ij"), run(" within a single window, which our parameter choice handles without oscillation; this is borne out by the convergence trajectories in Fig. 5.")),
];

module.exports = {
  titlePara, authorPara, affilPara, abstractBody, indexTerms,
  intro, related, background, sysmodel, protocol, analysis,
  tableNotation, captionTable1,
};
