import unittest
from unittest.mock import patch

from fairy.installation import installer


class SetupModelsTests(unittest.TestCase):
    def test_model_manifest_contains_the_source_files(self):
        from fairy.paths import BRAIN_MODEL, OMNI_MODEL, OMNI_PROJECTOR
        self.assertEqual({entry[0] for entry in installer.OMNI_MODELS},
                         {BRAIN_MODEL, OMNI_MODEL, OMNI_PROJECTOR})
        self.assertTrue(all(len(entry[2]) == 64 for entry in installer.OMNI_MODELS))

    def test_both_model_selectors_use_dual_installer(self):
        with patch.object(installer, "install_dual_models") as install:
            self.assertEqual(installer.main(["--only", "models", "--check", "--verify-models"]), 0)
            install.assert_called_once_with(check=True, hashes=True)
        with patch.object(installer, "install_dual_models") as install:
            self.assertEqual(installer.main(["--only", "dual-models"]), 0)
            install.assert_called_once_with(check=False, hashes=False)

    def test_all_installs_only_current_sections(self):
        with patch.object(installer, "install_environment") as environment, \
             patch.object(installer, "install_llama") as llama, \
             patch.object(installer, "install_dual_models") as models:
            self.assertEqual(installer.main(["--yes"]), 0)
            environment.assert_called_once()
            llama.assert_called_once()
            models.assert_called_once_with(check=False, hashes=False)


if __name__ == "__main__":
    unittest.main()
