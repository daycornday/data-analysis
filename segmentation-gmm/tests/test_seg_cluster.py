import numpy as np
from sklearn.metrics import adjusted_rand_score

from segmentation_gmm.synth import FEATURES, SEGMENTS, make_users
from segmentation_gmm.compose import shares_from_counts, clr, drop_last
from segmentation_gmm.cluster import fit_gmm, bic_curve, choose_k, kmeans_labels, segment_profile


def _planted(seed=3):
    df = make_users(3000, seed=seed)
    shares = shares_from_counts(df[FEATURES].to_numpy())
    return df, shares, clr(shares)


def test_synth_sizes_match_plan():
    df = make_users(6000, seed=0)
    share = df["true_segment"].value_counts(normalize=True)
    for name, spec in SEGMENTS.items():
        assert abs(share[name] - spec["size"]) < 0.03


def test_bic_recovers_planted_k():
    _, _, z = _planted()
    assert choose_k(bic_curve(drop_last(z), range(2, 7))) == len(SEGMENTS)


def test_clr_gmm_recovers_planted_segments():
    df, shares, z = _planted()
    labels = fit_gmm(drop_last(z), len(SEGMENTS)).predict(drop_last(z))
    assert adjusted_rand_score(df["true_segment"], labels) > 0.8


def test_clr_gmm_beats_raw_kmeans():
    df, shares, z = _planted()
    gmm = fit_gmm(drop_last(z), len(SEGMENTS)).predict(drop_last(z))
    km = kmeans_labels(shares, len(SEGMENTS))
    truth = df["true_segment"]
    assert adjusted_rand_score(truth, gmm) > adjusted_rand_score(truth, km) + 0.2


def test_profile_shares_sum_to_one_and_sizes_add_up():
    df, _, z = _planted()
    labels = kmeans_labels(z, 4)
    prof = segment_profile(z, labels, df["converted"].to_numpy(), FEATURES)
    assert np.allclose(prof[FEATURES].sum(axis=1), 1.0)
    assert prof["유저 수"].sum() == len(df)
    assert prof["전환 수"].sum() == df["converted"].sum()
