from core import config


def test_career_phase_buckets():
    assert config.career_phase(0) == "Début de carrière"
    assert config.career_phase(3) == "Début de carrière"
    assert config.career_phase(4) == "Milieu de carrière"
    assert config.career_phase(7) == "Milieu de carrière"
    assert config.career_phase(8) == "Fin de carrière"
    assert config.career_phase(len(config.GRADES) - 1) == "Fin de carrière"


def test_grades_and_tracks_well_formed():
    assert len(config.GRADES) == 12
    assert len(set(config.GRADES)) == len(config.GRADES)
    assert "Quant" in config.TRACKS


def test_continents_have_required_fields():
    for name, info in config.CONTINENTS.items():
        assert "color" in info
        assert "regulator" in info
        assert "framework" in info
        assert "currency" in info
        assert "blurb" in info


def test_layout_helpers_consistent_with_screen_size():
    assert config.footer_y() == config.SCREEN_HEIGHT - config.FOOTER_H
    x, y, w, h = config.back_button_rect()
    assert y == config.SCREEN_HEIGHT - h - 8
    assert config.content_top() < config.SCREEN_HEIGHT


def test_save_dir_resolution_not_frozen():
    assert config.SAVE_DIR == "saves"
    assert config.AUTOSAVE_SLOT == "autosave"
    assert len(config.SAVE_SLOTS) == 3
