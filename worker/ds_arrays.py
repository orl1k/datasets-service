import sys
import os
import glob
import zipfile
import xml.etree.ElementTree as ET
import numpy as np
import gc
import argparse
from scipy.interpolate import RectBivariateSpline
from scipy.spatial import cKDTree

# import gdal, osr


# https://gis.stackexchange.com/questions/332327/reading-big-raster-getting-warnings-using-gdal-python
# Stop GDAL printing both warnings and errors to STDERR
# gdal.PushErrorHandler("CPLQuietErrorHandler")

# Make GDAL raise python exceptions for errors (warnings won't raise an exception)
# gdal.UseExceptions()


weather_params = [
    "ACGRDFLX",
    "ACHFX",
    "ACLHF",
    "ACLWDNB",
    "ACLWDNBC",
    "ACLWUPB",
    "ACLWUPBC",
    "ACLWUPT",
    "ACLWUPTC",
    "ACSNOM",
    "ACSWDNB",
    "ACSWDNBC",
    "ACSWDNT",
    "ACSWUPB",
    "ACSWUPBC",
    "ACSWUPT",
    "ACSWUPTC",
    "ALBBCK",
    "ALBEDO",
    "CANWAT",
    "CLDFRA",
    "COSALPHA",
    "COSZEN",
    "Date",
    "EMISS",
    "GLW",
    "GRAUPELNC",
    "GRDFLX",
    "HFX",
    "HGT",
    "ISLTYP",
    "LAI",
    "LAKEMASK",
    "LANDMASK",
    "LH",
    "LU_INDEX",
    "LWDNB",
    "LWDNBC",
    "LWUPB",
    "LWUPBC",
    "LWUPT",
    "LWUPTC",
    "MU",
    "MUB",
    "NOAHRES",
    "OLR",
    "P",
    "PB",
    "PBLH",
    "PH",
    "PHB",
    "PSFC",
    "P_HYD",
    "Q2",
    "QFX",
    "QNICE",
    "QVAPOR",
    "RAINNC",
    "SEAICE",
    "SFROFF",
    "SH2O",
    "SHDMAX",
    "SHDMIN",
    "SINALPHA",
    "SMCREL",
    "SMOIS",
    "SNOALB",
    "SNOW",
    "SNOWC",
    "SNOWH",
    "SNOWNC",
    "SR",
    "SST",
    "SWDNB",
    "SWDNBC",
    "SWDNT",
    "SWDOWN",
    "SWUPB",
    "SWUPBC",
    "SWUPT",
    "SWUPTC",
    "T",
    "T2",
    "TH2",
    "THM",
    "TMN",
    "TSK",
    "TSLB",
    "U",
    "U10",
    "UDROFF",
    "UST",
    "V",
    "V10",
    "VAR",
    "VEGFRA",
    "W",
    "XLAND",
]


def get_geodata_from_raster(raster):
    """
    Get geodata from a raster

    Parameters:
    raster (gdal raster): Input raster

    Returns:
    x_res, y_res, gt, gcp_list, spatial_ref_wkt (tuple):
      x_res (int): Raster width
      y_res (int): Raster height
      gt (tuple): x_min, pixel_size, 0, y_max, 0, -pixel_size).
                  x_min - longitude of the upper left pixel;
                  y_max - latitude of the upper left pixel;
                  pixel_size - pixel width.
                  It can be None if there is a gcp_list.
      gcp_list (list): Ground control points.
                       It can be None if there is a gt.
      spatial_ref_wkt (string): Spatial reference as wkt

    """
    x_res = raster.RasterXSize
    y_res = raster.RasterYSize
    if raster.GetGCPCount() == 0:
        gt = raster.GetGeoTransform()
        spatial_ref_wkt = raster.GetProjection()
        # GCPs не используются вместе с GT!
        gcp_list = None
    else:
        gcp_list = raster.GetGCPs()
        spatial_ref_wkt = raster.GetGCPProjection()
        # GCPs не используются вместе с GT!
        gt = None
    return x_res, y_res, gt, gcp_list, spatial_ref_wkt


def create_empty_raster(
    x_res,
    y_res,
    spatial_ref_wkt,
    geo_transform=None,
    gcp_list=None,
    no_data_value=-99,
    # values_type=gdal.GDT_Int32,
):
    """
    Create empty gdal raster

    Parameters:
    x_res (int): Output file width
    y_res (int): Output file height
    spatial_ref_wkt (string): Spatial reference as wkt
    geo_transform (tuple): (x_min, pixel_size, 0, y_max, 0, -pixel_size).
                            x_min - longitude of the upper left pixel;
                            y_max - latitude of the upper left pixel;
                            pixel_size - pixel width.
                            Not used together with gcp_list!!!
    gcp_list (list/tuple): Ground control points.
                           Not used together with geo_transform!!!
    no_data_value (int): Values to mark missing data
    values_type (gdal data type): One of Byte, UInt16, Int16, UInt32, Int32, Float32, Float64, and the complex types CInt16, CInt32, CFloat32, and CFloat64

    Returns:
    out_ds (gdal raster): Empty gdal raster filled with no_data_value
    """
    if (geo_transform is None) and (gcp_list is None):
        raise RuntimeError("geo_transform and gcp_list are None")
    # Создание итогового гдал растра, 1 - указывает на кол-во слоев в создаваемом растре
    out_ds = gdal.GetDriverByName("MEM").Create(
        "", x_res, y_res, 1, values_type
    )
    # Добавление геоданных и проекции. Внимание: GCPs не используются вместе с GT, поэтому GCPs устанавливаются только в случае отсутствия GT
    if geo_transform is not None:
        out_ds.SetGeoTransform(geo_transform)
        out_ds.SetProjection(spatial_ref_wkt)
    else:
        out_ds.SetGCPs(gcp_list, spatial_ref_wkt)

    # Обращение к 1му слою
    out_ds_band = out_ds.GetRasterBand(1)
    # Указание NA значений
    out_ds_band.SetNoDataValue(no_data_value)
    # Заполнение неизвестных значений no_data_value,
    # потому как в memory-объектах значения автоматически заполняются 0
    out_ds_band.Fill(no_data_value, 0)
    return out_ds


def burn(
    in_ds,
    burn_param=None,
    burn_value=None,
    x_res=None,
    y_res=None,
    spatial_ref_wkt=None,
    geo_transform=None,
    gcp_list=None,
    base_raster=None,
    add=False,
    no_data_value=-99,
    # values_type=gdal.GDT_Int32,
):
    """
    Burn data from geofile (.shp/.geojson/.gpkg) or gdal dataset

    Parameters:
    in_ds (gdal dataset OR string): Object to burn data from (or full path to geo file). Note: check that the projections of the shapefile and other data/files match
    burn_param (string): Name of the shapefile field whose values you want to burn. Note: check that the field contains numeric values
    burn_value (int/float): The value you want to write. Type depends on the values_type
    x_res (int): Output file width
    y_res (int): Output file height
    spatial_ref_wkt (string): Spatial reference as wkt
    geo_transform (tuple): (x_min, pixel_size, 0, y_max, 0, -pixel_size).
                            x_min - longitude of the upper left pixel;
                            y_max - latitude of the upper left pixel;
                            pixel_size - pixel width.
                            Not used together with gcp_list!!!
    gcp_list (list/tuple): Ground control points.
                           Not used together with geo_transform!!!
    base_raster (gdal raster): gdal object that is the basis for creating a new one. Its dimensions and geodata are used. Note: if base_raster is used, then x_res, y_res, geo_transform, spatial_ref_wkt are determined automatically. Default: None.
    add (bool): Transfer array from base_raster as a basis for burning
    no_data_value (int): Values that will be filled in pixels for which there are no values in the shapefile
    values_type (gdal data type): One of Byte, UInt16, Int16, UInt32, Int32, Float32, Float64, and the complex types CInt16, CInt32, CFloat32, and CFloat64

    Returns:
    target (gdal raster): Raster containing burnt values
    """
    # Проверка корректности введенных данных
    if (burn_param is None) and (burn_value is None):
        raise RuntimeError("burn_param and burn_value are None")
    if all(
        v is None
        for v in [
            base_raster,
            x_res,
            y_res,
            spatial_ref_wkt,
            geo_transform,
            gcp_list,
        ]
    ):
        raise RuntimeError(
            "base_raster, x_res, y_res, geo_transform, spatial_ref_wkt are None"
        )
    # Если указан базовый объект прожига, то используются его геопараметры
    if base_raster is not None:
        x_res, y_res, gt, gcp_list, spatial_ref_wkt = get_geodata_from_raster(
            base_raster
        )
    # Создание пустого растра, выступающего в роли подложки для прожигаемых объектов
    target = create_empty_raster(
        x_res,
        y_res,
        spatial_ref_wkt,
        geo_transform=geo_transform,
        gcp_list=gcp_list,
        no_data_value=no_data_value,
        values_type=values_type,
    )
    # Нанесение матрицы из исходного файла, если данные нужно добавить на нее
    if add:
        if base_raster is None:
            raise RuntimeError("Can not add data when base_raster is None")
        base_array = base_raster.ReadAsArray()
        target_band = target.GetRasterBand(1)
        target_band.WriteArray(base_array)
    layer = in_ds.GetLayer()
    # Если необходимо прожечь значения из колонки геофайла
    if burn_param is not None:
        # Проверка наличия требуемого параметра в in_ds
        if burn_param not in in_ds.GetLayer()[0].keys():
            raise RuntimeError(f"{burn_param} not in in_ds")
        # Все фичи в слое фильтруются, чтобы не было пустых значений, т.к. при их наличии они будут прожжены 1  независимо от no_data_value
        layer.SetAttributeFilter(f"{burn_param} IS NOT NULL")
        rasterizeOptions = gdal.RasterizeOptions(
            bands=[1], allTouched=True, attribute=burn_param
        )
    # Если необходимо прожечь одним значением
    else:
        rasterizeOptions = gdal.RasterizeOptions(
            bands=[1], burnValues=[burn_value]
        )
    # Непостредственно прожиг
    gdal.Rasterize(target, in_ds, options=rasterizeOptions)
    # Сброс фильтра
    layer.SetAttributeFilter(None)
    return target


def create_ice_mask(
    rescaled_raster,
    icemap,
    land_ds,
    mask_raster,
    param_type="age_group",
    land_value=-99,
    na_value=-99,
):
    ice_raster = burn(
        icemap,
        burn_param=param_type,
        base_raster=rescaled_raster,
        no_data_value=na_value,
    )
    ice_raster = burn(
        land_ds,
        burn_value=land_value,
        base_raster=ice_raster,
        add=True,
        no_data_value=na_value,
    )
    ice_arr = ice_raster.ReadAsArray()
    ice_arr[mask_raster.ReadAsArray() == 1] = na_value
    return ice_arr


def select_textures(textures_raster, band_nums=None):
    if band_nums is None:
        band_nums = range(textures_raster.RasterCount)
    else:
        if (
            len([i for i in band_nums if i >= textures_raster.RasterCount])
            != 0
        ):
            raise RuntimeError(
                f"Band numbers must be less than {textures_raster.RasterCount}"
            )
    textures_arr = textures_raster.ReadAsArray()
    return [textures_arr[band_num, :, :] for band_num in band_nums]


def equal_size(
    rescaled_raster,
    in_angle_raster,
    mask_raster,
    simple_textures_raster,
    advanced_textures_raster,
):
    # Если не все совспадают, то их нельзя объединять
    if not all(
        [
            (rescaled_raster.RasterXSize == raster.RasterXSize)
            and (rescaled_raster.RasterYSize == raster.RasterYSize)
            for raster in [
                in_angle_raster,
                mask_raster,
                simple_textures_raster,
                advanced_textures_raster,
            ]
        ]
    ):
        return False
    return True


def create_stacked(
    rescaled_raster,
    in_angle_raster,
    mask_raster,
    simple_textures_raster,
    advanced_textures_raster,
    icemap,
    land_ds,
    ice_param_types=["age_group", "age", "concentrat"],
    simple_band_nums=None,
    advanced_band_nums=None,
    land_value=-99,
    na_value=-99,
):
    if not equal_size(
        rescaled_raster,
        in_angle_raster,
        mask_raster,
        simple_textures_raster,
        advanced_textures_raster,
    ):
        print("The arrays are not the same size")
        return
    stack = [rescaled_raster.ReadAsArray(), in_angle_raster.ReadAsArray()]
    print("Add rescaled, in_angle")
    if (simple_band_nums is None) or (len(simple_band_nums) != 0):
        stack += select_textures(
            simple_textures_raster, band_nums=simple_band_nums
        )
        print("Add simple textures")
    if (advanced_band_nums is None) or (len(advanced_band_nums) != 0):
        stack += select_textures(
            advanced_textures_raster, band_nums=advanced_band_nums
        )
        print("Add advanced textures")
    for ice_param_type in ice_param_types:
        ice_mask = create_ice_mask(
            rescaled_raster,
            icemap,
            land_ds,
            mask_raster,
            param_type=ice_param_type,
            land_value=land_value,
            na_value=na_value,
        )
        if np.all(ice_mask == -99):
            print("The raster does not contain information from the ice map")
            return
        stack.append(ice_mask)
        print(f"Add {ice_param_type}")
    del ice_mask
    print("Concatenate")
    return np.dstack(stack)


def get_pols(date_dir):
    """
    Determination of all polarizations in sars in one day

    Parameters:
    date_dir (str): The path to the folder containing rasters and other information for a specific date

    Returns:
    (list): Polarization list
    """
    search_path = os.path.join(date_dir, "rescaled", "*")
    return [os.path.basename(p) for p in glob.glob(search_path)]


def get_texture_feature(date_dir, pol, raster_fn, texture_type):
    """
    Returns the texture

    Parameters:
    date_dir (str): The path to the folder containing rasters and other information for a specific date
    pol (str): Polarization
    raster_fn (str): The name of the raster for which the texture is searched
    texture_type (str): Texture type

    Returns:
    (gdal raster dataset): Texture
    """
    raster_name, ext = os.path.splitext(raster_fn)
    texture_fp = os.path.join(
        date_dir, "textures", pol, f"{raster_name}_{texture_type}{ext}"
    )
    if not os.path.exists(texture_fp):
        print(
            f"  Not found {texture_type} for {raster_fn}\n {texture_fp} does not exist"
        )
        return
    return gdal.Open(texture_fp)


def get_in_angle(date_dir, pol, raster_fn):
    in_angle_fp = os.path.join(date_dir, "incidence_angles", pol, raster_fn)
    if not os.path.exists(in_angle_fp):
        print(
            f"  Not found incidence angle for {raster_fn}\n {in_angle_fp} does not exist"
        )
        return
    return gdal.Open(in_angle_fp)


def get_mask(date_dir, pol, raster_fn):
    """
    Returns the mask for a raster

    Parameters:
    date_dir (str): The path to the folder containing rasters and other information for a specific date
    pol (str): Polarization
    raster_fn (str): The name of the raster for which the mask is searched

    Returns:
    (gdal raster dataset): Raster mask
    """
    mask_fp = os.path.join(date_dir, "masks", pol, raster_fn)
    if not os.path.exists(mask_fp):
        print(f"  Not found mask for {raster_fn}\n {mask_fp} does not exist")
        return
    return gdal.Open(mask_fp)


def get_marked_icemap(icemap_dir):
    """
    Returns the icemap

    Parameters:
    icemap_dir (str): Path to the folder containing ice maps for the day

    Returns:
    (gdal vector dataset): Icemap
    """
    # search_path = os.path.join(icemap_dir, 'marked', '*_marked.shp')
    search_path = os.path.join(icemap_dir, "map", "source", "*_marked.shp")
    marked_icemap_fp = glob.glob(search_path)
    if len(marked_icemap_fp) == 0:
        print(f"  Not found marked icemap (regex: {search_path})")
        return
    return gdal.OpenEx(marked_icemap_fp[0])


def get_coords_types(weather_map_fp, weather_params):
    weather = gdal.Open(weather_map_fp)
    # Формирование списка уникальных координатных сеток
    coord_groups = []
    coord_keys = [
        k for k in weather.GetMetadata_Dict().keys() if "_coordinates" in k
    ]
    for k in coord_keys:
        coord_grid = tuple(weather.GetMetadata_Dict()[k].split(" ")[:2])
        if coord_grid not in coord_groups:
            coord_groups.append(coord_grid)
    # Формирование словаря, где ключ - тип координатной сетки, значение - список параметров с такой сеткой
    metadata = weather.GetMetadata_Dict()
    coords_types = {}
    for weather_param in weather_params:
        try:
            coords_type = tuple(
                metadata[f"{weather_param}_coordinates"].split(" ")[:2]
            )
        except:
            print(f"Invalid name {weather_param} ({weather_map_fp})")
            continue
        if coords_type not in coords_types.keys():
            coords_types.update({coords_type: [weather_param]})
        else:
            coords_types[coords_type].append(weather_param)
    return coords_types


def get_files(source_fp, pol):
    """Getting rasters (as gdal dataset) and a list of support files for SAR (as xml): measurement; annotation; calibration; noise; manifest

    Returns
    --------
    rasters, sar_files : tuple
       rasters (dict) contains rasters (gdal dataset) by polarizations
       sar_files (dict) contains xmls () for each polarizations
    """

    with zipfile.ZipFile(source_fp, "r") as zip_ref:
        files = zip_ref.namelist()
        for file in files:
            if (
                ("measurement" in file)
                and (".tiff" in file)
                and (pol.lower() in file)
            ):
                mds_full_path = os.path.join(source_fp, file)
                raster = gdal.Open(f"/vsizip/{mds_full_path}")
            # Папка annotation содержит подпапку calibration, поэтому calibration не должно присутвовать в искомом файле
            if (
                ("annotation" in file)
                and ("calibration" not in file)
                and (".xml" in file)
                and (pol.lower() in file)
            ):
                annotation = ET.parse(zip_ref.open(file))
    return raster, annotation


def get_geolocation_grid_point(annotation_tree):
    """Getting geolocation grid point from annotation xml

    Parameters
    ----------
    annotation_tree : xml ElementTree
        Annotation XML tree

    Returns
    --------
    geolocation_grid_point : dict
        Contains info about geolocation
    """
    geolocation_grid_point = {"line": [], "pixel": [], "lat": [], "lon": []}

    geolocation_grid_point_list = annotation_tree.find("geolocationGrid").find(
        "geolocationGridPointList"
    )
    for geolocation_grid_point_elem in geolocation_grid_point_list:
        geolocation_grid_point["line"].append(
            int(geolocation_grid_point_elem.find("line").text)
        )
        geolocation_grid_point["pixel"].append(
            int(geolocation_grid_point_elem.find("pixel").text)
        )
        geolocation_grid_point["lat"].append(
            float(geolocation_grid_point_elem.find("latitude").text)
        )
        geolocation_grid_point["lon"].append(
            float(geolocation_grid_point_elem.find("longitude").text)
        )
    return geolocation_grid_point


def resize_coords(geolocation_grid_point, rasters_shape, coord_type):
    # Вектор уникальных значений линий (y) и пикселей (x)
    pixels_vector = np.unique(geolocation_grid_point["pixel"])
    lines_vector = np.unique(geolocation_grid_point["line"])
    coords = np.array(geolocation_grid_point[coord_type]).reshape(
        len(lines_vector), len(pixels_vector)
    )
    # Сплайн для значений по линиям (y) и пикселям (x)
    coords_interpolator = RectBivariateSpline(
        lines_vector, pixels_vector, coords
    )
    return coords_interpolator(
        np.arange(0, rasters_shape[0]), np.arange(0, rasters_shape[1])
    )


def get_lat_lon_arr(raster, annotation):
    geolocation_grid_point = get_geolocation_grid_point(annotation)
    rasters_shape = (raster.RasterYSize, raster.RasterXSize)
    lat_arr = resize_coords(geolocation_grid_point, rasters_shape, "lat")
    lon_arr = resize_coords(geolocation_grid_point, rasters_shape, "lon")
    return lat_arr, lon_arr


def get_source_raster_path(date_dir, raster_fn):
    source_fp = os.path.join(date_dir, "source", f"{raster_fn}.zip")
    if not os.path.exists(source_fp):
        print(
            f"  Not found source for {raster_fn}. {source_fp} does not exist"
        )
        return
    return source_fp


def get_weather_param_id(weather_rasters, weather_param):
    # В метаданных хранится словарь с указанием индексов каждого погодного параметра
    param_indx = weather_rasters.GetMetadata().get(weather_param, None)
    if param_indx is None:
        print(f"  Not found {weather_param}")
        return
    # Индексация у растров начинается с 1, индексация в метаданных с 0
    return int(param_indx) + 1


def get_weather_rasters(weather_rasters_root, coord_type):
    weather_rasters_path = os.path.join(
        weather_rasters_root, f"{coord_type}.tif"
    )
    if not os.path.exists(weather_rasters_path):
        print(f"  Not found weather ({weather_rasters_path})")
        return
    return gdal.Open(weather_rasters_path)


def get_weather_param_array(weather_rasters, param):
    param_id = get_weather_param_id(weather_rasters, param)
    if param_id is None:
        return
    return weather_rasters.GetRasterBand(param_id).ReadAsArray()


def get_coord_arr(weather_fp, coord):
    coord_raster = gdal.Open(f'NETCDF:"{weather_fp}"://{coord}')
    return coord_raster.GetRasterBand(1).ReadAsArray()


def get_weather_coords_tree(weather_fp, coords_type):
    weather_lat_arr = get_coord_arr(weather_fp, coords_type[1])
    weather_lon_arr = get_coord_arr(weather_fp, coords_type[0])
    weather_coords_arr = np.stack(
        (weather_lon_arr.flatten(), weather_lat_arr.flatten()), axis=-1
    )
    return cKDTree(weather_coords_arr)


def get_weather_source_path(date_dir):
    weather_source_fp = glob.glob(
        os.path.join(date_dir, "weather", "wrfout_d03*")
    )
    if len(weather_source_fp) == 0:
        print(f"  Not found weather")
        return
    return weather_source_fp[0]


# def create_weather_ds(rasters_root, date, ds_root, weather_params, weather_step=0.08):
#   date_dir = os.path.join(rasters_root, date)
#   ds_dir = os.path.join(ds_root, date, 'weather')
#   pols = get_pols(date_dir)
#   pol_groups = [('HH', 'HV')*('HH' in pols and 'HV' in pols), ('VH', 'VV')*('VV' in pols and 'VH' in pols)]
#   pol_groups = [pol_group for pol_group in pol_groups if len(pol_group) != 0]
#   # Путь к растрам с погодой
#   weather_rasters_dir = os.path.join(date_dir, 'weather', 'rasters')
#   weather_fp = get_weather_source_path(date_dir)
#   if weather_fp is None:
#     return
#   # Словарь типа: {('XLONG', 'XLAT'): [param1,  param2], (...), [...]}
#   coords_types = get_coords_types(weather_fp, weather_params)
#   # Все данные про погоду общие, поэтому будут загружены единожды
#   print('Load weather rasters')
#   # Словарь типа: {('XLONG', 'XLAT'): rasters, (...), ...}, содержит растровые датасеты
#   weather_rasters = {coords_type: get_weather_rasters(weather_rasters_dir, '_'.join(coords_type)) for coords_type in coords_types}
#   # Словарь типа: {('XLONG', 'XLAT'): cKDTree, (...), ...}, содержит деревья с координатами, по которым будет искаться ближайший
#   weather_coords_trees = {coords_type: get_weather_coords_tree(weather_fp, coords_type) for coords_type in coords_types}
#   for pol_group in pol_groups:
#     pol = pol_group[0]
#     # Растры для одной поляризации
#     raster_fps = glob.glob(os.path.join(date_dir, 'rescaled', pol, '*.tif'))
#     print(f'{pol} | {len(raster_fps)} rasters')
#     if len(raster_fps) == 0:
#       continue
#     os.makedirs(os.path.join(ds_dir, pol), exist_ok=True)
#     for raster_fp in raster_fps:
#       print(f'{raster_fp}')
#       raster_fn = os.path.basename(raster_fp)
#       source_fp = get_source_raster_path(date_dir, raster_fn)
#       raster, annotation = get_files(source_fp, pol)
#       lat_arr, lon_arr = get_lat_lon_arr(raster, annotation)
#       raster_coords_arr = np.stack((lon_arr.flatten(),
#                                     lat_arr.flatten()),
#                                     axis=-1)
#       # Словарь типа: {('XLONG', 'XLAT'): (dist, idx), (...), ...}, содержит расстояние и индекс ближайшего пикселя в погоде к пикселю растра
#       query_result = {coords_type: weather_coords_trees[coords_type].query(raster_coords_arr, k=1) for coords_type in coords_types}
#       weather_by_raster_arrs = []
#       n_params = len(weather_params)
#       for i, weather_param in enumerate(weather_params):
#         if i%10 == 1:
#           print(f'{i}/{n_params}')
#         if weather_param in ['U', 'V']:
#           ctype = (f'XLONG_{weather_param}', f'XLAT_{weather_param}')
#         else:
#           ctype = ('XLONG', 'XLAT')
#         param_arr = get_weather_param_array(weather_rasters[ctype], weather_param)
#         param_flatten_arr = param_arr.flatten()
#         # Отбор только ближайших к растру пикселей погоды
#         weather_by_raster_flatten_arr = param_flatten_arr[query_result[ctype][1]]
#         # Фильтрация по расстоянию: если найденный погодный пиксель дальше,ч ем шаг координтаной сетки у погоды, то значит, что в этом месте погода и растр не пересекаются, а значит данное значение не будет использовано (и будет заменено на nan)
#         weather_by_raster_flatten_arr[query_result[ctype][0] > weather_step] = np.nan
#         # Приведение к размеру растра
#         weather_by_raster_arr = weather_by_raster_flatten_arr.reshape((raster.RasterYSize, raster.RasterXSize))
#         if i==0:
#           if np.all(weather_by_raster_arr == -99):
#             print('There is no weather for this zone')
#             continue
#         weather_by_raster_arrs.append(weather_by_raster_arr)
#       weather_stacked = np.dstack(weather_by_raster_arrs)
#       save_fp = os.path.join(ds_dir, '_'.join(pols), f'{os.path.splitext(raster_fn)[0]}_weather.npy')
#       print(f'Save: {save_fp}')
#       np.save(save_fp, weather_stacked)


def median_by_z(weather_arrs, n_rasters):
    z_count = int(n_rasters / 25)
    time_arrs = []
    for i in range(0, n_rasters, z_count + 1):
        time_arrs.append(
            np.median(weather_arrs[i : i + z_count, :, :], axis=0)
        )
    return np.array(time_arrs)


def median_by_time(weather_arrs):
    return np.median(weather_arrs, axis=0)


def create_weather_arr(weather_fp, param):
    print(param)
    try:
        param_map = gdal.Open(f'NETCDF:"{weather_fp}"://{param}')
    except:
        print(f"  Not found {param}")
        return
    param_arrs = param_map.ReadAsArray()
    if param_map.RasterCount > 25:
        param_arrs = median_by_z(param_arrs, param_map.RasterCount)
    return median_by_time(param_arrs)


def create_weather_ds(
    rasters_root, date, ds_root, weather_params, weather_step=0.08
):
    date_dir = os.path.join(rasters_root, date)
    weather_ds_dir = os.path.join(ds_root, date, "weather")
    os.makedirs(weather_ds_dir, exist_ok=True)
    pols = get_pols(date_dir)
    pol_groups = [
        ("HH", "HV") * ("HH" in pols and "HV" in pols),
        ("VH", "VV") * ("VV" in pols and "VH" in pols),
    ]
    pol_groups = [pol_group for pol_group in pol_groups if len(pol_group) != 0]
    weather_fp = get_weather_source_path(date_dir)
    if weather_fp is None:
        return
    # Словарь типа: {('XLONG', 'XLAT'): [param1,  param2], (...), [...]}
    coords_types = get_coords_types(weather_fp, weather_params)
    # Все данные про погоду общие, поэтому будут загружены единожды
    print("Load weather rasters")
    # Словарь типа: {погодный параметр: массив}
    weather_arrs = {
        param: create_weather_arr(weather_fp, param)
        for param in weather_params
    }
    # Словарь типа: {('XLONG', 'XLAT'): cKDTree, (...), ...}, содержит деревья с координатами, по которым будет искаться ближайший
    weather_coords_trees = {
        coords_type: get_weather_coords_tree(weather_fp, coords_type)
        for coords_type in coords_types
    }
    for pol_group in pol_groups:
        pol = pol_group[0]
        # Растры для одной поляризации
        ds_dir = os.path.join(ds_root, date, pol)
        if not os.path.exists(ds_dir):
            print(f"  Not found datasets ({ds_dir})")
            return
        raster_fps = glob.glob(os.path.join(ds_dir, "*.npy*"))
        print(f"{pol_group} ({pol}) | {len(raster_fps)} rasters")
        if len(raster_fps) == 0:
            continue
        for raster_fp in raster_fps:
            print(f"{raster_fp}")
            raster_fn = os.path.basename(raster_fp).split(".")[0]
            source_fp = get_source_raster_path(date_dir, raster_fn)
            raster, annotation = get_files(source_fp, pol)
            lat_arr, lon_arr = get_lat_lon_arr(raster, annotation)
            raster_coords_arr = np.stack(
                (lon_arr.flatten(), lat_arr.flatten()), axis=-1
            )
            # Словарь типа: {('XLONG', 'XLAT'): (dist, idx), (...), ...}, содержит расстояние и индекс ближайшего пикселя в погоде к пикселю растра
            query_result = {
                coords_type: weather_coords_trees[coords_type].query(
                    raster_coords_arr, k=1
                )
                for coords_type in coords_types
            }
            weather_by_raster_arrs = []
            n_params = len(weather_params)
            for i, weather_param in enumerate(weather_params):
                if i % 10 == 1:
                    print(f"{i}/{n_params}")
                if weather_param in ["U", "V"]:
                    ctype = (f"XLONG_{weather_param}", f"XLAT_{weather_param}")
                else:
                    ctype = ("XLONG", "XLAT")
                param_arr = weather_arrs[weather_param]
                if param_arr is None:
                    continue
                param_flatten_arr = param_arr.flatten()
                # Отбор только ближайших к растру пикселей погоды
                weather_by_raster_flatten_arr = param_flatten_arr[
                    query_result[ctype][1]
                ]
                # Фильтрация по расстоянию: если найденный погодный пиксель дальше,ч ем шаг координтаной сетки у погоды, то значит, что в этом месте погода и растр не пересекаются, а значит данное значение не будет использовано (и будет заменено на nan)
                weather_by_raster_flatten_arr[
                    query_result[ctype][0] > weather_step
                ] = np.nan
                # Приведение к размеру растра
                weather_by_raster_arr = weather_by_raster_flatten_arr.reshape(
                    (raster.RasterYSize, raster.RasterXSize)
                )
                if i == 0:
                    if np.all(weather_by_raster_arr == -99):
                        print("There is no weather for this zone")
                        continue
                weather_by_raster_arrs.append(weather_by_raster_arr)
            weather_stacked = np.dstack(weather_by_raster_arrs)
            save_fp = os.path.join(
                weather_ds_dir, f'{raster_fn}_{"_".join(pol_group)}.npy'
            )
            print(f"Save: {save_fp}")
            np.save(save_fp, weather_stacked)


def create_ds_arrays(
    date,
    icemaps_root,
    rasters_root,
    ds_root,
    land_fp,
    weather_fp,
    ice_param_types=["age_group", "age", "concentrat"],
    simple_band_nums=None,
    advanced_band_nums=None,
    land_value=-99,
    na_value=-99,
):
    icemap = get_marked_icemap(os.path.join(icemaps_root, date))
    if icemap is None:
        return
    land_ds = gdal.OpenEx(land_fp)
    date_dir = os.path.join(rasters_root, date)
    ds_dir = os.path.join(ds_root, date)
    pols = get_pols(date_dir)
    # Сбор производится для каждой поляризации по отдельности
    print(f"Pols: {pols}")
    for pol in pols:
        # Растры для одной поляризации
        raster_fps = glob.glob(
            os.path.join(date_dir, "rescaled", pol, "*.tif")
        )
        print(f"{pol} | {len(raster_fps)} rasters")
        if len(raster_fps) == 0:
            continue
        os.makedirs(os.path.join(ds_dir, pol), exist_ok=True)
        # Для каждого растра собирается массив: масштабированные значения снимка + угол + симпл характеристики + адвансед характеристики + параметры льда + маска для снимка
        for raster_fp in raster_fps:
            print(f"{pol} | {raster_fp}")
            raster_fn = os.path.basename(raster_fp)
            # масштабированные значения снимка
            rescaled_raster = gdal.Open(raster_fp)
            # текстуры
            simple_textures_raster = get_texture_feature(
                date_dir, pol, raster_fn, "simple"
            )
            if simple_textures_raster is None:
                continue
            advanced_textures_raster = get_texture_feature(
                date_dir, pol, raster_fn, "advanced"
            )
            if advanced_textures_raster is None:
                continue
            # угол
            in_angle_raster = get_in_angle(date_dir, pol, raster_fn)
            if in_angle_raster is None:
                continue
            # маска
            mask_raster = get_mask(date_dir, pol, raster_fn)
            if mask_raster is None:
                continue
            # Непосредственно склейка данных в один мега массив
            full_arr = create_stacked(
                rescaled_raster,
                in_angle_raster,
                mask_raster,
                simple_textures_raster,
                advanced_textures_raster,
                icemap,
                land_ds,
                ice_param_types=ice_param_types,
                simple_band_nums=simple_band_nums,
                advanced_band_nums=advanced_band_nums,
                land_value=land_value,
                na_value=na_value,
            )
            if full_arr is None:
                continue
            save_fp = os.path.join(
                ds_dir, pol, f"{os.path.splitext(raster_fn)[0]}.npy"
            )
            print(f"Save: {save_fp}")
            np.save(save_fp, full_arr)
            gc.collect()


def get_band_nums(x):
    if x is None:
        return []
    if "all" in x:
        return None
    return [int(i) for i in x]


if __name__ == "__main__":
    argparser = argparse.ArgumentParser()

    argparser.add_argument(
        "--date",
        type=str,
        help="Дата, за которую будет собран датасет. Пример: 20200101",
    )
    argparser.add_argument(
        "--rasters_root",
        type=str,
        help="Директория, содержащая снимки. Пример: /mnt/Gold2/rasters",
    )
    argparser.add_argument(
        "--ds_root",
        type=str,
        help="Директория с датасетами. Пример: /mnt/Gold1/datasets",
    )
    argparser.add_argument(
        "--icemaps_root",
        type=str,
        help="Директория с датасетами. Пример: /mnt/Gold2/ice_maps/KAR",
    )
    argparser.add_argument(
        "--land",
        type=str,
        help="Путь к шейпу с землей. Пример: /mnt/Gold2/land/bigger/Shore_20191212.shp",
    )
    argparser.add_argument(
        "--ice_params",
        type=str,
        nargs="+",
        default=["age", "concentrat", "age_group"],
        choices=["age", "concentrat", "age_group"],
        help="Характеристики льда, которые будут добавлены в датасет",
    )
    argparser.add_argument(
        "--simple",
        type=str,
        nargs="+",
        default=None,
        help="Номера добавляемых текстурных характеристик из группы simple. Нумерация с 0! Если необходимо использовать все, то указывается: all",
    )
    argparser.add_argument(
        "--advanced",
        type=str,
        nargs="+",
        default=None,
        help="Номера добавляемых текстурных характеристик из группы advanced. Нумерация с 0! Если необходимо использовать все, то указывается: all",
    )

    namespace, unknown = argparser.parse_known_args(sys.argv[1:])

    create_ds_arrays(
        namespace.date,
        namespace.icemaps_root,
        namespace.rasters_root,
        namespace.ds_root,
        namespace.land,
        namespace.ice_params,
        simple_band_nums=get_band_nums(namespace.simple),
        advanced_band_nums=get_band_nums(namespace.advanced),
    )

    create_weather_ds(
        namespace.rasters_root,
        namespace.date,
        namespace.ds_root,
        weather_params,
    )
