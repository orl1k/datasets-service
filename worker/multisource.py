import os
import pathlib
from pydantic import DirectoryPath


class DataGatherer:
    # Class is synchronizing multiple data sources in one place
    def __init__(
        self,
        volumes_root: DirectoryPath,  # folder in which each source data is located in subfolder
        gathering_place: DirectoryPath,
        link_folders_only: bool = False,
    ):
        self._name = self.__class__.__name__
        self.link_folders_only = link_folders_only
        self.volumes_root = pathlib.Path(volumes_root)
        self.gathering_place = pathlib.Path(gathering_place)
        # Enshure that required folders exist
        self.volumes_root.mkdir(parents=True, exist_ok=True)
        self.gathering_place.mkdir(parents=True, exist_ok=True)
        # Clear self.gathering_place folder before creating new symlinks
        print(f"{self._name}: clearing old links")
        self.prune()

    def _link_volume(self, volume: pathlib.Path) -> None:
        for child in volume.iterdir():
            if self.link_folders_only and (not child.is_dir()):
                continue
            link = self.gathering_place.joinpath(child.name)
            try:
                link.symlink_to(child, target_is_directory=True)
                print(f"{self._name}: link created: {link} -> {child}")
            except FileExistsError:
                pass

    def sync(self) -> None:
        """Synchronizing data between
        self.volumes_root folder and self.gathering_place folder"""
        print(f"{self._name}: synchronizing data")
        self.prune(only_broken=True)
        for volume in self.volumes_root.iterdir():
            self._link_volume(volume)

    def prune(self, only_broken: bool = False) -> None:
        """Remove symlinks from self.gathering_place folder
        If only_broken is True, remove only links that have no target"""
        for child in self.gathering_place.iterdir():
            remove = True
            if only_broken:
                # Using os package here because Path.readlink() method available
                # only for python >= 3.9
                remove = not os.path.exists(os.readlink(child))
            if child.is_symlink() and remove:
                child.unlink(missing_ok=True)
                print(f"{self._name}: link removed: {child} -> X")


class MultiDataGatherer:
    # Class to manage multiple DataGatherer apps
    def __init__(self):
        self._name = self.__class__.__name__
        # storege for names of all added apps for fast access
        self._apps = []

    def add_app(self, name: str, app: DataGatherer):
        if name in self._apps:
            print(f"{self._name}: app '{name}' already added")
            return
        self.__setattr__(name, app)
        self._apps.append(name)
        self.__getattribute__(name).sync()

    def remove_app(self, name: str):
        try:
            self.__getattribute__(name).prune()
            self.__delattr__(name)
            self._apps.remove(name)
        except AttributeError:
            print(f"{self._name}: app '{name}' is not found")

    def sync(self):
        for app in self._apps:
            self.__getattribute__(app).sync()

    def prune(self):
        for app in self._apps:
            self.__getattribute__(app).prune()
