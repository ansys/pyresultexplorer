import logging

from ansys.result_explorer.core import models

log = logging.getLogger(__name__)


def test_app(rx):
    # build info
    app_info = rx.app_info()
    assert app_info.version != ""
    assert app_info.commit_hash != ""

    # get settings
    app_settings = rx.app_settings()
    log.info(f"App settings: {app_settings}")

    # update settings
    app_settings.appearance.theme = models.AppTheme.APP_THEME_DARK
    app_settings.three_d.interaction_mode = (
        models.ThreeDInteractionMode.THREE_DINTERACTION_MODE_PRESET_3
    )
    app_settings.data_processing.chunking_strategy = models.ChunkingStrategy.CHUNKING_STRATEGY_SMALL
    app_settings.three_d.color_map = models.ThreeDColorMap.THREE_DCOLOR_MAP_VIRIDIS

    original_show_mesh_edges = app_settings.three_d.show_mesh_edges_by_default
    app_settings.three_d.show_mesh_edges_by_default = not original_show_mesh_edges
    new_settings = rx.update_app_settings(app_settings)

    assert new_settings.appearance.theme == models.AppTheme.APP_THEME_DARK
    assert (
        new_settings.three_d.interaction_mode
        == models.ThreeDInteractionMode.THREE_DINTERACTION_MODE_PRESET_3
    )
    assert (
        new_settings.data_processing.chunking_strategy
        == models.ChunkingStrategy.CHUNKING_STRATEGY_SMALL
    )
    assert new_settings.three_d.color_map == models.ThreeDColorMap.THREE_DCOLOR_MAP_VIRIDIS
    assert new_settings.three_d.show_mesh_edges_by_default == (not original_show_mesh_edges)
