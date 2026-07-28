"""Shape validation (프롬프트 §15 형상). Fast subset — the full report is
generated separately because silhouette rasterisation is slow."""
import pytest
from biogen.preset_compiler import compile_preset
from biogen.shape_metrics import proportion_error, landmark_error, lod_silhouette_iou


@pytest.mark.parametrize("taxon_id", ["oncorhynchus_mykiss", "hippocampus_kuda"])
def test_generator_honours_its_own_proportions(taxon_id):
    """The loft must realise the depth/width ratios the preset asked for.
    Length is standard length — the caudal fin extends past it by design."""
    p = proportion_error(compile_preset(taxon_id, seed=1))
    assert p["length_rel_error"] < 0.02, p
    assert p["depth_rel_error"] < 0.05, p
    assert p["width_rel_error"] < 0.05, p


@pytest.mark.parametrize("taxon_id", ["oncorhynchus_mykiss", "melanocetus_johnsonii"])
def test_girth_profile_is_followed(taxon_id):
    l = landmark_error(compile_preset(taxon_id, seed=1))
    assert l["stations"] >= 4
    assert l["mean_rel_error"] < 0.10, l


def test_lod_preserves_silhouette():
    """Gate G8 tolerance: decimation must keep the outline that identifies the
    animal at distance. LOD1 should be visually identical."""
    iou = lod_silhouette_iou(compile_preset("clupea_harengus", seed=1), res=120)
    assert iou[0] == pytest.approx(1.0)
    assert iou[1] > 0.99, iou
    assert iou[3] > 0.80, iou
    # and it must degrade monotonically — a coarser tier cannot match better
    assert iou[1] >= iou[2] >= iou[3], iou
