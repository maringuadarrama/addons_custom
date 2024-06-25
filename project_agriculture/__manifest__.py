{
    "name": "Project Agriculture",
    "summary": "Agriculture managment with project",
    "version": "17.0.0.0.0",
    "category": "Hidden",
    "website": "https://www.xiuman.mx",
    "author": "Luis Marin, Vauxoo",
    "depends": [
        "base_address_extended",
        "base_geoengine",
        "web_map",
        "project",
    ],
    "demo": [
        "data/project_agriculture_land_demo.xml",
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/data.xml",
        "data/species_pdw_data.xml",
        "data/species_crop_data.xml",
        "views/project_agriculture_land_views.xml",
        "data/geoengine_vector_layer_data.xml",
        "data/geoengine_raster_layer_data.xml",
        "views/project_agriculture_scout_views.xml",
        "views/project_agriculture_species_views.xml",
        "views/project_agriculture_production_plan_views.xml",
        "views/project_agriculture_asset_views.xml",
        "views/project_views.xml",
        "views/project_agriculture_menu.xml",
        "data/ir_actions_server.xml",
    ],
    "license": "AGPL-3",
    "application": False,
    "installable": True,
}