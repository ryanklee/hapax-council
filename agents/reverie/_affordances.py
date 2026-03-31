"""Reverie affordance registration — shader nodes, content types, legacy capabilities.

The system discovers which visual effects are relevant to each impingement
via cosine similarity in Qdrant, not prescribed semantic mappings.
"""

from __future__ import annotations

import logging

log = logging.getLogger("reverie.affordances")

# 12 shader node affordances — expressive descriptions for embedding
SHADER_NODE_AFFORDANCES = [
    ("node.noise_gen", "procedural texture, substrate, continuous field"),
    ("node.reaction_diffusion", "self-organizing emergent spatial patterns, regime-sensitive"),
    ("node.colorgrade", "palette regime, color world shift, atmospheric tone"),
    ("node.drift", "spatial displacement, coherence modulation, gentle warping"),
    ("node.breathing", "rhythmic pulse, expansion and contraction, life cadence"),
    ("node.feedback", "temporal persistence, afterimage, dwelling trace"),
    ("node.content_layer", "content materialization, imagination surface, phenomenology"),
    ("node.postprocess", "final composition, enclosure, vignette, sediment"),
    ("node.fluid_sim", "directional flow with inertia, vorticity, viscous movement"),
    ("node.trail", "motion history, velocity as visual thickness, temporal accumulation"),
    ("node.voronoi_overlay", "spatial partitioning, organic boundaries, cellular territory"),
    ("node.echo", "discrete temporal copies, ghosting, fading repetition"),
]

# 5 content type affordances
CONTENT_TYPE_AFFORDANCES = [
    ("content.camera_feed", "live spatial perception, room awareness, presence"),
    ("content.imagination_text", "narrative fragment, poetic image, dwelling thought"),
    ("content.imagination_image", "resolved visual content, concrete reference"),
    ("content.waveform_viz", "acoustic energy shape, sound made visible"),
    ("content.data_plot", "structured information, measurement, trend"),
]

# Legacy capabilities for backward compat with DMN dispatch
LEGACY_AFFORDANCES = [
    ("shader_graph", "Activate shader graph effects from imagination"),
    ("visual_chain", "Modulate visual chain from stimmung/evaluative"),
    ("fortress_visual_response", "Visual pipeline for fortress crises"),
]


def build_reverie_pipeline():
    """Build the affordance pipeline with all Reverie affordances registered in Qdrant."""
    from agents._affordance import CapabilityRecord, OperationalProperties
    from agents._affordance_pipeline import AffordancePipeline

    p = AffordancePipeline()

    all_affordances = SHADER_NODE_AFFORDANCES + CONTENT_TYPE_AFFORDANCES + LEGACY_AFFORDANCES
    registered = 0
    for name, desc in all_affordances:
        ok = p.index_capability(
            CapabilityRecord(
                name=name,
                description=desc,
                daemon="reverie",
                operational=OperationalProperties(latency_class="realtime"),
            )
        )
        if ok:
            registered += 1

    log.info("Registered %d/%d Reverie affordances in Qdrant", registered, len(all_affordances))
    return p
