import argparse, sys
import time

if __name__ == "__main__":
    time.sleep(20)
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
