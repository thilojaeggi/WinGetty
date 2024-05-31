
from distutils.version import LooseVersion

class Package:
    def to_dict(self):
        try:
            versions = sorted(
                self.versions, key=lambda v: LooseVersion(str(v))
            )
        except TypeError as e:
            # Handle the exception and log it or return an error response
            return {"error": f"Version sorting error: {str(e)}"}

        return {
            "id": self.id,
            "name": self.name,
            "versions": versions
        }
}
