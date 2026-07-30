from media_manager.indexer.classification import classify_release


def test_4k_remux():
    a = classify_release(
        "Dune.Part.Two.2024.2160p.UHD.BluRay.REMUX.HDR10.HEVC.Atmos.7.1-FraMeSToR"
    )
    assert a.resolution == "2160p"
    assert a.source == "remux"
    assert a.codec == "h265"
    assert a.hdr_flags == ["hdr10"]
    assert "atmos" in a.audio_codecs
    assert a.release_group == "FraMeSToR"


def test_4k_bluray_encode_dv_hdr10_hybrid():
    a = classify_release(
        "Dune.Part.Two.2024.2160p.UHD.BluRay.x265.HDR.DV.TrueHD.7.1.Atmos-EDGE2020"
    )
    assert a.source == "bluray-encode"
    assert set(a.hdr_flags) == {"dv", "hdr10"}
    assert "truehd" in a.audio_codecs
    assert "atmos" in a.audio_codecs


def test_web_dl_vs_webrip():
    web_dl = classify_release("The.Batman.2022.1080p.WEB-DL.DD5.1.H.264-EVO")
    webrip = classify_release("Oppenheimer.2023.1080p.WEBRip.x264-RARBG")
    assert web_dl.source == "web-dl"
    assert webrip.source == "webrip"


def test_bluray_remux_vs_encode():
    remux = classify_release("The.Batman.2022.1080p.BluRay.REMUX.AVC.DTS-HD.MA.5.1-EPSiLON")
    encode = classify_release("Interstellar.2014.1080p.BluRay.x264-LOST")
    assert remux.source == "remux"
    assert encode.source == "bluray-encode"


def test_hdtv_and_dvd_sources():
    assert classify_release("Inception.2010.720p.HDTV.x264-CAM").source == "hdtv"


def test_codec_normalization():
    assert classify_release("Movie.2024.1080p.WEB-DL.H.264-GRP").codec == "h264"
    assert classify_release("Movie.2024.1080p.WEB-DL.HEVC-GRP").codec == "h265"
    assert classify_release("Movie.2024.1080p.BluRay.XviD-GRP").codec == "xvid"


def test_av1_codec_fallback():
    # guessit 4.2.1 has no AV1 pattern at all; classify_release must catch
    # it via the raw-title fallback regex.
    a = classify_release("Movie.2024.1080p.WEB-DL.AV1.OPUS-GRP")
    assert a.codec == "av1"
    assert a.audio_codecs == ["opus"]


def test_hdr10_plus_variants():
    # All three common scene spellings must resolve to "hdr10plus", not
    # plain "hdr10" (guessit alone drops the "+"/"Plus" signal).
    assert "hdr10plus" in classify_release(
        "Movie.2024.2160p.WEB-DL.HDR10+.DDP5.1.H.265-GRP"
    ).hdr_flags
    assert "hdr10plus" in classify_release(
        "Movie.2024.2160p.WEB-DL.HDR10Plus.DDP5.1.H.265-GRP"
    ).hdr_flags
    assert "hdr10plus" in classify_release(
        "Spider-Man.Across.the.Spider-Verse.2023.2160p.WEB-DL.DV.HDR10.Plus.DDP5.1-FLUX"
    ).hdr_flags


def test_plain_hdr10_stays_hdr10():
    a = classify_release("Movie.2024.2160p.WEB-DL.HDR10.DDP5.1.H.265-GRP")
    assert a.hdr_flags == ["hdr10"]


def test_no_hdr_is_empty():
    assert classify_release("Movie.2024.1080p.WEB-DL.x264-GRP").hdr_flags == []


def test_language_variant_multi():
    assert classify_release("Interstellar.2014.MULTI.1080p.BluRay.x264-LOST").language_variant == "multi"


def test_language_variant_german_dl():
    assert (
        classify_release("Interstellar.2014.German.DL.1080p.BluRay.x264-EmpireHD").language_variant
        == "german_dl"
    )


def test_language_variant_nordic():
    assert classify_release("Interstellar.2014.NORDiC.1080p.BluRay.x264-COPS").language_variant == "nordic"


def test_language_variant_dubbed():
    assert classify_release("Movie.2024.DUBBED.1080p.WEB-DL.x264-GRP").language_variant == "dubbed"


def test_language_variant_none_for_original():
    assert classify_release("Movie.2024.1080p.WEB-DL.x264-GRP").language_variant is None


def test_subtitles_default_empty():
    # No NFO/mediainfo fetch in this scope - subtitle info from title/search
    # metadata alone is expected to be empty in the vast majority of cases.
    assert classify_release("Movie.2024.1080p.WEB-DL.x264-GRP").subtitles == []
