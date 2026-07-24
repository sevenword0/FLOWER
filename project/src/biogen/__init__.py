"""biogen — taxon-agnostic procedural biology pipeline.

The target biological group is defined ONCE in config/target_taxon.yaml and
resolved to an adaptation profile at runtime. No taxon literal appears in this
package (규칙 17 / Gate G9). Swapping the config value retargets the whole
pipeline: module map, source routing, bases, and generation.
"""
__version__ = "0.1.0"

from .taxon_profile import TaxonProfile, load_profile  # noqa: F401
