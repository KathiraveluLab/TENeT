import geopandas as gpd
from shapely.geometry import Point

def items_to_gdf(items):
    return gpd.GeoDataFrame(
        items,
        geometry=[
            Point(i["location"]["lon"], i["location"]["lat"])
            for i in items
        ],
        crs="EPSG:4326"
    )
def assign_items_to_communities(communities_gdf, items_gdf):
    return gpd.sjoin(
        items_gdf,
        communities_gdf[["GEOID", "NAME", "geometry"]],
        how="left",
        predicate="within"
    )
def group_items_by_community(joined_gdf):
    """
    Takes the output of spatial join and groups items per community.
    Returns: { GEOID -> [items] }
    """
    return (
        joined_gdf
        .groupby("GEOID")
        .apply(lambda df: df.to_dict("records"),include_groups=False)
        .to_dict()
    )
