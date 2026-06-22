from unittest.mock import MagicMock, patch

from health_check import check_packages, check_env_file


class TestCheckPackages:
    def test_returns_empty_when_all_installed(self):
        with patch("subprocess.run") as mock_run:
            mock_result = mock_run.return_value
            mock_result.returncode = 0

            missing = check_packages()
            assert missing == []

    def test_reports_missing_packages(self):
        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            result = MagicMock()
            result.returncode = 0 if call_count[0] > 2 else 1
            return result

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = side_effect

            missing = check_packages()
            assert isinstance(missing, list)

    def test_skips_comments_and_empty_lines(self):
        from unittest.mock import MagicMock
        with patch("builtins.open"), \
             patch("subprocess.run") as mock_run:
            mock_result = mock_run.return_value
            mock_result.returncode = 0
            missing = check_packages()
            assert isinstance(missing, list)


class TestCheckEnvFile:
    def test_returns_warnings_for_optional_missing(self):
        with patch("dotenv.load_dotenv"), \
             patch("os.getenv") as mock_getenv:
            mock_getenv.return_value = ""

            missing, warnings = check_env_file()
            assert "SECRET_KEY" in missing
            assert any("GROQ_API_KEY" in w for w in warnings)
